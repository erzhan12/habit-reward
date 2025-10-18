"""Unit tests for streak service."""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch

from src.services.streak_service import StreakService
from src.models.habit_log import HabitLog


@pytest.fixture
def streak_service():
    """Create streak service instance."""
    return StreakService()


@pytest.fixture
def mock_habit_log_repo():
    """Create mock habit log repository."""
    return Mock()


def create_mock_log(streak_count: int, last_completed_date: date):
    """Helper to create mock HabitLog."""
    return HabitLog(
        user_id="user123",
        habit_id="habit123",
        streak_count=streak_count,
        habit_weight=10,
        total_weight_applied=11.0,
        last_completed_date=last_completed_date
    )


class TestStreakCalculation:
    """Test streak calculation logic."""

    def test_first_time_completion(self, streak_service, mock_habit_log_repo):
        """Test streak calculation for first-time habit completion."""
        mock_habit_log_repo.get_last_log_for_habit.return_value = None

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 1

    def test_same_day_completion(self, streak_service, mock_habit_log_repo):
        """Test streak when habit already logged today."""
        today = date.today()
        mock_log = create_mock_log(streak_count=5, last_completed_date=today)
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 5

    def test_consecutive_day_completion(self, streak_service, mock_habit_log_repo):
        """Test streak increment for consecutive day."""
        yesterday = date.today() - timedelta(days=1)
        mock_log = create_mock_log(streak_count=5, last_completed_date=yesterday)
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 6

    def test_broken_streak(self, streak_service, mock_habit_log_repo):
        """Test streak reset when broken."""
        three_days_ago = date.today() - timedelta(days=3)
        mock_log = create_mock_log(streak_count=10, last_completed_date=three_days_ago)
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 1

    def test_get_last_completed_date_exists(self, streak_service, mock_habit_log_repo):
        """Test getting last completed date when exists."""
        yesterday = date.today() - timedelta(days=1)
        mock_log = create_mock_log(streak_count=5, last_completed_date=yesterday)
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            last_date = streak_service.get_last_completed_date("user123", "habit123")

        assert last_date == yesterday

    def test_get_last_completed_date_none(self, streak_service, mock_habit_log_repo):
        """Test getting last completed date when no logs exist."""
        mock_habit_log_repo.get_last_log_for_habit.return_value = None

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            last_date = streak_service.get_last_completed_date("user123", "habit123")

        assert last_date is None
