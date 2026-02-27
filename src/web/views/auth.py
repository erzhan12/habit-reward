"""Authentication views for bot-based Confirm/Deny login.

Endpoints
---------
POST /auth/bot-login/request/
    Initiate a login request — sends Confirm/Deny to the user's Telegram.
    Rate limit: ``AUTH_RATE_LIMIT`` (default ``10/m``).

GET  /auth/bot-login/status/<token>/
    Poll the status of a pending login request.
    Rate limit: ``AUTH_STATUS_RATE_LIMIT`` (default ``30/m``).

POST /auth/bot-login/complete/
    Complete login after Telegram confirmation — creates a Django session.
    Rate limit: ``AUTH_RATE_LIMIT`` (default ``10/m``).

Security properties
~~~~~~~~~~~~~~~~~~~
* **Anti-enumeration**: Both known and unknown usernames receive an identical
  200 response with a token.  Background processing is deferred to a thread
  pool so timing is constant.
* **Timing jitter**: ``check_status`` adds 50-200ms random jitter (configurable)
  from a ``secrets.SystemRandom()`` CSPRNG.
* **Atomic replay prevention**: Confirmed tokens are atomically marked
  ``used`` via ``UPDATE … WHERE status='confirmed'``.
* **Rate limiting**: All endpoints are rate-limited per IP via
  ``django-ratelimit``.
"""

import functools
import hashlib
import json
import logging
import re

from user_agents import parse as parse_ua

from django.contrib.auth import login, logout
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from inertia import render as inertia_render

from src.web.services.web_login_service import (
    LoginServiceUnavailable,
    TOKEN_MIN_LENGTH,
    TOKEN_MAX_LENGTH,
    web_login_service,
)
from src.web.utils.ip import parse_ip_address
from src.web.utils.sync import call_async
from src.web.utils.validation import TELEGRAM_USERNAME_PATTERN

logger = logging.getLogger(__name__)

# Maximum length for User-Agent string before parsing (prevent memory issues)
MAX_USER_AGENT_LENGTH = 1024
# Maximum device_info length (DB field constraint)
MAX_DEVICE_INFO_LENGTH = 255
# URL-safe base64 token format (secrets.token_urlsafe output)
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
# TOKEN_MIN_LENGTH and TOKEN_MAX_LENGTH are imported from
# web_login_service where they are derived from TOKEN_BYTES
# (single source of truth).

# Re-export for backward compatibility with existing tests.
_parse_ip_address = parse_ip_address


def login_page(request):
    """Render the login page."""
    if request.user.is_authenticated:
        return redirect("/")

    return inertia_render(request, "Login")


def _sanitize_user_agent(ua: str) -> str:
    """Truncate and filter a raw User-Agent string.

    Removes non-printable characters and caps length at
    ``MAX_USER_AGENT_LENGTH`` to bound downstream processing.
    """
    ua = ua[:MAX_USER_AGENT_LENGTH]
    return ''.join(c for c in ua if c.isprintable() or c.isspace())


# Default max entries for the User-Agent LRU parse cache.
# Used as the fallback when settings.UA_CACHE_MAX_SIZE is not set.
_UA_CACHE_DEFAULT_SIZE = 1024
_UA_CACHE_MAX_SIZE = getattr(settings, "UA_CACHE_MAX_SIZE", _UA_CACHE_DEFAULT_SIZE)


@functools.lru_cache(maxsize=_UA_CACHE_MAX_SIZE)
def _parse_ua_cached(ua: str) -> str:
    """Parse a sanitized User-Agent string into a human-readable description.

    LRU-cached because UA parsing (via ``user_agents`` library) is
    CPU-intensive and the same UA string repeats across requests from
    the same browser.  Cache is bounded to ``UA_CACHE_MAX_SIZE`` entries
    (default ``_UA_CACHE_DEFAULT_SIZE``) to limit memory usage while still
    providing excellent hit rates.  Configurable via ``settings.UA_CACHE_MAX_SIZE``.

    NOTE: This LRU cache is **per-process**.  In production with multiple
    workers (e.g. gunicorn with ``--workers 4``), each process maintains
    its own independent cache, reducing the overall hit rate compared to a
    single-process deployment.  This is acceptable because UA diversity is
    low (most users share a handful of browser/OS combos) and the per-process
    cache still prevents redundant parsing within each worker.
    """
    ua_parsed = parse_ua(ua)
    browser = f"{ua_parsed.browser.family} {ua_parsed.browser.version_string}".strip()
    os_name = f"{ua_parsed.os.family} {ua_parsed.os.version_string}".strip()

    if not browser or browser == "Other":
        browser = "Unknown browser"
    if not os_name or os_name == "Other":
        os_name = "Unknown OS"

    raw = f"{browser} on {os_name}"
    if not raw or raw.isspace():
        raw = "Unknown device"
    return raw[:MAX_DEVICE_INFO_LENGTH]


