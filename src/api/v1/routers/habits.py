"""Habit management and completion endpoints."""

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.dependencies.auth import get_current_active_user, get_current_user_flexible
from src.api.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
)
from src.core.models import User
from src.core.repositories import habit_repository
from src.services.habit_service import habit_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class HabitResponse(BaseModel):
    """Habit response model."""

    id: int
    name: str
    weight: int
    category: str | None
    allowed_skip_days: int
    exempt_weekdays: list[int]
    active: bool

    class Config:
        from_attributes = True


class HabitListResponse(BaseModel):
    """Habit list response model."""

    habits: list[HabitResponse]
    total: int


class RewardProgressResponse(BaseModel):
    """Reward progress in completion result."""

    pieces_earned: int
    pieces_required: int
    claimed: bool
    progress_percent: float


class RewardResponse(BaseModel):
    """Reward in completion result."""

    id: int
    name: str
    pieces_required: int

    class Config:
        from_attributes = True


class HabitCompletionResponse(BaseModel):
    """Habit completion result response."""

    habit_confirmed: bool
    habit_name: str
    streak_count: int
    got_reward: bool
    total_weight_applied: float
    reward: RewardResponse | None = None
    cumulative_progress: RewardProgressResponse | None = None


# Request Models
class HabitCreateRequest(BaseModel):
    """Habit creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    weight: int = Field(default=10, ge=1, le=100)
    category: str | None = Field(default=None, max_length=100)
    allowed_skip_days: int = Field(default=0, ge=0, le=7)
    exempt_weekdays: list[int] = Field(default_factory=list)


class HabitUpdateRequest(BaseModel):
    """Habit update request."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    weight: int | None = Field(default=None, ge=1, le=100)
    category: str | None = None
    allowed_skip_days: int | None = Field(default=None, ge=0, le=7)
    exempt_weekdays: list[int] | None = None
    active: bool | None = None


class HabitCompleteRequest(BaseModel):
    """Habit completion request."""

    target_date: date | None = Field(
        default=None,
        description="Date to complete habit for (defaults to today, can be up to 7 days back)",
    )


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# Batch completion models
class BatchCompletionItem(BaseModel):
    """Single item in batch completion request."""

    habit_id: int
    target_date: date | None = None


class BatchCompletionRequest(BaseModel):
    """Batch habit completion request."""

    completions: list[BatchCompletionItem]


class BatchCompletionError(BaseModel):
    """Error in batch completion."""

    habit_id: int
    error: str


class BatchCompletionResponse(BaseModel):
    """Batch completion response."""

    results: list[HabitCompletionResponse]
    errors: list[BatchCompletionError]


# Endpoints
@router.get("", response_model=HabitListResponse)
async def list_habits(
    current_user: Annotated[User, Depends(get_current_active_user)],
    active: bool = Query(default=True, description="Filter by active status"),
    category: str | None = Query(default=None, description="Filter by category"),
) -> HabitListResponse:
    """List all habits for current user.

    Args:
        current_user: Currently authenticated user
        active: Filter by active status (default: True)
        category: Optional category filter

    Returns:
        HabitListResponse with list of habits
    """
    logger.info(
        "List habits request for user %s (active=%s, category=%s)",
        current_user.id,
        active,
        category,
    )

    # Use get_all with active filter to properly return active or inactive habits
    habits = await maybe_await(habit_repository.get_all(current_user.id, active=active))

    # Filter by category if specified
    if category:
        habits = [h for h in habits if h.category == category]

    return HabitListResponse(
        habits=[
            HabitResponse(
                id=h.id,
                name=h.name,
                weight=h.weight,
                category=h.category,
                allowed_skip_days=h.allowed_skip_days,
                exempt_weekdays=h.exempt_weekdays or [],
                active=h.active,
            )
            for h in habits
        ],
        total=len(habits),
    )


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> HabitResponse:
    """Get a single habit by ID.

    Args:
        habit_id: Habit primary key
        current_user: Currently authenticated user

    Returns:
        HabitResponse with habit details

    Raises:
        NotFoundException: If habit not found
        ForbiddenException: If habit belongs to another user
    """
    logger.info("Get habit %s request for user %s", habit_id, current_user.id)

    habit = await maybe_await(habit_repository.get_by_id(habit_id))

    if habit is None:
        raise NotFoundException(
            message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND"
        )

    if habit.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    return HabitResponse(
        id=habit.id,
        name=habit.name,
        weight=habit.weight,
        category=habit.category,
        allowed_skip_days=habit.allowed_skip_days,
        exempt_weekdays=habit.exempt_weekdays or [],
        active=habit.active,
    )


