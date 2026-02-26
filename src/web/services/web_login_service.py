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

# Cache key prefix to avoid collisions in shared cache backends.
_CACHE_PREFIX = "habit_reward:"
WL_PENDING_KEY = f"{_CACHE_PREFIX}wl_pending:"
WL_FAILED_KEY = f"{_CACHE_PREFIX}wl_failed:"

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
# traffic, use PostgreSQL instead of SQLite. Also tune CONN_MAX_AGE so the
# DB connection pool can keep up with WEB_LOGIN_THREAD_POOL_SIZE workers.
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


class CacheWriteError(Exception):
    """Raised when cache writes fail repeatedly, indicating misconfiguration."""


# Consecutive cache write failure counter.
_cache_failure_count = 0
_cache_failure_lock = threading.Lock()
_CACHE_FAILURE_THRESHOLD = 3


def _safe_cache_set(key: str, value, timeout: int) -> None:
    """Write to cache with failure tracking.

    Logs warnings on individual failures.  Raises ``CacheWriteError``
    after ``_CACHE_FAILURE_THRESHOLD`` (3) consecutive failures to
    surface likely cache misconfiguration instead of silently degrading.
    """
    global _cache_failure_count
    from django.core.cache import cache

    try:
        cache.set(key, value, timeout=timeout)
        with _cache_failure_lock:
            _cache_failure_count = 0
    except (ConnectionError, TimeoutError, OSError):
        with _cache_failure_lock:
            _cache_failure_count += 1
            failure_count = _cache_failure_count
        logger.warning(
            "Cache write failed for %s (consecutive failures: %d)",
            key[:20], failure_count,
        )
        if failure_count >= _CACHE_FAILURE_THRESHOLD:
            raise CacheWriteError(
                f"Cache writes have failed {failure_count} times consecutively "
                "— check cache backend configuration"
            )


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
        try:
            _safe_cache_set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
        except CacheWriteError as exc:
            logger.critical(
                "Cache backend unhealthy during login request creation",
                extra={"username": username},
            )
            raise LoginServiceUnavailable("Login service temporarily unavailable") from exc

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
                future = _login_executor.submit(
                    self._process_login_background, user, token, expires_at, device_info
                )
                # Release the semaphore when the future completes (success,
                # exception, or cancellation).  This is the single release
                # point — _process_login_background must NOT release it.
                future.add_done_callback(lambda f: _queue_slots.release())
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

        The ``_queue_slots`` semaphore is released by the done_callback on
        the Future, not here — this avoids double-release on cancellation.
        """
        from src.web.utils.sync import call_async

        def _mark_failed():
            """Set a failure cache key so check_status can return 'error'."""
            cache_ttl = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 1)
            _safe_cache_set(f"{WL_FAILED_KEY}{token}", True, cache_ttl)

        def _mark_failed_safely():
            """Best-effort cache write; failures are logged but non-fatal here."""
            try:
                _mark_failed()
            except CacheWriteError as cache_error:
                logger.error(
                    "Failed to write wl_failed marker to cache",
                    extra={
                        "user_id": user.id,
                        "token_prefix": token[:8],
                        "error": str(cache_error),
                    },
                )

        try:
            call_async(self._process_login_request(user, token, expires_at, device_info))
        except (InvalidToken, Forbidden) as e:
            # Permanent Telegram errors — bot token is wrong or bot was
            # blocked by the user.  These won't resolve on retry.
            logger.critical(
                "Permanent Telegram error during login processing — check bot config",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()
        except TelegramError as e:
            # Temporary Telegram errors (network, rate limit, etc.) —
            # may resolve on next attempt.
            logger.error(
                "Temporary Telegram error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()
        except DatabaseError as e:
            logger.error(
                "Database error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()
        except Exception as e:
            logger.error(
                "Unexpected error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()

    @staticmethod
    def _create_login_request_with_retry(user_id, token, expires_at, device_info):
        """Invalidate pending requests and create a new one in a transaction.

        Retries on token collision (IntegrityError on unique constraint).
        Returns (login_request, final_token) since the token may change on retry.
        """
        for _attempt in range(TOKEN_GENERATION_MAX_RETRIES):
            try:
                with transaction.atomic():
                    WebLoginRequest.objects.filter(
                        user_id=user_id,
                        status=WebLoginRequest.Status.PENDING,
                    ).update(status=WebLoginRequest.Status.DENIED)
                    login_request = WebLoginRequest.objects.create(
                        user_id=user_id,
                        token=token,
                        expires_at=expires_at,
                        device_info=device_info,
                    )
                    return login_request, token
            except IntegrityError:
                # Token collision — regenerate and retry.
                token = secrets.token_urlsafe(TOKEN_BYTES)
        from django.core.cache import cache
        cache.delete(f"{WL_PENDING_KEY}{token}")
        raise DatabaseError("Failed to generate unique token after retries")

    async def _process_login_request(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Perform DB writes and send Telegram notification."""

        if not token or not token.strip():
            raise ValueError("Token cannot be empty")

        login_request, token = await sync_to_async(
            self._create_login_request_with_retry
        )(user.id, token, expires_at, device_info)

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
        """Send the Telegram message with Confirm/Deny buttons.

        Uses plain text (no parse_mode) as defense-in-depth — eliminates
        any risk from HTML parser bugs processing user-controlled device_info.
        """
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        device_text = device_info or "Unknown device"
        message_text = (
            "Web Login Request\n\n"
            "Someone is trying to log in to your account:\n"
            f"{device_text}\n\n"
            "If this was you, tap Confirm. Otherwise, tap Deny."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Confirm", callback_data=f"{WL_CONFIRM_PREFIX}{token}"),
                InlineKeyboardButton("Deny", callback_data=f"{WL_DENY_PREFIX}{token}"),
            ]
        ])

        async with bot:
            sent_message = await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard,
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

        Constant-time in cache paths: always performs a single cache.get_many()
        call, and only falls back to DB when both cache keys are missing.
        A small random jitter masks residual timing variation.

        Returns:
            One of: 'pending', 'confirmed', 'denied', 'expired', 'used', 'error'
        """
        from django.core.cache import cache
        from django.db import OperationalError

        pending_key = f"{WL_PENDING_KEY}{token}"
        failed_key = f"{WL_FAILED_KEY}{token}"
        try:
            cache_keys = cache.get_many([pending_key, failed_key])
        except Exception:
            logger.warning("Cache read failed during status check for token=%s…", token[:8])
            cache_keys = {}
        cache_pending = cache_keys.get(pending_key)
        cache_failed = cache_keys.get(failed_key)

        if cache_failed:
            status = "error"
        elif cache_pending:
            status = "pending"
        else:
            # Cache is empty; fall back to DB lookup.
            db_unavailable = False
            try:
                login_request = await maybe_await(self.request_repo.get_by_token(token))
            except OperationalError:
                logger.warning(
                    "DB lock during status check for token=%s…, and cache is empty",
                    token[:8],
                )
                login_request = None
                db_unavailable = True

            # Return string status values consistently for JSON serialization.
            # Django's TextChoices members must be converted to their .value
            # (string) for JSON responses.
            if not login_request:
                status = "error" if db_unavailable else "expired"
            elif datetime.now(timezone.utc) > login_request.expires_at:
                status = "expired"
            else:
                status = str(login_request.status)

        # Random jitter (50-200ms by default, configurable via settings)
        # masks residual timing differences between DB hit vs miss, cache
        # hit vs miss, etc.  Applied AFTER all lookups so that variable
        # work time (DB index hit vs miss, cache hit vs miss) is obscured
        # by the jitter.  Applied uniformly to all paths to avoid selective
        # jitter itself becoming a timing side-channel.
        await asyncio.sleep(_secure_random.uniform(_JITTER_MIN, _JITTER_MAX))

        return status

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
