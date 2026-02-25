# Feature 0036 — Manual Test Plan
# Web Interface (Mobile-First Dashboard + Habit Tracking)

**Plan**: `docs/features/0036_PLAN.md`
**Review**: `docs/features/0036_REVIEW.md`
**Date**: 2026-02-24

---

## Prerequisites & Environment Setup

### 1. Add missing `.env` variable

The Telegram Login Widget requires `TELEGRAM_BOT_USERNAME`. Add it to `.env`:

```
TELEGRAM_BOT_USERNAME=your_bot_username_without_@
```

Also confirm `NGROK_URL` will be refreshed each session (the stored URL expires when ngrok restarts).

---

### 2. Register your ngrok domain with BotFather

Run `/setdomain` in Telegram → @BotFather:

```
/setdomain
Select your bot
Enter: https://<your-ngrok-url>
```

> This must match the `NGROK_URL` you will start in Step 3. If ngrok gives you a new URL each session, you'll need to re-run `/setdomain` each time (or use a static ngrok domain).

---

### 3. Start the environment — 3 terminals required

Open **three separate terminal windows**, each in the project root (`/Users/erzhan/DATA/PROJ/habit_reward`).

#### Terminal A — ngrok tunnel

```bash
make ngrok
# or: ngrok http 8000
```

Wait until you see a line like:
```
Forwarding  https://xxxx.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS URL.

#### Terminal B — Update .env and set webhook

Run the webhook setup script (it reads ngrok URL automatically and calls `set_webhook.py`):

```bash
./scripts/start_webhook_dev.sh
```

Follow the prompts. At the end you should see `🎉 Webhook setup complete!`.

Verify the webhook is registered:

```bash
uv run python scripts/set_webhook.py --info
```

Expected output includes the current ngrok webhook URL.

#### Terminal C — Django + FastAPI ASGI server

```bash
make api
```

Expected: uvicorn starts and logs something like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Smoke-test it:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```
Expected: `302` (redirect to `/auth/login/` — auth middleware is working).

#### Terminal D — Vite dev server (frontend HMR)

```bash
cd frontend && npm run dev
```

Expected: Vite starts on `http://localhost:5173`.

---

## Test Suite

---

### T-01 — Server Startup Sanity Checks

| # | Action | Expected Result |
|---|--------|----------------|
| 1.1 | `curl http://localhost:8000/health` | `200 OK` with JSON status |
| 1.2 | `curl -I http://localhost:8000/` | `302` redirect to `/auth/login/` |
| 1.3 | Open `http://localhost:8000/` in browser (not ngrok) | Redirected to `/auth/login/` |
| 1.4 | Open `https://<ngrok-url>/` in browser | Redirected to `/auth/login/` (ngrok proxying works) |
| 1.5 | `curl http://localhost:5173/` | `200` (Vite dev server running) |

---

### T-02 — Login Page

| # | Action | Expected Result |
|---|--------|----------------|
| 2.1 | Navigate to `https://<ngrok-url>/auth/login/` | Login page renders, no 500 error |
| 2.2 | Page visual check | Dark background (`gray-950`), page title "Habit Reward", Telegram Login Widget button visible |
| 2.3 | Page on mobile viewport (DevTools → toggle device) | Single column layout, button centered, readable font size |
| 2.4 | Page source / Network tab | `base.html` served; Vite HMR script tag present; CSRF meta tag present |
| 2.5 | Console (browser DevTools) | No JavaScript errors on load |
| 2.6 | Telegram widget script | Script loaded with `integrity` attribute (SRI), no console errors |
| 2.7 | Navigate directly to `https://<ngrok-url>/auth/login/` while **already logged in** | Redirect to `/` (dashboard) |

---

### T-03 — Telegram Authentication Flow

> **Requirement**: Your Telegram account must have previously sent a message to the bot (so your `telegram_id` exists in the database).

| # | Action | Expected Result |
|---|--------|----------------|
| 3.1 | On login page, tap **"Log in with Telegram"** button | Telegram OAuth popup appears |
| 3.2 | Approve in Telegram | Popup closes; page redirects to `/` (Dashboard) |
| 3.3 | After login, check browser cookies (DevTools → Application → Cookies) | `sessionid` cookie present |
| 3.4 | Refresh the Dashboard page | Still logged in (session persists) |
| 3.5 | **Error path**: Use a different Telegram account that has never used the bot | Login returns error message "Authentication failed" (generic — no user enumeration) |
| 3.6 | **Rate limit**: Submit the auth callback 11 times rapidly (use browser or curl loop) | 11th request returns `429` JSON response |
| 3.7 | POST to `/auth/telegram/callback/` with missing `id` field | Returns `403` |
| 3.8 | POST to `/auth/telegram/callback/` with tampered `hash` value | Returns `403` |

