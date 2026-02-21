# Feature 0036 Review: Web Interface (Mobile-First Dashboard + Habit Tracking)

**Plan**: `docs/features/0036_PLAN.md`  
**Reviewed**: Full codebase pass (backend, frontend, tests, config).

---

## 1. Implementation vs Plan

| Area | Status | Notes |
|------|--------|--------|
| Tech stack | ✅ | Django + Inertia.js + Vue 3 + Tailwind CSS 4 + Vite; inertia-django, django-vite in use |
| Auth (Telegram Login Widget) | ✅ | Login page, callback with HMAC verification, session login, “use bot first” for unknown users |
| Django setup | ✅ | INSTALLED_APPS, MIDDLEWARE (WebAuth, InertiaFlash, Inertia), INERTIA_LAYOUT, DJANGO_VITE, TELEGRAM_BOT_USERNAME, templates dir |
| URLs | ✅ | `auth/` and `''` includes; web routes and auth routes match plan |
| Base template | ✅ | `base.html` with django_vite, dark class, viewport, inertia block |
| Frontend structure | ✅ | main.js, app.css, pages (Login, Dashboard, Streaks, History, Rewards), components (Layout, HabitCard, RewardCard, CalendarGrid, UndoToast, BottomNav, FlashMessages) |
| Dashboard (today’s habits) | ✅ | Habits + stats; complete/revert endpoints; UndoToast; uses repository + services |
| Streaks | ✅ | Per-habit current/longest streak, week completions; summary; batch query via repository |
| History | ✅ | Month calendar, completions by habit, month/habit query params, repository `get_logs_in_daterange` |
| Rewards | ✅ | Progress cards, claim endpoint, claimed list with `claimedAt` (from `progress.updated_at`) |
| Dark theme | ✅ | Tailwind @theme tokens in app.css, class strategy |
| Bottom nav / sidebar | ✅ | BottomNav (mobile), sidebar (lg), Inertia `<Link>`, active state |
| Deployment | ✅ | Dockerfile with Node frontend stage, Vite build, staticfiles |

Plan is implemented; no major gaps.

---

## 2. Backend

### Auth and security

- **CSRF**: Inertia middleware calls `get_token(request)` on every response, so the CSRF cookie is set for all pages (including login). No extra decorator needed.
- **Telegram auth**: `verify_telegram_auth()` implements HMAC-SHA256, sorted key=value, auth_date freshness (24h); `hmac.compare_digest` used.
- **Auth flow**: Callback validates hash → looks up user by `telegram_id` → checks `is_active` → `login(request, user)` → JSON `{ success, redirect }`. Inactive and unknown users get appropriate errors.

### Repository pattern

- **Streaks**: Uses `habit_log_repository.get_total_count_by_user` and `get_habit_streak_stats` (single annotated query). No direct ORM in the view.
- **History**: Uses `habit_log_repository.get_logs_in_daterange(user_id, start, end, habit_id)`. No direct ORM.
- **Dashboard**: Uses `habit_log_repository.get_todays_logs_by_user` and services. Complete uses `habit_service.get_habit_by_id(user.id, habit_id)` (single-habit lookup with ownership).

### Sync/async

- `run_sync_or_async()` used for async repository calls from sync views (dashboard, streaks, history). Service calls use existing sync/async bridging.

### User feedback

- `messages.error(request, str(e))` on complete, revert, and claim failures.
- `InertiaFlashMiddleware` shares messages as `flash`; Layout renders `<FlashMessages :messages="flash" />`.

### Middleware order

- WebAuthMiddleware after AuthenticationMiddleware; InertiaFlashMiddleware before InertiaMiddleware so flash is available on the same response. Order is correct.

### Minor

- Plan mentions `telegram_login_page`; code uses `login_page`. Name difference only; URL and behavior match.
- Auth view uses `User.objects.get(telegram_id=...)` directly; acceptable for a small auth callback. Optional: use `user_repository.get_by_telegram_id` for consistency.

---

## 3. Frontend

### Data alignment

