"""Chapter-related models"""
from pydantic import BaseModel
from datetime import datetime


class Chapter(BaseModel):
    id: str
    book_id: str
    chapter_number: int
    title: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    created_at: datetime


class ChapterCreate(BaseModel):
    book_id: str
    chapter_number: int
    title: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
