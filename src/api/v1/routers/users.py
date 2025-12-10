"""User management endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies.auth import get_current_active_user
from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""
    id: int
    telegram_id: str
    name: str
    language: str
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """User update request model."""
    name: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, pattern="^(en|ru|kk)$")


class UserSettingsResponse(BaseModel):
    """User settings response model."""
    language: str
    timezone: str = "UTC"  # Future: add timezone field to User model


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserResponse:
    """Get current authenticated user's profile.

    Returns:
        UserResponse with user profile information
    """
    logger.info("Get current user request for user %s", current_user.id)

    return UserResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        name=current_user.name,
        language=current_user.language,
        is_active=current_user.is_active
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    updates: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserResponse:
    """Update current authenticated user's profile.

    Args:
        updates: Fields to update (name, language)
        current_user: Currently authenticated user

    Returns:
        UserResponse with updated user profile
    """
    logger.info("Update user request for user %s", current_user.id)

    # Build update dict with only provided fields
    update_dict = {}
    if updates.name is not None:
        update_dict["name"] = updates.name
    if updates.language is not None:
        update_dict["language"] = updates.language

    if update_dict:
        updated_user = await maybe_await(
            user_repository.update(current_user.id, update_dict)
        )
        logger.info("User %s updated: %s", current_user.id, list(update_dict.keys()))
    else:
        updated_user = current_user
        logger.info("No updates provided for user %s", current_user.id)

    return UserResponse(
        id=updated_user.id,
        telegram_id=updated_user.telegram_id,
        name=updated_user.name,
        language=updated_user.language,
        is_active=updated_user.is_active
    )


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> UserSettingsResponse:
    """Get current user's settings.

    Returns:
        UserSettingsResponse with user settings
    """
    logger.info("Get settings request for user %s", current_user.id)

    return UserSettingsResponse(
        language=current_user.language,
        timezone="UTC"  # Placeholder until timezone is added to model
    )
