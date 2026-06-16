"""Discovery (Home) endpoints — public book catalog.

Surfaces books flagged `is_public = true`. Marking books public is an admin /
curation concern handled elsewhere.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.database import BookRepository
from app.core.dependencies import get_book_repository
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _by_read_count(books: list) -> list:
    return sorted(books, key=lambda b: b.get('read_count') or 0, reverse=True)


def _by_upload(books: list) -> list:
    return sorted(books, key=lambda b: b.get('upload_date') or '', reverse=True)


@router.get("/categories")
async def list_categories(
    book_repo: BookRepository = Depends(get_book_repository),
    _: str = Depends(get_current_user_id),
):
    """Distinct genres across the public catalog (for the home filter chips)."""
    return {"categories": book_repo.get_public_categories()}


@router.get("/featured")
async def get_featured(
    book_repo: BookRepository = Depends(get_book_repository),
    _: str = Depends(get_current_user_id),
):
    """The featured book for the home hero (most-read public book)."""
    books = book_repo.get_public(limit=50)
    featured = _by_read_count(books)[0] if books else None
    return {"book": featured}


@router.get("/sections")
async def get_sections(
    book_repo: BookRepository = Depends(get_book_repository),
    _: str = Depends(get_current_user_id),
):
    """Curated home carousels in one call (avoids multiple round-trips)."""
    books = book_repo.get_public(limit=100)
    return {
        "sections": [
            {"key": "popular", "title": "Popüler", "books": _by_read_count(books)[:12]},
            {"key": "new", "title": "Yeni Eklenenler", "books": _by_upload(books)[:12]},
        ]
    }


@router.get("/books")
async def list_public_books(
    category: Optional[str] = Query(None),
    sort: str = Query('popular', description="popular | new"),
    limit: int = Query(40, ge=1, le=100),
    book_repo: BookRepository = Depends(get_book_repository),
    _: str = Depends(get_current_user_id),
):
    """Filterable public catalog for the discover grid / category chips."""
    books = book_repo.get_public(category=category, limit=limit)
    ordered = _by_upload(books) if sort == 'new' else _by_read_count(books)
    return ordered
