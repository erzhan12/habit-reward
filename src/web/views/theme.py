"""Theme selection view."""

import json
import logging

from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from inertia import render as inertia_render

from src.core.models import User
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

VALID_THEMES = {choice[0] for choice in User.THEME_CHOICES}


async def theme_page(request):
    """Render the theme picker page."""
    return inertia_render(request, "Theme", props={
        "currentTheme": request.user.theme,
    })


@require_POST
async def save_theme(request):
    """Save the user's selected theme."""
    try:
        payload = json.loads(request.body)
        theme = payload.get("theme", "")
    except (json.JSONDecodeError, AttributeError):
        theme = ""

    if theme not in VALID_THEMES:
        logger.warning("Invalid theme '%s' submitted by user %s", theme, request.user.id)
        return redirect("/theme/")

    await maybe_await(user_repository.update(request.user.id, {"theme": theme}))
    logger.info("User %s switched theme to '%s'", request.user.id, theme)

    return redirect("/theme/")
