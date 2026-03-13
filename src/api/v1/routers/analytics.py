"""Habit performance analytics endpoints."""

import logging
from datetime import date, timedelta
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies.auth import get_current_active_user
from src.api.exceptions import NotFoundException, ForbiddenException
from src.bot.timezone_utils import get_user_today
from src.core.models import User
from src.core.repositories import habit_repository
from src.models.analytics import (
    HabitCompletionRate,
    HabitRanking,
    HabitTrendData,
)
from src.services.analytics_service import analytics_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


class Period(str, Enum):
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"


PERIOD_OFFSETS = {
    Period.SEVEN_DAYS: 6,
    Period.THIRTY_DAYS: 29,
    Period.NINETY_DAYS: 89,
}

MAX_RANGE_DAYS = 365


def _resolve_date_range(
    user_timezone: str,
    period: Period | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    """Resolve period / custom dates into a concrete (start, end) pair."""
    today = get_user_today(user_timezone)

    # Reject partial custom range — both or neither must be provided
    if (start_date is None) != (end_date is None):
        raise HTTPException(status_code=400, detail="Both start_date and end_date are required for a custom range")

    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="start_date must be <= end_date")
        # Inclusive day count: end - start + 1
        inclusive_days = (end_date - start_date).days + 1
        if inclusive_days > MAX_RANGE_DAYS:
            raise HTTPException(status_code=400, detail=f"Date range must not exceed {MAX_RANGE_DAYS} days")
        return start_date, end_date

    offset = PERIOD_OFFSETS.get(period or Period.THIRTY_DAYS, 29)
    return today - timedelta(days=offset), today


@router.get("/completion-rates", response_model=list[HabitCompletionRate])
async def get_completion_rates(
    current_user: Annotated[User, Depends(get_current_active_user)],
    period: Period | None = Query(None, description="Predefined period: 7d, 30d, 90d"),
    start_date: date | None = Query(None, description="Custom range start (ISO date)"),
    end_date: date | None = Query(None, description="Custom range end (ISO date)"),
) -> list[HabitCompletionRate]:
    """Get completion rate for each active habit, sorted by rate descending."""
    tz = current_user.timezone or "UTC"
    sd, ed = _resolve_date_range(tz, period, start_date, end_date)
    logger.info("GET /completion-rates user=%s range=%s..%s", current_user.id, sd, ed)
    return await analytics_service.get_habit_completion_rates(current_user.id, sd, ed)


@router.get("/rankings", response_model=list[HabitRanking])
async def get_rankings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    period: Period | None = Query(None, description="Predefined period: 7d, 30d, 90d"),
    start_date: date | None = Query(None, description="Custom range start (ISO date)"),
    end_date: date | None = Query(None, description="Custom range end (ISO date)"),
) -> list[HabitRanking]:
    """Get habits ranked by completion rate, enriched with streak data."""
    tz = current_user.timezone or "UTC"
    sd, ed = _resolve_date_range(tz, period, start_date, end_date)
    logger.info("GET /rankings user=%s range=%s..%s", current_user.id, sd, ed)
    return await analytics_service.get_habit_rankings(current_user.id, sd, ed, user_timezone=tz)


@router.get("/trends", response_model=HabitTrendData)
async def get_trends(
    current_user: Annotated[User, Depends(get_current_active_user)],
    period: Period | None = Query(None, description="Predefined period: 7d, 30d, 90d"),
    start_date: date | None = Query(None, description="Custom range start (ISO date)"),
    end_date: date | None = Query(None, description="Custom range end (ISO date)"),
    habit_id: int | None = Query(None, description="Filter to a single habit"),
) -> HabitTrendData:
    """Get daily + weekly completion trend data."""
    tz = current_user.timezone or "UTC"
    sd, ed = _resolve_date_range(tz, period, start_date, end_date)

    # Validate habit ownership before calling the service
    if habit_id is not None:
        habit = await maybe_await(habit_repository.get_by_id(habit_id))
        if habit is None:
            raise NotFoundException(message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND")
        if habit.user_id != current_user.id:
            raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    logger.info("GET /trends user=%s range=%s..%s habit_id=%s", current_user.id, sd, ed, habit_id)
    return await analytics_service.get_habit_trends(current_user.id, sd, ed, habit_id=habit_id)