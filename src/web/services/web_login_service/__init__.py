"""Web login service for bot-based Confirm/Deny authentication.

Package structure::

    web_login_service/
        __init__.py              — Main service class and thread pool
        cache_operations.py      — CacheManager, cache utilities
        token_operations.py      — Token generation constants
        telegram_operations.py   — Telegram message sending
"""

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
from telegram.error import Forbidden, InvalidToken, RetryAfter, TelegramError

from asgiref.sync import sync_to_async

from src.core.repositories import user_repository, web_login_request_repository
from src.utils.async_compat import maybe_await

# Re-export submodule symbols so existing imports continue to work:
#   from src.web.services.web_login_service import WL_PENDING_KEY, ...
from .cache_operations import (  # noqa: F401
    CacheWriteError,
    CacheManager,
    WL_PENDING_KEY,
    WL_FAILED_KEY,
    _CACHE_PREFIX,
    _MIN_FAILED_MARKER_TTL_SECONDS,
    _cache_ttl_seconds,
    _mark_failed_token,
    cache_manager,
)
from .token_operations import (  # noqa: F401
    TOKEN_BYTES,
    TOKEN_LENGTH,
    TOKEN_MIN_LENGTH,
    TOKEN_MAX_LENGTH,
    TOKEN_GENERATION_MAX_RETRIES,
)
from .telegram_operations import (  # noqa: F401
    WL_CONFIRM_PREFIX,
    WL_DENY_PREFIX,
    send_login_notification,
)

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC).

    Django's DateTimeField may return naive datetimes when USE_TZ=False.
    This prevents ``TypeError: can't compare offset-naive and offset-aware
    datetimes`` when comparing with ``datetime.now(timezone.utc)``.

    Raises:
        ValueError: If *dt* is None (prevents confusing downstream errors).
    """
    if dt is None:
        raise ValueError("_ensure_utc received None — expected a datetime instance")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# Backward-compatible wrapper — old code/tests reference _safe_cache_set.
# Prefer cache_manager.set() in new code.
def _safe_cache_set(key: str, value, timeout: int) -> None:
    """Write to cache with failure tracking (delegates to cache_manager)."""
    cache_manager.set(key, value, timeout)


# Cryptographically secure RNG for timing jitter — thread-safe and avoids
# the predictable Mersenne Twister used by the `random` module.
_secure_random = secrets.SystemRandom()

# Configurable via settings.WEB_LOGIN_EXPIRY_MINUTES (default 5).
# Must stay in sync with frontend LOGIN_EXPIRY_MS in Login.vue.
LOGIN_REQUEST_EXPIRY_MINUTES = getattr(settings, "WEB_LOGIN_EXPIRY_MINUTES", 5)

# Configurable timing jitter range (seconds) for status polling.
# Masks residual timing differences between DB hit/miss, cache hit/miss.
_JITTER_MIN = getattr(settings, "WEB_LOGIN_JITTER_MIN", 0.05)
_JITTER_MAX = getattr(settings, "WEB_LOGIN_JITTER_MAX", 0.2)

# Bounded thread pool for background login processing (DB writes + Telegram send).
# See token_operations.py for token constants, cache_operations.py for cache logic.
#
# IMPORTANT: SQLite doesn't handle concurrent writes well — its file-level
# locking means only one writer at a time.  For production with concurrent
# users, use PostgreSQL which has row-level locking.
_login_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared ThreadPoolExecutor, creating it on first use."""
    global _login_executor
    with _executor_lock:
        if _login_executor is None:
            _login_executor = ThreadPoolExecutor(
                max_workers=settings.WEB_LOGIN_THREAD_POOL_SIZE,
                thread_name_prefix="web_login",
            )
            # atexit handlers are best-effort: they only run during
            # graceful shutdown (SIGTERM / sys.exit).  A SIGKILL will
            # skip them, leaving in-flight background threads orphaned.
            # This is acceptable because login requests self-heal via
            # cache TTL expiry regardless of thread completion.
            atexit.register(_login_executor.shutdown, wait=True)
    return _login_executor


# Maximum number of queued items before rejecting new requests (circuit breaker).
_MAX_QUEUED_LOGINS = getattr(settings, "WEB_LOGIN_MAX_QUEUED", 50)

# Semaphore-based counter for queue depth — avoids relying on the private
# ``ThreadPoolExecutor._work_queue`` attribute which is a CPython
# implementation detail and could break in future Python versions.
_queue_slots = threading.Semaphore(_MAX_QUEUED_LOGINS)


