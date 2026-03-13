"""Tests for AnalyticsService."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.analytics import HabitTrendData
from src.services.analytics_service import AnalyticsService


def _make_habit(
    habit_id=1,
    name="Test Habit",
    exempt_weekdays=None,
    allowed_skip_days=0,
    created_at=None,
):
    """Helper to build a mock Habit."""
    h = MagicMock()
    h.id = habit_id
    h.name = name
    h.exempt_weekdays = exempt_weekdays or []
    h.allowed_skip_days = allowed_skip_days
    h.created_at = created_at or datetime(2025, 1, 1, tzinfo=timezone.utc)
    h.active = True
    return h


class TestCalculateAvailableDays:
    """Unit tests for the _calculate_available_days static method."""

    def test_basic_range(self):
        habit = _make_habit()
        # 10-day range, no exemptions
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 1), date(2026, 3, 10)
        )
        assert result == 10

    def test_exempt_weekdays(self):
        # Exempt Sat (6) and Sun (7) — isoweekday convention
        habit = _make_habit(exempt_weekdays=[6, 7])
        # 2026-03-02 (Mon) to 2026-03-15 (Sun) = 14 days, 4 weekend days
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 2), date(2026, 3, 15)
        )
        assert result == 10

    def test_allowed_skip_days(self):
        habit = _make_habit(allowed_skip_days=1)
        # 14-day range = 2 weeks, so 2 skip days subtracted
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 1), date(2026, 3, 14)
        )
        assert result == 14 - 2  # 12

    def test_new_habit_in_range(self):
        # Habit created 5 days ago, but range is 30 days
        habit = _make_habit(created_at=datetime(2026, 3, 9, tzinfo=timezone.utc))
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 2, 11), date(2026, 3, 13)
        )
        # Only 5 days available (Mar 9–13 inclusive)
        assert result == 5

    def test_habit_created_after_end_date(self):
        habit = _make_habit(created_at=datetime(2026, 4, 1, tzinfo=timezone.utc))
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 1), date(2026, 3, 10)
        )
        assert result == 0

    def test_clamps_to_minimum_one(self):
        # Extreme skip days that would make available negative
        habit = _make_habit(allowed_skip_days=7)
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 1), date(2026, 3, 7)
        )
        assert result == 1

    def test_created_at_as_date(self):
        # created_at could be a plain date in some contexts
        habit = _make_habit()
        habit.created_at = date(2025, 1, 1)
        result = AnalyticsService._calculate_available_days(
            habit, date(2026, 3, 1), date(2026, 3, 10)
        )
        assert result == 10


class TestGetHabitCompletionRates:

    @pytest.fixture
    def svc(self):
        s = AnalyticsService()
        s.habit_repo = MagicMock()
        s.habit_log_repo = MagicMock()
        s.streak_svc = MagicMock()
        return s

    @pytest.mark.asyncio
    async def test_basic_completion_rate(self, svc):
        habit = _make_habit()
        svc.habit_repo.get_all_active = AsyncMock(return_value=[habit])
        # 7 distinct dates out of 10 available
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(
            return_value=[
                {"last_completed_date": date(2026, 3, i), "count": 1}
                for i in range(1, 8)
            ]
        )

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 1), date(2026, 3, 10))

        assert len(result) == 1
        assert result[0].completion_rate == 0.7
        assert result[0].completed_days == 7
        assert result[0].available_days == 10

    @pytest.mark.asyncio
    async def test_no_logs_returns_zero_rate(self, svc):
        habit = _make_habit()
        svc.habit_repo.get_all_active = AsyncMock(return_value=[habit])
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(return_value=[])

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 1), date(2026, 3, 10))

        assert len(result) == 1
        assert result[0].completion_rate == 0.0
        assert result[0].completed_days == 0

    @pytest.mark.asyncio
    async def test_capped_at_one(self, svc):
        habit = _make_habit()
        svc.habit_repo.get_all_active = AsyncMock(return_value=[habit])
        # More dates than available days (e.g. via backdating)
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(
            return_value=[
                {"last_completed_date": date(2026, 3, i), "count": 1}
                for i in range(1, 6)
            ]
        )

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 1), date(2026, 3, 3))

        assert result[0].completion_rate == 1.0

    @pytest.mark.asyncio
    async def test_no_habits_returns_empty(self, svc):
        svc.habit_repo.get_all_active = AsyncMock(return_value=[])

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 1), date(2026, 3, 10))

        assert result == []

    @pytest.mark.asyncio
    async def test_sorted_by_rate_descending(self, svc):
        h1 = _make_habit(habit_id=1, name="Low")
        h2 = _make_habit(habit_id=2, name="High")
        h3 = _make_habit(habit_id=3, name="Mid")
        svc.habit_repo.get_all_active = AsyncMock(return_value=[h1, h2, h3])

        async def mock_counts(uid, sd, ed, habit_id=None):
            # h1: 3/10, h2: 9/10, h3: 5/10
            counts = {1: 3, 2: 9, 3: 5}
            n = counts.get(habit_id, 0)
            return [
                {"last_completed_date": date(2026, 3, i), "count": 1}
                for i in range(1, n + 1)
            ]

        svc.habit_log_repo.get_completion_counts_by_date = mock_counts

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 1), date(2026, 3, 10))

        assert [r.habit_name for r in result] == ["High", "Mid", "Low"]
        assert result[0].completion_rate == 0.9
        assert result[1].completion_rate == 0.5
        assert result[2].completion_rate == 0.3

    @pytest.mark.asyncio
    async def test_exempt_weekdays_affect_rate(self, svc):
        # Exempt Sat/Sun
        habit = _make_habit(exempt_weekdays=[6, 7])
        svc.habit_repo.get_all_active = AsyncMock(return_value=[habit])
        # 2026-03-02 Mon to 2026-03-15 Sun: 14 days, 4 weekend days = 10 available
        # 7 completions → rate = 7/10 = 0.7
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(
            return_value=[
                {"last_completed_date": date(2026, 3, i), "count": 1}
                for i in range(2, 9)  # 7 dates
            ]
        )

        result = await svc.get_habit_completion_rates(1, date(2026, 3, 2), date(2026, 3, 15))

        assert result[0].available_days == 10
        assert result[0].completion_rate == 0.7


class TestGetHabitRankings:

    @pytest.fixture
    def svc(self):
        s = AnalyticsService()
        s.habit_repo = MagicMock()
        s.habit_log_repo = MagicMock()
        s.streak_svc = MagicMock()
        return s

    @pytest.mark.asyncio
    async def test_rankings_sorted_with_streak_data(self, svc):
        h1 = _make_habit(habit_id=1, name="High")
        h2 = _make_habit(habit_id=2, name="Low")
        svc.habit_repo.get_all_active = AsyncMock(return_value=[h1, h2])

        async def mock_counts(uid, sd, ed, habit_id=None):
            counts = {1: 9, 2: 3}
            n = counts.get(habit_id, 0)
            return [
                {"last_completed_date": date(2026, 3, i), "count": 1}
                for i in range(1, n + 1)
            ]

        svc.habit_log_repo.get_completion_counts_by_date = mock_counts
        svc.streak_svc.get_current_streak = AsyncMock(return_value=5)
        svc.habit_log_repo.get_longest_streak_in_range = AsyncMock(return_value=8)
        svc.habit_log_repo.get_total_completions_in_range = AsyncMock(side_effect=[9, 3])

        result = await svc.get_habit_rankings(
            1, date(2026, 3, 1), date(2026, 3, 10), user_timezone="UTC"
        )

        assert len(result) == 2
        assert result[0].rank == 1
        assert result[0].habit_name == "High"
        assert result[0].current_streak == 5
        assert result[0].longest_streak_in_range == 8
        assert result[1].rank == 2
        assert result[1].habit_name == "Low"


class TestGetHabitTrends:

    @pytest.fixture
    def svc(self):
        s = AnalyticsService()
        s.habit_repo = MagicMock()
        s.habit_log_repo = MagicMock()
        s.streak_svc = MagicMock()
        return s

    @pytest.mark.asyncio
    async def test_daily_grouping(self, svc):
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(
            return_value=[
                {"last_completed_date": date(2026, 3, 2), "count": 2},
                {"last_completed_date": date(2026, 3, 5), "count": 1},
                {"last_completed_date": date(2026, 3, 9), "count": 3},
            ]
        )
        svc.habit_repo.get_all_active = AsyncMock(return_value=[_make_habit()])

        result = await svc.get_habit_trends(1, date(2026, 3, 1), date(2026, 3, 14))

        assert len(result.daily) == 3
        assert result.daily[0].date == date(2026, 3, 2)
        assert result.daily[0].completions == 2

    @pytest.mark.asyncio
    async def test_weekly_aggregation(self, svc):
        # Logs in two different ISO weeks
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(
            return_value=[
                {"last_completed_date": date(2026, 3, 2), "count": 1},   # week of Mar 2
                {"last_completed_date": date(2026, 3, 4), "count": 1},   # same week
                {"last_completed_date": date(2026, 3, 10), "count": 2},  # week of Mar 9
            ]
        )
        svc.habit_repo.get_all_active = AsyncMock(return_value=[_make_habit()])

        result = await svc.get_habit_trends(1, date(2026, 3, 1), date(2026, 3, 15))

        assert len(result.weekly) == 2
        assert result.weekly[0].week_start == date(2026, 3, 2)
        assert result.weekly[0].completions == 2
        assert result.weekly[1].week_start == date(2026, 3, 9)
        assert result.weekly[1].completions == 2

    @pytest.mark.asyncio
    async def test_single_habit_filter(self, svc):
        habit = _make_habit(habit_id=5)
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(return_value=[])
        svc.habit_repo.get_by_id = AsyncMock(return_value=habit)

        result = await svc.get_habit_trends(
            1, date(2026, 3, 1), date(2026, 3, 10), habit_id=5
        )

        svc.habit_log_repo.get_completion_counts_by_date.assert_called_once_with(
            1, date(2026, 3, 1), date(2026, 3, 10),
            habit_id=5, active_only=False,
        )
        assert isinstance(result, HabitTrendData)

    @pytest.mark.asyncio
    async def test_all_habits_aggregate(self, svc):
        svc.habit_log_repo.get_completion_counts_by_date = AsyncMock(return_value=[])
        svc.habit_repo.get_all_active = AsyncMock(return_value=[_make_habit()])

        result = await svc.get_habit_trends(1, date(2026, 3, 1), date(2026, 3, 10))

        # When habit_id is None, active_only=True to match available_days denominator
        svc.habit_log_repo.get_completion_counts_by_date.assert_called_once_with(
            1, date(2026, 3, 1), date(2026, 3, 10),
            habit_id=None, active_only=True,
        )
        assert result.daily == []
        assert result.weekly == []