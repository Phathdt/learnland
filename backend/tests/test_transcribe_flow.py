"""Tests for POST /api/transcribe SSE endpoint.

Services (youtube, transcriber) are monkeypatched so no network calls are made.
"""

import copy

import pytest
from unittest.mock import MagicMock, patch

from tests.conftest import collect_sse, seed_transcript
from app.services.youtube import VideoInfo, YouTubeError, Caption
from app.services.ipa import IpaError, IpaResult


VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
VIDEO_ID = "dQw4w9WgXcQ"

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 3.5, "text": "Never gonna give you up"},
    {"start": 3.5, "end": 7.0, "text": "Never gonna let you down"},
]


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
        lambda url: Caption(
            text="Never gonna give you up never gonna let you down",
            segments=copy.deepcopy(SAMPLE_SEGMENTS),
            language="en",
        ),
    )
    whisper_mock = MagicMock()
    monkeypatch.setattr("app.routers.transcribe.transcribe", whisper_mock)
    # IPA is best-effort; patch it out to avoid needing a real API key in tests
    monkeypatch.setattr(
        "app.routers.transcribe.generate_ipa",
        lambda texts: IpaResult(ipa=["" for _ in texts]),
    )

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"No 'done' event. Got: {events}"
    data = done_events[0]["data"]
    assert data["source"] == "youtube_caption"
    assert "never gonna" in data["content"].lower()
    whisper_mock.assert_not_called()

    # Segments must be present and non-empty with correct fields
    assert data["segments"], "Expected non-empty segments in done payload"
    assert len(data["segments"]) == len(SAMPLE_SEGMENTS)
    first = data["segments"][0]
    assert "start" in first and "end" in first and "text" in first
    assert isinstance(first["start"], float)
    assert isinstance(first["end"], float)


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

    whisper_segments = [
        {"start": 0.0, "end": 4.2, "text": "Whispered content"},
        {"start": 4.2, "end": 8.1, "text": "More whispered text"},
    ]

    def _fake_transcribe(path, on_progress=None):
        if on_progress:
            on_progress(50.0)
            on_progress(100.0)
        return TranscribeResult(
            text="Whispered content More whispered text",
            language="en",
            duration=212.0,
            segments=whisper_segments,
        )

    monkeypatch.setattr("app.routers.transcribe.transcribe", _fake_transcribe)
    monkeypatch.setattr(
        "app.routers.transcribe.generate_ipa",
        lambda texts: IpaResult(ipa=["" for _ in texts]),
    )

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"No 'done' event. Got: {events}"
    data = done_events[0]["data"]
    assert data["source"] == "whisper"
    assert "whispered" in data["content"].lower()

    # Segments must be present for whisper path too
    assert data["segments"], "Expected non-empty segments in whisper done payload"
    assert len(data["segments"]) == len(whisper_segments)
    first = data["segments"][0]
    assert first["start"] == 0.0
    assert first["end"] == 4.2
    assert "whispered" in first["text"].lower()

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


# ---------------------------------------------------------------------------
# IPA integration — Phase 2
# ---------------------------------------------------------------------------

def test_transcribe_ipa_attached_on_success(client, db, monkeypatch):
    """When generate_ipa succeeds, each segment carries an 'ipa' string."""
    sample_ipa = ["ˈnɛvər ˈɡɒnə ɡɪv juː ʌp", "ˈnɛvər ˈɡɒnə lɛt juː daʊn"]

    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: _make_info(has_caption=True),
    )
    monkeypatch.setattr(
        "app.routers.transcribe.get_caption",
        lambda url: Caption(
            text="Never gonna give you up never gonna let you down",
            segments=copy.deepcopy(SAMPLE_SEGMENTS),
            language="en",
        ),
    )
    monkeypatch.setattr("app.routers.transcribe.transcribe", MagicMock())
    monkeypatch.setattr(
        "app.routers.transcribe.generate_ipa",
        lambda texts: IpaResult(ipa=sample_ipa),
    )

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"No 'done' event. Got: {events}"
    segments = done_events[0]["data"]["segments"]
    assert segments, "Expected segments in done payload"
    assert segments[0].get("ipa") == sample_ipa[0]
    assert segments[1].get("ipa") == sample_ipa[1]

    # IPA progress stage emitted
    ipa_progress = [
        e for e in events
        if e.get("event") == "progress" and e["data"].get("stage") == "ipa"
    ]
    assert ipa_progress, "Expected at least one 'ipa' progress event"


def test_transcribe_ipa_failure_still_saves(client, db, monkeypatch):
    """When generate_ipa raises IpaError, transcript saves without ipa keys; no error event."""
    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: _make_info(has_caption=True),
    )
    monkeypatch.setattr(
        "app.routers.transcribe.get_caption",
        lambda url: Caption(
            text="Never gonna give you up never gonna let you down",
            segments=copy.deepcopy(SAMPLE_SEGMENTS),
            language="en",
        ),
    )
    monkeypatch.setattr("app.routers.transcribe.transcribe", MagicMock())
    monkeypatch.setattr(
        "app.routers.transcribe.generate_ipa",
        lambda texts: (_ for _ in ()).throw(IpaError("no key")),
    )

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    # Must still produce a 'done' event — not an 'error'
    done_events = [e for e in events if e.get("event") == "done"]
    error_events = [e for e in events if e.get("event") == "error"]
    assert done_events, f"Expected 'done' even when IPA fails. Got: {events}"
    assert not error_events, f"IPA failure must not emit error event. Got: {error_events}"

    # Segments present but without 'ipa' keys
    segments = done_events[0]["data"]["segments"]
    assert segments, "Expected segments saved even without IPA"
    for seg in segments:
        assert "ipa" not in seg or seg["ipa"] is None, (
            "Segment should not carry 'ipa' when IPA generation failed"
        )


def test_transcribe_ipa_skipped_for_non_english(client, db, monkeypatch):
    """Non-English language skips IPA; transcript saves normally."""
    ipa_mock = MagicMock()
    monkeypatch.setattr("app.routers.transcribe.generate_ipa", ipa_mock)
    monkeypatch.setattr(
        "app.routers.transcribe.extract_info",
        lambda url: _make_info(has_caption=True),
    )
    monkeypatch.setattr(
        "app.routers.transcribe.get_caption",
        lambda url: Caption(
            text="Xin chào thế giới",
            segments=[{"start": 0.0, "end": 2.0, "text": "Xin chào thế giới"}],
            language="vi",
        ),
    )
    monkeypatch.setattr("app.routers.transcribe.transcribe", MagicMock())

    with client.stream("POST", "/api/transcribe", json={"url": VIDEO_URL}) as resp:
        events = collect_sse(resp)

    done_events = [e for e in events if e.get("event") == "done"]
    assert done_events, f"Expected 'done' event. Got: {events}"
    ipa_mock.assert_not_called()

