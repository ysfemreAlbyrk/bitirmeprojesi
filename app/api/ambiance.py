"""Ambiance data API endpoints"""
from fastapi import APIRouter, HTTPException, Depends

from app.core.database import TextChunkRepository
from app.core.dependencies import get_text_chunk_repository
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/ambiance", tags=["ambiance"])


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

    return {
        "chunk_id": chunk_id,
        "scene": chunk.get('scene'),
        "emotion": chunk.get('emotion'),
        "audio_url": chunk.get('audio_url'),
        "image_url": chunk.get('image_url'),
    }