def _release_queue_slot(future) -> None:
    """Release a semaphore slot when a background login task completes."""
    _queue_slots.release()


class LoginServiceUnavailable(Exception):
    """Raised when the login background queue is full."""


class WebLoginService:
    """Service for bot-based web login flow."""

    def __init__(self):
        self.user_repo = user_repository
        self.request_repo = web_login_request_repository

    async def create_login_request(
        self, username: str, device_info: str | None = None
    ) -> dict:
        """Create a login request and dispatch Confirm/Deny to user via bot.

        For known users, the pending cache key is set inside the background
        thread (not here) to avoid blocking the main request thread with a
        cache write that could introduce a timing side-channel.  For unknown
        users, the cache key is set synchronously since there is no background
        thread to defer to.

        Args:
            username: Telegram @username (with or without @)
            device_info: Browser/device info string

        Returns:
            Dict with {token, expires_at} — always returned for both paths.
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        user = await maybe_await(self.user_repo.get_by_telegram_username(username))

        # Generate a cryptographically random token.
        token = secrets.token_urlsafe(TOKEN_BYTES)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=LOGIN_REQUEST_EXPIRY_MINUTES)

        if user and user.telegram_id:
            # Circuit breaker: reject if the background queue is saturated.
            if not _queue_slots.acquire(blocking=False):
                logger.critical(
                    "Login thread pool queue full (>=%d pending), rejecting request",
                    _MAX_QUEUED_LOGINS,
                )
                raise LoginServiceUnavailable(
                    "Login service temporarily unavailable"
                )
            # The pending cache key is set as the first action inside the
            # background thread — not here — to avoid blocking the main
            # request thread.  The frontend's 2-second initial poll delay
            # ensures the background thread has time to write the cache
            # entry before the first status check.
            try:
                future = _get_executor().submit(
                    self._process_login_background, user, token, expires_at, device_info
                )
                future.add_done_callback(_release_queue_slot)
            except RuntimeError:
                _queue_slots.release()
                raise LoginServiceUnavailable(
                    "Login service shutting down"
                )
            except Exception:
                _queue_slots.release()
                logger.error(
                    "Unexpected error during executor submit",
                    exc_info=True,
                    extra={"user_id": user.id},
                )
                raise
        else:
            # Unknown user or user without telegram_id — set cache marker
            # synchronously since there is no background thread.  Accept
            # a slight timing difference vs the known-user path; the jitter
            # in check_status masks it.
            cache_ttl = _cache_ttl_seconds(expires_at)
            try:
                cache_manager.set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
            except CacheWriteError as exc:
                logger.critical(
                    "Cache backend unhealthy during login request creation",
                    extra={"username": username},
                )
                raise LoginServiceUnavailable("Login service temporarily unavailable") from exc

            if not user:
                logger.warning(
                    "Web login request for unknown username",
                    extra={"username": username},
                )
            else:
                logger.warning(
                    "User has no telegram_id",
                    extra={"username": username, "user_id": user.id},
                )

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    def _process_login_background(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Process login request in a background thread (DB writes + Telegram send).

        Sets the pending cache key as its first action, then creates the DB
        record and sends the Telegram notification.
        """
        from src.web.utils.sync import call_async

        # Set the pending cache key first — moved here from
        # create_login_request() to keep the main request thread
        # constant-time (no cache write blocking the response).
        cache_ttl = _cache_ttl_seconds(expires_at)
        try:
            cache_manager.set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
        except CacheWriteError:
            logger.critical(
                "Cache backend unhealthy during background login processing",
                extra={"user_id": user.id, "token_prefix": token[:8]},
            )
            # Cannot proceed — check_status won't find this token.
            return

        def _mark_failed_safely():
            """Best-effort cache write; failures are logged but non-fatal here."""
            try:
                _mark_failed_token(token, expires_at)
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
            logger.critical(
                "Permanent Telegram error during login processing — check bot config",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()
        except RetryAfter as e:
            logger.warning(
                "Telegram rate limit during login processing (retry after %ds)",
                e.retry_after,
                extra={
                    "user_id": user.id,
                    "token_prefix": token[:8],
                    "retry_after": e.retry_after,
                },
            )
        except TelegramError as e:
            logger.error(
                "Temporary Telegram error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
        except DatabaseError as e:
            logger.error(
                "Database error during login processing",
                extra={"user_id": user.id, "token_prefix": token[:8], "error": str(e)},
            )
            _mark_failed_safely()
        except Exception as e:
            logger.error(
                "Unexpected error during login processing: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
                extra={"user_id": user.id, "token_prefix": token[:8]},
            )
            _mark_failed_safely()

    @staticmethod
    def _create_login_request_with_retry(user_id, token, expires_at: datetime, device_info):
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
                        created_at__gte=datetime.now(timezone.utc) - timedelta(hours=1),
                    ).update(status=WebLoginRequest.Status.DENIED)
                    login_request = WebLoginRequest.objects.create(
                        user_id=user_id,
                        token=token,
                        expires_at=expires_at,
                        device_info=device_info,
                    )
                    return login_request, token
            except IntegrityError:
                token = secrets.token_urlsafe(TOKEN_BYTES)
                cache_ttl = _cache_ttl_seconds(expires_at)
                try:
                    cache_manager.set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
                except CacheWriteError:
                    logger.critical(
                        "Cache write failed during token collision retry — "
                        "new token's pending marker not cached",
                        extra={"token_prefix": token[:8]},
                    )
        raise DatabaseError("Failed to generate unique token after retries")

    async def _process_login_request(
        self, user, token: str, expires_at: datetime, device_info: str | None
    ) -> None:
        """Perform DB writes and send Telegram notification."""
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

        try:
            chat_id = int(user.telegram_id)
        except (ValueError, TypeError):
            logger.error(
                "Invalid telegram_id for user — cannot send notification",
                extra={"user_id": user.id, "telegram_id": user.telegram_id},
            )
            _mark_failed_token(token, expires_at)
            return
        await self._send_login_notification(
            chat_id, login_request.id, token, device_info
        )

    async def _send_login_notification(
        self, chat_id: int, request_id: int, token: str, device_info: str | None
    ) -> None:
        """Delegate to telegram_operations.send_login_notification."""
        await send_login_notification(
            chat_id, request_id, token, device_info, self.request_repo
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

        now = datetime.now(timezone.utc)
        pending_key = f"{WL_PENDING_KEY}{token}"
        failed_key = f"{WL_FAILED_KEY}{token}"
        try:
            cache_keys = cache.get_many([pending_key, failed_key])
        except Exception:
            logger.warning(
                "Cache read failed during status check",
                extra={"token_prefix": token[:8]},
            )
            cache_keys = {}
        cache_pending = cache_keys.get(pending_key)
        cache_failed = cache_keys.get(failed_key)

        if cache_failed:
            status = "error"
        elif cache_pending:
            status = "pending"
        else:
            db_unavailable = False
            try:
                login_request = await maybe_await(self.request_repo.get_status_fields(token))
            except OperationalError:
                logger.warning(
                    "DB lock during status check, cache is empty",
                    extra={"token_prefix": token[:8]},
                )
                login_request = None
                db_unavailable = True

            if not login_request:
                if db_unavailable:
                    status = "error"
                else:
                    try:
                        cache.set(f"{WL_FAILED_KEY}{token}", True, timeout=300)
                    except Exception:
                        pass
                    status = "expired"
            elif login_request.expires_at is None or now > _ensure_utc(login_request.expires_at):
                status = "expired"
            else:
                status = str(login_request.status)

        if status in ("pending", "expired", "error"):
            await asyncio.sleep(_secure_random.uniform(_JITTER_MIN, _JITTER_MAX))

        return status

    async def complete_login(self, token: str):
        """Complete the login after confirmation.

        Args:
            token: Login request token

        Returns:
            User instance if login is valid, None otherwise
        """
        now = datetime.now(timezone.utc)
        login_request = await maybe_await(self.request_repo.get_by_token(token))
        if not login_request:
            logger.warning(
                "Complete login attempt with unknown token",
                extra={"token_prefix": token[:8]},
            )
            return None

        if login_request.status != WebLoginRequest.Status.CONFIRMED.value:
            logger.warning(
                "Complete login attempt with unexpected status",
                extra={
                    "token_prefix": token[:8],
                    "status": login_request.status,
                    "user_id": login_request.user_id,
                },
            )
            return None

        if login_request.expires_at is None or now > _ensure_utc(login_request.expires_at):
            logger.warning(
                "Complete login attempt with expired token",
                extra={"token_prefix": token[:8], "user_id": login_request.user_id},
            )
            return None

        updated = await maybe_await(self.request_repo.mark_as_used(token))
        if not updated:
            logger.warning(
                "Token replay attempt — already used: %s...",
                token[:8],
                extra={
                    "user_id": login_request.user_id,
                    "operation": "complete_login_replay",
                },
            )
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
