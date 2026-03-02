# Development Rules & Patterns

## User Validation Pattern

**CRITICAL**: All Telegram bot command handlers MUST validate user exists and is active before processing.

```python
telegram_id = str(update.effective_user.id)
user = user_repository.get_by_telegram_id(telegram_id)
if not user:
    await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
    return
if not user.is_active:
    await update.message.reply_text(msg('ERROR_USER_INACTIVE', lang))
    return
```

## Django Initialization for Entry Points

**CRITICAL**: Any entry point that imports from `src.core.repositories` or `src.core.models` MUST configure Django first. Without this: `django.core.exceptions.ImproperlyConfigured`.

```python
"""Entry point script."""
# ruff: noqa: E402
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
django.setup()
# Now safe to import Django-dependent modules
```

**Files requiring this**: `src/dashboard/app.py`, `src/bot/main.py`, any standalone script using repositories.

## Message Management & Multi-lingual Support

**CRITICAL**: All user-facing strings MUST use `msg()` from `src/bot/messages.py`. Never hardcode strings. Supported languages: `en`, `ru`, `kk`.

```python
from src.bot.messages import msg
from src.bot.language import get_message_language
lang = get_message_language(telegram_id, update)
await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
await update.message.reply_text(msg('ERROR_REWARD_NOT_FOUND', lang, reward_name='Coffee'))
```

**Adding new messages**: Add constant to `Messages` class → add translations to `_TRANSLATIONS` → use `msg('KEY', lang)`.

### Telegram Message Formatting

**CRITICAL**: Always use HTML formatting with `parse_mode="HTML"`. Never use Markdown. Escape: `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`.

### Date Formatting Standard

**CRITICAL**: All user-facing dates: `"%d %b %Y"` → "09 Dec 2025". Concise, international, unambiguous.

## ConversationHandler Pattern Matching

**CRITICAL**: `CallbackQueryHandler` patterns are evaluated in list order — **first match wins**.

**Pitfall** (Feature 0029): If patterns share prefixes, the generic pattern matches before the specific one. E.g., `^claim_reward_` matches `"claim_reward_back"` before `^claim_reward_back$` is reached, causing "Reward progress not found" error.

**Solution**: Order handlers from most specific to least specific:
1. Exact matches (`^exact_string$`) first
2. Specific prefixes before generic prefixes
3. Use `$` anchor for exact matches

```python
# ✅ Specific pattern FIRST, generic SECOND
states={
    AWAITING_REWARD_SELECTION: [
        CallbackQueryHandler(claim_back_callback, pattern="^claim_reward_back$"),
        CallbackQueryHandler(claim_reward_callback, pattern="^claim_reward_"),
    ]
}
```

Always write tests to verify callback routing when patterns share prefixes.

## Logging Pattern

**CRITICAL**: All handlers MUST include info-level logging. Use `logger = logging.getLogger(__name__)`.

**Emoji Legend** (use consistently):
- 📨 Incoming message | 🖱️ Callback/click | ✏️ Text input | 🎯 Selection
- 🎁 Claim reward | 🔄 Status change | 📝 Parameters | 🔍 Query results
- 🤖 AI/NLP | ⚙️ Processing | ✅ Success | 🔥 Streak | ℹ️ Info
- ⚠️ Warning | ❌ Error | 📤 Outgoing response

## Repository Pattern

All DB operations go through repository classes in `src/core/repositories.py`. Never query Django ORM directly from handlers or services.

```python
from src.core.repositories import (
    user_repository, habit_repository, habit_log_repository,
    reward_repository, reward_progress_repository
)
```

### Django ORM Repository Pattern

Repository methods use `sync_to_async` to bridge sync Django ORM with async handlers.

### Why `maybe_await` Is Used Everywhere

`maybe_await` (`src/utils/async_compat.py`) inspects if a value is awaitable and awaits it, or returns directly. This lets service code work across async handlers, sync Django views (`call_async`), and test harnesses. **Do NOT replace** `await maybe_await(repo.method(...))` with `await repo.method(...)` — it breaks sync call sites.

### Performance: Always use `select_related()`/`prefetch_related()` for FK relationships to avoid N+1 queries.

### Django Model Instantiation

**CRITICAL**: Pass dicts to repository `create()`, never instantiate Django models directly in services.

**Auto-set fields** (never pass to create): `auto_now_add` timestamps, `auto_now` updated_at, `date_joined`, fields with defaults.

