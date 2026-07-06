"""Whisper transcriber: lazy-loaded faster-whisper model singleton."""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger(__name__)


class TranscribeError(Exception):
    """Raised when audio transcription fails."""


@dataclass
class TranscribeResult:
    text: str
    language: str
    duration: Optional[float]  # seconds


# ---------------------------------------------------------------------------
# Singleton model loader — double-checked locking
# Note: concurrent transcription is safe (WhisperModel is re-entrant for reads),
# but this app is single-user MVP scope — parallel transcriptions are not expected.
# ---------------------------------------------------------------------------

_model: Optional[WhisperModel] = None
_model_lock = threading.Lock()


def get_model() -> WhisperModel:
    """Return the cached WhisperModel, loading it on first call (thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # second check inside lock
                logger.info(
                    "Loading Whisper model '%s' (cpu / int8) ...",
                    settings.whisper_model,
                )
                _model = WhisperModel(
                    settings.whisper_model,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("Whisper model loaded.")
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe(
    audio_path: str | Path,
    on_progress: Optional[Callable[[float], None]] = None,
) -> TranscribeResult:
    """Transcribe an audio file and return text + metadata.

    Args:
        audio_path: Path to the audio file (m4a, wav, mp3, …).
        on_progress: Optional callback called with progress percentage (0–100).

    Raises:
        TranscribeError: If the file is missing, empty, or unreadable.
    """
    path = Path(audio_path)
    if not path.exists():
        raise TranscribeError(f"Audio file not found: {path}")
    if path.stat().st_size == 0:
        raise TranscribeError(f"Audio file is empty: {path}")

    model = get_model()

    try:
        segments_gen, info = model.transcribe(str(path), beam_size=5)
    except Exception as exc:
        raise TranscribeError(f"Whisper failed to process audio: {exc}") from exc

    total_duration: float = info.duration or 0.0
    parts: list[str] = []

    try:
        for segment in segments_gen:
            parts.append(segment.text.strip())
            if on_progress and total_duration > 0:
                pct = min(100.0, (segment.end / total_duration) * 100.0)
                on_progress(pct)
    except Exception as exc:
        raise TranscribeError(f"Error reading transcription segments: {exc}") from exc

    if on_progress:
        on_progress(100.0)

    text = " ".join(p for p in parts if p)
    if not text:
        raise TranscribeError("Transcription produced empty output.")

    return TranscribeResult(
        text=text,
        language=info.language or "unknown",
        duration=total_duration if total_duration > 0 else None,
    )
