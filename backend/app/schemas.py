import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class TranscribeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url must not be empty")
        return v


class Segment(BaseModel):
    """A single time-coded transcript cue for shadowing/karaoke playback."""

    start: float  # seconds
    end: float    # seconds
    text: str


class TranscriptOut(BaseModel):
    id: uuid.UUID
    video_url: str
    video_id: str
    title: Optional[str]
    source: str
    language: Optional[str]
    content: str
    segments: Optional[list[Segment]] = None
    duration_sec: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