**Legacy mappings** (historical reference): `'active'` → `'is_active'`, `'created_at'` → `'date_joined'`. System fully migrated from Airtable to Django ORM.

### Computed Values Pattern

Use regular methods, not `@property`, for computed values (async compatibility):
- `get_status()` → RewardStatus | `get_pieces_required()` | `get_progress_percent()` | `get_status_emoji()`

Always `select_related('reward')` when querying RewardProgress.

### Async-Safe ForeignKey Access

**CRITICAL**: Model methods MUST NOT trigger sync DB queries in async contexts (`SynchronousOnlyOperation`).

**Solution**: Cache FK values in repositories after `select_related()`, then model methods use `_cached_*` attributes:

```python
# Repository: cache after select_related
progress._cached_pieces_required = progress.reward.pieces_required

# Model: use cached value
def _get_pieces_required_safe(self):
    if hasattr(self, '_cached_pieces_required'):
        return self._cached_pieces_required
    if hasattr(self, '_state') and 'reward' in self._state.fields_cache:
        return self.reward.pieces_required
    raise ValueError("RewardProgress requires reward to be prefetched or cached")
```

## Service Layer

Business logic in `src/services/`: `habit_service.py`, `streak_service.py`, `reward_service.py`, `nlp_service.py`, `audit_log_service.py`. Services coordinate between repositories — no direct DB calls.

### Multi-User Service Pattern

**CRITICAL**: Service methods require `user_id`. Always: get user → pass `user.id` to service methods.

```python
user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
habits = await maybe_await(habit_service.get_all_active_habits(user.id))
```

### NLP Service Optional Pattern

NLP gracefully degrades when `LLM_API_KEY` not configured — returns empty lists.

### Streak Service Pattern

Three methods + one helper:
1. **`calculate_streak(user_id, habit_id)`** — For LOGGING: returns next streak value
2. **`get_current_streak(user_id, habit_id, user_timezone)`** — For DISPLAYING: validates freshness, returns 0 if broken
3. **`get_validated_streak_map(user_id, habits, user_timezone)`** — Batch display: one DB query, validates all
4. **`_is_streak_alive()`** — Static helper shared by #2 and #3

**Critical Pitfall**: `get_latest_streak_counts()` returns raw stored values without freshness validation. Always use `streak_service.get_validated_streak_map()` (batch) or `get_current_streak()` (single).

### Streak Map Caching

Cached 5 min per user (`streaks:<user_id>`) via Django cache. Invalidated on: habit completion, revert (both variants). Cache key centralized in `StreakService.cache_key(user_id)`. Uses async cache API (`cache.aget()`, `cache.aset()`, `cache.adelete()`).

### Flexible Streak Tracking (Feature 0017)

**Habit Fields**: `allowed_skip_days` (int, default=0), `exempt_weekdays` (JSONField, default=[]), `category` (optional, NOT managed via Telegram — Feature 0024).

**Algorithm**: If gap > 1 day: filter out exempt weekday dates from gap → count remaining missed days → if `missed_days <= allowed_skip_days`: preserve streak, else break. Weekday numbering: `isoweekday()` (1=Mon, 7=Sun). Weekends = `[6, 7]`.

**Bot UI Flow**: name → weight → grace days (0-3) → exempt days (None/Weekends) → confirm.

## Import Pattern

Always use singleton instances: `from src.core.repositories import user_repository, habit_repository, ...`

## Django Transactions

**CRITICAL**: Use `transaction.atomic()` for multi-table operations. Wrap in `sync_to_async` for async contexts.

### Habit Completion Transaction

**CRITICAL**: Wrap both reward progress updates AND habit log creation atomically. Without this: orphaned progress entries.

### Reward Progress Validation

**Do NOT** validate `pieces_earned` by counting HabitLogs — for recurring rewards, logs accumulate across cycles while progress tracks current cycle only.

## Code Quality & Linting

**CRITICAL**: Before committing: run tests → self-review → fix → re-run → repeat until clean.

```bash
uv run ruff check src/        # Check
uv run ruff check src/ --fix   # Auto-fix
```

**Pitfall**: Background agents copy-paste full import blocks — always review for unused imports.

**Common issues**: Unused imports, ambiguous variable names (`l`, `O`, `I`), PEP 8 whitespace.

## Testing

```bash
uv run pytest tests/ -v                    # All tests
uv run pytest tests/test_file.py -v        # Specific file
uv run pytest --cov=src tests/             # Coverage
uv run pytest tests/ -v -m "not local_only"  # CI mode
```

