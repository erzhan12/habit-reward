"""JWT authentication dependencies."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from src.api.config import api_settings
from src.api.exceptions import UnauthorizedException
from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # user_id
    telegram_id: str | None = None
    exp: datetime
    type: str  # "access" or "refresh"


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Access token only response (for refresh)."""
    access_token: str
    token_type: str = "bearer"


def create_access_token(user_id: int | str, telegram_id: str | None = None) -> str:
    """Generate JWT access token.

    Args:
        user_id: Django User.id
        telegram_id: Optional Telegram ID for Telegram users

    Returns:
        Encoded JWT access token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=api_settings.api_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(
        payload,
        api_settings.get_secret_key(),
        algorithm=api_settings.api_algorithm
    )


def create_refresh_token(user_id: int | str, telegram_id: str | None = None) -> str:
    """Generate JWT refresh token.

    Args:
        user_id: Django User.id
        telegram_id: Optional Telegram ID for Telegram users

    Returns:
        Encoded JWT refresh token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=api_settings.api_refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(
        payload,
        api_settings.get_secret_key(),
        algorithm=api_settings.api_algorithm
    )


def verify_token(token: str, expected_type: str = "access") -> TokenPayload:
    """Decode and validate JWT token.

    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        UnauthorizedException: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            api_settings.get_secret_key(),
            algorithms=[api_settings.api_algorithm]
        )
        token_type = payload.get("type")
        if token_type != expected_type:
            logger.warning("Token type mismatch: expected %s, got %s", expected_type, token_type)
            raise UnauthorizedException(
                message=f"Invalid token type: expected {expected_type}",
                code="INVALID_TOKEN_TYPE"
            )

        return TokenPayload(
            sub=payload["sub"],
            telegram_id=payload.get("telegram_id"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            type=token_type
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise UnauthorizedException(
            message="Token has expired",
            code="TOKEN_EXPIRED"
        )
    except JWTError as e:
        logger.warning("JWT decode error: %s", str(e))
        raise UnauthorizedException(
            message="Invalid token",
            code="INVALID_TOKEN"
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)]
) -> User:
    """Extract and validate user from JWT token.

    This dependency extracts the JWT from the Authorization header,
    validates it, and returns the corresponding User object.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        User instance from database

    Raises:
        UnauthorizedException: If token is missing, invalid, or user not found
    """
    if credentials is None:
        logger.warning("No authorization credentials provided")
        raise UnauthorizedException(
            message="Authorization header required",
            code="MISSING_TOKEN"
        )

    token_payload = verify_token(credentials.credentials, expected_type="access")

    # Fetch user from database
    user = await maybe_await(user_repository.get_by_id(token_payload.sub))

    if user is None:
        logger.warning("User not found for token sub: %s", token_payload.sub)
        raise UnauthorizedException(
            message="User not found",
            code="USER_NOT_FOUND"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current user and verify they are active.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active User instance

    Raises:
        UnauthorizedException: If user is inactive
    """
    if not current_user.is_active:
        logger.warning("Inactive user attempted access: %s", current_user.id)
        raise UnauthorizedException(
            message="User account is inactive",
            code="USER_INACTIVE"
        )
    return current_user
