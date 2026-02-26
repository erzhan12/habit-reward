"""Web login service for bot-based Confirm/Deny authentication."""

import asyncio
import atexit
import html
import logging
import random
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from django.conf import settings
from django.db import transaction

from src.core.models import WebLoginRequest
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from asgiref.sync import sync_to_async

from src.core.repositories import user_repository, web_login_request_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

LOGIN_REQUEST_EXPIRY_MINUTES = 5
WL_CONFIRM_PREFIX = "wl_c_"
WL_DENY_PREFIX = "wl_d_"

# Bounded thread pool for background login processing (DB writes + Telegram send).
# Caps concurrent threads to prevent resource exhaustion under load; excess
# submissions queue up instead of spawning unbounded threads.
_login_executor = ThreadPoolExecutor(max_workers=settings.WEB_LOGIN_THREAD_POOL_SIZE, thread_name_prefix="web_login")
atexit.register(_login_executor.shutdown, wait=True)


class WebLoginService:
    """Service for bot-based web login flow."""

    def __init__(self):
        self.user_repo = user_repository
        self.request_repo = web_login_request_repository

    async def create_login_request(
        self, username: str, device_info: str | None = None
    ) -> dict:
        """Create a login request and dispatch Confirm/Deny to user via bot.

        Both known and unknown users execute the same constant-time path:
        lookup → generate token → cache as pending → return.  All DB writes
        and the Telegram notification are deferred to a background thread so
        that response timing is identical regardless of user existence.

        Args:
            username: Telegram @username (with or without @)
            device_info: Browser/device info string

        Returns:
            Dict with {token, expires_at} — always returned for both paths.
        """
        from django.core.cache import cache

        user = await maybe_await(self.user_repo.get_by_telegram_username(username))

        # Generate token and cache it immediately — identical work for both paths.
        # Derive cache timeout from the same expires_at timestamp so both
        # cache eviction and DB expiry use a single source of truth.
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=LOGIN_REQUEST_EXPIRY_MINUTES)
        cache_ttl = max(int((expires_at - now).total_seconds()), 1)
        cache.set(f"wl_pending:{token}", True, timeout=cache_ttl)

        if user and user.telegram_id:
            # All DB writes + Telegram send happen in the bounded thread pool
            # so the HTTP response time is constant for both paths.
            _login_executor.submit(
                self._process_login_background, user, token, expires_at, device_info
            )
        else:
            # SECURITY: We deliberately do nothing visible here — no error, no
            # different response.  Returning the same {token, expires_at} for
            # unknown users prevents an attacker from enumerating valid
            # usernames by observing response body, timing, or status polling
            # differences.  The cache-only token expires silently after TTL.
            if not user:
                logger.warning("Web login request for unknown username: @%s", username)
            else:
                logger.warning("User @%s has no telegram_id", username)

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    def _process_login_background(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Process login request in a background thread (DB writes + Telegram send)."""
        try:
            asyncio.run(self._process_login_request(user, token, expires_at, device_info))
        except Exception as e:
            logger.error("Background login processing failed for user %s: %s", user.id, e)
            # Set a failure cache key so check_status can return an error
            # instead of leaving the user polling "pending" indefinitely.
            from django.core.cache import cache
            cache_ttl = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 1)
            cache.set(f"wl_failed:{token}", True, timeout=cache_ttl)

    async def _process_login_request(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Perform DB writes and send Telegram notification."""

        # Wrap invalidate + create in a transaction so that if create fails,
        # the invalidation is rolled back and the user's pending request is preserved.
        @sync_to_async
        def _transactional_writes():
            with transaction.atomic():
                WebLoginRequest.objects.filter(
                    user_id=user.id,
                    status=WebLoginRequest.Status.PENDING,
                ).update(status=WebLoginRequest.Status.DENIED)
                return WebLoginRequest.objects.create(
                    user_id=user.id,
                    token=token,
                    expires_at=expires_at,
                    device_info=device_info,
                )

        login_request = await _transactional_writes()

        logger.info(
            "Web login request created for user %s (token=%s...)",
            user.id,
            token[:8],
        )

        # Send Telegram notification
        await self._send_login_notification(
            int(user.telegram_id), login_request.id, token, device_info
        )

    async def _send_login_notification(
        self, chat_id: int, request_id: int, token: str, device_info: str | None
    ) -> None:
        """Send the Telegram message with Confirm/Deny buttons."""
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        device_text = html.escape(device_info or "Unknown device")
        message_text = (
            f"🔐 <b>Web Login Request</b>\n\n"
            f"Someone is trying to log in to your account:\n"
            f"📱 {device_text}\n\n"
            f"If this was you, tap <b>Confirm</b>. Otherwise, tap <b>Deny</b>."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"{WL_CONFIRM_PREFIX}{token}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"{WL_DENY_PREFIX}{token}"),
            ]
        ])

        async with bot:
            sent_message = await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

        # Save telegram message ID for later editing
        await maybe_await(
            self.request_repo.update_telegram_message_id(
                request_id, sent_message.message_id
            )
        )

        logger.info("Login notification sent for request %s", request_id)

    async def check_status(self, token: str) -> str:
        """Check the status of a login request.

        Constant-time: always performs both DB query and cache lookup so
        that response timing is identical regardless of user existence.
        A small random jitter masks any residual timing variation.

        Returns:
            One of: 'pending', 'confirmed', 'denied', 'expired', 'used', 'error'
        """
        from django.core.cache import cache
        from django.db import OperationalError

        # Random jitter (50-200ms) masks residual timing differences
        # between DB hit vs miss, cache hit vs miss, etc.
        await asyncio.sleep(random.uniform(0.05, 0.2))

        # Always perform both lookups to ensure constant-time work.
        # Do NOT short-circuit — both must execute every time.
        try:
            login_request = await maybe_await(self.request_repo.get_by_token(token))
        except OperationalError:
            # SQLite can raise "database table is locked" when the background
            # thread is writing (invalidate + create).  The cache always holds
            # the correct fallback because it was set *before* the thread
            # launched.  Fall through to the cache check.
            logger.warning(
                "DB lock during status check for token=%s…, falling back to cache",
                token[:8],
            )
            login_request = None

        cache_pending = cache.get(f"wl_pending:{token}")
        cache_failed = cache.get(f"wl_failed:{token}")

        # Now use the results — logic is the same, but all lookups
        # have already been performed regardless of which path we take.
        if not login_request:
            if cache_failed:
                return "error"
            if cache_pending:
                return WebLoginRequest.Status.PENDING.value
            return "expired"

        # Check expiry
        if datetime.now(timezone.utc) > login_request.expires_at:
            return "expired"

        return login_request.status

    async def complete_login(self, token: str):
        """Complete the login after confirmation.

        Args:
            token: Login request token

        Returns:
            User instance if login is valid, None otherwise
        """
        login_request = await maybe_await(self.request_repo.get_by_token(token))
        if not login_request:
            logger.warning("Complete login attempt with unknown token: %s...", token[:8])
            return None

        # Must be confirmed
        if login_request.status != WebLoginRequest.Status.CONFIRMED.value:
            logger.warning(
                "Complete login attempt with status=%s for token=%s...",
                login_request.status,
                token[:8],
            )
            return None

        # Must not be expired
        if datetime.now(timezone.utc) > login_request.expires_at:
            logger.warning("Complete login attempt with expired token: %s...", token[:8])
            return None

        # Atomically mark as used to prevent token replay
        updated = await maybe_await(self.request_repo.mark_as_used(token))
        if not updated:
            logger.warning("Token replay attempt — already used: %s...", token[:8])
            return None

        logger.info("Web login completed for user %s", login_request.user_id)
        return login_request.user


# Global service instance
web_login_service = WebLoginService()
