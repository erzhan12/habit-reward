"""Dashboard view — Today's habits with completion status."""

import logging
from datetime import date

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
from src.services.transactions import ServiceBusyError
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
    log_map = {log.habit_id: log for log in todays_logs}

    # Batch-fetch streak states (streak 0 if broken; freezes spent or predicted)
    states = await maybe_await(
        streak_service.get_streak_states(user.id, all_habits, tz)
    )

    # Build habit list with streak and completion info
    habits = []
    completed_count = 0
    total_points = 0

    for habit in all_habits:
        state = states.get(habit.id)
        streak = state.streak if state else 0
        is_completed = habit.id in completed_habit_ids
        if is_completed:
            completed_count += 1
            total_points += habit.weight

        log = log_map.get(habit.id)
        today_result = None
        if is_completed and log is not None:
            reward_name = log.reward.name if log.reward_id and log.reward else None
            today_result = {"gotReward": log.got_reward, "rewardName": reward_name}
            # The chance that actually applied: the stored no-reward % snapshot.
            reward_chance = round(100 - log.total_weight_applied)
        else:
            # Chance of the next completion (feature 0048: streak only).
            next_streak = state.next_streak if state else 1
            reward_chance = round(reward_service.calculate_reward_chance(next_streak))

        habits.append({
            "id": habit.id,
            "name": habit.name,
            "weight": habit.weight,
            "streak": streak,
            "completedToday": is_completed,
            "rewardChance": reward_chance,
            "todayResult": today_result,
            "freezeCount": state.freeze_count if state else 0,
            "freezeUsedFor": state.freeze_used_for.isoformat() if state and state.freeze_used_for else None,
            "freezeAtRisk": bool(state and state.freeze_at_risk),
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


def _web_date(day) -> str:
    """Short web date label, e.g. "17 Nov"."""
    return f"{day.day} {day.strftime('%b')}"


def _freeze_flash(result) -> tuple[dict, str]:
    """Freeze fields and text lines for the completion flash (feature 0048).

    Compares with ``is True``: tests pass Mock results whose attributes are truthy
    and not JSON-serialisable, and the session must stay JSON.
    """
    covered = result.freeze_covered_date
    covered = covered if isinstance(covered, date) else None
    fields = {
        "freeze_won": result.freeze_won is True,
        "freeze_used": result.freeze_used is True and covered is not None,
        "freeze_burned": result.freeze_burned is True and covered is not None,
        "freeze_covered_date": covered.isoformat() if covered else None,
    }
    lines = []
    if fields["freeze_used"]:
        lines.append(f"❄️ Freeze covered {_web_date(covered)} — streak saved.")
    elif fields["freeze_burned"]:
        lines.append(f"❄️ Freeze was used for {_web_date(covered)}, but you missed more days — streak reset.")
    if fields["freeze_won"]:
        lines.append("❄️ You earned a streak freeze!")
    if result.freeze_returned is True:
        lines.append("❄️ Freeze returned.")
    return fields, "".join(f" {line}" for line in lines)


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
        freeze_fields, freeze_text = _freeze_flash(result)
        if result.got_reward and result.reward:
            reward_message = f"Reward: {result.reward.name}"
            pieces_earned = None
            pieces_required = None
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

            flash_data = {
                "text": f"Habit completed. {reward_message}{freeze_text}",
                "got_reward": True,
                "reward_name": result.reward.name,
            }
            if pieces_earned is not None:
                flash_data["pieces_earned"] = pieces_earned
            if pieces_required is not None:
                flash_data["pieces_required"] = pieces_required
            request.session["_completion_flash"] = {**flash_data, **freeze_fields}
        else:
            request.session["_completion_flash"] = {
                "text": f"Habit completed. No reward this time.{freeze_text}",
                "got_reward": False,
                **freeze_fields,
            }
    except ValueError as e:
        logger.warning("Habit completion failed: %s", e)
        messages.error(request, str(e))
    except ServiceBusyError:
        logger.warning("Habit completion busy for user %s", user.id)
        messages.error(request, "Busy, please try again.")

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
        revoked_text = " Earned freeze removed." if result.freeze_revoked is True else ""
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
            messages.info(request, f"{reward_message}{revoked_text}")
        else:
            messages.success(request, f"Habit undone.{revoked_text}")
    except ValueError as e:
        logger.warning("Habit revert failed: %s", e)
        messages.error(request, str(e))
    except ServiceBusyError:
        logger.warning("Habit revert busy for user %s", user.id)
        messages.error(request, "Busy, please try again.")

    return redirect("/")
