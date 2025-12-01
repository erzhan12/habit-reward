"""Unit tests for streak service."""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch

from src.services.streak_service import StreakService
from src.models.habit_log import HabitLog


@pytest.fixture
def streak_service():
    """Create streak service instance."""
    service = StreakService()
    # Prevent _refresh_dependencies from overriding mocked repos in tests
    service._refresh_dependencies = Mock()
    return service


@pytest.fixture
def mock_habit_log_repo():
    """Create mock habit log repository."""
    return Mock()


@pytest.fixture
def mock_habit_repo():
    """Create mock habit repository."""
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


def create_mock_habit(allowed_skip_days: int = 0, exempt_weekdays: list = None):
    """Helper to create mock Habit."""
    mock_habit = Mock()
    mock_habit.id = "habit123"
    mock_habit.allowed_skip_days = allowed_skip_days
    mock_habit.exempt_weekdays = exempt_weekdays if exempt_weekdays is not None else []
    return mock_habit


class TestStreakCalculation:
    """Test streak calculation logic."""

    def test_first_time_completion(self, streak_service, mock_habit_log_repo):
        """Test streak calculation for first-time habit completion."""
        mock_habit_log_repo.get_last_log_for_habit.return_value = None

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 1

    def test_same_day_completion(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak when habit already logged today."""
        today = date.today()
        mock_log = create_mock_log(streak_count=5, last_completed_date=today)
        mock_habit = create_mock_habit()
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 5

    def test_consecutive_day_completion(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak increment for consecutive day."""
        yesterday = date.today() - timedelta(days=1)
        mock_log = create_mock_log(streak_count=5, last_completed_date=yesterday)
        mock_habit = create_mock_habit()
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        assert streak == 6

    def test_broken_streak(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak reset when broken."""
        three_days_ago = date.today() - timedelta(days=3)
        mock_log = create_mock_log(streak_count=10, last_completed_date=three_days_ago)
        mock_habit = create_mock_habit()
        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
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

    def test_get_all_streaks_multi_habit_different_completion_dates(self, streak_service, mock_habit_log_repo):
        """
        Test BUG: Multiple habits with different last completion dates.

        Scenario:
        - Day 1: User logs both "pushups" and "drinking water"
        - Day 2: User logs only "pushups" (not "drinking water")
        - Day 2: User checks /streaks command

        Expected behavior:
        - Pushups: streak = 2 (logged on Day 1 and Day 2)
        - Drinking water: streak = 1 (only logged on Day 1, NOT on Day 2)

        Bug behavior (before fix):
        - Pushups: streak = 2 ✓
        - Drinking water: streak = 2 ✗ (incorrectly incremented because last_date was yesterday)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Habit A "pushups": logged yesterday (Day 1) with streak=1, then logged today (Day 2) with streak=2
        habit_a_id = "habit_pushups"
        habit_a_log = HabitLog(
            user_id="user123",
            habit_id=habit_a_id,
            streak_count=2,  # Current streak after Day 2 logging
            habit_weight=10,
            total_weight_applied=11.0,
            last_completed_date=today  # Last logged TODAY (Day 2)
        )

        # Habit B "drinking water": logged yesterday (Day 1) with streak=1, NOT logged today (Day 2)
        habit_b_id = "habit_water"
        habit_b_log = HabitLog(
            user_id="user123",
            habit_id=habit_b_id,
            streak_count=1,  # Current streak after Day 1 logging
            habit_weight=10,
            total_weight_applied=11.0,
            last_completed_date=yesterday  # Last logged YESTERDAY (Day 1), NOT today
        )

        # Mock get_logs_by_user to return both habits
        mock_habit_log_repo.get_logs_by_user.return_value = [habit_a_log, habit_b_log]

        # Mock get_last_log_for_habit to return the appropriate log for each habit
        def mock_get_last_log(user_id, habit_id):
            if habit_id == habit_a_id:
                return habit_a_log
            elif habit_id == habit_b_id:
                return habit_b_log
            return None

        mock_habit_log_repo.get_last_log_for_habit.side_effect = mock_get_last_log

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streaks = streak_service.get_all_streaks_for_user("user123")

        # Assertions
        assert habit_a_id in streaks, "Pushups should be in streaks"
        assert habit_b_id in streaks, "Drinking water should be in streaks"

        # CRITICAL: Pushups logged today, so streak should be current value (2)
        assert streaks[habit_a_id] == 2, "Pushups streak should be 2 (logged Day 1 and Day 2)"

        # CRITICAL BUG TEST: Drinking water last logged YESTERDAY (not today)
        # When checking current streaks (not logging a new habit), this should show 1, NOT 2
        # The bug is that calculate_streak() increments when last_date==yesterday,
        # which is correct when LOGGING a new habit, but INCORRECT when just CHECKING streaks
        assert streaks[habit_b_id] == 1, (
            "Drinking water streak should be 1 (only logged Day 1, not Day 2). "
            "BUG: calculate_streak() incorrectly increments to 2 when last_date is yesterday, "
            "even though we're not logging a new completion today."
        )


class TestFlexibleStreakTracking:
    """Test flexible streak tracking with grace days and exempt weekdays."""

    def test_streak_with_1_grace_day_preserved(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak preserved when skipping 1 day with 1 grace day allowed."""
        two_days_ago = date.today() - timedelta(days=2)
        mock_log = create_mock_log(streak_count=5, last_completed_date=two_days_ago)
        mock_habit = create_mock_habit(allowed_skip_days=1)

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # Gap of 1 day (yesterday), 1 grace day allowed → streak preserved
        assert streak == 6

    def test_streak_with_1_grace_day_broken(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak broken when skipping 2 days with only 1 grace day allowed."""
        three_days_ago = date.today() - timedelta(days=3)
        mock_log = create_mock_log(streak_count=5, last_completed_date=three_days_ago)
        mock_habit = create_mock_habit(allowed_skip_days=1)

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # Gap of 2 days (yesterday + day before), only 1 grace day → streak broken
        assert streak == 1

    def test_streak_with_3_grace_days_preserved(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak preserved when skipping 3 days with 3 grace days allowed."""
        four_days_ago = date.today() - timedelta(days=4)
        mock_log = create_mock_log(streak_count=10, last_completed_date=four_days_ago)
        mock_habit = create_mock_habit(allowed_skip_days=3)

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # Gap of 3 days, 3 grace days allowed → streak preserved
        assert streak == 11

    def test_streak_with_weekend_exempt_friday_to_monday(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak preserved over weekend when weekends are exempt."""
        # Use fixed dates: Friday Jan 5, 2024 → Monday Jan 8, 2024
        # Jan 6 = Saturday, Jan 7 = Sunday (both should be exempt)
        friday = date(2024, 1, 5)  # Friday
        monday = date(2024, 1, 8)  # Monday (3 days later)

        mock_log = create_mock_log(streak_count=5, last_completed_date=friday)
        mock_habit = create_mock_habit(allowed_skip_days=0, exempt_weekdays=[6, 7])  # Sat=6, Sun=7

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        # Mock date.today() to return Monday
        with patch('src.services.streak_service.date') as mock_date:
            mock_date.today.return_value = monday
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
                with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                    streak = streak_service.calculate_streak("user123", "habit123")

        # Gap: Sat (6), Sun (7) - both exempt → missed_days = 0 → streak preserved
        assert streak == 6

    def test_streak_with_weekend_exempt_but_weekday_missed(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak broken when weekday is missed even with weekends exempt."""
        # Last done 4 days ago (should include at least one weekday in gap)
        four_days_ago = date.today() - timedelta(days=4)

        mock_log = create_mock_log(streak_count=5, last_completed_date=four_days_ago)
        mock_habit = create_mock_habit(allowed_skip_days=0, exempt_weekdays=[6, 7])  # Sat=6, Sun=7

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # Gap of 3 days will include at least 1 weekday → streak broken
        assert streak == 1

    def test_streak_with_grace_days_and_exempt_weekends_combined(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test streak with both grace days AND exempt weekends."""
        # Use fixed dates: Thursday Jan 4, 2024 → Tuesday Jan 9, 2024
        # Gap includes: Fri Jan 5 (weekday), Sat Jan 6 (exempt), Sun Jan 7 (exempt), Mon Jan 8 (weekday)
        # Non-exempt days in gap: Fri, Mon = 2 days
        # With 2 grace days, streak should be preserved
        thursday = date(2024, 1, 4)  # Thursday
        tuesday = date(2024, 1, 9)   # Tuesday (5 days later)

        mock_log = create_mock_log(streak_count=7, last_completed_date=thursday)
        mock_habit = create_mock_habit(allowed_skip_days=2, exempt_weekdays=[6, 7])

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        # Mock date.today() to return Tuesday
        with patch('src.services.streak_service.date') as mock_date:
            mock_date.today.return_value = tuesday
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
                with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                    streak = streak_service.calculate_streak("user123", "habit123")

        # Gap: Fri (weekday), Sat (exempt), Sun (exempt), Mon (weekday)
        # Missed weekdays: 2 (Fri, Mon), allowed: 2 → streak preserved
        assert streak == 8

    def test_streak_with_no_grace_days_strict_mode(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test strict mode (0 grace days, no exemptions) breaks streak immediately."""
        two_days_ago = date.today() - timedelta(days=2)
        mock_log = create_mock_log(streak_count=10, last_completed_date=two_days_ago)
        mock_habit = create_mock_habit(allowed_skip_days=0, exempt_weekdays=[])

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = mock_habit

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # Strict mode: any gap > 1 day breaks streak
        assert streak == 1

    def test_streak_calculation_when_habit_not_found(self, streak_service, mock_habit_log_repo, mock_habit_repo):
        """Test fallback behavior when habit is not found."""
        two_days_ago = date.today() - timedelta(days=2)
        mock_log = create_mock_log(streak_count=5, last_completed_date=two_days_ago)

        mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log
        mock_habit_repo.get_by_id.return_value = None  # Habit not found

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            with patch.object(streak_service, 'habit_repo', mock_habit_repo):
                streak = streak_service.calculate_streak("user123", "habit123")

        # When habit not found, should fallback to simple logic (break streak)
        assert streak == 1
