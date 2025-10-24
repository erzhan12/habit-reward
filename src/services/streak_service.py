"""Streak calculation service for per-habit streak tracking."""

from datetime import date, timedelta
from src.core.repositories import habit_log_repository


class StreakService:
    """Service for calculating and managing habit streaks."""

    def __init__(self):
        """Initialize StreakService with repository."""
        self.habit_log_repo = habit_log_repository

    async def calculate_streak(self, user_id: str, habit_id: str) -> int:
        """
        Calculate current streak for a specific habit and user.

        Algorithm:
        1. Query Habit Log for the specific habit_id and user_id
        2. Get the most recent log entry for that habit
        3. Extract last_completed_date from that entry
        4. If last_completed_date is yesterday: increment streak
        5. If last_completed_date is today: return current streak (already logged today)
        6. Otherwise: reset streak to 1

        Args:
            user_id: Airtable record ID of the user
            habit_id: Airtable record ID of the habit

        Returns:
            Current streak count (minimum 1)
        """
        last_log = await self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)

        # First time completing this habit
        if last_log is None:
            return 1

        last_date = last_log.last_completed_date
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Already logged today - return current streak
        if last_date == today:
            return last_log.streak_count

        # Consecutive day - increment streak
        if last_date == yesterday:
            return last_log.streak_count + 1

        # Streak broken - reset to 1
        return 1

    async def get_last_completed_date(self, user_id: str, habit_id: str) -> date | None:
        """
        Get the last completed date for a specific habit and user.

        Args:
            user_id: Airtable record ID of the user
            habit_id: Airtable record ID of the habit

        Returns:
            Date of last completion or None if never completed
        """
        last_log = await self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
        return last_log.last_completed_date if last_log else None

    async def get_current_streak(self, user_id: str, habit_id: str) -> int:
        """
        Get the CURRENT streak for a habit (for display purposes).

        This differs from calculate_streak() which returns what the NEXT streak
        will be when logging a new habit.

        Logic:
        - If last_completed_date is today: return current streak (still active)
        - If last_completed_date is yesterday or earlier: return current streak (may be broken)

        Args:
            user_id: Airtable record ID of the user
            habit_id: Airtable record ID of the habit

        Returns:
            Current streak count (0 if never completed)
        """
        last_log = await self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)

        # Never completed this habit
        if last_log is None:
            return 0

        # Return the streak from the most recent log
        return last_log.streak_count

    async def get_all_streaks_for_user(self, user_id: str) -> dict[str, int]:
        """
        Get current streaks for all habits for a user.

        Args:
            user_id: Airtable record ID of the user

        Returns:
            Dictionary mapping habit_id to current streak count
        """
        logs = await self.habit_log_repo.get_logs_by_user(user_id)

        # Group by habit_id and get most recent for each
        habit_streaks: dict[str, int] = {}
        processed_habits: set[str] = set()

        for log in logs:
            if log.habit_id not in processed_habits:
                processed_habits.add(log.habit_id)
                # Use get_current_streak instead of calculate_streak
                # calculate_streak is for determining the NEXT streak when logging
                # get_current_streak is for displaying the CURRENT streak status
                streak = await self.get_current_streak(user_id, log.habit_id)
                habit_streaks[log.habit_id] = streak

        return habit_streaks


# Global service instance
streak_service = StreakService()