def _parse_device_info(request) -> str:
    """Extract a human-readable device description from the request.

    Delegates to ``_parse_ua_cached`` for the CPU-intensive UA parsing.
    Output is truncated to 255 characters (DB field limit) at this input
    boundary.  No IP address is included (GDPR).
    """
    ua = _sanitize_user_agent(request.META.get("HTTP_USER_AGENT", ""))

    result = _parse_ua_cached(ua)

    if "Unknown browser" in result or "Unknown OS" in result:
        logger.debug(
            "Unrecognised User-Agent during device_info parsing: %s",
            ua[:200],
        )

    return result


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True, group="bot_login_request")
def bot_login_request(request):
    """Initiate a bot-based login request.

    POST /auth/bot-login/request/
    Content-Type: application/json

    Request body::

        {"username": "johndoe"}

    Success response (200)::

        {
            "token": "<urlsafe-base64>",
            "expires_at": "2026-02-26T12:05:00+00:00",
            "message": "If this username is registered, a login confirmation has been sent."
        }

    Error responses:
        - 400: Invalid/missing request body or username fails validation.
        - 429: Rate limit exceeded (AUTH_RATE_LIMIT, default 10/m).

    Always returns 200 with a generic message to prevent username enumeration.
    The service always returns a token (real or cache-only) so no branching
    is needed here — both known and unknown users get the same response.

    Example::

        curl -X POST http://localhost:8000/auth/bot-login/request/ \\
             -H 'Content-Type: application/json' \\
             -H 'X-CSRFToken: <token>' \\
             -d '{"username": "johndoe"}'
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    username = str(data.get("username", "")).strip()
    if not username:
        return JsonResponse({"error": "Username is required"}, status=400)

    # Strip @ prefix if present
    username = username.lstrip("@")

    # Basic validation — canonical pattern from src/web/utils/validation.py
    # Must match frontend regex in frontend/src/pages/Login.vue
    if not re.match(TELEGRAM_USERNAME_PATTERN, username):
        return JsonResponse({"error": "Invalid Telegram username"}, status=400)

    device_info = _parse_device_info(request)

    try:
        result = call_async(
            web_login_service.create_login_request(username, device_info)
        )
    except LoginServiceUnavailable:
        return JsonResponse(
            {"error": "Service temporarily unavailable. Please try again shortly."},
            status=503,
        )

    # SECURITY: Always return 200 with a generic message and the token.
    # The service returns {token, expires_at} for BOTH known and unknown
    # users — no branching here prevents username enumeration via response
    # body or status code differences.
    result["message"] = "If this username is registered, a login confirmation has been sent."
    return JsonResponse(result)


@require_GET
@ratelimit(key="ip", rate=settings.AUTH_STATUS_RATE_LIMIT, method="GET", block=True)
def bot_login_status(request, token):
    """Poll the status of a pending login request.

    GET /auth/bot-login/status/<token>/

    Success response (200)::

        {"status": "pending|confirmed|denied|expired|used|error"}

    Status values:
        - ``pending``: Waiting for user to confirm/deny in Telegram.
        - ``confirmed``: User tapped Confirm — call ``/complete/`` next.
        - ``denied``: User tapped Deny.
        - ``expired``: Token TTL (5 min) elapsed.
        - ``used``: Token was already consumed by ``/complete/``.
        - ``error``: Background processing failed (Telegram/DB error).

    Error responses:
        - 400: Invalid token format.
        - 429: Rate limit exceeded (AUTH_STATUS_RATE_LIMIT, default 30/m).

    Includes random 50-200ms jitter (configurable) to mask timing side-channels.

    Example::

        curl http://localhost:8000/auth/bot-login/status/abc123def456/
    """
    token = str(token).strip()
    if not (TOKEN_MIN_LENGTH <= len(token) <= TOKEN_MAX_LENGTH) or not _TOKEN_PATTERN.match(token):
        return JsonResponse({"error": "Invalid token format"}, status=400)

    status = call_async(web_login_service.check_status(token))
    return JsonResponse({"status": status})


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True)
def bot_login_complete(request):
    """Complete login after Telegram confirmation — creates a Django session.

    POST /auth/bot-login/complete/
    Content-Type: application/json

    Request body::

        {"token": "<urlsafe-base64>"}

    Success response (200)::

        {"success": true, "redirect": "/"}

    Error responses:
        - 400: Invalid/missing request body or token.
        - 403: Token is expired, not confirmed, or already used.
        - 429: Rate limit exceeded (AUTH_RATE_LIMIT, default 10/m).

    The token must be in ``confirmed`` status. Atomically marks it as
    ``used`` to prevent replay attacks.

    Example::

        curl -X POST http://localhost:8000/auth/bot-login/complete/ \\
             -H 'Content-Type: application/json' \\
             -H 'X-CSRFToken: <token>' \\
             -d '{"token": "abc123def456"}'
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    token = str(data.get("token", "")).strip()
    if not token:
        return JsonResponse({"error": "Token is required"}, status=400)

    if not (TOKEN_MIN_LENGTH <= len(token) <= TOKEN_MAX_LENGTH):
        return JsonResponse({"error": "Invalid token format"}, status=400)

    if not _TOKEN_PATTERN.match(token):
        return JsonResponse({"error": "Invalid token format"}, status=400)

    user = call_async(web_login_service.complete_login(token))
    if not user:
        return JsonResponse({"error": "Login request expired or invalid. Please try again."}, status=403)

    # Create Django session
    login(request, user)
    logger.info("Web login successful for user %s (id=%s)", user.name, user.id)

    return JsonResponse({"success": True, "redirect": "/"})


