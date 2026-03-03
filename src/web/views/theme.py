"""Theme selection view."""

import json
import logging

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django_ratelimit.core import is_ratelimited

from inertia import render as inertia_render

from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

VALID_THEMES = {choice[0] for choice in User.THEME_CHOICES}


def _theme_action_ratelimited(request):
    """Sync helper for rate limit check (cache access from async view)."""
    return is_ratelimited(
        request,
        group="dashboard_action",
        key="user",
        rate=settings.DASHBOARD_ACTION_RATE_LIMIT,
        method="POST",
        increment=True,
    )


async def theme_page(request):
    """Render the theme picker page."""
    return inertia_render(request, "Theme", props={
        "currentTheme": request.user.theme,
    })


@require_POST
async def save_theme(request):
    """Save the user's selected theme."""
    if await sync_to_async(_theme_action_ratelimited)(request):
        messages.error(request, "Too many requests. Please wait a moment and try again.")
        return redirect("/theme/")

    try:
        payload = json.loads(request.body)
        theme = payload.get("theme", "")
    except (json.JSONDecodeError, AttributeError):
        theme = ""

    if theme not in VALID_THEMES:
        logger.warning("Invalid theme '%s' submitted by user %s", theme, request.user.id)
        messages.error(request, "Invalid theme selected. Please try again.")
        return redirect("/theme/")

    try:
        await maybe_await(user_repository.update(request.user.id, {"theme": theme}))
    except Exception:
        logger.exception("Failed to update theme for user %s", request.user.id)
        messages.error(request, "Failed to save theme. Please try again.")
        return redirect("/theme/")

    logger.info("User %s switched theme to '%s'", request.user.id, theme)

    return redirect("/theme/")
