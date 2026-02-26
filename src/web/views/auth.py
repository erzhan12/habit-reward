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

from django.contrib.auth import login, logout
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from inertia import render as inertia_render

from src.web.services.web_login_service import LoginServiceUnavailable, web_login_service
from src.web.utils.ip import parse_ip_address
from src.web.utils.sync import call_async
from src.web.utils.validation import TELEGRAM_USERNAME_PATTERN

logger = logging.getLogger(__name__)

# Maximum length for User-Agent string before parsing (prevent memory issues)
MAX_USER_AGENT_LENGTH = 1024
# Maximum device_info length (DB field constraint)
MAX_DEVICE_INFO_LENGTH = 255

# Re-export for backward compatibility with existing tests.
_parse_ip_address = parse_ip_address


def login_page(request):
    """Render the login page."""
    if request.user.is_authenticated:
        return redirect("/")

    return inertia_render(request, "Login")


def _parse_device_info(request) -> str:
    """Extract a human-readable device description from the request.

    Parses the User-Agent header for browser and OS information.
    Logs unrecognised User-Agent strings at DEBUG level for monitoring.
    Output is HTML-escaped and truncated to 255 characters (DB field limit)
    at this input boundary.
    """
    # Truncate extremely long UA strings immediately to avoid keeping
    # potentially multi-MB strings in memory before parsing.
    ua = request.META.get("HTTP_USER_AGENT", "")[:MAX_USER_AGENT_LENGTH]
    ua = ''.join(c for c in ua if c.isprintable() or c.isspace())
    ip = parse_ip_address(request)

    # Extract browser name
    browser = "Unknown browser"
    if "Firefox/" in ua:
        match = re.search(r"Firefox/([\d.]+)", ua)
        browser = f"Firefox {match.group(1)}" if match else "Firefox"
    elif "Edg/" in ua:
        match = re.search(r"Edg/([\d.]+)", ua)
        browser = f"Edge {match.group(1)}" if match else "Edge"
    elif "Chrome/" in ua:
        match = re.search(r"Chrome/([\d.]+)", ua)
        browser = f"Chrome {match.group(1)}" if match else "Chrome"
    elif "Safari/" in ua and "Chrome" not in ua:
        match = re.search(r"Version/([\d.]+)", ua)
        browser = f"Safari {match.group(1)}" if match else "Safari"

    # Extract OS
    os_name = "Unknown OS"
    if "Windows" in ua:
        os_name = "Windows"
    elif "Macintosh" in ua or "Mac OS" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Android" in ua:
        os_name = "Android"

    if browser == "Unknown browser" or os_name == "Unknown OS":
        logger.debug(
            "Unrecognised User-Agent during device_info parsing: %s",
            ua[:200],
        )

    # Truncate to 255 chars (DB field limit).  HTML-escaping for Telegram
    # is done at the output boundary in _send_login_notification, not here,
    # so the DB stores clean data usable in any context.
    raw = f"{browser} on {os_name}, IP: {ip}"
    if not raw or raw.isspace():
        raw = "Unknown device"
    return raw[:MAX_DEVICE_INFO_LENGTH]


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True)
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
        - 429: Rate limit exceeded (AUTH_STATUS_RATE_LIMIT, default 30/m).

    Includes random 50-200ms jitter (configurable) to mask timing side-channels.

    Example::

        curl http://localhost:8000/auth/bot-login/status/abc123def456/
    """
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

    Returns a short SHA-256 prefix that's sufficient for correlating
    log entries without storing the raw IP.
    """
    return hashlib.sha256(ip.encode()).hexdigest()[:12]


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
