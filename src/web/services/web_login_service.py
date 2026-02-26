"""Web login service for bot-based Confirm/Deny authentication."""

import asyncio
import atexit
import logging
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from django.conf import settings
from django.db import DatabaseError, IntegrityError, transaction

from src.core.models import WebLoginRequest
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, InvalidToken, TelegramError

from asgiref.sync import sync_to_async

from src.core.repositories import user_repository, web_login_request_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

# Cryptographically secure RNG for timing jitter — avoids the predictable
# Mersenne Twister used by the `random` module.
_secure_random = secrets.SystemRandom()

# Configurable via settings.WEB_LOGIN_EXPIRY_MINUTES (default 5).
# Must stay in sync with frontend LOGIN_EXPIRY_MS in Login.vue.
LOGIN_REQUEST_EXPIRY_MINUTES = getattr(settings, "WEB_LOGIN_EXPIRY_MINUTES", 5)
WL_CONFIRM_PREFIX = "wl_c_"
WL_DENY_PREFIX = "wl_d_"

# Token generation parameters.
TOKEN_BYTES = 32  # 256 bits of entropy for secrets.token_urlsafe
TOKEN_GENERATION_MAX_RETRIES = 3  # Max attempts to generate a unique token

# Configurable timing jitter range (seconds) for status polling.
# Masks residual timing differences between DB hit/miss, cache hit/miss.
_JITTER_MIN = getattr(settings, "WEB_LOGIN_JITTER_MIN", 0.05)
_JITTER_MAX = getattr(settings, "WEB_LOGIN_JITTER_MAX", 0.2)

# Bounded thread pool for background login processing (DB writes + Telegram send).
# Caps concurrent threads to prevent resource exhaustion under load; excess
# submissions queue up instead of spawning unbounded threads.
# NOTE: WEB_LOGIN_THREAD_POOL_SIZE (default 10) means at most 10 concurrent
# login requests can be processed.  Excess requests queue up to
# WEB_LOGIN_MAX_QUEUED (default 50) before returning HTTP 503.  If you
# observe frequent 503s, increase these values or investigate slow Telegram
# API responses / DB writes.
# IMPORTANT: SQLite doesn't handle concurrent writes well. Under high load,
# you may see "database is locked" errors. For production with significant
# traffic, use PostgreSQL instead of SQLite.
_login_executor = ThreadPoolExecutor(max_workers=settings.WEB_LOGIN_THREAD_POOL_SIZE, thread_name_prefix="web_login")
atexit.register(_login_executor.shutdown, wait=True)

# Maximum number of queued items before rejecting new requests (circuit breaker).
_MAX_QUEUED_LOGINS = getattr(settings, "WEB_LOGIN_MAX_QUEUED", 50)

# Semaphore-based counter for queue depth — avoids relying on the private
# ``ThreadPoolExecutor._work_queue`` attribute which is a CPython
# implementation detail and could break in future Python versions.
_queue_slots = threading.Semaphore(_MAX_QUEUED_LOGINS)


class LoginServiceUnavailable(Exception):
    """Raised when the login background queue is full."""


