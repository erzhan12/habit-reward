"""Cache operations for web login service.

Provides a ``CacheManager`` class that wraps Django's cache backend with
consecutive failure tracking. Raises ``CacheWriteError`` after a configurable
threshold of consecutive failures to surface likely cache misconfiguration.
Emits structured log fields (``metric=...``) so external monitoring can alert
on repeated cache write failures.
"""

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Cache key prefix to avoid collisions in shared cache backends.
_CACHE_PREFIX = "habit_reward:"
WL_PENDING_KEY = f"{_CACHE_PREFIX}wl_pending:"
WL_FAILED_KEY = f"{_CACHE_PREFIX}wl_failed:"

# Minimum TTL (seconds) for the wl_failed cache marker.  60 seconds is
# chosen to outlast the longest expected polling interval (30s max backoff
# + network delay) so the client sees the "error" status at least once.
_MIN_FAILED_MARKER_TTL_SECONDS = 60


class CacheWriteError(Exception):
    """Raised when cache writes fail repeatedly, indicating misconfiguration."""


class CacheManager:
    """Thread-safe cache writer with consecutive failure tracking.

    Raises ``CacheWriteError`` after ``failure_threshold`` consecutive
    write failures.  Individual failures are logged as warnings.

    Thread-safety: ``_failure_count`` is guarded by ``_lock``.  Both the
    increment and the threshold check happen inside the same ``with``
    block, preventing a TOCTOU race.  ``cache.set()`` is called outside
    the lock — Django cache backends are already thread-safe.

    Args:
        failure_threshold: Number of consecutive failures before raising.
            Default 10 — high enough to tolerate transient cache blips
            (e.g. Redis failover ≈ 1-5s), low enough to surface genuine
            misconfiguration quickly.
    """

    def __init__(self, failure_threshold: int | None = None):
        from django.conf import settings

        self._failure_count = 0
        self._lock = threading.Lock()
        self._failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else getattr(settings, "CACHE_FAILURE_THRESHOLD", 10)
        )

    def set(self, key: str, value, timeout: int) -> None:
        """Write to cache with failure tracking."""
        from django.core.cache import cache

        try:
            cache.set(key, value, timeout=timeout)
            with self._lock:
                previous_failures = self._failure_count
                self._failure_count = 0
            if previous_failures:
                logger.info(
                    "Cache write recovered after %d consecutive failures",
                    previous_failures,
                    extra={
                        "metric": "web_login.cache_write.recovered",
                        "consecutive_failures": previous_failures,
                    },
                )
        except (ConnectionError, TimeoutError, OSError):
            with self._lock:
                self._failure_count += 1
                failure_count = self._failure_count
                should_raise = failure_count >= self._failure_threshold
            logger.warning(
                "Cache write failed for %s (consecutive failures: %d)",
                key[:20], failure_count,
                extra={
                    "metric": "web_login.cache_write.failure",
                    "consecutive_failures": failure_count,
                },
            )
            if should_raise:
                logger.error(
                    "Cache write failure threshold reached",
                    extra={
                        "metric": "web_login.cache_write.threshold_exceeded",
                        "consecutive_failures": failure_count,
                        "failure_threshold": self._failure_threshold,
                    },
                )
                raise CacheWriteError(
                    f"Cache writes have failed {failure_count} times consecutively "
                    "— check cache backend configuration"
                )

    def reset(self) -> None:
        """Reset failure counter (useful for testing)."""
        with self._lock:
            self._failure_count = 0

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count (for monitoring)."""
        with self._lock:
            return self._failure_count


# Module-level singleton — shared across all callers.
cache_manager = CacheManager()


def _cache_ttl_seconds(expires_at, min_ttl: int = 1) -> int:
    """Calculate cache TTL in seconds from an expiry datetime.

    Returns at least ``min_ttl`` seconds so the cache entry doesn't
    expire prematurely or get a zero/negative timeout.
    """
    return max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), min_ttl)


def _mark_failed_token(token: str, expires_at) -> None:
    """Set a failure cache key so check_status can return 'error'."""
    cache_ttl = _cache_ttl_seconds(expires_at, min_ttl=_MIN_FAILED_MARKER_TTL_SECONDS)
    cache_manager.set(f"{WL_FAILED_KEY}{token}", True, cache_ttl)
