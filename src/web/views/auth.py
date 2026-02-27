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
MAX_USER_AGENT_LENGTH: int = 1024
# Maximum device_info length (DB field constraint)
MAX_DEVICE_INFO_LENGTH: int = 255
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


_NON_PRINTABLE_RE = re.compile(r'[^\x20-\x7E\s]')


def _sanitize_user_agent(ua: str) -> str:
    """Filter non-printable characters from a User-Agent string.

    Expects input already truncated to ``MAX_USER_AGENT_LENGTH`` by the
    caller (``_parse_ua_cached``).  Only performs character filtering.
    """
    return _NON_PRINTABLE_RE.sub('', ua)


_UA_CACHE_KEY_PREFIX = "ua_parse:"
_UA_CACHE_TTL = 3600  # 1 hour


def _parse_ua_cached(ua: str) -> str:
    """Parse a User-Agent string into a human-readable device description.

    Uses Django's cache framework (shared across processes, auto-evicted by
    TTL) instead of ``functools.lru_cache`` to avoid per-process memory
    buildup and test pollution. Cache key is a truncated BLAKE2b hash of
    the raw UA string (truncated once to ``MAX_USER_AGENT_LENGTH``) with a
    1-hour TTL.

    Performance note: UA truncation is computed once (``ua_truncated``) and
    reused for both cache key generation and sanitization.  UA sanitization
    is deferred until after cache lookup, so cache hits avoid extra string
    processing.
    """
    from django.core.cache import cache

    # Truncate once — used for both cache key and parsing.
    ua_truncated = ua[:MAX_USER_AGENT_LENGTH]
    # blake2b with digest_size=8 produces an 8-byte digest, which
    # hexdigest() encodes as a 16-character hex string.
    # Faster than SHA-256 and sufficient for cache key uniqueness.
    cache_key = (
        f"{_UA_CACHE_KEY_PREFIX}"
        f"{hashlib.blake2b(ua_truncated.encode(errors='ignore'), digest_size=8).hexdigest()}"
    )
    try:
        cached = cache.get(cache_key)
    except Exception:
        logger.warning("Cache read failed for UA parsing; falling back to direct parse")
        cached = None
    if cached is not None:
        return cached

    sanitized_ua = _sanitize_user_agent(ua_truncated)
    ua_parsed = parse_ua(sanitized_ua)
    browser = f"{ua_parsed.browser.family} {ua_parsed.browser.version_string}".strip()
    os_name = f"{ua_parsed.os.family} {ua_parsed.os.version_string}".strip()

    if not browser or browser == "Other":
        browser = "Unknown browser"
    if not os_name or os_name == "Other":
        os_name = "Unknown OS"

    raw = f"{browser} on {os_name}"
    if not raw or raw.isspace():
        raw = "Unknown device"
    # Truncate to DB field limit (255 chars) BEFORE caching.
    # Defense-in-depth: even though parse_ua usually produces short strings,
    # a crafted UA between 255-1024 chars could yield a longer parsed result.
    result = raw[:MAX_DEVICE_INFO_LENGTH]

    try:
        cache.set(cache_key, result, timeout=_UA_CACHE_TTL)
    except Exception:
        logger.warning("Cache write failed for UA parsing; result not cached")
    return result


def _parse_device_info(request) -> str:
    """Extract a human-readable device description from the request.

    Delegates to ``_parse_ua_cached`` for the CPU-intensive UA parsing.
    Output is truncated to 255 characters (DB field limit) at this input
    boundary.  No IP address is included (GDPR).
    """
    ua = request.META.get("HTTP_USER_AGENT", "")

    result = _parse_ua_cached(ua)

    if "Unknown browser" in result or "Unknown OS" in result:
        logger.debug(
            "Unrecognised User-Agent during device_info parsing: %s",
            _sanitize_user_agent(ua)[:200],
        )

    return result


def validate_login_token(token: str) -> bool:
    """Validate web login token format and length."""
    return (
        TOKEN_MIN_LENGTH <= len(token) <= TOKEN_MAX_LENGTH
        and _TOKEN_PATTERN.match(token) is not None
    )


def _validate_token_or_400(token: str):
    """Validate token format; return a 400 JsonResponse on failure, else None."""
    if not validate_login_token(token):
        return JsonResponse({"error": "Invalid token format"}, status=400)
    return None


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True, group="bot_login_request")
@ratelimit(key="user_or_ip", rate="5/m", method="POST", block=True)
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

    # Strip @ prefix if present (frontend also normalizes, but defense-in-depth)
    username = username.lstrip("@")

    # Basic validation — canonical pattern from src/web/utils/validation.py
    # Must match frontend regex in frontend/src/pages/Login.vue
    if not re.match(TELEGRAM_USERNAME_PATTERN, username):
        return JsonResponse({"error": "Invalid Telegram username"}, status=400)

    # Defense-in-depth: truncate even if _parse_device_info already does,
    # in case the parsing function changes or returns longer output.
    device_info = _parse_device_info(request)[:MAX_DEVICE_INFO_LENGTH]

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

        # Success: {"status": "pending"}
        # Success: {"status": "confirmed"}
        # Error:   {"error": "Invalid token format"}  (400)
    """
    token = str(token).strip()
    error = _validate_token_or_400(token)
    if error:
        return error

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

        # Success: {"success": true, "redirect": "/"}
        # Error:   {"error": "Token is required"}                              (400)
        # Error:   {"error": "Invalid token format"}                           (400)
        # Error:   {"error": "Login request expired or invalid. ..."}          (403)
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

    error = _validate_token_or_400(token)
    if error:
        return error

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

    The 16-hex-char prefix (64 bits) gives 2^64 buckets. Collisions are still
    possible (birthday bound reaches ~50% around 77k distinct IPs), so this
    is for coarse correlation only, not uniqueness guarantees.
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
