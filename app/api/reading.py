"""Reading progress and session API endpoints"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models.reading import ReadingProgress, Bookmark, BookmarkCreate
from app.core.database import Database, ReadingProgressRepository, BookRepository, TextChunkRepository
from app.core.dependencies import get_database, get_reading_progress_repository, get_book_repository, get_text_chunk_repository
from app.utils.pagination import PaginatedResponse, PaginationParams, paginate

router = APIRouter(prefix="/reading", tags=["reading"])


@router.get("/progress/{user_id}/{book_id}")
async def get_reading_progress(
    user_id: str,
    book_id: str,
    progress_repo: ReadingProgressRepository = Depends(lambda: ReadingProgressRepository())
):
    """
    Get reading progress for a user-book pair.
    """
    progress = progress_repo.get_progress(user_id, book_id)
    
    if not progress:
        return {
            "user_id": user_id,
            "book_id": book_id,
            "current_chunk_id": None,
            "chapter_number": 0,
            "offset": 0
        }
    
    return progress


@router.post("/progress")
async def save_reading_progress(
    user_id: str,
    book_id: str,
    current_chunk_id: str,
    chapter_number: int,
    offset: int,
    progress_repo: ReadingProgressRepository = Depends(lambda: ReadingProgressRepository())
):
    """
    Save reading progress for a user-book pair.
    """
    progress_data = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'book_id': book_id,
        'current_chunk_id': current_chunk_id,
        'chapter_number': chapter_number,
        'offset': offset
    }
    
    progress = progress_repo.upsert(progress_data)
    return progress


@router.post("/bookmarks")
async def create_bookmark(
    bookmark: BookmarkCreate,
    db: Database = Depends(get_database)
):
    """
    Create a bookmark.
    """
    bookmark_data = bookmark.model_dump()
    bookmark_data['id'] = str(uuid.uuid4())
    bookmark_data['created_at'] = datetime.now().isoformat()
    
    response = db.client.table('bookmarks').insert(bookmark_data).execute()
    
    if response.data:
        return response.data[0]
    else:
        raise HTTPException(status_code=500, detail="Failed to create bookmark")


@router.get("/bookmarks/{user_id}/{book_id}", response_model=PaginatedResponse)
async def list_bookmarks(
    user_id: str,
    book_id: str,
    pagination: PaginationParams = Depends(),
    db: Database = Depends(get_database)
):
    """
    List all bookmarks for a user-book pair with pagination.
    """
    response = db.client.table('bookmarks').select('*').eq('user_id', user_id).eq('book_id', book_id).execute()
    all_bookmarks = response.data
    total = len(all_bookmarks)
    
    # Apply pagination
    paginated_items = all_bookmarks[pagination.offset:pagination.offset + pagination.page_size]
    
    return paginate(
        items=paginated_items,
        total=total,
        params=pagination
    )


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str,
    db: Database = Depends(get_database)
):
    """
    Delete a bookmark.
    """
    response = db.client.table('bookmarks').delete().eq('id', bookmark_id).execute()
    
    if response.data:
        return {"message": "Bookmark deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Bookmark not found")
