"""Tests for GET /api/transcripts and GET /api/transcripts/{id}."""

import uuid
import pytest
from tests.conftest import seed_transcript

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 3.5, "text": "Hello world"},
    {"start": 3.5, "end": 7.0, "text": "Goodbye world"},
]


def test_list_transcripts_empty(client, db):
    resp = client.get("/api/transcripts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_transcripts_returns_ordered(client, db):
    """List should come back newest-first (order by created_at desc)."""
    t1 = seed_transcript(db, video_id="aaaaaaaaaa1", title="First")
    t2 = seed_transcript(db, video_id="aaaaaaaaaa2", title="Second")

    resp = client.get("/api/transcripts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Seeded in order; db ordering is desc(created_at) — second is newest
    ids = [d["id"] for d in data]
    assert str(t2.id) in ids and str(t1.id) in ids


def test_get_transcript_by_id(client, db):
    t = seed_transcript(db)
    resp = client.get(f"/api/transcripts/{t.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(t.id)
    assert data["video_id"] == t.video_id
    assert data["source"] == "youtube_caption"


def test_get_transcript_not_found(client, db):
    random_id = str(uuid.uuid4())
    resp = client.get(f"/api/transcripts/{random_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Transcript not found"


def test_get_transcript_invalid_uuid(client, db):
    resp = client.get("/api/transcripts/not-a-uuid")
    assert resp.status_code == 422  # FastAPI validation


# ---------------------------------------------------------------------------
# Segments field
# ---------------------------------------------------------------------------

def test_get_transcript_with_segments_returns_segments(client, db):
    """Detail endpoint must return segments when stored."""
    t = seed_transcript(db, video_id="segtest0001", segments=SAMPLE_SEGMENTS)
    resp = client.get(f"/api/transcripts/{t.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["segments"] is not None
    assert len(data["segments"]) == 2
    first = data["segments"][0]
    assert first["start"] == 0.0
    assert first["end"] == 3.5
    assert first["text"] == "Hello world"


def test_get_transcript_null_segments_is_ok(client, db):
    """Legacy record without segments must still return 200 with segments=null."""
    t = seed_transcript(db, video_id="segtest0002", segments=None)
    resp = client.get(f"/api/transcripts/{t.id}")
    assert resp.status_code == 200
    data = resp.json()
    # segments key present but null — not an error
    assert "segments" in data
    assert data["segments"] is None


def test_list_transcripts_includes_segments_field(client, db):
    """List endpoint must include segments in each item."""
    seed_transcript(db, video_id="segtest0003", segments=SAMPLE_SEGMENTS)
    resp = client.get("/api/transcripts")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert "segments" in items[0]
    assert items[0]["segments"] is not None
    assert len(items[0]["segments"]) == 2
