"""Reading progress and session API endpoints"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.models.reading import ReadingProgress, Bookmark, BookmarkCreate, ReadingSessionCreate, ReadingSessionUpdate
from app.core.database import Database, ReadingProgressRepository, BookRepository, TextChunkRepository
from app.core.dependencies import get_database, get_reading_progress_repository, get_book_repository, get_text_chunk_repository
from app.core.auth import get_current_user_id
from app.utils.pagination import PaginatedResponse, PaginationParams, paginate

router = APIRouter(prefix="/reading", tags=["reading"])


@router.post("/sessions")
async def create_reading_session(
    session: ReadingSessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database)
):
    """Start a new reading session."""
    session_data = session.model_dump()
    session_data['id'] = str(uuid.uuid4())
    session_data['user_id'] = user_id
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

    # If the session is ending, also update the book's last_read_date
    if update_data.get('ended_at'):
        session = db.client.table('reading_sessions').select('book_id').eq('id', session_id).execute()
        if session.data:
            book_id = session.data[0]['book_id']
            db.client.table('books').update({'last_read_date': datetime.now().isoformat()}).eq('id', book_id).execute()

    response = db.client.table('reading_sessions').update(update_data).eq('id', session_id).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=404, detail="Reading session not found")


@router.get("/sessions")
async def list_reading_sessions(
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database)
):
    """List all reading sessions for a user."""
    response = db.client.table('reading_sessions').select('*').eq('user_id', user_id).order('started_at', desc=True).execute()
    return {"sessions": response.data or []}


@router.get("/progress/{book_id}")
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


class ReadingProgressSave(BaseModel):
    book_id: str
    current_chunk_id: str
    chapter_number: int
    offset: int


@router.post("/progress")
async def save_reading_progress(
    payload: ReadingProgressSave,
    user_id: str = Depends(get_current_user_id),
    progress_repo: ReadingProgressRepository = Depends(get_reading_progress_repository),
    db: Database = Depends(get_database),
):
    """Save reading progress for the authenticated user."""
    progress_data = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'book_id': payload.book_id,
        'current_chunk_id': payload.current_chunk_id,
        'chapter_number': payload.chapter_number,
        'offset': payload.offset,
    }

    progress = progress_repo.upsert(progress_data)

    # Update last_read_date on the book
    db.client.table('books').update({'last_read_date': datetime.now().isoformat()}).eq('id', payload.book_id).execute()

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


@router.get("/stats")
async def get_reading_stats(
    period: str = Query("week", pattern="^(day|week|month|all)$"),
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database)
):
    """
    Aggregate reading statistics for the authenticated user.

    - **period**: `day` | `week` | `month` | `all`

    Returns total duration, immersive mode duration, session count,
    books touched, and a daily breakdown for charts.
    """
    now = datetime.now()
    if period == "day":
        start = now - timedelta(days=1)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = datetime.min

    sessions = (
        db.client.table('reading_sessions')
        .select('*')
        .eq('user_id', user_id)
        .gte('started_at', start.isoformat())
        .execute()
        .data or []
    )

    total_seconds = sum(s.get('duration_seconds', 0) or 0 for s in sessions)
    immersive_seconds = sum(s.get('immersive_mode_seconds', 0) or 0 for s in sessions)
    unique_books = len({s['book_id'] for s in sessions})

    # Daily breakdown for charts
    daily: dict[str, dict] = {}
    for s in sessions:
        day = s['started_at'][:10] if s.get('started_at') else 'unknown'
        if day not in daily:
            daily[day] = {"duration_seconds": 0, "immersive_seconds": 0, "sessions": 0}
        daily[day]["duration_seconds"] += s.get('duration_seconds', 0) or 0
        daily[day]["immersive_seconds"] += s.get('immersive_mode_seconds', 0) or 0
        daily[day]["sessions"] += 1

    return {
        "period": period,
        "total_seconds": total_seconds,
        "total_minutes": round(total_seconds / 60, 1),
        "immersive_seconds": immersive_seconds,
        "immersive_minutes": round(immersive_seconds / 60, 1),
        "session_count": len(sessions),
        "books_read": unique_books,
        "daily_breakdown": [
            {"date": d, **v} for d, v in sorted(daily.items())
        ],
    }
