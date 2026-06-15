"""Reading progress and session API endpoints"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.models.reading import ReadingProgress, Bookmark, BookmarkCreate, ReadingSessionCreate, ReadingSessionUpdate
from app.core.database import Database, ReadingProgressRepository, BookRepository, TextChunkRepository
from app.core.dependencies import get_database, get_reading_progress_repository, get_book_repository, get_text_chunk_repository
from app.core.auth import get_current_user_id
from app.utils.pagination import PaginatedResponse, PaginationParams, paginate

router = APIRouter(prefix="/reading", tags=["reading"])


@router.get("/progress/{book_id}")
@router.post("/sessions")
async def create_reading_session(
    session: ReadingSessionCreate,
    db: Database = Depends(get_database)
):
    """Start a new reading session."""
    session_data = session.model_dump()
    session_data['id'] = str(uuid.uuid4())
    response = db.client.table('reading_sessions').insert(session_data).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to create reading session")


@router.put("/sessions/{session_id}")
async def update_reading_session(
    session_id: str,
    update: ReadingSessionUpdate,
    db: Database = Depends(get_database)
):
    """End or update a reading session."""
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = db.client.table('reading_sessions').update(update_data).eq('id', session_id).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=404, detail="Reading session not found")


@router.get("/sessions/{user_id}")
async def list_reading_sessions(
    user_id: str,
    db: Database = Depends(get_database)
):
    """List all reading sessions for a user."""
    response = db.client.table('reading_sessions').select('*').eq('user_id', user_id).order('started_at', desc=True).execute()
    return {"sessions": response.data or []}


@router.get("/progress/{user_id}/{book_id}")
async def get_reading_progress(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    progress_repo: ReadingProgressRepository = Depends(get_reading_progress_repository),
):
    """Get reading progress for the authenticated user and a book."""
    progress = progress_repo.get_progress(user_id, book_id)

    if not progress:
        return {
            "user_id": user_id,
            "book_id": book_id,
            "current_chunk_id": None,
            "chapter_number": 0,
            "offset": 0,
        }

    return progress


@router.post("/progress")
async def save_reading_progress(
    book_id: str,
    current_chunk_id: str,
    chapter_number: int,
    offset: int,
    user_id: str = Depends(get_current_user_id),
    progress_repo: ReadingProgressRepository = Depends(get_reading_progress_repository),
):
    """Save reading progress for the authenticated user."""
    progress_data = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'book_id': book_id,
        'current_chunk_id': current_chunk_id,
        'chapter_number': chapter_number,
        'offset': offset,
    }

    progress = progress_repo.upsert(progress_data)
    return progress


@router.post("/bookmarks", status_code=201)
async def create_bookmark(
    bookmark: BookmarkCreate,
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database),
):
    """Create a bookmark for the authenticated user."""
    bookmark_data = bookmark.model_dump()
    bookmark_data['id'] = str(uuid.uuid4())
    bookmark_data['user_id'] = user_id
    bookmark_data['created_at'] = datetime.now().isoformat()

    response = db.client.table('bookmarks').insert(bookmark_data).execute()

    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to create bookmark")


@router.get("/bookmarks/{book_id}", response_model=PaginatedResponse)
async def list_bookmarks(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    pagination: PaginationParams = Depends(),
    db: Database = Depends(get_database),
):
    """List all bookmarks for the authenticated user and a book."""
    response = (
        db.client.table('bookmarks')
        .select('*')
        .eq('user_id', user_id)
        .eq('book_id', book_id)
        .execute()
    )
    all_bookmarks = response.data
    total = len(all_bookmarks)

    paginated_items = all_bookmarks[pagination.offset:pagination.offset + pagination.page_size]

    return paginate(items=paginated_items, total=total, params=pagination)


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database),
):
    """Delete a bookmark (ownership verified)."""
    existing = db.client.table('bookmarks').select('user_id').eq('id', bookmark_id).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if existing.data[0]['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Bu yer imine erişim izniniz yok")

    db.client.table('bookmarks').delete().eq('id', bookmark_id).execute()
    return {"message": "Bookmark deleted successfully"}