**Bot handler tests**: Use `@patch` to mock repositories, `AsyncMock` for `reply_text`, `Mock(spec=Update)`.

**`@pytest.mark.local_only`**: Complex/long-running tests skipped in CI.

## Unified Reward System

**CRITICAL**: All rewards are cumulative. `pieces_required=1` for instant, `>1` for multi-piece.

**3-State Workflow** (computed by `get_status()`, never set manually):
1. **Pending**: `pieces_earned < pieces_required`
2. **Achieved**: `pieces_earned >= pieces_required && !claimed` — counter frozen, cannot earn more
3. **Claimed**: `claimed == true` — after `mark_reward_claimed()` resets to 0

**Key methods**: `update_reward_progress()` (smart increment) | `mark_reward_claimed()` (reset + claim)

### Daily Frequency Control

`Reward.max_daily_claims`: NULL/0=unlimited, 1+=limit. Counts individual pieces (claimed+unclaimed). Rewards at limit or completed are excluded from lottery selection.

### Piece Value Field

`piece_value` is optional analytics metadata. **Do NOT** expose in Telegram bot flows.

## Caddy Deployment

**Architecture**: 2 containers — Web (Django+Bot+SQLite) + Caddy (auto HTTPS).

**Files**: `deployment/caddy/Caddyfile`, `deployment/docker/docker-compose.caddy.yml`, `.github/workflows/deploy-caddy.yml`.

**DB**: `/home/deploy/habit_reward_bot/data/db.sqlite3`. Backup: `cp data/db.sqlite3 backups/db_$(date +%Y%m%d).sqlite3`.

**Domain blocking**: Caddy catch-all (MUST come last) rejects non-configured domains with 444.

**Health checks**: `start_period=60s`, `--max-time 5` in curl. Keep Dockerfile and compose consistent.

## Bot Audit Logging

Log high-level events via `audit_log_service`: commands, habit completions, reward claims/reverts, significant clicks, errors. Do NOT log low-level operations.

```python
await maybe_await(audit_log_service.log_command(user_id=user.id, command="/start", snapshot={...}))
await maybe_await(audit_log_service.log_habit_completion(user_id=user.id, habit=habit, reward=reward, ...))
await maybe_await(audit_log_service.log_error(user_id=user.id, error_message=str(e), context={...}))
```

**Admin**: `/admin/core/botauditlog/` (read-only). **Retention**: 90 days (`cleanup_audit_logs` command).

## Django Admin

### ID Fields in Details View

Add `'id'` to `readonly_fields` and first fieldset in `src/core/admin.py`.

### Custom Actions

**CRITICAL**: Admin runs in WSGI (sync). Never use `asyncio.run()` or async services — causes `RuntimeError: CurrentThreadExecutor`. Use pure Django ORM instead.

**Consistency**: Admin actions mirroring bot functionality must use same event types, fields, and audit logging. Always use enum constants (`BotAuditLog.EventType.HABIT_REVERTED`), never strings (typos → NULL).

**Best practices**: `select_related()`, `transaction.atomic()`, validate data, track success/failure counts, provide user feedback via Django messages.

## Web Login Status: String Returns & Enum Comparisons

- **Return values** from `check_status()`: plain strings for JSON serialization
- **Comparisons** in handlers/queries: `WebLoginRequest.Status.PENDING.value` for type safety

## HabitLog Ordering

**CRITICAL**: Always order by `last_completed_date DESC`, never `timestamp DESC`. Backdated entries have newer timestamps but older completion dates — wrong ordering breaks streak display.

```python
# ✅ Good
HabitLog.objects.filter(...).latest("last_completed_date")
# ❌ Bad
HabitLog.objects.filter(...).latest("timestamp")
```

## Backdate Habit Completion Pattern

Users can log habits for past dates (up to 7 days back).

### Architecture

- **Repository**: `get_log_for_habit_on_date()` (duplicate check), `get_logs_for_habit_in_daterange()` (calendar)
- **Service**: `process_habit_completion(target_date=None)`, `calculate_streak_for_date()`
- **Handler**: `src/bot/handlers/backdate_handler.py` (ConversationHandler: SELECTING_HABIT → SELECTING_DATE → CONFIRMING)

### Key Design Decisions

**HabitLog fields**: `timestamp` (auto_now_add, when logged) vs `last_completed_date` (actual completion date, can be backdated).

**Validation**: 7-day limit, no future dates, no before-habit-creation, duplicate prevention per date.

**Streak**: `calculate_streak()` for today, `calculate_streak_for_date()` for backdated (different gap logic).

