"""Dashboard view — Today's habits with completion status."""

import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django_ratelimit.core import is_ratelimited

from inertia import render as inertia_render

from asgiref.sync import sync_to_async
from src.bot.timezone_utils import get_user_today
from src.core.repositories import habit_log_repository
from src.services.habit_service import habit_service
from src.services.reward_service import reward_service
from src.services.streak_service import streak_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


async def dashboard(request):
    """Main screen: list of today's habits with completion status."""
    user = request.user
    tz = user.timezone or "UTC"
    if not user.timezone:
        logger.warning("User %s has no timezone set, falling back to UTC", user.id)
    today = get_user_today(tz)

    # In async context, service returns coroutine via run_sync_or_async
    all_habits = await maybe_await(habit_service.get_all_active_habits(user.id))

    # Repository calls are async — await directly
    todays_logs = await habit_log_repository.get_todays_logs_by_user(
        str(user.id), target_date=today
    )
    completed_habit_ids = {log.habit_id for log in todays_logs}

    # Batch-fetch validated streaks (1 query; returns 0 for broken streaks)
    streak_map = await maybe_await(
        streak_service.get_validated_streak_map(user.id, all_habits, tz)
    )

    # Build habit list with streak and completion info
    habits = []
    completed_count = 0
    total_points = 0

    base_no_reward = float(user.no_reward_probability)

    for habit in all_habits:
        streak = streak_map.get(habit.id, 0)
        is_completed = habit.id in completed_habit_ids
        if is_completed:
            completed_count += 1
            total_points += habit.weight

        effective_no_reward = reward_service.calculate_effective_no_reward_probability(
            base_no_reward=base_no_reward,
            habit_weight=habit.weight,
            streak_count=streak,
        )
        reward_chance = round(100 - effective_no_reward)

        habits.append({
            "id": habit.id,
            "name": habit.name,
            "weight": habit.weight,
            "streak": streak,
            "completedToday": is_completed,
            "rewardChance": reward_chance,
        })

    # Sort: incomplete first, then completed
    habits.sort(key=lambda h: h["completedToday"])

    completion_flash = request.session.pop("_completion_flash", None)

    return inertia_render(request, "Dashboard", props={
        "habits": habits,
        "stats": {
            "completedToday": completed_count,
            "totalToday": len(all_habits),
            "totalPointsToday": total_points,
        },
        "completionFlash": completion_flash,
    })


def _dashboard_action_ratelimited(request):  # Sync helper for cache access from async view
    return is_ratelimited(
        request,
        group="dashboard_action",
        key="user",
        rate=settings.DASHBOARD_ACTION_RATE_LIMIT,
        method="POST",
        increment=True,
    )


@require_POST
async def complete_habit(request, habit_id):
    """Mark a habit as completed for today."""
    if await sync_to_async(_dashboard_action_ratelimited)(request):
        messages.error(request, "Too many requests. Please wait a moment and try again.")
        return redirect("/")

    try:
        habit_id = int(habit_id)
    except (ValueError, TypeError):
        logger.warning("Invalid habit_id format: %s", habit_id)
        messages.error(request, "Invalid habit ID")
        return redirect("/")

    user = request.user

    habit = await maybe_await(habit_service.get_habit_by_id(user.id, habit_id))
    if not habit:
        logger.warning("User %s attempted to complete habit %s (not found or unauthorized)", user.id, habit_id)
        return redirect("/")

    try:
        result = await maybe_await(habit_service.process_habit_completion(
            user_telegram_id=user.telegram_id,
            habit_name=habit.name,
            user_timezone=user.timezone or "UTC",
        ))
        if result.got_reward and result.reward:
            reward_message = f"Reward: {result.reward.name}"
            if result.cumulative_progress:
                pieces_required = (
                    result.cumulative_progress.get_pieces_required()
                    if hasattr(result.cumulative_progress, "get_pieces_required")
                    else getattr(result.cumulative_progress, "pieces_required", None)
                )
                pieces_earned = getattr(result.cumulative_progress, "pieces_earned", None)
                if pieces_required is not None and pieces_earned is not None:
                    reward_message = (
                        f"{reward_message} ({pieces_earned}/{pieces_required})"
                    )

            request.session["_completion_flash"] = {
                "text": f"Habit completed. {reward_message}",
                "got_reward": True,
            }
        else:
            request.session["_completion_flash"] = {
                "text": "Habit completed. No reward this time.",
                "got_reward": False,
            }
    except ValueError as e:
        logger.warning("Habit completion failed: %s", e)
        messages.error(request, str(e))

    return redirect("/")


@require_POST
async def revert_habit(request, habit_id):
    """Revert the most recent completion of a habit."""
    if await sync_to_async(_dashboard_action_ratelimited)(request):
        messages.error(request, "Too many requests. Please wait a moment and try again.")
        return redirect("/")

    try:
        habit_id = int(habit_id)
    except (ValueError, TypeError):
        logger.warning("Invalid habit_id format: %s", habit_id)
        messages.error(request, "Invalid habit ID")
        return redirect("/")

    user = request.user

    habit = await maybe_await(habit_service.get_habit_by_id(user.id, habit_id))
    if not habit:
        logger.warning("User %s attempted to revert habit %s (not found or unauthorized)", user.id, habit_id)
        return redirect("/")

    try:
        result = await maybe_await(habit_service.revert_habit_completion(
            user_telegram_id=user.telegram_id,
            habit_id=habit_id,
        ))
        if result.reward_reverted:
            reward_message = f"Habit undone. Reward removed: {result.reward_name or 'Unknown'}"
            if result.reward_progress:
                pieces_required = (
                    result.reward_progress.get_pieces_required()
                    if hasattr(result.reward_progress, "get_pieces_required")
                    else getattr(result.reward_progress, "pieces_required", None)
                )
                pieces_earned = getattr(result.reward_progress, "pieces_earned", None)
                if pieces_required is not None and pieces_earned is not None:
                    reward_message = (
                        f"{reward_message} ({pieces_earned}/{pieces_required})"
                    )
            messages.info(request, reward_message)
        else:
            messages.success(request, "Habit undone.")
    except ValueError as e:
        logger.warning("Habit revert failed: %s", e)
        messages.error(request, str(e))

    return redirect("/")
