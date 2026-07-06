"""Tests for POST /api/transcribe SSE endpoint.

Services (youtube, transcriber) are monkeypatched so no network calls are made.
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import collect_sse, seed_transcript
from app.services.youtube import VideoInfo, YouTubeError


VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
VIDEO_ID = "dQw4w9WgXcQ"


def _make_info(has_caption: bool = True) -> VideoInfo:
    return VideoInfo(
        video_id=VIDEO_ID,
        title="Never Gonna Give You Up",
        duration=212,
        has_caption=has_caption,
        caption_langs=["en"] if has_caption else [],
    )


# ---------------------------------------------------------------------------
# Caption path
# ---------------------------------------------------------------------------

def test_transcribe_caption_path(client, db, monkeypatch):
    """When a caption is available, source=youtube_caption and whisper is NOT called."""
    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: _make_info(has_caption=True),
    )
    monkeypatch.setattr(
        "app.routers.transcribe.get_caption",
        lambda url: "Never gonna give you up never gonna let you down",
    )
    whisper_mock = MagicMock()
    monkeypatch.setattr("app.routers.transcribe.transcribe", whisper_mock)

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"No 'done' event. Got: {events}"
    data = done_events[0]["data"]
    assert data["source"] == "youtube_caption"
    assert "never gonna" in data["content"].lower()
    whisper_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Whisper path
# ---------------------------------------------------------------------------

def test_transcribe_whisper_path(client, db, monkeypatch, tmp_path):
    """When no caption, download audio + transcribe → source=whisper."""
    audio_file = tmp_path / "audio.m4a"
    audio_file.write_bytes(b"fake audio")

    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: _make_info(has_caption=False),
    )
    monkeypatch.setattr(
        "app.routers.transcribe.get_caption",
        lambda url: None,
    )
    monkeypatch.setattr(
        "app.routers.transcribe.download_audio",
        lambda url, out_dir: audio_file,
    )

    from app.services.transcriber import TranscribeResult

    def _fake_transcribe(path, on_progress=None):
        if on_progress:
            on_progress(50.0)
            on_progress(100.0)
        return TranscribeResult(text="Whispered content", language="en", duration=212.0)

    monkeypatch.setattr("app.routers.transcribe.transcribe", _fake_transcribe)

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"No 'done' event. Got: {events}"
    data = done_events[0]["data"]
    assert data["source"] == "whisper"
    assert "whispered" in data["content"].lower()

    # Progress events for transcribe stage should appear
    progress_events = [
        e for e in events
        if e.get("event") == "progress" and e["data"].get("stage") == "transcribe"
    ]
    assert progress_events


# ---------------------------------------------------------------------------
# Dedup / cache path
# ---------------------------------------------------------------------------

def test_transcribe_dedup_returns_cache(client, db, monkeypatch):
    """Submitting the same URL twice returns the cached transcript immediately."""
    seed_transcript(db, video_url=VIDEO_URL, video_id=VIDEO_ID)

    extract_mock = MagicMock()
    monkeypatch.setattr("app.routers.transcribe.extract_info", extract_mock)

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events
    assert done_events[0]["data"]["video_id"] == VIDEO_ID
    # No network call made
    extract_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

def test_transcribe_youtube_error(client, db, monkeypatch):
    """A YouTubeError from extract_info emits an SSE error event."""
    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: (_ for _ in ()).throw(YouTubeError("Video unavailable")),
    )

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events, f"Expected error event. Got: {events}"
    assert "unavailable" in error_events[0]["data"]["message"].lower()


def test_transcribe_invalid_url_returns_error(client, db):
    """A completely invalid URL returns an SSE error without crashing."""
    with client.stream("POST", "/api/transcribe", json={"url": "not-a-youtube-url"}) as resp:
        events = collect_sse(resp)

    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events
