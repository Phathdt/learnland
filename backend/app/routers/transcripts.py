"""Read-only endpoints: GET /api/transcripts and GET /api/transcripts/{id}."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import transcript_repository as repo
from app.schemas import TranscriptOut

router = APIRouter(prefix="/api/transcripts")


@router.get("", response_model=list[TranscriptOut])
def list_transcripts(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[TranscriptOut]:
    """Return transcripts ordered by created_at descending."""
    records = repo.list_all(db, limit=limit)
    return [TranscriptOut.model_validate(r) for r in records]


@router.get("/{transcript_id}", response_model=TranscriptOut)
def get_transcript(
    transcript_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TranscriptOut:
    """Return a single transcript by UUID, or 404."""
    record = repo.get_by_id(db, transcript_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return TranscriptOut.model_validate(record)