@router.post("", response_model=HabitResponse, status_code=201)
async def create_habit(
    request: HabitCreateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> HabitResponse:
    """Create a new habit.

    Args:
        request: Habit creation data
        current_user: Currently authenticated user

    Returns:
        HabitResponse with created habit

    Raises:
        ConflictException: If habit name already exists for user
    """
    logger.info("Create habit request for user %s: %s", current_user.id, request.name)

    # Check for duplicate name
    existing = await maybe_await(
        habit_repository.get_by_name(current_user.id, request.name)
    )
    if existing:
        logger.warning("Habit creation failed: duplicate name '%s' for user %s", request.name, current_user.id)
        raise ConflictException(
            message=f"Habit '{request.name}' already exists", code="HABIT_EXISTS"
        )

    # Validate exempt_weekdays (should be 1-7, ISO weekday format)
    if request.exempt_weekdays:
        invalid_days = [d for d in request.exempt_weekdays if d < 1 or d > 7]
        if invalid_days:
            logger.warning("Habit creation failed: invalid weekdays %s for user %s", invalid_days, current_user.id)
            raise ValidationException(
                message=f"Invalid weekday numbers: {invalid_days}. Must be 1-7 (Mon-Sun, ISO format)",
                code="INVALID_WEEKDAYS",
            )

    habit = await maybe_await(
        habit_repository.create(
            {
                "user_id": current_user.id,
                "name": request.name,
                "weight": request.weight,
                "category": request.category,
                "allowed_skip_days": request.allowed_skip_days,
                "exempt_weekdays": request.exempt_weekdays,
                "active": True,
            }
        )
    )

    logger.info(
        "Habit created: %s (id=%s) for user %s", habit.name, habit.id, current_user.id
    )

    return HabitResponse(
        id=habit.id,
        name=habit.name,
        weight=habit.weight,
        category=habit.category,
        allowed_skip_days=habit.allowed_skip_days,
        exempt_weekdays=habit.exempt_weekdays or [],
        active=habit.active,
    )


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: int,
    request: HabitUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> HabitResponse:
    """Update a habit.

    Args:
        habit_id: Habit primary key
        request: Fields to update
        current_user: Currently authenticated user

    Returns:
        HabitResponse with updated habit

    Raises:
        NotFoundException: If habit not found
        ForbiddenException: If habit belongs to another user
        ConflictException: If new name already exists
    """
    logger.info("Update habit %s request for user %s", habit_id, current_user.id)

    habit = await maybe_await(habit_repository.get_by_id(habit_id))

    if habit is None:
        raise NotFoundException(
            message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND"
        )

    if habit.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Check for name conflict if name is being updated
    if request.name and request.name != habit.name:
        existing = await maybe_await(
            habit_repository.get_by_name(current_user.id, request.name)
        )
        if existing:
            logger.warning("Habit update failed: duplicate name '%s' for user %s", request.name, current_user.id)
            raise ConflictException(
                message=f"Habit '{request.name}' already exists", code="HABIT_EXISTS"
            )

    # Validate exempt_weekdays if provided (ISO weekday format: 1-7)
    if request.exempt_weekdays:
        invalid_days = [d for d in request.exempt_weekdays if d < 1 or d > 7]
        if invalid_days:
            logger.warning("Habit update failed: invalid weekdays %s for user %s", invalid_days, current_user.id)
            raise ValidationException(
                message=f"Invalid weekday numbers: {invalid_days}. Must be 1-7 (Mon-Sun, ISO format)",
                code="INVALID_WEEKDAYS",
            )

    # Build update dict
    update_dict = {}
    if request.name is not None:
        update_dict["name"] = request.name
    if request.weight is not None:
        update_dict["weight"] = request.weight
    if request.category is not None:
        update_dict["category"] = request.category
    if request.allowed_skip_days is not None:
        update_dict["allowed_skip_days"] = request.allowed_skip_days
    if request.exempt_weekdays is not None:
        update_dict["exempt_weekdays"] = request.exempt_weekdays
    if request.active is not None:
        update_dict["active"] = request.active

    if update_dict:
        habit = await maybe_await(habit_repository.update(habit_id, update_dict))
        logger.info("Habit %s updated: %s", habit_id, list(update_dict.keys()))

    return HabitResponse(
        id=habit.id,
        name=habit.name,
        weight=habit.weight,
        category=habit.category,
        allowed_skip_days=habit.allowed_skip_days,
        exempt_weekdays=habit.exempt_weekdays or [],
        active=habit.active,
    )


@router.delete("/{habit_id}", response_model=MessageResponse)
async def delete_habit(
    habit_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> MessageResponse:
    """Soft delete a habit (set active=False).

    Args:
        habit_id: Habit primary key
        current_user: Currently authenticated user

    Returns:
        MessageResponse confirming deletion

    Raises:
        NotFoundException: If habit not found
        ForbiddenException: If habit belongs to another user
    """
    logger.info("Delete habit %s request for user %s", habit_id, current_user.id)

    habit = await maybe_await(habit_repository.get_by_id(habit_id))

    if habit is None:
        raise NotFoundException(
            message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND"
        )

    if habit.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    await maybe_await(habit_repository.soft_delete(habit_id))
    logger.info("Habit %s soft deleted for user %s", habit_id, current_user.id)

    return MessageResponse(message="Habit deleted")


@router.post("/{habit_id}/complete", response_model=HabitCompletionResponse)
async def complete_habit(
    habit_id: int,
    request: HabitCompleteRequest,
    current_user: Annotated[User, Depends(get_current_user_flexible)],
) -> HabitCompletionResponse:
    """Complete a habit and receive reward.

    Args:
        habit_id: Habit primary key
        request: Completion request with optional target_date
        current_user: Currently authenticated user

    Returns:
        HabitCompletionResponse with completion details and reward

    Raises:
        NotFoundException: If habit not found
        ForbiddenException: If habit belongs to another user
        ConflictException: If habit already completed on target_date
    """
    logger.info(
        "Complete habit %s request for user %s (target_date=%s)",
        habit_id,
        current_user.id,
        request.target_date,
    )

    # Get habit first to verify ownership
    habit = await maybe_await(habit_repository.get_by_id(habit_id))

    if habit is None:
        raise NotFoundException(
            message=f"Habit {habit_id} not found", code="HABIT_NOT_FOUND"
        )

    if habit.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Process completion through service
    try:
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=current_user.telegram_id,
                habit_name=habit.name,
                target_date=request.target_date,
                user_timezone=current_user.timezone or "UTC",
            )
        )
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Habit completion failed for user %s on habit %s: %s", current_user.id, habit_id, error_msg)
        if "already completed" in error_msg.lower():
            raise ConflictException(message=error_msg, code="ALREADY_COMPLETED")
        raise

    # Build response
    reward_response = None
    if result.reward and result.got_reward:
        reward_response = RewardResponse(
            id=result.reward.id,
            name=result.reward.name,
            pieces_required=result.reward.pieces_required,
        )

    progress_response = None
    if result.cumulative_progress:
        progress = result.cumulative_progress
        progress_response = RewardProgressResponse(
            pieces_earned=progress.pieces_earned,
            pieces_required=progress.get_pieces_required()
            if hasattr(progress, "get_pieces_required")
            else progress.pieces_required,
            claimed=progress.claimed,
            progress_percent=progress.progress_percent
            if hasattr(progress, "progress_percent")
            else progress.get_progress_percent(),
        )

    logger.info(
        "Habit %s completed for user %s (streak=%d, got_reward=%s)",
        habit_id,
        current_user.id,
        result.streak_count,
        result.got_reward,
    )

    return HabitCompletionResponse(
        habit_confirmed=result.habit_confirmed,
        habit_name=result.habit_name,
        streak_count=result.streak_count,
        got_reward=result.got_reward,
        total_weight_applied=result.total_weight_applied,
        reward=reward_response,
        cumulative_progress=progress_response,
    )


