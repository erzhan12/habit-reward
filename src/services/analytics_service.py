"""Habit performance analytics service."""

import logging
from collections import defaultdict
from datetime import date, timedelta

from src.core.repositories import habit_repository, habit_log_repository
from src.models.analytics import (
    DailyCompletion,
    HabitCompletionRate,
    HabitRanking,
    HabitTrendData,
    WeeklySummary,
)
from src.services.streak_service import streak_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating habit performance metrics."""

    def __init__(self):
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.streak_svc = streak_service

    def _refresh_dependencies(self) -> None:
        """Rebind repositories to allow test patching."""
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.streak_svc = streak_service

    # ------------------------------------------------------------------
    # Available days calculation
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_available_days(
        habit,
        start_date: date,
        end_date: date,
    ) -> int:
        """Calculate the number of days a habit was expected to be completed.

        Excludes exempt weekdays and subtracts allowed skip days proportionally.
        Returns at least 1 to avoid division by zero.
        """
        # Adjust start if habit was created after range start
        created_date = habit.created_at
        if hasattr(created_date, "date"):
            created_date = created_date.date()
        effective_start = max(start_date, created_date)
        if effective_start > end_date:
            return 0

        total_days = (end_date - effective_start).days + 1  # inclusive

        # Subtract exempt weekdays
        # Model stores weekdays as 1=Mon..7=Sun (isoweekday convention)
        exempt_weekdays = set(habit.exempt_weekdays or [])
        exempt_count = 0
        if exempt_weekdays:
            # Calculate occurrences of each weekday mathematically
            # instead of iterating through every day in the range.
            start_iso = effective_start.isoweekday()  # 1=Mon..7=Sun
            for wd in exempt_weekdays:
                # Days from effective_start to the first occurrence of wd
                offset = (wd - start_iso) % 7
                if offset < total_days:
                    exempt_count += 1 + (total_days - offset - 1) // 7

        available = total_days - exempt_count

        # Subtract allowed skip days proportionally
        allowed_skip = getattr(habit, "allowed_skip_days", 0) or 0
        if allowed_skip > 0:
            weeks_in_range = total_days / 7
            skip_allowance = int(allowed_skip * weeks_in_range)
            available -= skip_allowance

        return max(available, 1)

    # ------------------------------------------------------------------
    # Completion rates
    # ------------------------------------------------------------------

    async def get_habit_completion_rates(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[HabitCompletionRate]:
        """Get completion rate for each active habit in the date range.

        Returns list sorted by completion_rate descending.
        """
        habits = await maybe_await(self.habit_repo.get_all_active(user_id))
        if not habits:
            return []

        results: list[HabitCompletionRate] = []
        for habit in habits:
            available = self._calculate_available_days(habit, start_date, end_date)
            if available == 0:
                continue

            # Count distinct completion dates for this habit
            counts = await maybe_await(
                self.habit_log_repo.get_completion_counts_by_date(
                    user_id, start_date, end_date, habit_id=habit.id,
                )
            )
            completed_days = len(counts)  # each row = one distinct date

            rate = min(completed_days / available, 1.0)
            results.append(
                HabitCompletionRate(
                    habit_id=habit.id,
                    habit_name=habit.name,
                    completion_rate=round(rate, 4),
                    completed_days=completed_days,
                    available_days=available,
                )
            )

        results.sort(key=lambda r: r.completion_rate, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------

    async def get_habit_rankings(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        user_timezone: str = "UTC",
    ) -> list[HabitRanking]:
        """Get habits ranked by completion rate, enriched with streak data."""
        rates = await self.get_habit_completion_rates(user_id, start_date, end_date)
        if not rates:
            return []

        habit_ids = [cr.habit_id for cr in rates]

        # Batch fetch all data in 3 queries instead of 3N
        habits = await maybe_await(self.habit_repo.get_all_active(user_id))
        streak_map = await maybe_await(
            self.streak_svc.get_validated_streak_map(user_id, habits, user_timezone)
        )
        longest_map = await maybe_await(
            self.habit_log_repo.get_longest_streaks_in_range_bulk(
                user_id, habit_ids, start_date, end_date,
            )
        )
        completions_map = await maybe_await(
            self.habit_log_repo.get_total_completions_in_range_bulk(
                user_id, habit_ids, start_date, end_date,
            )
        )

        rankings: list[HabitRanking] = []
        for idx, cr in enumerate(rates, start=1):
            rankings.append(
                HabitRanking(
                    rank=idx,
                    habit_id=cr.habit_id,
                    habit_name=cr.habit_name,
                    completion_rate=cr.completion_rate,
                    total_completions=completions_map.get(cr.habit_id, 0),
                    current_streak=streak_map.get(cr.habit_id, 0),
                    longest_streak_in_range=longest_map.get(cr.habit_id, 0),
                )
            )

        return rankings

    # ------------------------------------------------------------------
    # Trends
    # ------------------------------------------------------------------

    async def get_habit_trends(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        habit_id: int | None = None,
    ) -> HabitTrendData:
        """Get daily and weekly completion trend data.

        If habit_id is None, aggregates across all active habits.
        """
        # Defense-in-depth: validate habit ownership at the service layer.
        # Also reuse the fetched habit object for available_days calculation.
        validated_habit = None
        if habit_id is not None:
            validated_habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            if validated_habit is None or validated_habit.user_id != user_id:
                raise ValueError("Invalid habit_id or access denied")

        # When aggregating across all habits, only count logs from active habits
        # so the numerator (completions) matches the denominator (available_days
        # calculated from active habits only).
        counts = await maybe_await(
            self.habit_log_repo.get_completion_counts_by_date(
                user_id, start_date, end_date,
                habit_id=habit_id,
                active_only=(habit_id is None),
            )
        )

        # Build daily data
        daily = [
            DailyCompletion(date=row["last_completed_date"], completions=row["count"])
            for row in counts
        ]

        # Build weekly summaries
        weekly_completions: dict[date, int] = defaultdict(int)
        for row in counts:
            d = row["last_completed_date"]
            # ISO week starts on Monday
            week_start = d - timedelta(days=d.weekday())
            weekly_completions[week_start] += row["count"]

        # Calculate available days per week
        if validated_habit is not None:
            habits = [validated_habit]
        else:
            habits = await maybe_await(self.habit_repo.get_all_active(user_id))

        weekly: list[WeeklySummary] = []
        for week_start in sorted(weekly_completions):
            week_end = min(week_start + timedelta(days=6), end_date)
            week_actual_start = max(week_start, start_date)

            # Sum available days across all relevant habits for this week
            total_available = 0
            for habit in habits:
                total_available += self._calculate_available_days(
                    habit, week_actual_start, week_end,
                )

            comps = weekly_completions[week_start]
            rate = min(comps / total_available, 1.0) if total_available > 0 else 0.0

            weekly.append(
                WeeklySummary(
                    week_start=week_start,
                    completions=comps,
                    available_days=total_available,
                    rate=round(rate, 4),
                )
            )

        return HabitTrendData(daily=daily, weekly=weekly)


analytics_service = AnalyticsService()
