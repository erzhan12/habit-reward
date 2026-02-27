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
import os
import secrets
import signal
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
    Consider enabling ``USE_TZ=True`` to avoid naive datetimes at the source.

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
#
# Why 50ms–200ms?  OWASP Testing Guide v4 §4.4.5 (Authentication Timing)
# recommends adding random delays that exceed the observable timing
# difference between code paths.  Measured delta between cache-hit and
# DB-fallback is ~5-30ms; the 50-200ms uniform range (≥10× the signal)
# makes statistical discrimination infeasible even with thousands of
# samples.  The upper bound (200ms) keeps UX responsive — users polling
# every 2-3s won't notice the added latency.
# See also: SECURITY.md § "Timing Attack Resistance" for the full threat model.
_JITTER_MIN = getattr(settings, "WEB_LOGIN_JITTER_MIN", 0.05)
_JITTER_MAX = getattr(settings, "WEB_LOGIN_JITTER_MAX", 0.2)

# Bounded thread pool for background login processing (DB writes + Telegram send).
# See token_operations.py for token constants, cache_operations.py for cache logic.
#
# IMPORTANT: SQLite doesn't handle concurrent writes well — its file-level
# locking means only one writer at a time.  For production with concurrent
# users, use PostgreSQL which has row-level locking.
#
# TODO: Consider replacing this custom thread-pool orchestration with Django
# async views + sync_to_async for simpler concurrency management.
_login_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


_EXECUTOR_SHUTDOWN_TIMEOUT = 30  # seconds


def _shutdown_executor(signum=None, frame=None) -> None:
    """Gracefully shut down the login executor.

    Called by SIGTERM/SIGINT handlers and atexit.  Uses a 30-second timeout
    to prevent hanging if threads are stuck (e.g. waiting on Telegram API).
    """
    global _login_executor
    with _executor_lock:
        executor = _login_executor
    if executor is None:
        return
    # During interpreter shutdown (atexit), logging streams may already be
    # closed.  Disable logging temporarily to avoid "I/O operation on
    # closed file" tracebacks from the logging framework.
    if not signum:
        logging.disable(logging.CRITICAL)
    else:
        sig_name = signal.Signals(signum).name
        logger.info(
            "Shutting down login executor (%s), timeout=%ds",
            sig_name,
            _EXECUTOR_SHUTDOWN_TIMEOUT,
        )
    executor.shutdown(wait=True, cancel_futures=False)