@require_POST
def logout_view(request):
    """Log out the user and redirect to login page."""
    logout(request)
    return redirect("/auth/login/")


def dev_login(request):
    """DEV ONLY: Log in as user from DEFAULT_USER_TELEGRAM_ID setting.

    Only available when DEBUG=True. Skips Telegram auth entirely.
    """
    if not settings.DEBUG:
        return redirect("/auth/login/")

    from src.core.models import User

    telegram_id = settings.DEFAULT_USER_TELEGRAM_ID
    if telegram_id:
        user = User.objects.filter(telegram_id=str(telegram_id), is_active=True).first()
    else:
        user = User.objects.filter(is_active=True).first()

    if not user:
        return JsonResponse({"error": "No active users in database"}, status=404)

    login(request, user)
    logger.info("Dev login as user %s (id=%s)", user.name, user.id)
    return redirect("/")


def _anonymize_ip(ip: str) -> str:
    """Hash an IP address for GDPR-safe logging.

    Returns a 16-character SHA-256 prefix that is sufficient for correlating
    log entries (e.g. rate-limit events) without storing the raw IP address,
    which is PII under GDPR.

    The 16-hex-char prefix (64 bits) provides ~4 billion unique buckets,
    virtually eliminating collision risk even across large IP pools while
    remaining irreversible.  This is the standard pattern used throughout
    the web layer — prefer this over logging raw IPs.
    """
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def rate_limited_view(request, exception=None):
    """Custom 403 handler — returns JSON for rate-limited requests."""
    from django_ratelimit.exceptions import Ratelimited

    if isinstance(exception, Ratelimited):
        logger.warning("Rate limit exceeded for ip=%s on %s", _anonymize_ip(request.META.get("REMOTE_ADDR", "unknown")), request.path)
        return JsonResponse(
            {"error": "Too many requests. Please wait a moment and try again."},
            status=429,
        )

    # Default 403 for non-rate-limit cases
    return JsonResponse({"error": "Forbidden"}, status=403)
