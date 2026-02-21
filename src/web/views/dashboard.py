"""Dashboard view — Today's habits with completion status."""

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from inertia import render as inertia_render

from src.bot.timezone_utils import get_user_today
from src.core.repositories import habit_log_repository
from src.services.habit_service import habit_service
from src.services.streak_service import streak_service
from src.utils.async_compat import run_sync_or_async

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main screen: list of today's habits with completion status."""
    user = request.user
    today = get_user_today(user.timezone or "UTC")

    # Services handle sync/async bridging internally
    all_habits = habit_service.get_all_active_habits(user.id)

    # Repository calls are async — need run_sync_or_async
    todays_logs = run_sync_or_async(
        habit_log_repository.get_todays_logs_by_user(str(user.id), target_date=today)
    )
    completed_habit_ids = {log.habit_id for log in todays_logs}

    # Build habit list with streak and completion info
    habits = []
    completed_count = 0
    total_points = 0

    for habit in all_habits:
        streak = streak_service.get_current_streak(str(user.id), str(habit.id))
        is_completed = habit.id in completed_habit_ids
        if is_completed:
            completed_count += 1
            total_points += habit.weight

        habits.append({
            "id": habit.id,
            "name": habit.name,
            "weight": habit.weight,
            "streak": streak,
            "completedToday": is_completed,
        })

    # Sort: incomplete first, then completed
    habits.sort(key=lambda h: h["completedToday"])

    return inertia_render(request, "Dashboard", props={
        "habits": habits,
        "stats": {
            "completedToday": completed_count,
            "totalToday": len(all_habits),
            "totalPointsToday": total_points,
        },
    })


@require_POST
def complete_habit(request, habit_id):
    """Mark a habit as completed for today."""
    user = request.user

    habit = habit_service.get_habit_by_id(user.id, habit_id)
    if not habit:
        return redirect("/")

    try:
        habit_service.process_habit_completion(
            user_telegram_id=user.telegram_id,
            habit_name=habit.name,
            user_timezone=user.timezone or "UTC",
        )
    except ValueError as e:
        logger.warning("Habit completion failed: %s", e)
        messages.error(request, str(e))

    return redirect("/")


@require_POST
def revert_habit(request, habit_id):
    """Revert the most recent completion of a habit."""
    user = request.user

    try:
        habit_service.revert_habit_completion(
            user_telegram_id=user.telegram_id,
            habit_id=habit_id,
        )
    except ValueError as e:
        logger.warning("Habit revert failed: %s", e)
        messages.error(request, str(e))

    return redirect("/")
