"""Auth code service for secure API login."""

import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from src.core.repositories import auth_code_repository, user_repository, api_key_repository
from src.core.models import User, AuthCode, APIKey
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

# Configuration
AUTH_CODE_EXPIRY_MINUTES = 5
AUTH_CODE_MAX_REQUESTS_PER_HOUR = 3
API_KEY_PREFIX = "hrk_"


class AuthCodeService:
    """Service for managing authentication codes."""

    def __init__(self):
        self.auth_code_repo = auth_code_repository
        self.user_repo = user_repository

    async def generate_code(self) -> str:
        """Generate a 6-digit numeric code.

        Returns:
            6-digit string (e.g., "847291")
        """
        code = secrets.randbelow(1000000)
        return str(code).zfill(6)

    async def create_auth_code(
        self,
        telegram_id: str,
        device_info: str | None = None,
    ) -> tuple[AuthCode, User] | None:
        """Create a new auth code for a user.

        Args:
            telegram_id: User's Telegram ID
            device_info: Optional device/browser info

        Returns:
            Tuple of (AuthCode, User) if successful, None if user not found

        Raises:
            ValueError: If rate limited
        """
        # Get user
        user = await maybe_await(self.user_repo.get_by_telegram_id(telegram_id))
        if not user:
            logger.warning("Auth code request for unknown telegram_id: %s", telegram_id)
            return None

        if not user.is_active:
            logger.warning("Auth code request for inactive user: %s", telegram_id)
            return None

        # Check rate limit
        recent_count = await maybe_await(
            self.auth_code_repo.count_recent_requests(user.id, hours=1)
        )
        if recent_count >= AUTH_CODE_MAX_REQUESTS_PER_HOUR:
            logger.warning(
                "Rate limit exceeded for user %s: %d requests in last hour",
                user.id,
                recent_count,
            )
            raise ValueError("Too many code requests. Please try again later.")

        # Invalidate any existing codes
        await maybe_await(self.auth_code_repo.invalidate_user_codes(user.id))

        # Generate new code
        code = await self.generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=AUTH_CODE_EXPIRY_MINUTES)

        # Create code
        auth_code = await maybe_await(
            self.auth_code_repo.create(
                user_id=user.id,
                code=code,
                expires_at=expires_at,
                device_info=device_info,
            )
        )

        logger.info(
            "Auth code created for user %s (expires: %s, device: %s)",
            user.id,
            expires_at,
            device_info,
        )

        return auth_code, user

    async def verify_code(
        self,
        telegram_id: str,
        code: str,
    ) -> User | None:
        """Verify an auth code and return the user.

        Args:
            telegram_id: User's Telegram ID
            code: 6-digit code to verify

        Returns:
            User if code is valid, None otherwise
        """
        # Get user
        user = await maybe_await(self.user_repo.get_by_telegram_id(telegram_id))
        if not user:
            logger.warning("Code verification for unknown telegram_id: %s", telegram_id)
            return None

        if not user.is_active:
            logger.warning("Code verification for inactive user: %s", telegram_id)
            return None

        # Verify and consume code atomically
        auth_code = await maybe_await(
            self.auth_code_repo.verify_and_consume_code(user.id, code)
        )
        if not auth_code:
            # Register failed attempt on the latest active code
            await maybe_await(self.auth_code_repo.register_failed_attempt(user.id))
            
            logger.warning(
                "Invalid or expired code for user %s: %s",
                user.id,
                code[:2] + "****",
            )
            return None

        logger.info("Auth code verified successfully for user %s", user.id)
        return user

    async def cleanup_expired_codes(self) -> int:
        """Delete expired auth codes.

        Returns:
            Number of deleted codes
        """
        deleted = await maybe_await(self.auth_code_repo.delete_expired())
        if deleted > 0:
            logger.info("Cleaned up %d expired auth codes", deleted)
        return deleted


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self):
        self.api_key_repo = api_key_repository
        self.user_repo = user_repository

    def generate_key(self) -> str:
        """Generate a new API key.

        Returns:
            Raw API key string (e.g., "hrk_AbC123...")
        """
        # Generate 32 bytes of random data
        raw_key = secrets.token_urlsafe(32)
        return f"{API_KEY_PREFIX}{raw_key}"

    def hash_key(self, key: str) -> str:
        """Hash an API key for storage.

        Args:
            key: Raw API key

        Returns:
            SHA256 hash of the key
        """
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_api_key(
        self,
        user_id: int | str,
        name: str,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user.

        Args:
            user_id: User primary key
            name: User-friendly name for the key
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (APIKey, raw_key) - raw_key should be shown once then discarded

        Raises:
            ValueError: If name already exists for user
        """
        # Check for duplicate name
        existing = await maybe_await(
            self.api_key_repo.get_by_user_and_name(user_id, name)
        )
        if existing:
            raise ValueError(f"API key with name '{name}' already exists")

        # Generate key and hash
        raw_key = self.generate_key()
        key_hash = self.hash_key(raw_key)

        # Create key
        api_key = await maybe_await(
            self.api_key_repo.create(
                user_id=user_id,
                key_hash=key_hash,
                name=name,
                expires_at=expires_at,
            )
        )

        logger.info(
            "API key '%s' created for user %s (expires: %s)",
            name,
            user_id,
            expires_at,
        )

        return api_key, raw_key

    async def verify_api_key(self, raw_key: str) -> User | None:
        """Verify an API key and return the associated user.

        Args:
            raw_key: Raw API key from request header

        Returns:
            User if key is valid, None otherwise
        """
        # Validate format
        if not raw_key.startswith(API_KEY_PREFIX):
            logger.warning("Invalid API key format (missing prefix)")
            return None

        # Hash and lookup
        key_hash = self.hash_key(raw_key)
        api_key = await maybe_await(self.api_key_repo.get_by_key_hash(key_hash))

        if not api_key:
            logger.warning("API key not found or inactive")
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            logger.warning("API key '%s' has expired", api_key.name)
            return None

        # Check user is active
        if not api_key.user.is_active:
            logger.warning("API key user is inactive: %s", api_key.user.id)
            return None

        # Update last used
        await maybe_await(self.api_key_repo.update_last_used(api_key.id))

        logger.debug("API key '%s' verified for user %s", api_key.name, api_key.user.id)
        return api_key.user

    async def list_user_keys(self, user_id: int | str) -> list[APIKey]:
        """Get all API keys for a user.

        Args:
            user_id: User primary key

        Returns:
            List of APIKey instances
        """
        return await maybe_await(self.api_key_repo.list_by_user(user_id))

    async def revoke_key(self, key_id: int | str, user_id: int | str) -> APIKey | None:
        """Revoke an API key.

        Args:
            key_id: APIKey primary key
            user_id: User primary key (for ownership verification)

        Returns:
            Revoked APIKey or None if not found/not owned
        """
        api_key = await maybe_await(self.api_key_repo.get_by_id(key_id))
        if not api_key:
            return None

        # Verify ownership
        if api_key.user_id != int(user_id):
            logger.warning(
                "User %s attempted to revoke key owned by user %s",
                user_id,
                api_key.user_id,
            )
            return None

        revoked = await maybe_await(self.api_key_repo.revoke(key_id))
        logger.info("API key '%s' revoked for user %s", api_key.name, user_id)
        return revoked


# Global service instances
auth_code_service = AuthCodeService()
api_key_service = APIKeyService()
