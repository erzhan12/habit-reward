# Feature 0036 Review: Web Interface (Mobile-First Dashboard + Habit Tracking)

**Plan**: `docs/features/0036_PLAN.md`
**Reviewed**: Full codebase pass (backend, frontend, tests, config).
**Post-review hardening**: Three rounds of security and quality fixes applied.

---

## 1. Implementation vs Plan

| Area | Status | Notes |
|------|--------|--------|
| Tech stack | ✅ | Django + Inertia.js + Vue 3 + Tailwind CSS 4 + Vite; inertia-django, django-vite in use |
| Auth (Telegram Login Widget) | ✅ | Login page, callback with HMAC verification, session login, generic error for unknown/inactive users |
| Django setup | ✅ | INSTALLED_APPS, MIDDLEWARE (Security, CSP, WhiteNoise, WebAuth, InertiaFlash, Inertia), INERTIA_LAYOUT, DJANGO_VITE, TELEGRAM_BOT_USERNAME, templates dir |
| URLs | ✅ | `auth/` and `''` includes; web routes and auth routes match plan; custom `handler403` for rate limiting |
| Base template | ✅ | `base.html` with django_vite, dark class, viewport, CSRF meta tag, inertia block |
| Frontend structure | ✅ | main.js, app.css, pages (Login, Dashboard, Streaks, History, Rewards), components (Layout, HabitCard, RewardCard, CalendarGrid, UndoToast, BottomNav, FlashMessages) |
| Dashboard (today's habits) | ✅ | Habits + stats; complete/revert endpoints; UndoToast (onSuccess only); batch streak query |
| Streaks | ✅ | Per-habit current/longest streak, week completions; summary; batch query via repository |
| History | ✅ | Month calendar, completions by habit, month/habit query params, repository `get_logs_in_daterange`, `userToday` prop |
| Rewards | ✅ | Progress cards, claim endpoint with ownership validation, claimed list with `claimedAt` |
| Dark theme | ✅ | Tailwind @theme tokens in app.css, class strategy |
| Bottom nav / sidebar | ✅ | BottomNav (mobile), sidebar (lg), Inertia `<Link>`, active state |
| Deployment | ✅ | Dockerfile with Node frontend stage, Vite build, staticfiles |

Plan is implemented; no major gaps. Security hardening applied post-review.

---

## 2. Backend

### Auth and security

- **CSRF**: Token served via `<meta name="csrf-token">` in `base.html`. Frontend reads from meta tag (not cookie). `getCsrfToken()` throws if meta tag is missing, preventing fetch with empty token.
- **Telegram auth**: `verify_telegram_auth()` validates required fields (`id`, `auth_date`, `hash`), checks numeric types, filters to allowed fields only (strips unexpected keys), then does HMAC-SHA256 with `hmac.compare_digest`. Auth_date freshness enforced (24h).
- **Auth flow**: Rate limited (10/m per IP via `django-ratelimit`). Callback validates hash → looks up user via `user_repository.get_by_telegram_id` → checks `is_active` → `login(request, user)` → JSON `{ success, redirect }`. All failure paths return generic `403 "Authentication failed"` (no user enumeration). Custom `handler403` returns `429` JSON for rate-limited requests.
- **SRI**: Telegram widget script loaded with `integrity` (SHA-384) and `crossOrigin="anonymous"`. `script.onerror` handler shows user-facing error on load failure.
- **HTTPS**: Production (`DEBUG=False`) enforces SSL redirect, secure cookies, HSTS (1 year, subdomains, preload).
- **CSP**: `ContentSecurityPolicyMiddleware` sets `Content-Security-Policy` header in production. Allows `'self'`, `telegram.org` scripts, `oauth.telegram.org` frames, `'unsafe-inline'` styles, `https:` images. Skipped in dev for Vite HMR.
- **Failure logging**: All auth failures log client IP. Unauthorized access to habits/rewards logged with user ID and resource ID.

### Repository pattern

- **Auth**: Uses `user_repository.get_by_telegram_id` via `run_sync_or_async` (no direct ORM).
- **Dashboard**: Uses `habit_log_repository.get_todays_logs_by_user` and `get_latest_streak_counts` (batch Subquery, avoids N+1). Complete/revert use `habit_service.get_habit_by_id(user.id, habit_id)` for ownership validation.
- **Streaks**: Uses `habit_log_repository.get_total_count_by_user` and `get_habit_streak_stats` (single annotated query).
- **History**: Uses `habit_log_repository.get_logs_in_daterange(user_id, start, end, habit_id)`.
- **Rewards**: Uses `reward_repository.get_by_id` + `user_id` check for claim ownership validation.

### Sync/async

- `run_sync_or_async()` used for async repository calls from sync views. Tests mock it with `side_effect=lambda x: x` or `return_value=...` to avoid SQLite locking in test transactions.

### User feedback

- `messages.error(request, str(e))` on complete, revert, and claim failures.
- `InertiaFlashMiddleware` shares messages as `flash`; Layout renders `<FlashMessages :messages="flash" />`.
- Dashboard `completeHabit` uses `onSuccess` (not `onFinish`) for undo toast — no false "Habit completed" on errors.

### Middleware order

- SecurityMiddleware → CSP → WhiteNoise → Session → Common → CSRF → Auth → WebAuth → Messages → XFrame → InertiaFlash → Inertia. Order is correct.

### Timezone handling

- Views log a warning when `user.timezone` is `None` and falling back to UTC. Model field has `validate_iana_timezone` validator preventing invalid values at write time.

### Database indexes

- HabitLog: `(user, last_completed_date)` and `(user, habit, last_completed_date)` — migration 0017.
- RewardProgress: `(user, claimed)` — migration 0018.

---

## 3. Frontend

### Data alignment

- Backend sends camelCase props (e.g. `completedToday`, `totalPointsToday`, `currentStreak`, `piecesEarned`, `claimedAt`, `userToday`). Vue components use the same names. No snake_case/camelCase mismatch.

### History and calendar

- **Prop sync**: `selectedHabit` is a ref synced with `watch(() => props.selectedHabit, ...)`. No stale local state on Inertia navigation.
- **Timezone**: Backend sends `userToday` (server-side "today" in user TZ). CalendarGrid uses `userToday` for `isCurrentMonth` and `today` when present, else falls back to browser date.
- **Performance**: `completionsByDate` is a computed map (date string → habit ids). `getDayCompletions(day)` does O(1) lookup.

### Login security

- CSRF token from meta tag; throws on missing (prevents fetch with empty token).
- Telegram widget script with SRI integrity hash and `onerror` handler.
- Auth errors caught with distinct messages: CSRF missing → "Page configuration error", network → "Network error".

### Layout and flash

- Layout includes `<FlashMessages :messages="flash" />`; flash comes from `page.props.flash` (shared by InertiaFlashMiddleware).

---

## 4. Tests

**49 tests** across `tests/web/`:

- **Auth (7)**: Login page 200; authenticated redirect from login; callback rejects bad JSON, missing id, invalid hash (403); unknown user returns generic 403; success creates session and returns JSON; rate limit exceeded returns 429 with JSON; logout redirects.
- **Unauthenticated (4)**: Dashboard, streaks, history, rewards all redirect to `/auth/login/`.
- **Dashboard (5)**: 200 with mocked habits/logs/streaks; complete redirects; nonexistent habit redirects; revert redirects; nonexistent revert redirects.
- **Streaks (1)**: 200 with mocked `get_total_count_by_user` and `get_habit_streak_stats`.
- **History (4)**: 200 default and with `?month=2026-01`, invalid month fallback, `?habit=1` filter.
- **Rewards (4)**: 200 with no data and with progress; claim redirects; nonexistent claim redirects.
- **Telegram auth util (11)**: Valid hash, tampered data, wrong token, missing hash, missing auth_date, expired auth_date, custom max_age, non-numeric id, missing id, invalid auth_date format, unexpected fields stripped.
- **Prop structure (3)**: Dashboard, Rewards, History prop shapes verified via Inertia JSON mode.
- **Error flash messages (3)**: Complete, revert, and claim failure paths assert `messages.error` is called.
- **Auth mocks**: `run_sync_or_async` mocked in auth tests (`return_value=None` for not-found, `return_value=user` for success) to avoid SQLite locking.

Tests are well targeted; coverage is sufficient for the current design.

---

## 5. Configuration and deployment

- **Settings**: `STATICFILES_DIRS` includes frontend dist; `DJANGO_VITE` with dev server host/port from env; `INERTIA_LAYOUT = 'base.html'`; `TELEGRAM_BOT_USERNAME` from env.
- **Production security**: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (1 year) when `DEBUG=False`.
- **Test settings**: `SECURE_SSL_REDIRECT = False` override to prevent SSL redirect in tests.
- **Dockerfile**: Builder (Python/uv), frontend (Node, npm ci, build), runtime copies site-packages and frontend dist.
- **pyproject.toml**: inertia-django, django-vite, django-ratelimit listed.

---

## 6. Open / Optional Items

- **P0 / P1**: None. All critical security and performance items resolved.
- **Optional**: Add ARIA labels to interactive components (HabitCard, RewardCard, CalendarGrid, BottomNav) for accessibility.
- **Optional**: Run `EXPLAIN ANALYZE` on production PostgreSQL after deployment to verify index effectiveness (indexes added in migrations 0017, 0018).

---

## 7. Conclusion

Feature 0036 is implemented in line with the plan, with three rounds of post-review security hardening:

1. **Security**: CSRF meta tag, SRI for external scripts, rate limiting (10/m), generic auth errors (no enumeration), input validation with field filtering, HTTPS enforcement, CSP headers.
2. **Performance**: N+1 streak query eliminated (batch Subquery), database indexes on HabitLog date fields and RewardProgress claimed field.
3. **Quality**: Repository pattern enforced in all views (no direct ORM), unauthorized access logging, timezone fallback warnings, `onSuccess` for completion toast.

Backend uses repositories and services correctly, exposes user-facing errors via Django messages and Inertia flash, and uses batch queries where it matters. Frontend reads CSRF from meta tag, validates external script integrity, and handles errors distinctly. 512 tests pass (49 web-specific).

**Status**: **Approved.**
