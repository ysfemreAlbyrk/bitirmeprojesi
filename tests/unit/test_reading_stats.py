"""Unit tests for reading stats aggregation"""
import pytest
from datetime import datetime, timedelta


@pytest.mark.unit
class TestReadingStats:
    """Test stats aggregation logic (mirrors the endpoint implementation)."""

    def _aggregate(self, sessions, start):
        """Mirror of the /reading/stats endpoint logic for testing."""
        total_seconds = sum(s.get('duration_seconds', 0) or 0 for s in sessions)
        immersive_seconds = sum(s.get('immersive_mode_seconds', 0) or 0 for s in sessions)
        unique_books = len({s['book_id'] for s in sessions})
        daily = {}
        for s in sessions:
            day = s['started_at'][:10] if s.get('started_at') else 'unknown'
            if day not in daily:
                daily[day] = {"duration_seconds": 0, "immersive_seconds": 0, "sessions": 0}
            daily[day]["duration_seconds"] += s.get('duration_seconds', 0) or 0
            daily[day]["immersive_seconds"] += s.get('immersive_mode_seconds', 0) or 0
            daily[day]["sessions"] += 1
        return {
            "total_seconds": total_seconds,
            "immersive_seconds": immersive_seconds,
            "books_read": unique_books,
            "session_count": len(sessions),
            "daily_breakdown": daily,
        }

    def test_empty_sessions(self):
        result = self._aggregate([], datetime.min)
        assert result["total_seconds"] == 0
        assert result["immersive_seconds"] == 0
        assert result["session_count"] == 0

    def test_single_session(self):
        now = datetime.now()
        sessions = [{
            "book_id": "b1",
            "started_at": now.isoformat(),
            "duration_seconds": 300,
            "immersive_mode_seconds": 120
        }]
        result = self._aggregate(sessions, datetime.min)
        assert result["total_seconds"] == 300
        assert result["immersive_seconds"] == 120
        assert result["books_read"] == 1
        assert result["session_count"] == 1

    def test_multiple_sessions_same_book(self):
        now = datetime.now()
        sessions = [
            {"book_id": "b1", "started_at": now.isoformat(), "duration_seconds": 60, "immersive_mode_seconds": 30},
            {"book_id": "b1", "started_at": (now + timedelta(hours=1)).isoformat(), "duration_seconds": 120, "immersive_mode_seconds": 0},
        ]
        result = self._aggregate(sessions, datetime.min)
        assert result["total_seconds"] == 180
        assert result["books_read"] == 1
        assert result["session_count"] == 2

    def test_none_values_treated_as_zero(self):
        sessions = [{"book_id": "b1", "started_at": "2024-01-01T00:00:00", "duration_seconds": None, "immersive_mode_seconds": None}]
        result = self._aggregate(sessions, datetime.min)
        assert result["total_seconds"] == 0
        assert result["immersive_seconds"] == 0
