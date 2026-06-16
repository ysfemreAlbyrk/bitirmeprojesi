"""User library models"""
from pydantic import BaseModel
from typing import Optional


class LibraryUpdate(BaseModel):
    """Patch a book's state in the current user's library."""
    reading_status: Optional[str] = None  # not_started | reading | completed
    is_favorite: Optional[bool] = None
