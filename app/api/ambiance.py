"""Ambiance data API endpoints"""
import uuid

from fastapi import APIRouter, HTTPException, Depends

from app.core.database import TextChunkRepository, BookRepository
from app.core.dependencies import get_text_chunk_repository, get_book_repository
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/ambiance", tags=["ambiance"])


def _ambiance_of(chunk: dict) -> dict:
    return {
        "chunk_id": chunk["id"],
        "scene": chunk.get("scene"),
        "emotion": chunk.get("emotion"),
        "audio_url": chunk.get("audio_url"),
        "image_url": chunk.get("image_url"),
    }


@router.get("/chunk/{chunk_id}")
async def get_chunk_ambiance(
    chunk_id: str,
    chunk_repo: TextChunkRepository = Depends(get_text_chunk_repository),
    _: str = Depends(get_current_user_id),
):
    """Get ambiance data (audio URL, image URL, scene info) for a text chunk."""
    chunk = chunk_repo.get_by_id(chunk_id)

    if not chunk:
        raise HTTPException(status_code=404, detail="Text chunk not found")

    return _ambiance_of({**chunk, "id": chunk_id})


@router.get("/book/{book_id}")
async def get_book_ambiance(
    book_id: str,
    chunk_repo: TextChunkRepository = Depends(get_text_chunk_repository),
    book_repo: BookRepository = Depends(get_book_repository),
    user_id: str = Depends(get_current_user_id),
):
    """All chunks' ambiance for a book in one call (avoids per-chunk N+1)."""
    try:
        uuid.UUID(book_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Book not found")

    book = book_repo.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # NOTE: access is owner-only for now; broadened to public/library in the
    # discovery phase once those columns exist.
    if book.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Bu kitaba erişim izniniz yok")

    chunks = chunk_repo.get_by_book(book_id) or []
    return [_ambiance_of(c) for c in chunks]