---

### T-04 — Logout

| # | Action | Expected Result |
|---|--------|----------------|
| 4.1 | While logged in, POST to `/auth/logout/` (or trigger logout from UI if a button exists) | Session cleared; redirected to `/auth/login/` |
| 4.2 | After logout, try navigating to `/` | Redirected to `/auth/login/` |

---

### T-05 — Auth-Required Middleware (unauthenticated access)

| # | Action | Expected Result |
|---|--------|----------------|
| 5.1 | Open incognito window, navigate to `https://<ngrok-url>/` | Redirected to `/auth/login/` |
| 5.2 | Navigate to `/streaks` without session | Redirected to `/auth/login/` |
| 5.3 | Navigate to `/history` without session | Redirected to `/auth/login/` |
| 5.4 | Navigate to `/rewards` without session | Redirected to `/auth/login/` |

---

### T-06 — Dashboard (Today's Habits)

| # | Action | Expected Result |
|---|--------|----------------|
| 6.1 | Navigate to `/` while logged in | Dashboard renders; list of today's habits visible |
| 6.2 | Visual check | Dark card surfaces (`gray-900`), habit names, weight badges, streak counts |
| 6.3 | Stats section | "Completed today: X / Y" count visible; total points today displayed |
| 6.4 | Habit with **completed today = false** | Shows "Done" button (emerald accent), unchecked state |
| 6.5 | Habit with **completed today = true** | Shows checked state (checkmark); "Done" button absent or disabled |
| 6.6 | Tap **"Done"** on a pending habit | Instant visual feedback (check animation); **UndoToast** appears at bottom |
| 6.7 | UndoToast countdown | Toast counts down 5 seconds then disappears |
| 6.8 | Tap **"Undo"** on the UndoToast within 5 seconds | Habit reverts to uncompleted state; toast disappears |
| 6.9 | After completing a habit, reload the page | Habit shows as completed (state persisted to DB) |
| 6.10 | Complete all habits for today | Stats show "X / X completed" |
| 6.11 | **Error path**: Complete already-completed habit (via direct POST) | Flash error message shown; no duplicate log created |
| 6.12 | Mobile viewport | Cards full-width; "Done" button easily tappable (44px+ touch target) |

---

### T-07 — Bottom Navigation

| # | Action | Expected Result |
|---|--------|----------------|
| 7.1 | Check bottom nav visible on mobile viewport | 4 tabs: Today, Streaks, History, Rewards |
| 7.2 | Active tab on Dashboard | "Today" tab highlighted with `accent` (emerald) color |
| 7.3 | Tap "Streaks" tab | Navigate to `/streaks`; "Streaks" tab becomes active |
| 7.4 | Tap "History" tab | Navigate to `/history` |
| 7.5 | Tap "Rewards" tab | Navigate to `/rewards` |
| 7.6 | Tap "Today" tab | Navigate back to `/` |
| 7.7 | Navigation is SPA | No full page reload between tabs (Inertia Link behavior — watch Network tab) |
| 7.8 | Desktop viewport (1024px+) | Bottom nav hidden; sidebar visible on left |

---

### T-08 — Streaks Page

| # | Action | Expected Result |
|---|--------|----------------|
| 8.1 | Navigate to `/streaks` | Page renders without errors |
| 8.2 | Summary card | "Total completions", "Active habits", "Best streak" stats shown |
| 8.3 | Habit list | Sorted by current streak descending |
| 8.4 | Per-habit row | Habit name, fire emoji + current streak count, weekly mini progress bar |
| 8.5 | Longest streak | Shown per habit (different from current streak if streak was broken) |
| 8.6 | Complete a habit on Dashboard, return to Streaks | Streak count updated (or will update at next page load) |

---

### T-09 — History Page (Calendar View)

| # | Action | Expected Result |
|---|--------|----------------|
| 9.1 | Navigate to `/history` | Current month calendar renders |
| 9.2 | Current month | Month header shows correct month (e.g. "February 2026") |
| 9.3 | Today's date | Highlighted in calendar |
| 9.4 | Days with completions | Colored dots visible for each completed habit |
| 9.5 | Tap a day that has completions | Shows which habits were completed that day |
| 9.6 | Previous month button | Navigates to January 2026; URL updates to `?month=2026-01` |
| 9.7 | Next month button | Navigates forward; future dates show no completions (greyed out) |
| 9.8 | Habit filter dropdown | Select a single habit; calendar shows only that habit's dots |
| 9.9 | URL `?month=2026-01` directly | January calendar loaded correctly |
| 9.10 | URL `?month=invalid` | Falls back to current month (no 500 error) |
| 9.11 | URL `?habit=1` | Calendar filtered to habit ID 1 |
| 9.12 | Mobile viewport | Calendar grid readable; day cells not overlapping |

