"""Unit tests for Airtable repositories."""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch

from src.airtable.repositories import HabitLogRepository


@pytest.fixture
def habit_log_repo():
    """Create habit log repository instance."""
    return HabitLogRepository()


@pytest.fixture
def mock_table():
    """Create mock Airtable table."""
    return Mock()


class TestGetTodaysLogsByUser:
    """Test get_todays_logs_by_user method for filtering today's logs."""

    def test_returns_todays_logs_only(self, habit_log_repo, mock_table):
        """Test with target_date=today - returns today's logs only."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit2"],
                    "last_completed_date": yesterday.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # Only today's log should be returned
        assert len(result) == 1
        assert result[0].id == "log1"
        assert result[0].last_completed_date == today

    def test_returns_yesterdays_logs(self, habit_log_repo, mock_table):
        """Test with target_date=yesterday - returns yesterday's logs."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit2"],
                    "last_completed_date": yesterday.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=yesterday)

        # Only yesterday's log should be returned
        assert len(result) == 1
        assert result[0].id == "log2"
        assert result[0].last_completed_date == yesterday

    def test_no_logs_for_date(self, habit_log_repo, mock_table):
        """Test with no logs for date - returns empty list."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": yesterday.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # No logs for today
        assert len(result) == 0

    def test_filters_by_user_id(self, habit_log_repo, mock_table):
        """Test filtering by user_id - only returns user's logs."""
        today = date.today()

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user456"],  # Different user
                    "habit_id": ["habit2"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
            {
                "id": "log3",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit3"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": False,
                    "reward_id": None,
                    "streak_count": 1,
                    "habit_weight": 20,
                    "total_weight_applied": 22.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # Only user123's logs should be returned
        assert len(result) == 2
        assert result[0].id == "log1"
        assert result[1].id == "log3"
        assert result[0].user_id == "user123"
        assert result[1].user_id == "user123"

    def test_default_target_date_is_today(self, habit_log_repo, mock_table):
        """Test with no target_date parameter - defaults to today."""
        today = date.today()

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123")

        # Should return today's logs by default
        assert len(result) == 1
        assert result[0].last_completed_date == today

    def test_multiple_logs_same_day(self, habit_log_repo, mock_table):
        """Test with multiple logs for same user on same day."""
        today = date.today()

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit2"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
            {
                "id": "log3",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit3"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": False,
                    "reward_id": None,
                    "streak_count": 1,
                    "habit_weight": 20,
                    "total_weight_applied": 22.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # All three logs for today should be returned
        assert len(result) == 3
        assert all(log.last_completed_date == today for log in result)
        assert all(log.user_id == "user123" for log in result)

    def test_handles_empty_user_id_array(self, habit_log_repo, mock_table):
        """Test handling of empty user_id array."""
        today = date.today()

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": [],  # Empty array
                    "habit_id": ["habit1"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit2"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # Only log2 should be returned (log1 has empty user_id)
        assert len(result) == 1
        assert result[0].id == "log2"

    def test_handles_missing_date_field(self, habit_log_repo, mock_table):
        """Test handling of records with missing last_completed_date."""
        today = date.today()

        mock_records = [
            {
                "id": "log1",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit1"],
                    # Missing last_completed_date
                    "got_reward": True,
                    "reward_id": ["reward1"],
                    "streak_count": 5,
                    "habit_weight": 10,
                    "total_weight_applied": 15.0,
                }
            },
            {
                "id": "log2",
                "fields": {
                    "user_id": ["user123"],
                    "habit_id": ["habit2"],
                    "last_completed_date": today.isoformat(),
                    "got_reward": True,
                    "reward_id": ["reward2"],
                    "streak_count": 3,
                    "habit_weight": 15,
                    "total_weight_applied": 18.0,
                }
            },
        ]
        mock_table.all.return_value = mock_records

        with patch.object(habit_log_repo, 'table', mock_table):
            result = habit_log_repo.get_todays_logs_by_user("user123", target_date=today)

        # Only log2 should be returned (log1 missing date)
        assert len(result) == 1
        assert result[0].id == "log2"

