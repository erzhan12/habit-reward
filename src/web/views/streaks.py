"""Streaks overview view."""

import logging
from datetime import timedelta

from inertia import render as inertia_render

from src.bot.timezone_utils import get_user_today
from src.core.repositories import habit_log_repository
from src.services.habit_service import habit_service
from src.services.streak_service import streak_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


async def streaks_page(request):
    """Streaks & progress overview."""
    user = request.user
    if not user.timezone:
        logger.warning("User %s has no timezone set, falling back to UTC", user.id)
    today = get_user_today(user.timezone or "UTC")
    week_start = today - timedelta(days=today.weekday())  # Monday

    all_habits = await maybe_await(habit_service.get_all_active_habits(user.id))

    # Batch queries via repository (avoids N+1)
    total_completions = await habit_log_repository.get_total_count_by_user(
        str(user.id)
    )
    streak_stats = await habit_log_repository.get_habit_streak_stats(
        str(user.id), week_start, today
    )

    # Index stats by habit_id for O(1) lookup
    stats_by_habit = {
        s["habit_id"]: s for s in streak_stats
    }

    habits = []
    best_streak_habit = None
    best_streak_count = 0

    for habit in all_habits:
        current_streak = await maybe_await(
            streak_service.get_current_streak(str(user.id), str(habit.id), user.timezone or "UTC")
        )
        stats = stats_by_habit.get(habit.id, {})

        if current_streak > best_streak_count:
            best_streak_count = current_streak
            best_streak_habit = habit.name

        habits.append({
            "id": habit.id,
            "name": habit.name,
            "currentStreak": current_streak,
            "longestStreak": stats.get("longest_streak") or 0,
            "weight": habit.weight,
            "completionsThisWeek": stats.get("week_completions") or 0,
        })

    # Sort by current streak descending
    habits.sort(key=lambda h: h["currentStreak"], reverse=True)

    return inertia_render(request, "Streaks", props={
        "habits": habits,
        "summary": {
            "totalCompletions": total_completions,
            "activeHabits": len(all_habits),
            "bestStreak": {
                "habitName": best_streak_habit or "N/A",
                "count": best_streak_count,
            },
        },
    })
