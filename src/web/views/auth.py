"""Authentication views for Telegram Login Widget."""

import json
import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from inertia import render as inertia_render

from src.core.models import User
from src.web.utils.telegram_auth import verify_telegram_auth

logger = logging.getLogger(__name__)


def login_page(request):
    """Render the login page with Telegram Login Widget."""
    if request.user.is_authenticated:
        return redirect("/")

    return inertia_render(request, "Login", props={
        "telegramBotUsername": settings.TELEGRAM_BOT_USERNAME,
    })


@require_POST
def telegram_callback(request):
    """Handle Telegram Login Widget callback.

    Receives auth data from the frontend, verifies HMAC hash,
    looks up the user by telegram_id, and creates a Django session.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    telegram_id = data.get("id")
    if not telegram_id:
        return JsonResponse({"error": "Missing Telegram user ID"}, status=400)

    # Verify HMAC-SHA-256 hash
    if not verify_telegram_auth(data, settings.TELEGRAM_BOT_TOKEN):
        logger.warning("Invalid Telegram auth hash for id=%s", telegram_id)
        return JsonResponse({"error": "Invalid authentication"}, status=403)

    # Look up existing user
    try:
        user = User.objects.get(telegram_id=str(telegram_id))
    except User.DoesNotExist:
        logger.info("Telegram user %s not found in database", telegram_id)
        return JsonResponse(
            {"error": "User not found. Please use the Telegram bot first."},
            status=404,
        )

    if not user.is_active:
        return JsonResponse({"error": "Account is inactive"}, status=403)

    # Create Django session
    login(request, user)
    logger.info("Web login successful for user %s (telegram_id=%s)", user.id, telegram_id)

    return JsonResponse({"success": True, "redirect": "/"})


@require_POST
def logout_view(request):
    """Log out the user and redirect to login page."""
    logout(request)
    return redirect("/auth/login/")
