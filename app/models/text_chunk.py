"""Text chunk models"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TextChunk(BaseModel):
    id: str
    book_id: str
    chapter_id: str
    order: int
    text: str
    scene: Optional[str] = None
    emotion: Optional[str] = None
    sfx_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    word_count: int
    created_at: datetime
    analyzed: bool = False


class TextChunkCreate(BaseModel):
    book_id: str
    chapter_id: str
    order: int
    text: str
    word_count: int


class TextChunkUpdate(BaseModel):
    scene: Optional[str] = None
    emotion: Optional[str] = None
    sfx_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    analyzed: bool = False


class TextChunkResponse(BaseModel):
    id: str
    scene: Optional[str] = None
    emotion: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
