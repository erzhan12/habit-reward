"""Habit history / calendar view."""

import logging
from datetime import date

from inertia import render as inertia_render

from src.bot.timezone_utils import get_user_today
from src.core.repositories import habit_log_repository
from src.services.habit_service import habit_service
from src.utils.async_compat import run_sync_or_async

logger = logging.getLogger(__name__)


def history_page(request):
    """Calendar history view showing habit completions by month."""
    user = request.user

    # Parse month from query params (default: current month in user's timezone)
    if not user.timezone:
        logger.warning("User %s has no timezone set, falling back to UTC", user.id)
    user_today = get_user_today(user.timezone or "UTC")
    month_str = request.GET.get("month")
    if month_str:
        try:
            year, month = month_str.split("-")
            current_date = date(int(year), int(month), 1)
        except (ValueError, TypeError):
            current_date = user_today.replace(day=1)
    else:
        current_date = user_today.replace(day=1)

    # Calculate month boundaries
    if current_date.month == 12:
        next_month = current_date.replace(year=current_date.year + 1, month=1)
    else:
        next_month = current_date.replace(month=current_date.month + 1)

    all_habits = habit_service.get_all_active_habits(user.id)

    # Optional habit filter
    habit_filter = request.GET.get("habit")
    habit_id = None
    if habit_filter:
        try:
            habit_id = int(habit_filter)
        except (ValueError, TypeError):
            pass

    # Query logs for this month via repository
    logs = run_sync_or_async(
        habit_log_repository.get_logs_in_daterange(
            str(user.id), current_date, next_month, habit_id=habit_id
        )
    )

    # Group completions by habit_id -> list of date strings
    completions = {}
    for log in logs:
        hid = log.habit_id
        date_str = log.last_completed_date.isoformat()
        if hid not in completions:
            completions[hid] = []
        completions[hid].append(date_str)

    habits_list = [{"id": h.id, "name": h.name} for h in all_habits]

    return inertia_render(request, "History", props={
        "currentMonth": current_date.strftime("%Y-%m"),
        "completions": completions,
        "habits": habits_list,
        "selectedHabit": habit_filter,
        "userToday": user_today.isoformat(),
    })
