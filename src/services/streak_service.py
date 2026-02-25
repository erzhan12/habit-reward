"""Streak calculation service for per-habit streak tracking."""

import logging
from datetime import date, timedelta
from typing import Awaitable
from django.core.cache import cache
from src.core.repositories import habit_log_repository, habit_repository
from src.utils.async_compat import run_sync_or_async, maybe_await
from src.bot.timezone_utils import get_user_today

logger = logging.getLogger(__name__)


class StreakService:
    """Service for calculating and managing habit streaks."""

    def __init__(self):
        """Initialize StreakService with repositories."""
        self.habit_log_repo = habit_log_repository
        self.habit_repo = habit_repository

    def _refresh_dependencies(self) -> None:
        """Rebind repositories to allow test patching."""
        self.habit_log_repo = habit_log_repository
        self.habit_repo = habit_repository

    @staticmethod
    def _is_streak_alive(
        last_completed_date: date,
        today: date,
        allowed_skip_days: int = 0,
        exempt_weekdays: list[int] | None = None,
    ) -> bool:
        """Return True if the streak is still active (not broken).

        A streak is alive if the last completion was today, yesterday, or within
        the grace-day/exempt-weekday window.

        Args:
            last_completed_date: Date of the most recent habit completion.
            today: Today's date in the user's timezone.
            allowed_skip_days: Number of non-exempt days the user may skip without breaking.
            exempt_weekdays: Weekday numbers (1=Mon, 7=Sun) that don't count as missed.

        Returns:
            True if the streak should still be shown, False if it has been broken.
        """
        if exempt_weekdays is None:
            exempt_weekdays = []

        if last_completed_date >= today:
            return True

        yesterday = today - timedelta(days=1)
        if last_completed_date == yesterday:
            return True

        # Gap > 1 day — count non-exempt missed days
        current = last_completed_date + timedelta(days=1)
        missed = 0
        while current < today:
            if current.isoweekday() not in exempt_weekdays:
                missed += 1
            current += timedelta(days=1)

        return missed <= allowed_skip_days

    def calculate_streak(
        self,
        user_id: str,
        habit_id: str,
        user_timezone: str = 'UTC',
    ) -> int | Awaitable[int]:
        """Calculate current streak for a specific habit and user with grace days and exempt weekdays support."""

        async def _impl() -> int:
            self._refresh_dependencies()
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )

            if last_log is None:
                return 1

            # Get habit settings for flexible streak tracking
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))

            last_date = last_log.last_completed_date
            today = get_user_today(user_timezone)
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

    def calculate_streak_for_date(
        self,
        user_id: str,
        habit_id: str,
        target_date: date
    ) -> int | Awaitable[int]:
        """Calculate streak for a specific target date (for backdated completions).

        This method is used when logging a habit for a past date. It calculates what
        the streak should be for that specific date, taking into account:
        - Previous completions before the target date
        - Grace days and exempt weekdays settings
        - Whether target date continues an existing streak

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            target_date: The date we're calculating the streak for (past date)

        Returns:
            Calculated streak count for the target date
        """

        async def _impl() -> int:
            self._refresh_dependencies()
            # Get the most recent log BEFORE the target date (not just any log)
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_before_date(user_id, habit_id, target_date)
            )

            # If no previous log exists, this is the first completion
            if last_log is None:
                return 1

            # Get habit settings for flexible streak tracking
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))

            last_date = last_log.last_completed_date
            day_before_target = target_date - timedelta(days=1)

            # Simple case: target date is consecutive (day after last completion)
            if last_date == day_before_target:
                # Target date continues the streak (consecutive day)
                return last_log.streak_count + 1

            # If habit not found, use strict logic (break streak for gap > 1 day)
            if not habit:
                return 1

            # Gap between last completion and day before target
            if last_date < day_before_target:
                # Calculate all dates in the gap (exclusive of both endpoints)
                current_date = last_date + timedelta(days=1)
                missed_days = 0

                while current_date < target_date:
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

            # This shouldn't happen (last_date > day_before_target means last_date >= target_date)
            # But if it does, the target date is same as or before last completion
            # This means duplicate, which should be caught earlier
            logger.warning(
                "Unexpected state in calculate_streak_for_date: last_date=%s >= target_date=%s",
                last_date,
                target_date
            )
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
        habit_id: str,
        user_timezone: str = 'UTC',
    ) -> int | Awaitable[int]:
        """Get the CURRENT streak for a habit (for display purposes).

        Returns 0 if the streak has been broken (last completion is too far in
        the past, accounting for grace days and exempt weekdays).
        """

        async def _impl() -> int:
            self._refresh_dependencies()
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )

            if last_log is None:
                return 0

            today = get_user_today(user_timezone)

            # Fetch habit settings for grace-day/exempt-weekday validation
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            allowed_skip = habit.allowed_skip_days if habit else 0
            exempt = habit.exempt_weekdays if habit else []

            if not self._is_streak_alive(last_log.last_completed_date, today, allowed_skip, exempt):
                return 0

            return last_log.streak_count

        return run_sync_or_async(_impl())

    def get_all_streaks_for_user(
        self,
        user_id: str,
        user_timezone: str = 'UTC',
    ) -> dict[str, int] | Awaitable[dict[str, int]]:
        """Get current streaks for all habits for a user.

        Returns 0 for any habit whose streak has been broken.
        """

        async def _impl() -> dict[str, int]:
            self._refresh_dependencies()
            logs = await maybe_await(self.habit_log_repo.get_logs_by_user(user_id))

            habit_streaks: dict[str, int] = {}
            processed_habits: set[str] = set()

            for log in logs:
                if log.habit_id not in processed_habits:
                    processed_habits.add(log.habit_id)
                    streak = await maybe_await(
                        self.get_current_streak(user_id, log.habit_id, user_timezone)
                    )
                    habit_streaks[log.habit_id] = streak

            return habit_streaks

        return run_sync_or_async(_impl())

    @staticmethod
    def cache_key(user_id: int | str) -> str:
        """Return the cache key for a user's validated streak map."""
        return f'streaks:{user_id}'

    def get_validated_streak_map(
        self,
        user_id: int | str,
        habits: list,
        user_timezone: str = 'UTC',
    ) -> dict[int, int] | Awaitable[dict[int, int]]:
        """Return a validated streak count for each habit in a single batch query.

        Uses one DB query via get_latest_streak_counts(), then applies
        _is_streak_alive() per habit so broken streaks show as 0.
        Results are cached for 5 minutes (keyed by user_id) and invalidated
        whenever a habit completion or revert changes the underlying data.

        Args:
            user_id: User primary key.
            habits: List of Habit model instances (must have .id, .allowed_skip_days,
                    .exempt_weekdays attributes).
            user_timezone: IANA timezone string for the user.

        Returns:
            Dict mapping habit_id (int) to validated streak count (0 if broken).
        """

        async def _impl() -> dict[int, int]:
            self._refresh_dependencies()

            key = self.cache_key(user_id)
            cached = await cache.aget(key)
            if cached is not None:
                return cached

            today = get_user_today(user_timezone)

            # Single DB round-trip: habit_id -> (streak_count, last_completed_date)
            raw = await self.habit_log_repo.get_latest_streak_counts(user_id)

            # Build a lookup of habit settings keyed by id
            habit_map = {h.id: h for h in habits}

            result: dict[int, int] = {}
            for habit in habits:
                entry = raw.get(habit.id)
                if entry is None:
                    result[habit.id] = 0
                    continue

                streak_count, last_completed_date = entry
                h = habit_map.get(habit.id)
                allowed_skip = h.allowed_skip_days if h else 0
                exempt = h.exempt_weekdays if h else []

                if self._is_streak_alive(last_completed_date, today, allowed_skip, exempt):
                    result[habit.id] = streak_count
                else:
                    result[habit.id] = 0

            await cache.aset(key, result, timeout=300)
            return result

        return run_sync_or_async(_impl())


# Global service instance
streak_service = StreakService()
