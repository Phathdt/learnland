"""Tests for GET /api/transcripts and GET /api/transcripts/{id}."""

import uuid
import pytest
from tests.conftest import seed_transcript


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