def _safe_cache_set(key: str, value, timeout: int) -> None:
    """Write to cache with failure logging — never raises."""
    from django.core.cache import cache

    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning("Cache write failed for %s", key[:20])


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

        # Generate a cryptographically random token.  Instead of the old
        # check-then-insert pattern (which had a TOCTOU race under
        # concurrency), we just generate one — the 256-bit token space makes
        # collisions astronomically unlikely, and the unique DB constraint
        # on ``WebLoginRequest.token`` catches any that do occur.
        token = secrets.token_urlsafe(TOKEN_BYTES)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=LOGIN_REQUEST_EXPIRY_MINUTES)
        cache_ttl = max(int((expires_at - now).total_seconds()), 1)
        # Cache backend failure is non-fatal — the login flow can still
        # proceed via DB-only path (check_status will find the DB record
        # once the background thread writes it).
        _safe_cache_set(f"wl_pending:{token}", True, cache_ttl)

        if user and user.telegram_id:
            # Circuit breaker: reject if the background queue is saturated.
            # Uses a semaphore instead of the private _work_queue to avoid
            # relying on CPython implementation details.
            if not _queue_slots.acquire(blocking=False):
                logger.critical(
                    "Login thread pool queue full (>=%d pending), rejecting request",
                    _MAX_QUEUED_LOGINS,
                )
                raise LoginServiceUnavailable(
                    "Login service temporarily unavailable"
                )
            # All DB writes + Telegram send happen in the bounded thread pool
            # so the HTTP response time is constant for both paths.
            try:
                _login_executor.submit(
                    self._process_login_background, user, token, expires_at, device_info
                )
            except RuntimeError:
                # Executor is shut down (e.g. during server shutdown).
                # Release the semaphore to prevent leaks.
                _queue_slots.release()
                raise LoginServiceUnavailable(
                    "Login service shutting down"
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
        """Process login request in a background thread (DB writes + Telegram send).

        Uses call_async() (asgiref) instead of asyncio.run() to reuse the
        existing event loop, consistent with the rest of the codebase.

        Always releases the ``_queue_slots`` semaphore on completion so the
        circuit breaker accurately tracks in-flight work.
        """
        from src.web.utils.sync import call_async

        def _mark_failed():
            """Set a failure cache key so check_status can return 'error'."""
            cache_ttl = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 1)
            _safe_cache_set(f"wl_failed:{token}", True, cache_ttl)

        try:
            call_async(self._process_login_request(user, token, expires_at, device_info))
        except (InvalidToken, Forbidden) as e:
            # Permanent Telegram errors — bot token is wrong or bot was
            # blocked by the user.  These won't resolve on retry.
            logger.critical(
                "Permanent Telegram error during login processing — check bot config",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed()
        except TelegramError as e:
            # Temporary Telegram errors (network, rate limit, etc.) —
            # may resolve on next attempt.
            logger.error(
                "Temporary Telegram error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed()
        except DatabaseError as e:
            logger.error(
                "Database error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed()
        except Exception as e:
            logger.error(
                "Unexpected error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed()
        finally:
            _queue_slots.release()

    async def _process_login_request(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Perform DB writes and send Telegram notification."""

        # Wrap invalidate + create in a transaction so that if create fails,
        # the invalidation is rolled back and the user's pending request is preserved.
        # Uses try/except on IntegrityError (unique constraint on token) to
        # handle the astronomically unlikely collision without a TOCTOU race.
        @sync_to_async
        def _transactional_writes():
            nonlocal token
            for _attempt in range(TOKEN_GENERATION_MAX_RETRIES):
                try:
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
                except IntegrityError:
                    # Token collision — regenerate and retry.
                    token = secrets.token_urlsafe(TOKEN_BYTES)
            raise DatabaseError("Failed to generate unique token after retries")

        login_request = await _transactional_writes()

        logger.info(
            "Web login request created",
            extra={
                "user_id": user.id,
                "token_prefix": token[:8],
                "operation": "create_login_request",
            },
        )

        # Send Telegram notification
        try:
            chat_id = int(user.telegram_id)
        except (ValueError, TypeError):
            logger.error(
                "Invalid telegram_id for user — cannot send notification",
                extra={"user_id": user.id, "telegram_id": user.telegram_id},
            )
            return
        await self._send_login_notification(
            chat_id, login_request.id, token, device_info
        )

    async def _send_login_notification(
        self, chat_id: int, request_id: int, token: str, device_info: str | None
    ) -> None:
        """Send the Telegram message with Confirm/Deny buttons."""
        import html as html_mod

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        # HTML-escape at the output boundary — device_info is truncated in
        # auth.py but stored unescaped so the DB data is context-neutral.
        device_text = html_mod.escape(device_info) if device_info else "Unknown device"
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

        logger.info(
            "Login notification sent",
            extra={"request_id": request_id, "operation": "send_notification"},
        )

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

        # Random jitter (50-200ms by default, configurable via settings)
        # masks residual timing differences between DB hit vs miss, cache
        # hit vs miss, etc.  Applied uniformly to all paths to avoid
        # selective jitter itself becoming a timing side-channel.
        await asyncio.sleep(_secure_random.uniform(_JITTER_MIN, _JITTER_MAX))

        # Always perform both lookups to ensure constant-time work.
        # Do NOT short-circuit — both must execute every time.
        db_unavailable = False
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
            db_unavailable = True

        try:
            cache_keys = cache.get_many([f"wl_pending:{token}", f"wl_failed:{token}"])
        except Exception:
            logger.warning("Cache read failed during status check for token=%s…", token[:8])
            cache_keys = {}
        cache_pending = cache_keys.get(f"wl_pending:{token}")
        cache_failed = cache_keys.get(f"wl_failed:{token}")

        # Now use the results — logic is the same, but all lookups
        # have already been performed regardless of which path we take.
        # Return string status values consistently for JSON serialization.
        # Django's TextChoices members must be converted to their .value
        # (string) for JSON responses.
        if not login_request:
            if cache_failed:
                return "error"
            if cache_pending:
                return "pending"
            if db_unavailable and not cache_keys:  # DB is down, no cache data
                return "error"
            return "expired"

        # Check expiry
        if datetime.now(timezone.utc) > login_request.expires_at:
            return "expired"

        return str(login_request.status)

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

        # Must be confirmed — compare to .value for consistency with the
        # rest of the codebase (handler, repository queries).
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

        logger.info(
            "Web login completed",
            extra={
                "user_id": login_request.user_id,
                "token_prefix": token[:8],
                "operation": "complete_login",
            },
        )
        return login_request.user


# Global service instance
web_login_service = WebLoginService()