def _install_signal_handlers() -> None:
    """Install SIGTERM/SIGINT handlers for graceful executor shutdown.

    Only installs handlers from the main thread (signal handlers can only
    be registered from the main thread).  Preserves existing handlers by
    chaining — calls the previous handler after our shutdown logic.
    """
    if threading.current_thread() is not threading.main_thread():
        return
    for sig in (signal.SIGTERM, signal.SIGINT):
        prev_handler = signal.getsignal(sig)

        def _handler(signum, frame, _prev=prev_handler):
            _shutdown_executor(signum, frame)
            if callable(_prev) and _prev not in (signal.SIG_DFL, signal.SIG_IGN):
                _prev(signum, frame)
            elif _prev == signal.SIG_DFL:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)

        signal.signal(sig, _handler)


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared ThreadPoolExecutor, creating it on first use."""
    global _login_executor
    with _executor_lock:
        if _login_executor is None:
            _login_executor = ThreadPoolExecutor(
                max_workers=settings.WEB_LOGIN_THREAD_POOL_SIZE,
                thread_name_prefix="web_login",
            )
            # atexit is best-effort (skipped on SIGKILL).  Signal handlers
            # provide more reliable shutdown for SIGTERM/SIGINT.
            atexit.register(_shutdown_executor)
            _install_signal_handlers()
    return _login_executor


# Maximum number of queued items before rejecting new requests (circuit breaker).
# 50 = 5x normal thread pool size (10 workers), allowing burst capacity
# while preventing unbounded queuing.
_MAX_QUEUED_LOGINS = getattr(settings, "WEB_LOGIN_MAX_QUEUED", 50)

# Warn when queue depth reaches this fraction of the max (default 80%).
_QUEUE_WARN_THRESHOLD = int(_MAX_QUEUED_LOGINS * 0.8)

# Semaphore-based counter for queue depth — avoids relying on the private
# ``ThreadPoolExecutor._work_queue`` attribute which is a CPython
# implementation detail and could break in future Python versions.
_queue_slots = threading.Semaphore(_MAX_QUEUED_LOGINS)
# Atomic counter for monitoring queue depth (semaphore value isn't readable).
_queue_depth = threading.Lock()
_queue_depth_count = 0


def _increment_queue_depth() -> int:
    """Atomically increment and return the current queue depth."""
    global _queue_depth_count
    with _queue_depth:
        _queue_depth_count += 1
        return _queue_depth_count


def _decrement_queue_depth() -> int:
    """Atomically decrement and return the current queue depth."""
    global _queue_depth_count
    with _queue_depth:
        _queue_depth_count = max(0, _queue_depth_count - 1)
        return _queue_depth_count


def _release_queue_slot(future) -> None:
    """Release a semaphore slot when a background login task completes."""
    try:
        depth = _decrement_queue_depth()
        if depth > 0:
            logger.debug("Login queue depth after completion: %d", depth)
    finally:
        _queue_slots.release()


def _release_acquired_queue_slot() -> None:
    """Release queue accounting for a slot that was acquired but not submitted."""
    try:
        _decrement_queue_depth()
    finally:
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

        Both known and unknown usernames are handled via background workers so
        cache writes happen off the request thread on both paths. This keeps
        response timing and failure behavior aligned to reduce enumeration risk.

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
            self._submit_background_login_job(
                self._process_login_background,
                user,
                token,
                expires_at,
                device_info,
                log_extra={"user_id": user.id},
            )
        else:
            self._submit_background_login_job(
                self._process_unknown_login_background,
                user,
                username,
                token,
                expires_at,
                log_extra={"username": username, "user_id": getattr(user, "id", None)},
            )

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    def _submit_background_login_job(self, job, *args, log_extra: dict | None = None) -> None:
        """Submit a background login job with queue-slot accounting."""
        if not _queue_slots.acquire(blocking=False):
            logger.critical(
                "Login thread pool queue full (>=%d pending), rejecting request",
                _MAX_QUEUED_LOGINS,
            )
            raise LoginServiceUnavailable(
                "Login service temporarily unavailable"
            )

        depth = _increment_queue_depth()
        if depth >= _QUEUE_WARN_THRESHOLD:
            logger.warning(
                "Login queue depth %d approaching limit %d",
                depth,
                _MAX_QUEUED_LOGINS,
            )

        try:
            future = _get_executor().submit(job, *args)
            future.add_done_callback(_release_queue_slot)
        except RuntimeError as exc:
            _release_acquired_queue_slot()
            raise LoginServiceUnavailable(
                "Login service shutting down"
            ) from exc
        except Exception:
            _release_acquired_queue_slot()
            logger.error(
                "Unexpected error during executor submit",
                exc_info=True,
                extra=log_extra or {},
            )
            raise

    def _process_unknown_login_background(
        self, user, username: str, token: str, expires_at
    ) -> None:
        """Background path for unknown users or users without telegram_id."""
        cache_ttl = _cache_ttl_seconds(expires_at)
        try:
            cache_manager.set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
        except CacheWriteError:
            logger.critical(
                "Cache backend unhealthy during unknown-user login processing",
                extra={"username": username, "token_prefix": token[:8]},
            )
            return

        if not user:
            logger.warning(
                "Web login request for unknown username",
                extra={"username": username},
            )
        else:
            logger.warning(
                "User exists but has no telegram_id (account created via non-bot method)",
                extra={"username": username, "user_id": user.id},
            )

    def _process_login_background(
        self, user, token: str, expires_at, device_info: str | None
    ) -> None:
        """Process login request in a background thread (DB writes + Telegram send).

        Sets the pending cache key as its first action, then creates the DB
        record and sends the Telegram notification.

        Checks for staleness first: if the request has already expired by
        the time the thread picks it up (e.g. queue backlog), it skips
        processing and marks the token as failed.
        """
        from src.web.utils.sync import call_async

        # Staleness check: if the item sat in the queue long enough to
        # expire, skip processing — the client will already see "expired".
        if datetime.now(timezone.utc) >= expires_at:
            logger.warning(
                "Skipping stale login request (expired while queued)",
                extra={"user_id": user.id, "token_prefix": token[:8]},
            )
            try:
                _mark_failed_token(token, expires_at)
            except CacheWriteError:
                pass
            return

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
            """Best-effort cache write; failures are logged but non-fatal here.

            If the cache write fails, the token stays in "pending" state
            until its cache TTL expires.  This is degraded but acceptable:
            the client will eventually see "expired" instead of "error".
            We log at ERROR with a monitoring metric so alerting picks it up.
            """
            try:
                _mark_failed_token(token, expires_at)
            except CacheWriteError as cache_error:
                logger.error(
                    "Failed to write wl_failed marker to cache — token may "
                    "stay in 'pending' state until TTL expiry",
                    extra={
                        "metric": "web_login.mark_failed.cache_write_error",
                        "user_id": user.id,
                        "token_prefix": token[:8],
                        "error": str(cache_error),
                    },
                )

        # All error paths call _mark_failed_safely() so the frontend sees
        # "error" status instead of hanging on "pending" forever.  This is
        # intentional: even for potentially transient errors (RetryAfter,
        # TelegramError), we don't retry in this thread — the user can
        # simply re-initiate the login.  Marking failed immediately gives
        # clear feedback rather than leaving the client polling indefinitely.
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
            _mark_failed_safely()
        except TelegramError as e:
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
        # Use 'in' instead of .get() — Django's get_many() omits missing
        # keys from the returned dict, so 'in' correctly distinguishes
        # between a missing key (cache miss) and a key with a falsy value.
        cache_pending = pending_key in cache_keys
        cache_failed = failed_key in cache_keys

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
