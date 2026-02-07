"""Habit log history endpoints."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencies.auth import get_current_active_user
from src.api.exceptions import NotFoundException, ForbiddenException
from src.core.models import User
from src.core.repositories import habit_log_repository, habit_repository
from src.services.habit_service import habit_service
from src.utils.async_compat import maybe_await

# Note: habit_repository is still used for ownership verification in list_habit_logs

logger = logging.getLogger(__name__)

router = APIRouter()


class HabitLogResponse(BaseModel):
    """Habit log response model."""

    id: int
    habit_id: int
    habit_name: str
    reward_id: int | None
    reward_name: str | None
    got_reward: bool
    streak_count: int
    habit_weight: int
    total_weight_applied: float
    last_completed_date: date
    timestamp: str  # ISO format datetime

    class Config:
        from_attributes = True


class HabitLogListResponse(BaseModel):
    """Habit log list response model."""

    logs: list[HabitLogResponse]
    total: int


class HabitRevertResponse(BaseModel):
    """Habit completion revert response."""

    success: bool
    habit_name: str
    reward_reverted: bool
    reward_name: str | None = None


@router.get("", response_model=HabitLogListResponse)
async def list_habit_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    start_date: date | None = Query(
        default=None, description="Filter logs from this date"
    ),
    end_date: date | None = Query(
        default=None, description="Filter logs until this date"
    ),
    habit_id: int | None = Query(default=None, description="Filter by habit ID"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of logs to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of logs to skip"),
) -> HabitLogListResponse:
    """Get habit completion history.

    Args:
        current_user: Currently authenticated user
        start_date: Optional start date filter
        end_date: Optional end date filter
        habit_id: Optional habit ID filter
        limit: Maximum logs to return (default 20, max 100)
        offset: Number of logs to skip for pagination

    Returns:
        HabitLogListResponse with list of habit logs
    """
    logger.info(
        "List habit logs for user %s (start=%s, end=%s, habit=%s, limit=%d, offset=%d)",
        current_user.id,
        start_date,
        end_date,
        habit_id,
        limit,
        offset,
    )

    # Default date range to last 30 days if not specified
    if end_date is None:
        user_tz = current_user.timezone or 'UTC'
        try:
            end_date = datetime.now(ZoneInfo(user_tz)).date()
        except (KeyError, Exception):
            end_date = datetime.now(ZoneInfo('UTC')).date()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Verify habit ownership if habit_id provided
    if habit_id:
        habit = await maybe_await(habit_repository.get_by_id(habit_id))
        if habit is None:
            raise NotFoundException(
                message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND"
            )
        if habit.user_id != current_user.id:
            raise ForbiddenException(message="Access denied", code="NOT_OWNER")

        logs = await maybe_await(
            habit_log_repository.get_logs_for_habit_in_daterange(
                current_user.id, habit_id, start_date, end_date
            )
        )
    else:
        # Get all logs for user
        logs = await maybe_await(
            habit_log_repository.get_logs_by_user(current_user.id, limit=limit + offset)
        )
        # Filter by date range
        logs = [
            log for log in logs if start_date <= log.last_completed_date <= end_date
        ]

    # Apply pagination
    total = len(logs)
    logs = logs[offset : offset + limit]

    return HabitLogListResponse(
        logs=[
            HabitLogResponse(
                id=log.id,
                habit_id=log.habit_id,
                habit_name=log.habit.name if log.habit else "Unknown",
                reward_id=log.reward_id,
                reward_name=log.reward.name if log.reward else None,
                got_reward=log.got_reward,
                streak_count=log.streak_count,
                habit_weight=log.habit_weight,
                total_weight_applied=log.total_weight_applied,
                last_completed_date=log.last_completed_date,
                timestamp=log.timestamp.isoformat(),
            )
            for log in logs
        ],
        total=total,
    )


@router.get("/{log_id}", response_model=HabitLogResponse)
async def get_habit_log(
    log_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> HabitLogResponse:
    """Get a single habit log entry.

    Args:
        log_id: Habit log primary key
        current_user: Currently authenticated user

    Returns:
        HabitLogResponse with log details

    Raises:
        NotFoundException: If log not found
        ForbiddenException: If log belongs to another user
    """
    logger.info("Get habit log %s for user %s", log_id, current_user.id)

    # Get log directly by ID
    log = await maybe_await(habit_log_repository.get_by_id(log_id))

    if log is None:
        raise NotFoundException(
            message=f"Habit log {log_id} not found", code="LOG_NOT_FOUND"
        )

    if log.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    return HabitLogResponse(
        id=log.id,
        habit_id=log.habit_id,
        habit_name=log.habit.name if log.habit else "Unknown",
        reward_id=log.reward_id,
        reward_name=log.reward.name if log.reward else None,
        got_reward=log.got_reward,
        streak_count=log.streak_count,
        habit_weight=log.habit_weight,
        total_weight_applied=log.total_weight_applied,
        last_completed_date=log.last_completed_date,
        timestamp=log.timestamp.isoformat(),
    )


@router.delete("/{log_id}", response_model=HabitRevertResponse)
async def revert_habit_completion(
    log_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> HabitRevertResponse:
    """Revert a habit completion (delete log and undo reward progress).

    This endpoint allows users to undo a habit completion. It will:
    1. Delete the habit log entry
    2. If a reward was earned, decrement the reward progress

    Args:
        log_id: Habit log primary key to revert
        current_user: Currently authenticated user

    Returns:
        HabitRevertResponse confirming the revert

    Raises:
        NotFoundException: If log not found
        ForbiddenException: If log belongs to another user
    """
    logger.info("Revert habit log %s for user %s", log_id, current_user.id)

    # Use habit service to revert the specific log by ID
    # The service handles ownership verification internally
    try:
        result = await maybe_await(
            habit_service.revert_habit_completion_by_log_id(
                user_id=current_user.id, log_id=log_id
            )
        )
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Habit revert failed for user %s on log %s: %s", current_user.id, log_id, error_msg)
        if "not found" in error_msg.lower():
            raise NotFoundException(message=error_msg, code="LOG_NOT_FOUND")
        if "access denied" in error_msg.lower():
            raise ForbiddenException(message=error_msg, code="NOT_OWNER")
        raise

    logger.info("Habit log %s reverted for user %s", log_id, current_user.id)

    return HabitRevertResponse(
        success=result.success,
        habit_name=result.habit_name,
        reward_reverted=result.reward_reverted,
        reward_name=result.reward_name,
    )
