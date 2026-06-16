"""Leaderboard endpoint — ranks users by reading activity for a period.

Python aggregation (small scale). Move to a Postgres RPC if the user base grows.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.core.database import Database
from app.core.dependencies import get_database
from app.core.auth import get_current_user_id

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def _period_start(period: str):
    now = datetime.now(timezone.utc)
    if period == 'week':
        return now - timedelta(days=7)
    if period == 'month':
        return now - timedelta(days=30)
    return None  # all-time


def _badge(rank: int) -> str:
    return {1: '🏆', 2: '🥈', 3: '🥉'}.get(rank, '🔥')


@router.get("")
async def get_leaderboard(
    period: str = Query('all', description="week | month | all"),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_database),
):
    """Ranked users by books read + pages, scoped to a period. Includes `me`."""
    since = _period_start(period)

    users = db.client.table('users').select(
        'id, display_name, avatar_url, is_public').execute().data or []
    library = db.client.table('user_library').select(
        'user_id, reading_status, updated_at, books(total_pages)').execute().data or []
    sessions = db.client.table('reading_sessions').select(
        'user_id, started_at, duration_seconds').execute().data or []

    # Aggregate per user.
    agg: dict = {
        u['id']: {
            "user_id": u['id'],
            "display_name": u.get('display_name') or 'Okuyucu',
            "avatar_url": u.get('avatar_url'),
            "is_public": u.get('is_public', True),
            "books_read": 0,
            "pages_read": 0,
            "reading_minutes": 0,
            "_days": set(),
        }
        for u in users
    }

    for e in library:
        a = agg.get(e['user_id'])
        if not a or e.get('reading_status') != 'completed':
            continue
        ts = _parse_ts(e.get('updated_at'))
        if since and (ts is None or ts < since):
            continue
        a['books_read'] += 1
        a['pages_read'] += (e.get('books') or {}).get('total_pages') or 0

    for s in sessions:
        a = agg.get(s['user_id'])
        if not a:
            continue
        ts = _parse_ts(s.get('started_at'))
        if since and (ts is None or ts < since):
            continue
        a['reading_minutes'] += int((s.get('duration_seconds') or 0) / 60)
        if ts:
            a['_days'].add(ts.date())

    # Streak (consecutive days up to today).
    today = datetime.now(timezone.utc).date()
    rows = []
    for a in agg.values():
        streak = 0
        cur = today
        while cur in a['_days']:
            streak += 1
            cur -= timedelta(days=1)
        rows.append({
            "user_id": a['user_id'],
            "display_name": a['display_name'],
            "avatar_url": a['avatar_url'],
            "books_read": a['books_read'],
            "pages_read": a['pages_read'],
            "reading_streak": streak,
            "is_public": a['is_public'],
        })

    # Rank by books_read, then pages_read, then minutes.
    rows.sort(key=lambda r: (r['books_read'], r['pages_read']), reverse=True)

    public_rows = [r for r in rows if r.get('is_public', True)]
    ranking = []
    for i, r in enumerate(public_rows[:limit], start=1):
        ranking.append({**{k: v for k, v in r.items() if k != 'is_public'},
                        "rank": i, "badge": _badge(i)})

    # The requesting user's own entry (rank within the full public list).
    me = None
    for i, r in enumerate(public_rows, start=1):
        if r['user_id'] == user_id:
            me = {**{k: v for k, v in r.items() if k != 'is_public'},
                  "rank": i, "badge": _badge(i)}
            break

    return {"period": period, "me": me, "ranking": ranking}
