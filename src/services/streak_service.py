"""Streak calculation service for per-habit streak tracking."""

from datetime import date, timedelta
from typing import Awaitable
from src.core.repositories import habit_log_repository, habit_repository
from src.utils.async_compat import run_sync_or_async, maybe_await


class StreakService:
    """Service for calculating and managing habit streaks."""

    def __init__(self):
        """Initialize StreakService with repositories."""
        self.habit_log_repo = habit_log_repository
        self.habit_repo = habit_repository

    def calculate_streak(
        self,
        user_id: str,
        habit_id: str
    ) -> int | Awaitable[int]:
        """Calculate current streak for a specific habit and user with grace days and exempt weekdays support."""

        async def _impl() -> int:
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )

            if last_log is None:
                return 1

            # Get habit settings for flexible streak tracking
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            
            last_date = last_log.last_completed_date
            today = date.today()
            yesterday = today - timedelta(days=1)

            # Simple cases: today or yesterday
            if last_date == today:
                return last_log.streak_count

            if last_date == yesterday:
                return last_log.streak_count + 1

            # If habit not found, use strict logic (break streak for gap > 1 day)
            if not habit:
                return 1

            # Gap of more than 1 day - check if flexible tracking preserves streak
            if last_date < yesterday:
                # Get all dates in the gap (exclusive of both endpoints)
                current_date = last_date + timedelta(days=1)
                missed_days = 0

                while current_date < today:
                    # Get weekday (1=Monday, 7=Sunday)
                    weekday = current_date.isoweekday()

                    # Only count as missed if not in exempt_weekdays
                    if weekday not in habit.exempt_weekdays:
                        missed_days += 1

                    current_date += timedelta(days=1)

                # Check if missed days are within allowed grace days
                if missed_days <= habit.allowed_skip_days:
                    # Streak preserved
                    return last_log.streak_count + 1
                else:
                    # Streak broken
                    return 1

            return 1

        return run_sync_or_async(_impl())

    def get_last_completed_date(
        self,
        user_id: str,
        habit_id: str
    ) -> date | None | Awaitable[date | None]:
        """Get the last completed date for a specific habit and user."""

        async def _impl() -> date | None:
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )
            return last_log.last_completed_date if last_log else None

        return run_sync_or_async(_impl())

    def get_current_streak(
        self,
        user_id: str,
        habit_id: str
    ) -> int | Awaitable[int]:
        """Get the CURRENT streak for a habit (for display purposes)."""

        async def _impl() -> int:
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )

            if last_log is None:
                return 0

            return last_log.streak_count

        return run_sync_or_async(_impl())

    def get_all_streaks_for_user(
        self,
        user_id: str
    ) -> dict[str, int] | Awaitable[dict[str, int]]:
        """Get current streaks for all habits for a user."""

        async def _impl() -> dict[str, int]:
            logs = await maybe_await(self.habit_log_repo.get_logs_by_user(user_id))

            habit_streaks: dict[str, int] = {}
            processed_habits: set[str] = set()

            for log in logs:
                if log.habit_id not in processed_habits:
                    processed_habits.add(log.habit_id)
                    streak = await maybe_await(
                        self.get_current_streak(user_id, log.habit_id)
                    )
                    habit_streaks[log.habit_id] = streak

            return habit_streaks

        return run_sync_or_async(_impl())


# Global service instance
streak_service = StreakService()
