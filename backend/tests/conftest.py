"""Shared pytest fixtures for backend tests."""

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base, Transcript

TEST_DATABASE_URL = "postgresql+psycopg://ytapp:ytapp@localhost:5433/ytapp"

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Ensure all tables exist (idempotent — skips if already created by Alembic)."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db():
    """Provide a test DB session; truncate transcripts before/after each test."""
    session = TestingSession()
    session.execute(text("TRUNCATE TABLE transcripts RESTART IDENTITY CASCADE"))
    session.commit()
    try:
        yield session
    finally:
        session.execute(text("TRUNCATE TABLE transcripts RESTART IDENTITY CASCADE"))
        session.commit()
        session.close()


@pytest.fixture()
def client(db):
    """FastAPI TestClient with get_db overridden to use the test session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def collect_sse(response) -> list[dict]:
    """Read a streaming TestClient response and return a list of SSE event dicts."""
    events: list[dict] = []
    current: dict = {}
    for raw_line in response.iter_lines():
        line = raw_line if isinstance(raw_line, str) else raw_line.decode()
        if line.startswith("event: "):
            current["event"] = line[7:].strip()
        elif line.startswith("data: "):
            try:
                current["data"] = json.loads(line[6:].strip())
            except json.JSONDecodeError:
                current["data"] = line[6:].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


# ---------------------------------------------------------------------------
# Seed helper
# ---------------------------------------------------------------------------

def seed_transcript(db, **kwargs) -> Transcript:
    defaults = dict(
        video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ",
        title="Test Video",
        source="youtube_caption",
        language="en",
        content="This is test content.",
        duration_sec=212,
    )
    defaults.update(kwargs)
    t = Transcript(**defaults)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t
