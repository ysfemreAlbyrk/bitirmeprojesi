"""Reading session and progress models"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ReadingSession(BaseModel):
    id: str
    user_id: str
    book_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    immersive_mode_seconds: Optional[int] = None


class ReadingProgress(BaseModel):
    id: str
    user_id: str
    book_id: str
    current_chunk_id: str
    chapter_number: int
    offset: int
    last_updated: datetime


class Bookmark(BaseModel):
    id: str
    user_id: str
    book_id: str
    chunk_id: str
    chapter_number: int
    offset: int
    note: Optional[str] = None
    created_at: datetime


class ReadingSessionCreate(BaseModel):
    user_id: Optional[str] = None
    book_id: str


class ReadingSessionUpdate(BaseModel):
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    immersive_mode_seconds: Optional[int] = None


class BookmarkCreate(BaseModel):
    user_id: Optional[str] = None
    book_id: str
    chunk_id: str
    chapter_number: int
    offset: int
    note: Optional[str] = None
