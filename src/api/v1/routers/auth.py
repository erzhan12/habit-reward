"""Authentication endpoints."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.dependencies.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenResponse,
    AccessTokenResponse,
    get_current_active_user,
)
from src.api.exceptions import (
    GoneException,
    UnauthorizedException,
    TooManyRequestsException,
)
from src.api.services.auth_code_service import auth_code_service
from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()


class TelegramLoginRequest(BaseModel):
    """Login request using Telegram ID.

    DEPRECATED: Use request-code + verify-code flow for secure authentication.
    """
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


class RequestCodeRequest(BaseModel):
    """Request auth code for secure login."""
    telegram_id: str = Field(..., description="User's Telegram ID")
    device_info: str | None = Field(
        default=None,
        max_length=255,
        description="Optional device/browser info (e.g., 'iPhone 15 Pro', 'Chrome on macOS')"
    )


class RequestCodeResponse(BaseModel):
    """Response after requesting auth code."""
    message: str
    expires_in_seconds: int


class VerifyCodeRequest(BaseModel):
    """Verify auth code to get tokens."""
    telegram_id: str = Field(..., description="User's Telegram ID")
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit code received via Telegram"
    )


@router.post("/login", response_model=TokenResponse, deprecated=True, include_in_schema=False)
async def login(request: TelegramLoginRequest) -> TokenResponse:
    """Login with Telegram ID.

    Disabled.

    Historically, this endpoint minted JWT tokens solely from a `telegram_id`, which is not a secret and enables
    account takeover. Keep the route for backward compatibility, but do not allow authentication without proof of
    Telegram ownership.

    Args:
        request: Login request containing telegram_id

    Returns:
        Never returns successfully.
    """
    logger.warning("Blocked deprecated /login attempt for telegram_id: %s", request.telegram_id)
    raise GoneException(
        message="This endpoint is disabled. Use /v1/auth/request-code and /v1/auth/verify-code instead.",
        code="DEPRECATED_LOGIN",
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


@router.post("/request-code", response_model=RequestCodeResponse)
async def request_auth_code(request: RequestCodeRequest) -> RequestCodeResponse:
    """Request an authentication code for secure login.

    This endpoint generates a 6-digit code and sends it to the user's Telegram.
    The user then enters this code in the web/mobile app to prove Telegram ownership.

    Rate limited to 3 requests per hour per user.

    Args:
        request: Request containing telegram_id and optional device_info

    Returns:
        RequestCodeResponse confirming code was sent

    Raises:
        NotFoundException: If user with given telegram_id doesn't exist
        TooManyRequestsException: If rate limit exceeded
    """
    logger.info(
        "Auth code request for telegram_id: %s (device: %s)",
        request.telegram_id,
        request.device_info
    )

    try:
        result = await auth_code_service.create_auth_code(
            telegram_id=request.telegram_id,
            device_info=request.device_info,
        )
    except ValueError as e:
        # Rate limit exceeded
        logger.warning("Rate limit for auth code: %s", str(e))
        raise TooManyRequestsException(
            message=str(e),
            code="RATE_LIMITED"
        )
    except Exception as e:
        # Log unexpected errors and return 500
        logger.error("Unexpected error creating auth code: %s", str(e), exc_info=True)
        raise

    if result is None:
        # User not found - return generic message to prevent enumeration
        # We don't actually send a code because we don't know the user,
        # but we return success to the caller.
        logger.warning("Auth code request for unknown/inactive user: %s (mimicking success)", request.telegram_id)
        return RequestCodeResponse(
            message="If the account exists, a code was sent to Telegram",
            expires_in_seconds=5 * 60
        )

    auth_code, user = result

    # Send code via Telegram bot
    # Wrap in try-catch to ensure endpoint doesn't fail if Telegram send fails
    try:
        message_id = await _send_auth_code_to_telegram(user, auth_code.code, request.device_info)
        logger.info("Auth code sent to user %s", user.id)

        # Save message_id and schedule auto-deletion on expiry
        if message_id:
            from src.core.repositories import auth_code_repository

            await maybe_await(
                auth_code_repository.update_telegram_message_id(auth_code.id, message_id)
            )
            asyncio.create_task(
                _delete_auth_code_message_delayed(user.telegram_id, message_id, delay=5 * 60)
            )
    except Exception as e:
        # Log error but don't fail the request - code was created successfully
        logger.error("Failed to send auth code via Telegram (endpoint level): %s", str(e))

    return RequestCodeResponse(
        message="If the account exists, a code was sent to Telegram",
        expires_in_seconds=5 * 60  # 5 minutes
    )


@router.post("/verify-code", response_model=TokenResponse)
async def verify_auth_code(request: VerifyCodeRequest) -> TokenResponse:
    """Verify authentication code and get JWT tokens.

    Exchanges a valid auth code for access and refresh tokens.

    Args:
        request: Request containing telegram_id and code

    Returns:
        TokenResponse with access_token and refresh_token

    Raises:
        UnauthorizedException: If code is invalid or expired
    """
    logger.info("Auth code verification for telegram_id: %s", request.telegram_id)

    result = await auth_code_service.verify_code(
        telegram_id=request.telegram_id,
        code=request.code,
    )

    if result is None:
        logger.warning("Invalid auth code for telegram_id: %s", request.telegram_id)
        raise UnauthorizedException(
            message="Invalid or expired code",
            code="INVALID_CODE"
        )

    user, auth_code = result

    # Delete the auth code Telegram message now that it's verified
    if auth_code.telegram_message_id:
        asyncio.create_task(
            _delete_telegram_message(request.telegram_id, auth_code.telegram_message_id)
        )

    # Generate tokens
    access_token = create_access_token(
        user_id=user.id,
        telegram_id=user.telegram_id
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        telegram_id=user.telegram_id
    )

    logger.info("Auth code verified, tokens issued for user %s", user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


async def _send_auth_code_to_telegram(user: User, code: str, device_info: str | None) -> int | None:
    """Send auth code to user via Telegram bot.

    Args:
        user: User to send code to
        code: 6-digit auth code
        device_info: Optional device/browser info

    Returns:
        Telegram message_id if sent successfully, None otherwise
    """
    try:
        from telegram import Bot
        from src.config import settings
        from src.bot.messages import Messages
        import html

        bot = Bot(token=settings.telegram_bot_token)

        # Build message
        message_lines = [
            Messages.AUTH_CODE_LOGIN_CODE.format(code=code),
            "",
        ]

        if device_info:
            message_lines.append(
                Messages.AUTH_CODE_DEVICE.format(device=html.escape(device_info))
            )

        message_lines.extend([
            Messages.AUTH_CODE_EXPIRES,
            "",
            Messages.AUTH_CODE_WARNING_1,
            Messages.AUTH_CODE_WARNING_2,
        ])

        message = "\n".join(message_lines)

        sent_msg = await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            parse_mode="HTML"
        )

        logger.info("Auth code sent via Telegram to user %s (message_id=%s)", user.id, sent_msg.message_id)
        return sent_msg.message_id

    except Exception as e:
        # Log error but don't fail the request
        # The code was created, user can request again if needed
        logger.error("Failed to send auth code via Telegram: %s", str(e))
        return None


async def _delete_telegram_message(telegram_id: str, message_id: int) -> None:
    """Delete a Telegram message (best effort).

    Args:
        telegram_id: Chat ID to delete message from
        message_id: Telegram message ID to delete
    """
    try:
        from telegram import Bot
        from src.config import settings

        bot = Bot(token=settings.telegram_bot_token)
        await bot.delete_message(chat_id=telegram_id, message_id=message_id)
        logger.info("Deleted Telegram message %s for chat %s", message_id, telegram_id)
    except Exception as e:
        logger.warning("Failed to delete Telegram message %s: %s", message_id, e)


async def _delete_auth_code_message_delayed(telegram_id: str, message_id: int, delay: int) -> None:
    """Delete auth code Telegram message after a delay (fire-and-forget).

    Args:
        telegram_id: Chat ID to delete message from
        message_id: Telegram message ID to delete
        delay: Seconds to wait before deleting
    """
    await asyncio.sleep(delay)
    await _delete_telegram_message(telegram_id, message_id)
