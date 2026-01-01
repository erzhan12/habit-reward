"""ASGI entry point (combined Django + FastAPI).

This project uses:
- Django (admin + Telegram webhook endpoint)
- FastAPI (REST API + docs)

When running under Uvicorn, serve a single ASGI app that routes:
- FastAPI: `/v1/*`, `/health`, `/docs`, `/redoc`, `/openapi.json`
- Django: everything else (including `/admin/*` and `/webhook/telegram`)
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from django.core.asgi import get_asgi_application

# Setup Django before importing FastAPI modules that use ORM models/repositories.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.habit_reward_project.settings")
django_asgi_app = get_asgi_application()

from src.api.main import app as fastapi_app  # noqa: E402

ASGIApp = Callable[[dict, Callable[[], Awaitable[dict]], Callable[[dict], Awaitable[None]]], Awaitable[None]]

FASTAPI_PREFIXES = ("/v1/",)
FASTAPI_EXACT_PATHS = {"/v1", "/health", "/docs", "/redoc", "/openapi.json"}


class CombinedASGIApp:
    """Route requests to FastAPI or Django based on URL path."""

    def __init__(self, api_app: ASGIApp, django_app: ASGIApp) -> None:
        self._api_app = api_app
        self._django_app = django_app

    async def __call__(self, scope, receive, send) -> None:
        scope_type = scope.get("type")
        if scope_type == "lifespan":
            await self._api_app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in FASTAPI_EXACT_PATHS or any(path.startswith(prefix) for prefix in FASTAPI_PREFIXES):
            await self._api_app(scope, receive, send)
            return

        await self._django_app(scope, receive, send)


app = CombinedASGIApp(api_app=fastapi_app, django_app=django_asgi_app)
