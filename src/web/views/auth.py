"""Authentication views for bot-based Confirm/Deny login."""

import json
import logging
import re
import secrets
from datetime import datetime, timezone, timedelta

from django.contrib.auth import login, logout
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from inertia import render as inertia_render

from src.web.services.web_login_service import web_login_service
from src.web.utils.sync import call_async

logger = logging.getLogger(__name__)


def login_page(request):
    """Render the login page."""
    if request.user.is_authenticated:
        return redirect("/")

    return inertia_render(request, "Login")


def _parse_device_info(request) -> str:
    """Extract a human-readable device description from the request."""
    ua = request.META.get("HTTP_USER_AGENT", "")
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    if not ip:
        ip = request.META.get("REMOTE_ADDR", "unknown")

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

    return f"{browser} on {os_name}, IP: {ip}"


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True)
def bot_login_request(request):
    """Handle login request: user submits their @username.

    POST /auth/bot-login/request/
    Body: {"username": "johndoe"}
    Returns: {"token": "...", "expires_at": "...", "sent": true}

    Always returns 200 with a generic message to prevent username enumeration.
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

    # Basic validation
    if not re.match(r"^[a-zA-Z0-9_]{3,32}$", username):
        return JsonResponse({"error": "Invalid Telegram username"}, status=400)

    device_info = _parse_device_info(request)

    result = call_async(
        web_login_service.create_login_request(username, device_info)
    )

    if not result:
        # Return a fake token/expiry so frontend transitions to polling
        # identically for known and unknown users (anti-enumeration).
        fake_token = secrets.token_urlsafe(32)
        fake_expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        # Cache fake token so status endpoint returns 'pending' until expiry
        cache.set(f"wl_fake:{fake_token}", True, timeout=300)
        return JsonResponse({
            "message": "If this username is registered, a login confirmation has been sent.",
            "token": fake_token,
            "expires_at": fake_expires,
        })

    result["message"] = "If this username is registered, a login confirmation has been sent."
    return JsonResponse(result)


@require_GET
@ratelimit(key="ip", rate="30/m", method="GET", block=True)
def bot_login_status(request, token):
    """Check login request status.

    GET /auth/bot-login/status/<token>/
    Returns: {"status": "pending|confirmed|denied|expired"}
    """
    status = call_async(web_login_service.check_status(token))
    return JsonResponse({"status": status})


@require_POST
@ratelimit(key="ip", rate=settings.AUTH_RATE_LIMIT, method="POST", block=True)
def bot_login_complete(request):
    """Complete login after confirmation.

    POST /auth/bot-login/complete/
    Body: {"token": "..."}
    Returns: {"success": true, "redirect": "/"}
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
        return JsonResponse({"error": "Login failed. Request may have expired or been denied."}, status=403)

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


def rate_limited_view(request, exception=None):
    """Custom 403 handler — returns JSON for rate-limited requests."""
    from django_ratelimit.exceptions import Ratelimited

    if isinstance(exception, Ratelimited):
        logger.warning("Rate limit exceeded for ip=%s on %s", request.META.get("REMOTE_ADDR", "unknown"), request.path)
        return JsonResponse(
            {"error": "Too many requests. Please wait a moment and try again."},
            status=429,
        )

    # Default 403 for non-rate-limit cases
    return JsonResponse({"error": "Forbidden"}, status=403)