- Backend sends camelCase props (e.g. `completedToday`, `totalPointsToday`, `currentStreak`, `piecesEarned`, `claimedAt`, `userToday`). Vue components use the same names. No snake_case/camelCase mismatch.

### History and calendar

- **Prop sync**: `selectedHabit` is a ref synced with `watch(() => props.selectedHabit, ...)`. No stale local state on Inertia navigation.
- **Timezone**: Backend sends `userToday` (server-side “today” in user TZ). CalendarGrid uses `userToday` for `isCurrentMonth` and `today` when present, else falls back to browser date. Avoids midnight TZ mismatch.
- **Performance**: `completionsByDate` is a computed map (date string → habit ids). `getDayCompletions(day)` does O(1) lookup. No per-cell scan over all habits.

### Layout and flash

- Layout includes `<FlashMessages :messages="flash" />`; flash comes from `page.props.flash` (shared by InertiaFlashMiddleware). Error toasts from complete/revert/claim will show when Layout is used.

### Other

- Login: no layout, CSRF from cookie, Telegram widget script with `data-telegram-login`, `onTelegramAuth` POSTs to callback.
- RewardCard: uses `reward.status`, `reward.piecesEarned`, `reward.piecesRequired`, `reward.isRecurring`; status badge and Claim button for ACHIEVED.
- HabitCard: Done/Undo, `completedToday`, streak display, weight badge.

---

## 4. Tests

- **Auth**: Login page 200; authenticated redirect from login; callback rejects bad JSON, missing id, invalid hash (403); unknown user 404 with message; success creates session and returns JSON; logout redirects.
- **Unauthenticated**: Dashboard, streaks, history, rewards all redirect to `/auth/login/`.
- **Dashboard**: 200 with mocked habits/logs/streaks; complete uses `get_habit_by_id`, redirects; nonexistent habit redirects; revert redirects; revert failure still redirects (message is in session).
- **Streaks**: 200 with mocked `get_total_count_by_user` and `get_habit_streak_stats`.
- **History**: 200 default and with `?month=2026-01`, invalid month fallback, `?habit=1` filter; mocks `get_logs_in_daterange`.
- **Rewards**: 200 with no data and with progress; status uses `.name`; claim redirects; claim failure redirects.
- **Telegram auth util**: Valid hash, tampered data, wrong token, missing hash, missing auth_date, expired auth_date, custom max_age.

- **Prop structure**: Dashboard, Rewards, History prop shapes verified via Inertia JSON mode (`HTTP_X_INERTIA` header); asserts component name and key fields.
- **Error flash messages**: Complete, revert, and claim failure paths assert `messages.error` is called with expected text.

Tests are well targeted; coverage is sufficient for the current design.

---

## 5. Configuration and deployment

- **Settings**: `STATICFILES_DIRS` includes frontend dist; `DJANGO_VITE` with dev server host/port from env; `INERTIA_LAYOUT = 'base.html'`; `TELEGRAM_BOT_USERNAME` from env.
- **Dockerfile**: Builder (Python/uv), frontend (Node, npm ci, build), runtime copies site-packages and frontend dist. No redundant steps.
- **pyproject.toml**: inertia-django, django-vite listed.

---

## 6. Open / Optional Items

- **P0 / P1**: None. CSRF is handled by Inertia; repository pattern and N+1 fixes are in place; user feedback and single-habit lookup are implemented.
- **Optional**: Use `user_repository.get_by_telegram_id` in the Telegram callback for full repository consistency.
- **Optional**: Confirm inertia-django 1.x and @inertiajs/vue3 2.x protocol compatibility if upgrading either side.

---

## 7. Conclusion

Feature 0036 is implemented in line with the plan. Backend uses repositories and services correctly, exposes user-facing errors via Django messages and Inertia flash, and uses batch queries where it matters. Frontend uses server-supplied `userToday` for the calendar and a precomputed map for day completions; History keeps the habit filter in sync with props. Tests cover auth, redirects, and view behavior with mocks. No blocking issues; optional improvements are minor.

**Status**: **Approved.**
