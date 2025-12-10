"""Authentication endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenResponse,
    AccessTokenResponse,
    get_current_active_user,
)
from src.api.exceptions import UnauthorizedException, NotFoundException
from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


class TelegramLoginRequest(BaseModel):
    """Login request using Telegram ID."""
    telegram_id: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request."""
    refresh_token: str


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


@router.post("/login", response_model=TokenResponse)
async def login(request: TelegramLoginRequest) -> TokenResponse:
    """Login with Telegram ID.

    Authenticates user by their Telegram ID and returns JWT tokens.
    For now, only Telegram-based authentication is supported.

    Args:
        request: Login request containing telegram_id

    Returns:
        TokenResponse with access_token and refresh_token

    Raises:
        NotFoundException: If user with given telegram_id doesn't exist
        UnauthorizedException: If user is inactive
    """
    logger.info("Login attempt for telegram_id: %s", request.telegram_id)

    user = await maybe_await(user_repository.get_by_telegram_id(request.telegram_id))

    if user is None:
        logger.warning("Login failed: user not found for telegram_id %s", request.telegram_id)
        raise NotFoundException(
            message="User not found",
            code="USER_NOT_FOUND"
        )

    if not user.is_active:
        logger.warning("Login failed: inactive user %s", request.telegram_id)
        raise UnauthorizedException(
            message="User account is inactive",
            code="USER_INACTIVE"
        )

    access_token = create_access_token(
        user_id=user.id,
        telegram_id=user.telegram_id
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        telegram_id=user.telegram_id
    )

    logger.info("Login successful for user %s (telegram_id: %s)", user.id, request.telegram_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> AccessTokenResponse:
    """Refresh access token.

    Validates the refresh token and issues a new access token.

    Args:
        request: Request containing refresh_token

    Returns:
        AccessTokenResponse with new access_token

    Raises:
        UnauthorizedException: If refresh token is invalid or expired
    """
    logger.info("Token refresh request")

    # Verify refresh token
    payload = verify_token(request.refresh_token, expected_type="refresh")

    # Verify user still exists and is active
    user = await maybe_await(user_repository.get_by_id(payload.sub))

    if user is None:
        logger.warning("Refresh failed: user not found for id %s", payload.sub)
        raise UnauthorizedException(
            message="User not found",
            code="USER_NOT_FOUND"
        )

    if not user.is_active:
        logger.warning("Refresh failed: inactive user %s", payload.sub)
        raise UnauthorizedException(
            message="User account is inactive",
            code="USER_INACTIVE"
        )

    access_token = create_access_token(
        user_id=user.id,
        telegram_id=user.telegram_id
    )

    logger.info("Token refreshed for user %s", user.id)

    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> MessageResponse:
    """Logout and invalidate refresh token.

    Note: In this simple implementation, we don't maintain a token blacklist.
    The refresh token will still be valid until it expires.
    For production, consider implementing a token blacklist using Redis.

    Args:
        request: Request containing refresh_token to invalidate
        current_user: Currently authenticated user

    Returns:
        MessageResponse confirming logout
    """
    logger.info("Logout request for user %s", current_user.id)

    # In a production system, you would add the refresh token to a blacklist
    # For now, we just log the logout
    # TODO: Implement token blacklist with Redis

    return MessageResponse(message="Logged out successfully")
