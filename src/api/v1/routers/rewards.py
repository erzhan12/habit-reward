"""Reward management endpoints."""

import logging
from typing import Annotated

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.dependencies.auth import get_current_active_user
from src.api.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
)
from src.core.models import User, Reward as RewardModel, RewardProgress
from src.core.repositories import reward_repository, reward_progress_repository
from src.services.reward_service import reward_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class RewardResponse(BaseModel):
    """Reward response model."""

    id: int
    name: str
    weight: float
    type: str
    pieces_required: int
    piece_value: float | None
    max_daily_claims: int | None
    active: bool

    class Config:
        from_attributes = True


class RewardProgressResponse(BaseModel):
    """Reward progress response model."""

    reward_id: int
    pieces_earned: int
    pieces_required: int
    claimed: bool
    status: str
    progress_percent: float


class RewardWithProgressResponse(BaseModel):
    """Reward with progress response."""

    reward: RewardResponse
    progress: RewardProgressResponse | None


class RewardListResponse(BaseModel):
    """Reward list response model."""

    rewards: list[RewardWithProgressResponse]
    total: int


class ProgressListResponse(BaseModel):
    """Progress list response model."""

    progress: list[RewardWithProgressResponse]
    total: int


# Request Models
class RewardCreateRequest(BaseModel):
    """Reward creation request."""

    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(default="virtual", pattern="^(virtual|real|none)$")
    weight: float = Field(default=1.0, gt=0, le=100)
    pieces_required: int = Field(default=1, ge=1)
    piece_value: float | None = Field(default=None, ge=0)
    max_daily_claims: int | None = Field(default=None, ge=0)


