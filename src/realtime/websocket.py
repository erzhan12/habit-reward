"""FastAPI WebSocket endpoint with Django session authentication."""

import asyncio
import logging
import time
from collections import defaultdict
from importlib import import_module
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from asgiref.sync import sync_to_async
from src.realtime.manager import connection_manager
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()

PING_INTERVAL_SECONDS = 30

# Rate limiting: max connection attempts per IP per window
# NOTE: In-memory rate limiters are per-process. In multi-server deployments,
# each server tracks independently — effective limits are multiplied by server count.
# Use Redis-backed rate limiting (e.g. django-ratelimit) for shared state if needed.
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_WINDOW_SECONDS = 60

# In-memory rate limiter: IP -> list of timestamps
_MAX_RATE_LIMITER_ENTRIES = 10_000  # Max tracked IPs/users to cap memory usage
_connection_attempts: dict[str, list[float]] = defaultdict(list)

# Message rate limiting: max messages per user per window
_MESSAGE_RATE_LIMIT = 10  # messages per window
_MESSAGE_RATE_WINDOW = 60  # seconds
_message_counts: dict[int, list[float]] = defaultdict(list)


def _get_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket connection.

    Only trusts X-Forwarded-For if explicitly configured in settings.
    """
    try:
        from django.conf import settings
        trust_proxy = getattr(settings, "TRUST_PROXY_HEADERS", False)

        if trust_proxy:
            forwarded = websocket.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
    except ImportError:
        pass

    client = websocket.client
    return client.host if client else "unknown"


def _check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limit. Returns True if allowed."""
    now = time.monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS

    # Prune old entries and remove empty keys to prevent memory leak
    pruned = [t for t in _connection_attempts.get(ip, []) if t > cutoff]
    if not pruned:
        _connection_attempts.pop(ip, None)
    else:
        _connection_attempts[ip] = pruned

    if len(pruned) >= _RATE_LIMIT_MAX:
        return False

    # Evict oldest entries if dict grows too large
    if len(_connection_attempts) >= _MAX_RATE_LIMITER_ENTRIES:
        oldest_key = min(_connection_attempts, key=lambda k: _connection_attempts[k][-1])
        del _connection_attempts[oldest_key]

    _connection_attempts[ip].append(now)
    return True


def _check_message_rate_limit(user_id: int) -> bool:
    """Check if user is within message rate limit."""
    now = time.monotonic()
    cutoff = now - _MESSAGE_RATE_WINDOW

    # Prune old entries and remove empty keys to prevent memory leak
    pruned = [t for t in _message_counts.get(user_id, []) if t > cutoff]
    if not pruned:
        _message_counts.pop(user_id, None)
    else:
        _message_counts[user_id] = pruned

    if len(pruned) >= _MESSAGE_RATE_LIMIT:
        return False

    # Evict oldest entries if dict grows too large
    if len(_message_counts) >= _MAX_RATE_LIMITER_ENTRIES:
        oldest_key = min(_message_counts, key=lambda k: _message_counts[k][-1])
        del _message_counts[oldest_key]

    _message_counts[user_id].append(now)
    return True


def _validate_origin(websocket: WebSocket) -> bool:
    """Validate the Origin header against Django's ALLOWED_HOSTS.

    Returns True if origin is present and matches an allowed host.
    Returns False if origin is missing, invalid, or not in allowed hosts.
    Wildcard '*' in ALLOWED_HOSTS is only accepted when DEBUG=True.
    """
    origin = websocket.headers.get("origin")
    if not origin:
        logger.warning("WebSocket connection rejected: missing Origin header")
        return False

    try:
        from django.conf import settings

        parsed = urlparse(origin)
        origin_host = parsed.hostname
        if not origin_host:
            return False

        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        for host in allowed_hosts:
            if host == "*":
                if not getattr(settings, "DEBUG", False):
                    logger.warning(
                        "WebSocket origin check: wildcard '*' in ALLOWED_HOSTS ignored in production"
                    )
                    continue
                return True
            if host.startswith(".") and (
                origin_host == host[1:] or origin_host.endswith(host)
            ):
                return True
            if origin_host == host:
                return True

        logger.warning(
            "WebSocket connection rejected: origin %s not in ALLOWED_HOSTS", origin
        )
        return False
    except ImportError:
        logger.error("Django settings not available for origin validation")
        return False


async def _authenticate_websocket(websocket: WebSocket) -> int | None:
    """Authenticate a WebSocket connection using Django session cookie.

    Returns user_id if authenticated, None otherwise.
    """
    session_key = websocket.cookies.get("sessionid")
    if not session_key:
        return None

    try:
        from django.conf import settings

        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(session_key)

        # Load session data (sync ORM call)
        session_data = await sync_to_async(session.load)()

        # Reject expired sessions
        expiry_age = await sync_to_async(session.get_expiry_age)()
        if expiry_age <= 0:
            logger.warning("WebSocket connection rejected: expired session")
            return None

        user_id_str = session_data.get("_auth_user_id")
        if not user_id_str:
            return None

        user_id = int(user_id_str)

        # Verify user exists and is active
        user = await maybe_await(user_repository.get_by_id(user_id))
        if not user or not user.is_active:
            return None

        return user_id
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("WebSocket authentication failed: %s: %s", type(e).__name__, e)
        return None
    except ImportError:
        logger.error("Django session engine not available for WebSocket auth")
        return None
    except Exception:
        logger.exception("Unexpected WebSocket authentication error")
        return None


@router.websocket("/ws/updates/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates.

    Authenticates via Django session cookie, then keeps the connection
    open and forwards notification signals from the ConnectionManager.
    """
    # Rate limit check (before accept)
    client_ip = _get_client_ip(websocket)
    if not _check_rate_limit(client_ip):
        logger.warning("WebSocket rate limit exceeded for IP %s", client_ip)
        await websocket.close(code=1008)
        return

    # Origin validation (before accept)
    if not _validate_origin(websocket):
        await websocket.close(code=4403)
        return

    user_id = await _authenticate_websocket(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    if not await connection_manager.connect(user_id, websocket):
        return

    # Background task for keep-alive pings
    ping_task = asyncio.create_task(_ping_loop(websocket))

    try:
        while True:
            # Wait for client messages (keeps connection alive)
            await websocket.receive_text()
            if not _check_message_rate_limit(user_id):
                logger.warning("Message rate limit exceeded for user %s", user_id)
                await websocket.close(code=1008)
                break
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        await connection_manager.disconnect(user_id, websocket)


async def _ping_loop(websocket: WebSocket) -> None:
    """Send periodic pings to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            await websocket.send_json({"type": "ping"})
    except (RuntimeError, ConnectionError, WebSocketDisconnect, asyncio.CancelledError):
        pass  # Connection closed or task cancelled
