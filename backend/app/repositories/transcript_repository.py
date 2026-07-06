import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Transcript


def get_by_video_id(db: Session, video_id: str) -> Optional[Transcript]:
    """Return transcript for the given video_id, or None."""
    stmt = select(Transcript).where(Transcript.video_id == video_id)
    return db.execute(stmt).scalar_one_or_none()


def get_by_id(db: Session, transcript_id: uuid.UUID) -> Optional[Transcript]:
    """Return transcript by primary key, or None."""
    return db.get(Transcript, transcript_id)


def list_all(db: Session, limit: int = 100) -> list[Transcript]:
    """Return transcripts ordered by created_at descending."""
    stmt = select(Transcript).order_by(Transcript.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars())


def create(db: Session, *, transcript: Transcript) -> Optional[Transcript]:
    """Persist a new Transcript; return None on duplicate video_id (race dedup).

    Concurrent requests for the same video_id may both pass the pre-check and
    race to insert. The second insert hits the unique constraint; we roll back,
    re-fetch the winner's row, and return it so the caller can emit a done event
    from the cached record instead of surfacing a raw DB error.
    """
    try:
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        return transcript
    except IntegrityError:
        db.rollback()
        return get_by_video_id(db, transcript.video_id)
