"""SSE endpoint: POST /api/transcribe — orchestrate caption→whisper→save."""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transcript
from app.repositories import transcript_repository as repo
from app.schemas import TranscribeRequest, TranscriptOut
from app.services.url_utils import InvalidYouTubeURLError, extract_video_id
from app.services.youtube import YouTubeError, download_audio, extract_info, get_caption
from app.services.transcriber import TranscribeError, transcribe
from app.services.ipa import generate_ipa

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _transcribe_stream(url: str, db: Session) -> AsyncGenerator[str, None]:
    # Pre-create temp dir before any executor call so `finally` always cleans up
    # even if the client disconnects mid-download (M1).
    audio_dir: Optional[str] = tempfile.mkdtemp(prefix="ytapp_audio_")

    try:
        try:
            video_id = extract_video_id(url)
        except InvalidYouTubeURLError as exc:
            yield _sse("error", {"message": str(exc)})
            return

        # Dedup: return cached result immediately
        existing = repo.get_by_video_id(db, video_id)
        if existing:
            yield _sse("done", TranscriptOut.model_validate(existing).model_dump(mode="json"))
            return

        yield _sse("progress", {"stage": "caption_check", "percent": 0})
        loop = asyncio.get_running_loop()

        try:
            info = await loop.run_in_executor(None, extract_info, url)
        except YouTubeError as exc:
            logger.error("extract_info failed for video %r: %s", video_id, exc)
            yield _sse("error", {"message": str(exc)})
            return

        content: Optional[str] = None
        segments: Optional[list] = None
        source: str
        language: Optional[str] = None

        if info.has_caption:
            try:
                caption = await loop.run_in_executor(None, get_caption, url)
                if caption and caption.text.strip():
                    content = caption.text.strip()
                    segments = caption.segments
                    source = "youtube_caption"
                    language = caption.language  # use resolved lang, not alphabetical sort
            except YouTubeError:
                content = None  # fall through to whisper

        if content is None:
            yield _sse("progress", {"stage": "download", "percent": 0})
            try:
                # Pass pre-created dir so finally block always has it (M1)
                audio_path: Path = await loop.run_in_executor(
                    None, download_audio, url, audio_dir
                )
            except YouTubeError as exc:
                logger.error("download_audio failed for video %r: %s", video_id, exc)
                yield _sse("error", {"message": str(exc)})
                return

            yield _sse("progress", {"stage": "transcribe", "percent": 0})

            progress_queue: asyncio.Queue[float] = asyncio.Queue()

            def _on_progress(pct: float) -> None:
                # Loop captured here is safe to call from a worker thread
                loop.call_soon_threadsafe(progress_queue.put_nowait, pct)

            transcribe_future = loop.run_in_executor(
                None, transcribe, audio_path, _on_progress
            )

            while not transcribe_future.done():
                try:
                    pct = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield _sse("progress", {"stage": "transcribe", "percent": round(pct, 1)})
                except asyncio.TimeoutError:
                    pass

            while not progress_queue.empty():
                pct = progress_queue.get_nowait()
                yield _sse("progress", {"stage": "transcribe", "percent": round(pct, 1)})

            try:
                result = await transcribe_future
            except TranscribeError as exc:
                logger.error("transcribe failed for video %r: %s", video_id, exc)
                yield _sse("error", {"message": "Transcription failed. Please try again."})
                return

            content = result.text
            segments = result.segments
            source = "whisper"
            language = result.language

        # IPA: best-effort phonetic transcription for English segments only.
        # Any failure is swallowed — transcript still saves without IPA.
        if segments and language and language.lower().startswith("en"):
            try:
                yield _sse("progress", {"stage": "ipa", "percent": 0})
                texts = [s["text"] for s in segments]
                ipa_result = await loop.run_in_executor(None, generate_ipa, texts)
                for seg, ipa in zip(segments, ipa_result.ipa):
                    seg["ipa"] = ipa
                yield _sse("progress", {"stage": "ipa", "percent": 100})
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "IPA generation skipped for video %r: %s",
                    video_id,
                    type(exc).__name__,
                )

        saved = repo.create(db, transcript=Transcript(
            video_url=url,
            video_id=video_id,
            title=info.title,
            source=source,
            language=language,
            content=content,
            segments=segments,
            duration_sec=info.duration,
        ))
        # saved is None only on a race-dedup IntegrityError — re-fetch the winner row
        if saved is None:
            saved = repo.get_by_video_id(db, video_id)
        yield _sse("done", TranscriptOut.model_validate(saved).model_dump(mode="json"))

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in transcribe stream for %r: %s", url, exc)
        yield _sse("error", {"message": "An unexpected error occurred. Please try again."})

    finally:
        if audio_dir and os.path.isdir(audio_dir):
            shutil.rmtree(audio_dir, ignore_errors=True)


@router.post("/api/transcribe")
async def transcribe_endpoint(
    body: TranscribeRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream transcription progress via Server-Sent Events."""
    return StreamingResponse(
        _transcribe_stream(body.url, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