class RewardUpdateRequest(BaseModel):
    """Reward update request."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, pattern="^(virtual|real|none)$")
    weight: float | None = Field(default=None, gt=0, le=100)
    pieces_required: int | None = Field(default=None, ge=1)
    piece_value: float | None = None
    max_daily_claims: int | None = None
    active: bool | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ClaimResponse(BaseModel):
    """Reward claim response."""

    message: str
    reward: RewardResponse


def _get_status_string(progress: RewardProgress) -> str:
    """Get status string from progress object."""
    status = progress.get_status()
    if hasattr(status, "value"):
        return status.value
    return str(status)


def _build_progress_response(
    progress: RewardProgress, reward: RewardModel
) -> RewardProgressResponse:
    """Build progress response from progress and reward objects."""
    pieces_required = reward.pieces_required
    status_str = _get_status_string(progress)

    return RewardProgressResponse(
        reward_id=progress.reward_id,
        pieces_earned=progress.pieces_earned,
        pieces_required=pieces_required,
        claimed=progress.claimed,
        status=status_str,
        progress_percent=min((progress.pieces_earned / pieces_required) * 100, 100.0)
        if pieces_required > 0
        else 0.0,
    )


# Endpoints
@router.get("", response_model=RewardListResponse)
async def list_rewards(
    current_user: Annotated[User, Depends(get_current_active_user)],
    type: str | None = Query(default=None, description="Filter by reward type"),
    status: str | None = Query(
        default=None, description="Filter by progress status (pending|achieved|claimed)"
    ),
) -> RewardListResponse:
    """List all rewards for current user with progress.

    Args:
        current_user: Currently authenticated user
        type: Optional reward type filter
        status: Optional progress status filter

    Returns:
        RewardListResponse with list of rewards and their progress
    """
    logger.info(
        "List rewards for user %s (type=%s, status=%s)", current_user.id, type, status
    )

    # Get all active rewards
    rewards = await maybe_await(reward_repository.get_all_active(current_user.id))

    # Filter by type if specified
    if type:
        rewards = [r for r in rewards if r.type == type]

    # Get all progress for user
    progress_list = await maybe_await(
        reward_progress_repository.get_all_by_user(current_user.id)
    )
    progress_by_reward = {p.reward_id: p for p in progress_list}

    # Build response with progress
    result = []
    for reward in rewards:
        progress = progress_by_reward.get(reward.id)

        progress_response = None
        if progress:
            progress_response = _build_progress_response(progress, reward)

            # Filter by status if specified
            if status:
                status_value = _get_status_string(progress).lower()
                if status.lower() not in status_value:
                    continue
        elif status:
            # No progress = pending, skip if looking for achieved/claimed
            if status.lower() != "pending":
                continue

        result.append(
            RewardWithProgressResponse(
                reward=RewardResponse(
                    id=reward.id,
                    name=reward.name,
                    weight=reward.weight,
                    type=reward.type,
                    pieces_required=reward.pieces_required,
                    piece_value=float(reward.piece_value)
                    if reward.piece_value
                    else None,
                    max_daily_claims=reward.max_daily_claims,
                    active=reward.active,
                ),
                progress=progress_response,
            )
        )

    return RewardListResponse(rewards=result, total=len(result))


@router.get("/progress", response_model=ProgressListResponse)
async def get_all_progress(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ProgressListResponse:
    """Get all reward progress for current user.

    Returns:
        ProgressListResponse with all progress entries
    """
    logger.info("Get all progress for user %s", current_user.id)

    progress_list = await maybe_await(
        reward_progress_repository.get_all_by_user(current_user.id)
    )

    result = []
    for progress in progress_list:
        reward = await maybe_await(reward_repository.get_by_id(progress.reward_id))
        if reward:
            result.append(
                RewardWithProgressResponse(
                    reward=RewardResponse(
                        id=reward.id,
                        name=reward.name,
                        weight=reward.weight,
                        type=reward.type,
                        pieces_required=reward.pieces_required,
                        piece_value=float(reward.piece_value)
                        if reward.piece_value
                        else None,
                        max_daily_claims=reward.max_daily_claims,
                        active=reward.active,
                    ),
                    progress=_build_progress_response(progress, reward),
                )
            )

    return ProgressListResponse(progress=result, total=len(result))


@router.get("/{reward_id}", response_model=RewardWithProgressResponse)
async def get_reward(
    reward_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> RewardWithProgressResponse:
    """Get a single reward with progress.

    Args:
        reward_id: Reward primary key
        current_user: Currently authenticated user

    Returns:
        RewardWithProgressResponse with reward and progress details

    Raises:
        NotFoundException: If reward not found
        ForbiddenException: If reward belongs to another user
    """
    logger.info("Get reward %s for user %s", reward_id, current_user.id)

    reward = await maybe_await(reward_repository.get_by_id(reward_id))

    if reward is None:
        raise NotFoundException(
            message=f"Reward {reward_id} not found", code="REWARD_NOT_FOUND"
        )

    if reward.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    progress = await maybe_await(
        reward_progress_repository.get_by_user_and_reward(current_user.id, reward_id)
    )

    progress_response = None
    if progress:
        progress_response = _build_progress_response(progress, reward)

    return RewardWithProgressResponse(
        reward=RewardResponse(
            id=reward.id,
            name=reward.name,
            weight=reward.weight,
            type=reward.type,
            pieces_required=reward.pieces_required,
            piece_value=float(reward.piece_value) if reward.piece_value else None,
            max_daily_claims=reward.max_daily_claims,
            active=reward.active,
        ),
        progress=progress_response,
    )


@router.post("", response_model=RewardResponse, status_code=201)
async def create_reward(
    request: RewardCreateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RewardResponse:
    """Create a new reward.

    Args:
        request: Reward creation data
        current_user: Currently authenticated user

    Returns:
        RewardResponse with created reward

    Raises:
        ConflictException: If reward name already exists
    """
    logger.info("Create reward for user %s: %s", current_user.id, request.name)

    # Check for duplicate name
    existing = await maybe_await(
        reward_repository.get_by_name(current_user.id, request.name)
    )
    if existing:
        logger.warning("Reward creation failed: duplicate name '%s' for user %s", request.name, current_user.id)
        raise ConflictException(
            message=f"Reward '{request.name}' already exists", code="REWARD_EXISTS"
        )

    # Create reward using service
    reward = await maybe_await(
        reward_service.create_reward(
            user_id=current_user.id,
            name=request.name,
            reward_type=request.type,
            weight=request.weight,
            pieces_required=request.pieces_required,
            piece_value=request.piece_value,
        )
    )

    # Update max_daily_claims if provided (service doesn't handle this)
    if request.max_daily_claims is not None:
        await sync_to_async(RewardModel.objects.filter(pk=reward.id).update)(
            max_daily_claims=request.max_daily_claims
        )
        reward = await maybe_await(reward_repository.get_by_id(reward.id))

    logger.info(
        "Reward created: %s (id=%s) for user %s",
        reward.name,
        reward.id,
        current_user.id,
    )

    return RewardResponse(
        id=reward.id,
        name=reward.name,
        weight=reward.weight,
        type=reward.type,
        pieces_required=reward.pieces_required,
        piece_value=float(reward.piece_value) if reward.piece_value else None,
        max_daily_claims=reward.max_daily_claims,
        active=reward.active,
    )


@router.patch("/{reward_id}", response_model=RewardResponse)
async def update_reward(
    reward_id: int,
    request: RewardUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> RewardResponse:
    """Update a reward.

    Args:
        reward_id: Reward primary key
        request: Fields to update
        current_user: Currently authenticated user

    Returns:
        RewardResponse with updated reward

    Raises:
        NotFoundException: If reward not found
        ForbiddenException: If reward belongs to another user
        ConflictException: If new name already exists
    """
    logger.info("Update reward %s for user %s", reward_id, current_user.id)

    reward = await maybe_await(reward_repository.get_by_id(reward_id))

    if reward is None:
        raise NotFoundException(
            message=f"Reward {reward_id} not found", code="REWARD_NOT_FOUND"
        )

    if reward.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Check name conflict if changing name
    if request.name and request.name != reward.name:
        existing = await maybe_await(
            reward_repository.get_by_name(current_user.id, request.name)
        )
        if existing:
            logger.warning("Reward update failed: duplicate name '%s' for user %s", request.name, current_user.id)
            raise ConflictException(
                message=f"Reward '{request.name}' already exists", code="REWARD_EXISTS"
            )

    # Build update dict - use model_fields_set to detect explicitly provided fields
    # This allows clearing piece_value and max_daily_claims to None
    update_dict = {}
    if request.name is not None:
        update_dict["name"] = request.name
    if request.type is not None:
        update_dict["type"] = request.type
    if request.weight is not None:
        update_dict["weight"] = request.weight
    if request.pieces_required is not None:
        update_dict["pieces_required"] = request.pieces_required
    # Allow piece_value and max_daily_claims to be explicitly set to None
    if "piece_value" in request.model_fields_set:
        update_dict["piece_value"] = request.piece_value
    if "max_daily_claims" in request.model_fields_set:
        update_dict["max_daily_claims"] = request.max_daily_claims
    if request.active is not None:
        update_dict["active"] = request.active

    if update_dict:
        await sync_to_async(RewardModel.objects.filter(pk=reward_id).update)(
            **update_dict
        )
        reward = await maybe_await(reward_repository.get_by_id(reward_id))
        logger.info("Reward %s updated: %s", reward_id, list(update_dict.keys()))

    return RewardResponse(
        id=reward.id,
        name=reward.name,
        weight=reward.weight,
        type=reward.type,
        pieces_required=reward.pieces_required,
        piece_value=float(reward.piece_value) if reward.piece_value else None,
        max_daily_claims=reward.max_daily_claims,
        active=reward.active,
    )


@router.delete("/{reward_id}", response_model=MessageResponse)
async def delete_reward(
    reward_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> MessageResponse:
    """Delete a reward.

    Note: Rewards with active progress cannot be deleted.

    Args:
        reward_id: Reward primary key
        current_user: Currently authenticated user

    Returns:
        MessageResponse confirming deletion

    Raises:
        NotFoundException: If reward not found
        ForbiddenException: If reward belongs to another user
        ConflictException: If reward has active progress
    """
    logger.info("Delete reward %s for user %s", reward_id, current_user.id)

    reward = await maybe_await(reward_repository.get_by_id(reward_id))

    if reward is None:
        raise NotFoundException(
            message=f"Reward {reward_id} not found", code="REWARD_NOT_FOUND"
        )

    if reward.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Check for active progress
    progress = await maybe_await(
        reward_progress_repository.get_by_user_and_reward(current_user.id, reward_id)
    )
    if progress and progress.pieces_earned > 0:
        logger.warning("Reward deletion failed: reward %s has active progress (%d/%d pieces) for user %s", reward_id, progress.pieces_earned, reward.pieces_required, current_user.id)
        raise ConflictException(
            message="Cannot delete reward with active progress", code="HAS_PROGRESS"
        )

    # Soft delete by setting active=False
    await sync_to_async(RewardModel.objects.filter(pk=reward_id).update)(active=False)

    logger.info("Reward %s deleted for user %s", reward_id, current_user.id)

    return MessageResponse(message="Reward deleted")


@router.post("/{reward_id}/claim", response_model=ClaimResponse)
async def claim_reward(
    reward_id: int, current_user: Annotated[User, Depends(get_current_active_user)]
) -> ClaimResponse:
    """Claim an achieved reward.

    Marks the reward as claimed and resets progress for the next cycle.

    Args:
        reward_id: Reward primary key
        current_user: Currently authenticated user

    Returns:
        ClaimResponse confirming the claim

    Raises:
        NotFoundException: If reward not found
        ForbiddenException: If reward belongs to another user
        ValidationException: If reward not achieved or already claimed
    """
    logger.info("Claim reward %s for user %s", reward_id, current_user.id)

    reward = await maybe_await(reward_repository.get_by_id(reward_id))

    if reward is None:
        raise NotFoundException(
            message=f"Reward {reward_id} not found", code="REWARD_NOT_FOUND"
        )

    if reward.user_id != current_user.id:
        raise ForbiddenException(message="Access denied", code="NOT_OWNER")

    # Claim through service
    try:
        await maybe_await(
            reward_service.mark_reward_claimed(current_user.id, reward_id)
        )
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Reward claim failed for user %s on reward %s: %s", current_user.id, reward_id, error_msg)
        raise ValidationException(message=error_msg, code="CLAIM_ERROR")

    logger.info("Reward %s claimed by user %s", reward_id, current_user.id)

    return ClaimResponse(
        message="Reward claimed",
        reward=RewardResponse(
            id=reward.id,
            name=reward.name,
            weight=reward.weight,
            type=reward.type,
            pieces_required=reward.pieces_required,
            piece_value=float(reward.piece_value) if reward.piece_value else None,
            max_daily_claims=reward.max_daily_claims,
            active=reward.active,
        ),
    )
