"""Analytics page view."""

import asyncio
import logging
from datetime import timedelta

from django.contrib import messages
from django.shortcuts import redirect
from inertia import render as inertia_render

from src.bot.timezone_utils import get_user_today
from src.services.analytics_service import analytics_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

PERIOD_OFFSETS = {"7d": 6, "30d": 29, "90d": 89}
VALID_PERIODS = set(PERIOD_OFFSETS.keys())


async def analytics_page(request):
    """Habit performance analytics page."""
    user = request.user
    tz = user.timezone or "UTC"
    today = get_user_today(tz)

    period = request.GET.get("period", "30d")
    if period not in VALID_PERIODS:
        period = "30d"

    offset = PERIOD_OFFSETS[period]
    start_date = today - timedelta(days=offset)
    end_date = today

    try:
        rates, rankings, trends = await asyncio.gather(
            maybe_await(analytics_service.get_habit_completion_rates(user.id, start_date, end_date)),
            maybe_await(analytics_service.get_habit_rankings(user.id, start_date, end_date, user_timezone=tz)),
            maybe_await(analytics_service.get_habit_trends(user.id, start_date, end_date)),
        )
    except Exception:
        logger.exception("Failed to load analytics for user %s", user.id)
        messages.error(request, "Failed to load analytics. Please try again.")
        return redirect("/")

    # Compute summary stats
    if rates:
        avg_rate = sum(r.completion_rate for r in rates) / len(rates)
        total_completions = sum(r.completed_days for r in rates)
        total_available = sum(r.available_days for r in rates)
        best = max(rates, key=lambda r: r.completion_rate)
        best_habit = {"name": best.habit_name, "rate": best.completion_rate}
    else:
        avg_rate = 0
        total_completions = 0
        total_available = 0
        best_habit = None

    return inertia_render(request, "Analytics", props={
        "rates": [r.model_dump() for r in rates],
        "rankings": [r.model_dump() for r in rankings],
        "trends": {
            "daily": [{"date": str(d.date), "completions": d.completions} for d in trends.daily],
            "weekly": [
                {
                    "week_start": str(w.week_start),
                    "completions": w.completions,
                    "available_days": w.available_days,
                    "rate": w.rate,
                }
                for w in trends.weekly
            ],
        },
        "summary": {
            "avgCompletionRate": avg_rate,
            "totalCompletions": total_completions,
            "bestHabit": best_habit,
            "totalAvailableDays": total_available,
        },
        "currentPeriod": period,
    })
