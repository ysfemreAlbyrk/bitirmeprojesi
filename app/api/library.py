"""User library (reading status + favorites) API endpoints.

Powers the Library tabs: Reading / Completed / Saved.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query

from app.core.database import UserLibraryRepository, BookRepository, Database
from app.core.dependencies import (
    get_user_library_repository,
    get_book_repository,
    get_database,
)
from app.core.auth import get_current_user_id
from app.models.library import LibraryUpdate

router = APIRouter(prefix="/library", tags=["library"])

_VALID_STATUS = ('not_started', 'reading', 'completed')


def _compute_progress(db: Database, user_id: str) -> dict:
    """Per-book reading progress: book_id -> {progress 0..1, total_chunks}.

    Progress is chunk-based: position of the current chunk over the total
    number of chunks in the book.
    """
    rows = db.client.table('reading_progress').select(
        'book_id, current_chunk_id').eq('user_id', user_id).execute().data or []
    current_by_book = {
        r['book_id']: r['current_chunk_id']
        for r in rows if r.get('current_chunk_id')
    }

    result: dict = {}
    # Orders of the current chunks (one query).
    chunk_ids = list(current_by_book.values())
    order_by_chunk: dict = {}
    if chunk_ids:
        crows = db.client.table('text_chunks').select(
            'id, order, book_id').in_('id', chunk_ids).execute().data or []
        order_by_chunk = {c['id']: (c.get('order') or 0) for c in crows}

    for book_id, chunk_id in current_by_book.items():
        total = db.client.table('text_chunks').select(
            'id', count='exact', head=True).eq('book_id', book_id).execute().count or 0
        order = order_by_chunk.get(chunk_id, 0)
        progress = ((order + 1) / total) if total > 0 else 0.0
        result[book_id] = {
            "progress": round(min(progress, 1.0), 3),
            "total_chunks": total,
        }
    return result


def _flatten(entry: dict, progress_map: dict) -> dict:
    """Merge the joined book record with the user's library state + progress."""
    book = entry.get('books') or {}
    prog = progress_map.get(book.get('id'), {})
    return {
        **book,
        "reading_status": entry.get('reading_status'),
        "is_favorite": entry.get('is_favorite'),
        "added_at": entry.get('added_at'),
        "progress": prog.get('progress', 0.0),
        "total_chunks": prog.get('total_chunks', 0),
    }


@router.get("")
async def list_library(
    status: Optional[str] = Query(None, description="reading | completed | saved"),
    lib_repo: UserLibraryRepository = Depends(get_user_library_repository),
    db: Database = Depends(get_database),
    user_id: str = Depends(get_current_user_id),
):
    """List the user's library, optionally filtered to a tab."""
    entries = lib_repo.list_for_user(user_id)
    if status == 'reading':
        entries = [e for e in entries
                   if e.get('reading_status') in ('not_started', 'reading')]
    elif status == 'completed':
        entries = [e for e in entries if e.get('reading_status') == 'completed']
    elif status in ('saved', 'favorite'):
        entries = [e for e in entries if e.get('is_favorite')]

    progress_map = _compute_progress(db, user_id)
    return [_flatten(e, progress_map) for e in entries if e.get('books')]


@router.put("/{book_id}")
async def set_library_state(
    book_id: str,
    body: LibraryUpdate,
    lib_repo: UserLibraryRepository = Depends(get_user_library_repository),
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Add or update a book in the user's library (status + favorite)."""
    try:
        uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book_repo.get_by_id(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    if body.reading_status is not None and body.reading_status not in _VALID_STATUS:
        raise HTTPException(status_code=400, detail="Invalid reading_status")

    return lib_repo.set_state(user_id, book_id, body.reading_status, body.is_favorite)


@router.delete("/{book_id}")
async def remove_from_library(
    book_id: str,
    lib_repo: UserLibraryRepository = Depends(get_user_library_repository),
    user_id: str = Depends(get_current_user_id),
):
    """Remove a book from the user's library."""
    if not lib_repo.remove(user_id, book_id):
        raise HTTPException(status_code=404, detail="Not in library")
    return {"message": "Removed from library"}
