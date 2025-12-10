"""Streak information endpoints."""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies.auth import get_current_active_user
from src.api.exceptions import NotFoundException, ForbiddenException
from src.core.models import User
from src.core.repositories import habit_repository, habit_log_repository
from src.services.streak_service import streak_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


class HabitStreakResponse(BaseModel):
    """Habit streak response model."""
    habit_id: int
    habit_name: str
    current_streak: int
    last_completed: date | None


class HabitStreakDetailResponse(BaseModel):
    """Detailed habit streak response."""
    habit_id: int
    habit_name: str
    current_streak: int
    longest_streak: int
    last_completed: date | None


class StreakListResponse(BaseModel):
    """Streak list response."""
    streaks: list[HabitStreakResponse]
    total: int


@router.get("", response_model=StreakListResponse)
async def get_all_streaks(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> StreakListResponse:
    """Get current streaks for all habits.

    Returns current streak counts for all active habits belonging to the user.

    Args:
        current_user: Currently authenticated user

    Returns:
        StreakListResponse with all habit streaks
    """
    logger.info("Get all streaks for user %s", current_user.id)

    # Get all active habits
    habits = await maybe_await(habit_repository.get_all_active(current_user.id))

    streaks = []
    for habit in habits:
        # Get current streak
        current_streak = await maybe_await(
            streak_service.get_current_streak(current_user.id, habit.id)
        )

        # Get last completed date
        last_completed = await maybe_await(
            streak_service.get_last_completed_date(current_user.id, habit.id)
        )

        streaks.append(HabitStreakResponse(
            habit_id=habit.id,
            habit_name=habit.name,
            current_streak=current_streak,
            last_completed=last_completed
        ))

    return StreakListResponse(streaks=streaks, total=len(streaks))


@router.get("/{habit_id}", response_model=HabitStreakDetailResponse)
async def get_habit_streak(
    habit_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> HabitStreakDetailResponse:
    """Get detailed streak information for a specific habit.

    Includes current streak, longest streak ever, and last completion date.

    Args:
        habit_id: Habit primary key
        current_user: Currently authenticated user

    Returns:
        HabitStreakDetailResponse with detailed streak info

    Raises:
        NotFoundException: If habit not found
        ForbiddenException: If habit belongs to another user
    """
    logger.info("Get streak for habit %s, user %s", habit_id, current_user.id)

    habit = await maybe_await(habit_repository.get_by_id(habit_id))

    if habit is None:
        raise NotFoundException(message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND")

    if habit.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Get current streak
    current_streak = await maybe_await(
        streak_service.get_current_streak(current_user.id, habit_id)
    )

    # Get last completed date
    last_completed = await maybe_await(
        streak_service.get_last_completed_date(current_user.id, habit_id)
    )

    # Calculate longest streak from all logs
    logs = await maybe_await(
        habit_log_repository.get_logs_by_user(current_user.id, limit=1000)
    )
    habit_logs = [log for log in logs if log.habit_id == habit_id]

    longest_streak = 0
    if habit_logs:
        longest_streak = max(log.streak_count for log in habit_logs)

    return HabitStreakDetailResponse(
        habit_id=habit.id,
        habit_name=habit.name,
        current_streak=current_streak,
        longest_streak=longest_streak,
        last_completed=last_completed
    )