**Date picker**: Shows 7-day calendar with checkmarks on completed dates.

**Error handling**: Map service `ValueError` messages to localized user messages in handlers.

### Duplicate Handler Pitfalls

1. **Bridge vs ConversationHandler**: Callbacks handled by ConversationHandler entry points MUST NOT also appear in `bridge_command_callback` mapping in `menu_handler.py`. Already excluded: `menu_habits_edit`, `menu_rewards_claim`.

2. **menu_handler.py vs habit_done_handler.py**: Habit completion flow exists in TWO places with different context key prefixes (`habit_id` vs `menu_habit_id`). **Update BOTH** when modifying yesterday/backdate flow.

3. **cancel_handler**: Must check `update.callback_query` to decide between `edit_message_text()` or `reply_text()`.

### In-Memory Object Sync After DB Update in Loops

**CRITICAL**: After DB update in a loop, sync the in-memory object too — otherwise subsequent iterations use stale values:
```python
await maybe_await(self.habit_log_repo.update(log.id, {"streak_count": new_streak}))
log.streak_count = new_streak  # ← sync the object
```
Affects: `recalculate_streaks_after_backdate()` in `src/services/habit_service.py`.

### Known Limitations

Backdating does NOT recalculate streak counts for existing future logs. Intentional — avoids expensive cascading updates. Current streak display via `get_current_streak()` is still correct.

## REST API (Feature 0022)

### Architecture

FastAPI alongside Django: `Mobile/Web Client → FastAPI (src/api/) → Service Layer → Django ORM → DB`. Combined ASGI entry point in `asgi.py`.

**Structure**: `src/api/main.py` (factory), `config.py` (JWT/CORS), `dependencies/auth.py` (JWT), `exceptions.py`, `v1/routers/` (endpoints).

### Running

```bash
uvicorn asgi:app --reload --port 8000
# Docs: /docs (Swagger), /redoc
```

### JWT Authentication

Login → `access_token` (15min) + `refresh_token` (7d). Use `Authorization: Bearer <token>`. Refresh with `POST /v1/auth/refresh`. Logout doesn't blacklist tokens (TODO: Redis).

**Dependency**: `current_user: Annotated[User, Depends(get_current_active_user)]`

### Endpoints (27 total)

- **Auth** `/v1/auth`: login, refresh, logout
- **Users** `/v1/users`: me, update, settings
- **Habits** `/v1/habits`: CRUD, complete, batch-complete
- **Habit Logs** `/v1/habit-logs`: list, get, revert (DELETE)
- **Rewards** `/v1/rewards`: CRUD, progress, claim
- **Streaks** `/v1/streaks`: list, detail
- **Health**: `/health` (NOT `/v1/health`)

### Error Responses

Standardized: `{"error": {"code": "ERROR_CODE", "message": "...", "details": {}}}`. Custom exceptions: `UnauthorizedException` (401), `ForbiddenException` (403), `NotFoundException` (404), `ConflictException` (409), `ValidationException` (422).

### Known Critical Issues

1. **P0 — Habit Log Revert Bug** (`habit_logs.py:214-218`): Accepts `log_id` but calls service with `habit_id` → reverts wrong log
2. **P0 — JWT Secret Regenerates** (`config.py:11`): Without `API_SECRET_KEY` env var, new key each restart invalidates all tokens
3. **P1 — Broken Active Filter** (`habits.py:150-154`): `?active=false` still returns only active (both branches call `get_all_active()`)
4. **P1 — Inefficient Log Lookup** (`habit_logs.py:150-151`): Fetches 1000 logs to find one by ID (needs `get_by_id()`)

### Configuration (.env)

`API_SECRET_KEY`, `API_ACCESS_TOKEN_EXPIRE_MINUTES=15`, `API_REFRESH_TOKEN_EXPIRE_DAYS=7`, `API_ALGORITHM=HS256`, `API_CORS_ORIGINS`.

### API Test Script

`scripts/test_api.sh`: 70+ assertions, multi-user isolation, error scenarios. Run with `./scripts/test_api.sh`.

## Claimed Rewards Feature (Feature 0035)

