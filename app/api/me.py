"""Current-user aggregate endpoints: reading stats and achievements.

Aggregation is done in Python (small scale). For larger scale, move the
hot paths to Postgres RPC functions.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import Database
from app.core.dependencies import get_database
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/me", tags=["me"])

_WEEKDAYS_TR = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']


def _session_day(session: dict):
    ts = session.get('started_at')
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00')).date()
    except (ValueError, AttributeError):
        return None


def _weekly_and_streak(sessions: list):
    """Minutes per weekday (current week) + current consecutive-day streak."""
    minutes_by_day: dict = {}
    for s in sessions:
        day = _session_day(s)
        if day:
            minutes_by_day[day] = minutes_by_day.get(day, 0) + (s.get('duration_seconds') or 0) / 60

    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    weekly = [
        {"day": _WEEKDAYS_TR[i], "minutes": int(minutes_by_day.get(monday + timedelta(days=i), 0))}
        for i in range(7)
    ]

    days_with_reading = set(minutes_by_day.keys())
    streak = 0
    cursor = today
    while cursor in days_with_reading:
        streak += 1
        cursor -= timedelta(days=1)

    return weekly, streak


def _gather(db: Database, user_id: str):
    sessions = db.client.table('reading_sessions').select(
        'duration_seconds, started_at').eq('user_id', user_id).execute().data or []
    library = db.client.table('user_library').select(
        'reading_status, books(total_pages)').eq('user_id', user_id).execute().data or []

    total_minutes = int(sum((s.get('duration_seconds') or 0) for s in sessions) / 60)
    books_read = len(library)
    completed = [e for e in library if e.get('reading_status') == 'completed']
    books_completed = len(completed)
    pages_read = sum((e.get('books') or {}).get('total_pages') or 0 for e in completed)
    weekly, streak = _weekly_and_streak(sessions)

    month_minutes = 0
    now = datetime.now(timezone.utc)
    for s in sessions:
        day = _session_day(s)
        if day and day.year == now.year and day.month == now.month:
            month_minutes += int((s.get('duration_seconds') or 0) / 60)

    return {
        "books_read": books_read,
        "books_completed": books_completed,
        "total_reading_minutes": total_minutes,
        "pages_read": pages_read,
        "reading_streak_days": streak,
        "weekly_activity": weekly,
        "_month_minutes": month_minutes,
    }


@router.get("/stats")
async def get_my_stats(
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database),
):
    """Reading statistics for the Profile and Stats screens."""
    stats = _gather(db, user_id)
    stats.pop("_month_minutes", None)
    return stats


@router.get("/achievements")
async def get_my_achievements(
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database),
):
    """Achievement badges (key + earned + progress 0..1). Labels live in the app."""
    s = _gather(db, user_id)

    def ach(key, earned: bool, progress: float):
        return {"key": key, "earned": earned, "progress": round(min(progress, 1.0), 2)}

    return {
        "achievements": [
            ach("first_book", s["books_read"] >= 1, s["books_read"] / 1),
            ach("streak_7", s["reading_streak_days"] >= 7, s["reading_streak_days"] / 7),
            ach("speed_reader", s["total_reading_minutes"] >= 120, s["total_reading_minutes"] / 120),
            ach("super_reader", s["books_completed"] >= 5, s["books_completed"] / 5),
            ach("month_record", s["_month_minutes"] >= 300, s["_month_minutes"] / 300),
        ]
    }
