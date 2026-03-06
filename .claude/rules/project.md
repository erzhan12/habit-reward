# Architecture Decisions

These are non-obvious conventions that can't be inferred from code alone.

**Package manager**: `uv` (not pip/poetry). Run everything via `uv run`.

**Frontend**: Vue 3 + Inertia.js + Tailwind CSS. Build with Vite.

**Database access**: All DB ops go through repository classes in `src/core/repositories.py`, never direct ORM queries from handlers or services.

**Service layer**: Business logic in `src/services/`. Services coordinate between repositories — no direct DB calls from handlers.

**Async compatibility**: `maybe_await` (`src/utils/async_compat.py`) bridges sync Django ORM with async handlers. Do NOT replace `await maybe_await(repo.method(...))` with direct awaits — it breaks sync call sites.

**API**: FastAPI alongside Django via combined ASGI entry point in `asgi.py`. JWT auth for API, Django sessions for web.

**WebSocket**: FastAPI endpoint at `/ws/updates/` with Django session auth. `ConnectionManager` in `src/realtime/manager.py`.

**Telegram bot**: All user-facing strings via `msg()` from `src/bot/messages.py`. HTML formatting only (never Markdown). User validation required in all handlers.

**Themes**: 8 theme personalities. Config in `frontend/src/themes/index.js`, applied via `useTheme.js` composable.

## Environment Variables
- `DJANGO_SECRET_KEY`, `DATABASE_PATH`, `DEBUG`
- `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY`
- `API_SECRET_KEY`, `API_ACCESS_TOKEN_EXPIRE_MINUTES`, `API_REFRESH_TOKEN_EXPIRE_DAYS`
- See `RULES.md` for full documentation
