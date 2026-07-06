"""YouTube service: extract metadata, captions, and audio via yt-dlp."""

import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yt_dlp

from app.services.url_utils import InvalidYouTubeURLError, canonical_url, extract_video_id

logger = logging.getLogger(__name__)


class YouTubeError(Exception):
    """Raised when yt-dlp cannot access or process a YouTube video."""


@dataclass
class VideoInfo:
    video_id: str
    title: str
    duration: Optional[int]  # seconds
    has_caption: bool
    caption_langs: list[str] = field(default_factory=list)


# --- Internal helpers --------------------------------------------------------

def _make_quiet_opts(extra: Optional[dict] = None) -> dict:
    opts: dict = {"quiet": True, "no_warnings": True, "skip_download": True}
    if extra:
        opts.update(extra)
    return opts


def _raise_on_ydl_error(url: str, exc: Exception) -> None:
    """Log full yt-dlp detail server-side; raise a sanitized client message."""
    logger.error("yt-dlp error for %r: %s", url, exc)
    msg = str(exc).lower()
    if any(kw in msg for kw in ("private", "members only", "sign in")):
        raise YouTubeError("Video is private or requires login.") from exc
    if any(kw in msg for kw in ("not available", "unavailable", "no video")):
        raise YouTubeError("Video is unavailable or region-locked.") from exc
    raise YouTubeError("Could not process the video. Please check the URL and try again.") from exc


def _strip_vtt_markup(text: str) -> str:
    """Remove WebVTT timestamps and tags, return deduplicated plain text."""
    lines: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


# --- Public API --------------------------------------------------------------

def extract_info(url: str) -> VideoInfo:
    """Return metadata without downloading. Raises YouTubeError on failure."""
    try:
        video_id = extract_video_id(url)
    except InvalidYouTubeURLError as exc:
        raise YouTubeError(str(exc)) from exc

    # Always pass canonical URL to yt-dlp — never the raw user string (SSRF)
    safe_url = canonical_url(video_id)
    try:
        with yt_dlp.YoutubeDL(_make_quiet_opts()) as ydl:
            info = ydl.extract_info(safe_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        _raise_on_ydl_error(safe_url, exc)

    video_id = info.get("id", video_id)
    title: str = info.get("title") or "Untitled"
    duration: Optional[int] = info.get("duration")
    manual_subs: dict = info.get("subtitles") or {}
    auto_subs: dict = info.get("automatic_captions") or {}
    all_langs = list(set(list(manual_subs.keys()) + list(auto_subs.keys())))

    return VideoInfo(
        video_id=video_id,
        title=title,
        duration=int(duration) if duration else None,
        has_caption=bool(manual_subs or auto_subs),
        caption_langs=sorted(all_langs),
    )


def get_caption(url: str, lang: str = "en") -> Optional[str]:
    """Fetch caption text for a video, returning None if unavailable."""
    video_id = extract_video_id(url)
    safe_url = canonical_url(video_id)

    try:
        with yt_dlp.YoutubeDL(_make_quiet_opts()) as ydl:
            info = ydl.extract_info(safe_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        _raise_on_ydl_error(safe_url, exc)

    manual_subs: dict = info.get("subtitles") or {}
    auto_subs: dict = info.get("automatic_captions") or {}
    chosen_subs: Optional[dict] = None
    chosen_lang: Optional[str] = None

    for subs in (manual_subs, auto_subs):
        if lang in subs:
            chosen_subs, chosen_lang = subs, lang
            break
        for k in subs:
            if k.startswith(lang):
                chosen_subs, chosen_lang = subs, k
                break
        if chosen_subs:
            break

    if not chosen_subs:
        for subs in (manual_subs, auto_subs):
            if subs:
                chosen_lang = next(iter(subs))
                chosen_subs = subs
                break

    if not chosen_subs or not chosen_lang:
        return None

    sub_entries: list[dict] = chosen_subs.get(chosen_lang, [])
    sub_url: Optional[str] = next(
        (e.get("url") for e in sub_entries if e.get("ext") in ("vtt", "json3")),
        sub_entries[0].get("url") if sub_entries else None,
    )
    if not sub_url:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        sub_opts = _make_quiet_opts({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [chosen_lang],
            "subtitlesformat": "vtt",
            "outtmpl": os.path.join(tmp, "sub"),
        })
        try:
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                ydl.download([safe_url])
        except yt_dlp.utils.DownloadError:
            pass  # subtitle write may trigger this; check files regardless

        for fname in os.listdir(tmp):
            if fname.endswith((".vtt", ".json3", ".srt")):
                text = Path(os.path.join(tmp, fname)).read_text(encoding="utf-8")
                return _strip_vtt_markup(text) or None

    return None


def download_audio(url: str, out_dir: str) -> Path:
    """Download best audio into out_dir and return the file path.

    Caller is responsible for providing and cleaning up out_dir.
    Using a caller-provided directory ensures cleanup even on mid-download disconnect.
    """
    video_id = extract_video_id(url)
    safe_url = canonical_url(video_id)
    out_template = os.path.join(out_dir, "audio.%(ext)s")

    audio_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
            "preferredquality": "128",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            ydl.download([safe_url])
    except yt_dlp.utils.DownloadError as exc:
        _raise_on_ydl_error(safe_url, exc)

    for fname in os.listdir(out_dir):
        return Path(os.path.join(out_dir, fname))

    raise YouTubeError("Audio download produced no output file.")