---

### T-10 — Rewards Page

| # | Action | Expected Result |
|---|--------|----------------|
| 10.1 | Navigate to `/rewards` | Rewards page renders |
| 10.2 | Reward cards grid | Cards in grid layout (2-col on tablet, 3-col on desktop) |
| 10.3 | PENDING reward | Progress bar shows `pieces_earned / pieces_required`; no "Claim" button |
| 10.4 | ACHIEVED reward | Progress bar full; green "Claim" button visible |
| 10.5 | Tap **"Claim"** on achieved reward | Page reloads; reward moves to "Claimed" section |
| 10.6 | Claimed section | Claimed rewards listed with claim date |
| 10.7 | **Error path**: Claim already-claimed reward (via direct POST) | Flash error message shown |
| 10.8 | Recurring reward (after claim) | Reappears in active list with progress reset |
| 10.9 | Non-recurring reward (after claim) | Disappears from active list; appears in claimed section |
| 10.10 | Mobile viewport | Full-width cards, progress bars visible |

---

### T-11 — Flash Messages

| # | Action | Expected Result |
|---|--------|----------------|
| 11.1 | Trigger an error (e.g. revert a habit that isn't completed) | Red flash message banner appears at top of page |
| 11.2 | Flash message auto-dismiss | Message disappears after a few seconds (or has a close button) |
| 11.3 | Successful action | No spurious success flash messages on normal operations |

---

### T-12 — Telegram Bot Webhook (via ngrok)

| # | Action | Expected Result |
|---|--------|----------------|
| 12.1 | Send `/start` to the bot in Telegram | Bot responds (webhook received by server; check Terminal C logs) |
| 12.2 | Check ngrok web UI at `http://127.0.0.1:4040` | Webhook POST requests visible in request log |
| 12.3 | Complete a habit via the **Telegram bot** | Habit logged; verify it now shows as completed on the web Dashboard |

---

### T-13 — CSP & Security Headers (Dev environment note)

> In `DEBUG=True` mode, CSP middleware is skipped (per review). The following apply to production but are good to verify mentally:

| # | Check | Note |
|---|-------|------|
| 13.1 | CSRF token in `<meta name="csrf-token">` | Inspect page source; meta tag must be present |
| 13.2 | Telegram widget script has `integrity` attribute | Inspect `<script>` tag on Login page |
| 13.3 | All auth failure paths return identical error message | "Authentication failed" regardless of failure reason |

---

### T-14 — Mobile Responsiveness Spot-Check

Open DevTools → Device Toolbar and test each page at **375px width (iPhone SE)** and **390px width (iPhone 14)**:

| # | Page | Check |
|---|------|-------|
| 14.1 | Login | Telegram button not clipped |
| 14.2 | Dashboard | Habit cards full width; Done button tap target ≥ 44px |
| 14.3 | Streaks | Text readable; progress bars visible |
| 14.4 | History | Calendar grid fits screen without horizontal scroll |
| 14.5 | Rewards | Cards stacked; progress bars visible |
| 14.6 | All pages | Bottom nav fixed at bottom; does not overlap content |

---

## Quick Start Checklist

Before beginning any tests, verify:

- [ ] `TELEGRAM_BOT_USERNAME` set in `.env`
- [ ] `/setdomain` run in BotFather with current ngrok URL
- [ ] Terminal A: `make ngrok` running (ngrok tunnel active)
- [ ] Terminal B: `./scripts/start_webhook_dev.sh` completed (webhook registered)
- [ ] Terminal C: `make api` running (Django ASGI server on port 8000)
- [ ] Terminal D: `cd frontend && npm run dev` running (Vite on port 5173)
- [ ] `curl http://localhost:8000/` returns `302` → confirms server + auth middleware up

---

## Known Environment Notes

- **ngrok URL changes** every session unless you have a paid static domain. Re-run `start_webhook_dev.sh` and `/setdomain` on each restart.
- **DEBUG=True** disables CSP middleware and SSL redirect — expected in local dev.
- **Vite HMR**: Frontend changes hot-reload automatically; Django view changes require uvicorn restart.
- **Session cookie**: `sessionid` is not `Secure` in dev (HTTP localhost). Expected.
