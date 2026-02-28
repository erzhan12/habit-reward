"""Token collision retry logic for login request creation.

Handles the rare case where a generated login token collides with an
existing one in the database.  Retries with a fresh token and writes
a cache alias so clients that received the original token can still
resolve the correct status.

See ``__init__.py`` for the ``WebLoginService`` class that calls this.
"""

import logging
import secrets
from datetime import datetime, timezone

from django.db import DatabaseError, IntegrityError, transaction

from src.core.models import WebLoginRequest

from .cache_operations import (
    CacheWriteError,
    WL_ALIAS_KEY,
    WL_FAILED_KEY,
    WL_PENDING_KEY,
    _MIN_FAILED_MARKER_TTL_SECONDS,
    _cache_ttl_seconds,
    cache_manager,
)
from .token_operations import TOKEN_BYTES, TOKEN_GENERATION_MAX_RETRIES

logger = logging.getLogger(__name__)


def create_login_request_with_retry(user_id, token, expires_at: datetime, device_info):
    """Invalidate pending requests and create a new one in a transaction.

    This function handles the full lifecycle of creating a ``WebLoginRequest``:

    1. **Invalidate existing requests** — Any pending requests for the same
       user that have not yet expired are marked as DENIED inside the same
       atomic transaction, ensuring only one active request exists per user.

    2. **Create the new request** — A new ``WebLoginRequest`` row is inserted
       with the provided token, expiry, and device info.

    3. **Retry on token collision** — If the ``INSERT`` fails with an
       ``IntegrityError`` (unique constraint on ``token``), a fresh token is
       generated.  A cache alias is written from the previous token to the
       new one so clients that already received the previous token continue
       to resolve the correct status and completion path.  The previous
       token's pending marker is removed to avoid stale ``pending`` responses
       if the alias key is later unavailable.  Up to
       ``TOKEN_GENERATION_MAX_RETRIES`` attempts are made before raising
       ``DatabaseError``.

    Example — alias chain on collision::

        1. Client receives token A in the HTTP response.
        2. Background thread tries INSERT with token A → IntegrityError.
        3. New token B is generated; DB row is created with token B.
        4. Cache alias written: wl_alias:A → B
        5. Client polls GET /status/A/
        6. _resolve_token_alias(A) follows alias → B
        7. check_status looks up B in cache/DB → returns correct status.
        8. Client calls POST /complete/ with token A → resolves to B → login succeeds.

    Returns:
        tuple[WebLoginRequest, str]: The created login request and the final
        token (which may differ from the input if a collision occurred).

    Raises:
        DatabaseError: If a unique token cannot be generated within the
        retry limit.
    """
    for _attempt in range(TOKEN_GENERATION_MAX_RETRIES):
        try:
            with transaction.atomic():
                WebLoginRequest.objects.filter(
                    user_id=user_id,
                    status=WebLoginRequest.Status.PENDING,
                    expires_at__gte=datetime.now(timezone.utc),
                ).update(status=WebLoginRequest.Status.DENIED)
                login_request = WebLoginRequest.objects.create(
                    user_id=user_id,
                    token=token,
                    expires_at=expires_at,
                    device_info=device_info,
                )
                return login_request, token
        except IntegrityError:
            previous_token = token
            token = secrets.token_urlsafe(TOKEN_BYTES)
            cache_ttl = _cache_ttl_seconds(expires_at)
            alias_written = False
            try:
                cache_manager.set(f"{WL_PENDING_KEY}{token}", True, cache_ttl)
                cache_manager.set(f"{WL_ALIAS_KEY}{previous_token}", token, cache_ttl)
                alias_written = True
            except CacheWriteError:
                logger.critical(
                    "Cache write failed during token collision retry — "
                    "pending marker/alias may be missing",
                    extra={
                        "token_prefix": token[:8],
                        "previous_token_prefix": previous_token[:8],
                    },
                )
            # Best-effort cleanup of the original token's pending marker.
            # Without this, old tokens can look permanently pending if the
            # alias key is unavailable (evicted/write failure).
            from django.core.cache import cache

            try:
                cache.delete(f"{WL_PENDING_KEY}{previous_token}")
                if not alias_written:
                    cache.set(
                        f"{WL_FAILED_KEY}{previous_token}",
                        True,
                        timeout=max(_MIN_FAILED_MARKER_TTL_SECONDS, cache_ttl),
                    )
            except (ConnectionError, TimeoutError, OSError):
                logger.warning(
                    "Cache cleanup failed during token collision retry",
                    extra={
                        "token_prefix": token[:8],
                        "previous_token_prefix": previous_token[:8],
                    },
                )
    raise DatabaseError("Failed to generate unique token after retries")