@router.post("/batch-complete", response_model=BatchCompletionResponse)
async def batch_complete_habits(
    request: BatchCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user_flexible)],
) -> BatchCompletionResponse:
    """Complete multiple habits at once.

    Args:
        request: Batch completion request with list of habits to complete
        current_user: Currently authenticated user

    Returns:
        BatchCompletionResponse with results and errors
    """
    logger.info(
        "Batch complete request for user %s: %d habits",
        current_user.id,
        len(request.completions),
    )

    results = []
    errors = []

    for item in request.completions:
        try:
            # Get habit first to verify ownership
            habit = await maybe_await(habit_repository.get_by_id(item.habit_id))

            if habit is None:
                errors.append(
                    BatchCompletionError(
                        habit_id=item.habit_id, error=f"Habit {item.habit_id} not found"
                    )
                )
                continue

            if habit.user_id != current_user.id:
                errors.append(
                    BatchCompletionError(habit_id=item.habit_id, error="Access denied")
                )
                continue

            # Process completion
            result = await maybe_await(
                habit_service.process_habit_completion(
                    user_telegram_id=current_user.telegram_id,
                    habit_name=habit.name,
                    target_date=item.target_date,
                    user_timezone=current_user.timezone or "UTC",
                )
            )

            # Build response
            reward_response = None
            if result.reward and result.got_reward:
                reward_response = RewardResponse(
                    id=result.reward.id,
                    name=result.reward.name,
                    pieces_required=result.reward.pieces_required,
                )

            progress_response = None
            if result.cumulative_progress:
                progress = result.cumulative_progress
                progress_response = RewardProgressResponse(
                    pieces_earned=progress.pieces_earned,
                    pieces_required=progress.get_pieces_required()
                    if hasattr(progress, "get_pieces_required")
                    else progress.pieces_required,
                    claimed=progress.claimed,
                    progress_percent=progress.progress_percent
                    if hasattr(progress, "progress_percent")
                    else progress.get_progress_percent(),
                )

            results.append(
                HabitCompletionResponse(
                    habit_confirmed=result.habit_confirmed,
                    habit_name=result.habit_name,
                    streak_count=result.streak_count,
                    got_reward=result.got_reward,
                    total_weight_applied=result.total_weight_applied,
                    reward=reward_response,
                    cumulative_progress=progress_response,
                )
            )

        except Exception as e:
            error_msg = str(e)
            logger.warning("Batch completion error for user %s on habit %s: %s", current_user.id, item.habit_id, error_msg)
            errors.append(BatchCompletionError(habit_id=item.habit_id, error=error_msg))

    logger.info(
        "Batch complete finished for user %s: %d success, %d errors",
        current_user.id,
        len(results),
        len(errors),
    )

    return BatchCompletionResponse(results=results, errors=errors)