**Key patterns**:
- **Sorting**: When repository query has `.order_by()`, don't re-sort in service layer
- **Language detection**: Use pre-fetched `lang` everywhere — don't call `detect_language_from_telegram()` separately for errors
- **Imports**: All imports at top of handler files, not inline in functions
- **Test assertions**: Assert against exact `msg()` constants, not loose substrings
- **Silent fallbacks**: Log warnings for unexpected None values instead of silent `or 1`
- **DB-backed tests**: For critical query filters, write DB-backed integration tests alongside unit tests (mocked repos can't verify actual filtering)

## Web Interface Security Patterns (Feature 0036)

### Security Headers

`ContentSecurityPolicyMiddleware` (`src/web/middleware.py`) sets CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy in production (`DEBUG=False`). CSP nonce via `request.csp_nonce` → `csp_nonce` context processor → `<meta name="csp-nonce">`.

### Authentication Endpoint Hardening

**Rate limiting**: All auth endpoints use `django-ratelimit`. Rate configurable via `settings.AUTH_RATE_LIMIT` (default `'10/m'`). Always pair `method=` with `@require_POST`/`@require_GET`. Dashboard actions: `settings.DASHBOARD_ACTION_RATE_LIMIT` (default `'60/m'`), shared `group="dashboard_action"`.

**Anti-enumeration**: Bot-login endpoint MUST NOT leak username existence. Both paths return identical `{token, expires_at}` + 200. Background work (DB write + Telegram send) runs in `_login_executor` (bounded ThreadPoolExecutor). `check_status()` always performs both DB + cache lookups (no short-circuiting) with random jitter (100-500ms, `secrets.SystemRandom()`).

**Token replay prevention**: After confirmation, token status transitions `confirmed → used` atomically via `filter(token=..., status='confirmed').update(status='used')`.

**Token flow**: View receives POST → service looks up user (same path for known/unknown) → `secrets.token_urlsafe(32)` → `cache.set("wl_pending:{token}")` → for known users: `_login_executor.submit(DB write + Telegram send)` → return `{token, expires_at}` → frontend polls with additive backoff (2s→5s cap) → bot confirms → next poll returns "confirmed" → `POST /complete/` → session created.

**Frontend polling** (`Login.vue`): Additive backoff via recursive `setTimeout` (NOT `setInterval`). Server's `expires_at` drives client-side expiry (floor 60s, cap 5min). Stops after 5 consecutive network failures.

**IP binding**: Tokens bound to originating IP via `LoginTokenIpBinding`. Both status and complete endpoints enforce IP matching. Session also stores `wl_origin_ip:{token}`.

**Thread pool**: `ThreadPoolExecutor(max_workers=WEB_LOGIN_THREAD_POOL_SIZE)` with semaphore-based circuit breaker (`_queue_slots`). HTTP 503 when queue full. Named done callback `_release_queue_slot`.

**Background failure**: `TelegramError` (temporary) → don't mark failed, let TTL expire. `InvalidToken`/`Forbidden` (permanent) → mark failed via `wl_failed:{token}` cache key. All cache writes wrapped in try/except.

### Repository Pattern in Web Views

Use repositories with `run_sync_or_async` in sync Django views. In tests, mock `run_sync_or_async` to avoid SQLite locking.

### Other Web Patterns

- **Telegram username recycling**: `update_telegram_username` clears from previous owner before assigning. `/start` always syncs username.
- **CSRF**: Frontend reads from `<meta name="csrf-token">`, NOT cookies. Do NOT set `CSRF_COOKIE_HTTPONLY=True` (Inertia.js/axios needs cookie).
- **Batch queries**: Use batch queries for per-item aggregates. `get_latest_streak_counts()` uses Django `Subquery` for one-query streak fetch.

## Web Login Security Patterns

### Token & Validation
- `secrets.token_urlsafe(32)` → 43 chars. Validation: `TOKEN_MIN_LENGTH=40`, `TOKEN_MAX_LENGTH=50`.
- Username regex synced between `src/web/utils/validation.py` and `frontend/src/pages/Login.vue`. Pre-commit hook verifies sync.
- `CheckConstraint` (`user_telegram_username_format`) enforces format at DB level (bypasses `save()`).

### IP & Proxy
- X-Forwarded-For: take leftmost IP, validate with `ipaddress.ip_address()`. Only trusted when `settings.TRUST_X_FORWARDED_FOR=True`. Multi-proxy chains (>2) logged at WARNING.
- `_anonymize_ip()`: 64-bit SHA-256 prefix for GDPR-safe logging.

### Timing & Caching
- Jitter applied to ALL status paths (including confirmed/denied/used) — named constants `_JITTER_MIN`/`_JITTER_MAX`.
- `_ensure_utc()` for datetime comparisons — Django may return naive datetimes.
- `wl_pending` cache key set eagerly (before thread) by design — anti-enumeration.
- Cache TTL: `_cache_ttl_seconds(expires_at, min_ttl=1)` — always use this helper.
- `CacheManager.set` threshold check MUST be inside `_lock` to prevent race condition.

### Threading & Testing
- Mock Django cache across threads: patch `LocMemCache` class, not the proxy (thread-local connections).
- SQLite threading tests: use `RequestFactory` not `Client()`, mock `login()` and `call_async`.
- Bounded queue: `queue.Queue(maxsize=_MAX_QUEUED_LOGINS)` complements semaphore.

### DB Patterns
- `mark_as_used()`: `SELECT FOR UPDATE` inside `transaction.atomic()` for row-level locking (PostgreSQL). SQLite: no-op but sequential via file lock.
- Token collision: retry with `IntegrityError` catch, write pending cache for new token.

### Named Constants
`TOKEN_BYTES=32`, `TOKEN_GENERATION_MAX_RETRIES=3`, `_MIN_FAILED_MARKER_TTL_SECONDS=60`, `_CACHE_FAILURE_THRESHOLD=10`.

### Other
- Temporary vs permanent Telegram errors: only permanent (`InvalidToken`, `Forbidden`) mark request failed.
- SQLite system check: Warning for pool 2-10, Error for >10 (`web.E003`).
- Per-token rate limiting on `bot_login_status`: 10/m using token from URL path.
- `Login.vue` uses server's `expires_at` for client expiry (floor 60s, cap `LOGIN_EXPIRY_MS`).
- HTML escaping: store unescaped in DB, escape at output boundary in `_send_login_notification`.
- Exception chaining: `validate_iana_timezone` chains with `from e`.
- Keep `SECURITY.md` in sync with login flow changes.

### Web Test File Organization
- `tests/web/conftest.py` — shared fixtures
- `tests/web/test_middleware.py`, `test_dashboard_views.py`, `test_history_views.py`, `test_rewards_views.py`
- `tests/web/test_auth_views.py` — all auth/login flow tests
- `tests/web/test_cache_operations.py` — cache manager tests
- `tests/web/test_timing_jitter.py`, `test_cleanup_command.py`

## Reward Probability Formula (Subtractive System)

```
effective_no_reward = max(base_no_reward - habit_weight - (streak × STREAK_REDUCTION_RATE), MIN_NO_REWARD_PROBABILITY)
```

- `base_no_reward`: User's `no_reward_probability` (default 50%)
- `habit_weight`: 0-30, each point = 1% reduction (default 0)
- `STREAK_REDUCTION_RATE`: 2% per streak day (setting)
- `MIN_NO_REWARD_PROBABILITY`: 10% floor (setting)
- Reward chance = `round(100 - effective_no_reward)`

**Key files**: `src/services/reward_service.py` (formula), `src/services/habit_service.py` (caller), `src/web/views/dashboard.py` (frontend), `src/bot/keyboards.py` (weight values: `[0, 5, 10, 15, 20, 25, 30]`), `settings.py` (constants).

**Migration note**: Old `STREAK_MULTIPLIER_RATE` deprecated. Migration `0026` resets weights to 0. `HabitLog.total_weight_applied` stores effective no-reward %.

## Claimed Rewards & `times_claimed` Counter

`RewardProgress.times_claimed` (PositiveIntegerField, default=0) tracks total claims. Incremented atomically via `F("times_claimed") + 1` in `mark_reward_claimed()`.

**Key files**: `src/core/models.py`, `src/models/reward_progress.py` (Pydantic), `src/services/reward_service.py`, `src/bot/formatters.py`, `src/bot/messages.py` (`LABEL_TIMES_CLAIMED`), `src/web/views/rewards.py`, `frontend/src/pages/Rewards.vue`. Migration: `0027` (backfills `times_claimed=1` for existing claimed rows).

**Decrement pattern**: Never check `progress.times_claimed > 0` on a stale Python object — use `filter(times_claimed__gt=0).update(times_claimed=F("times_claimed") - 1, ...)` to check and decrement atomically at the DB level. If 0 rows updated, fall back to update without decrement. Applied in `src/core/admin.py` (revert action) and `src/core/repositories.py` (`decrement_pieces_earned`).

**Query**: `get_ever_claimed_by_user()` filters `times_claimed__gt=0` (not `claimed=True`) — ensures recurring rewards appear even when `claimed` reset to False. Does NOT filter by `reward__active` or `reward__is_recurring`.
