# Tasks

<!-- Track current work as checkable items. Validate plan before implementing. -->

## In progress: 0052 review cosmetics

Branch `feature/0052-review-cosmetics` (worktree `.claude/worktrees/0052-review-cosmetics`).

- [x] `MobileTopBar.vue` replaces the mobile bar duplicated in both `Layout.vue` branches
- [x] Shared `MONTH_NAMES` (`utils/months.js`) for CalendarGrid and History
- [x] FlashMessages: one `watch(..., { immediate: true })` instead of `onMounted` + `watch`
- [x] CalendarGrid spec: drop the comment on `dayButton`; todo header below names the right PR

## Done: 0051 review nits from PR #111 (shipped as PR #112)

Branch `feature/0051-review-nits` (worktree `.claude/worktrees/0051-review-nits`).

- [x] CalendarGrid: `aria-controls` only on the selected day (the panel is not in the DOM otherwise)
- [x] FlashMessages spec: hide timer is cleared on unmount
- [x] CalendarGrid spec: `dayButton` helper throws a readable error when the day is missing

## Done: 0050 review P2 follow-ups (PR #110)

Branch `feature/0050-review-p2` (worktree `.claude/worktrees/0050-review-p2`).

- [x] FlashMessages: stable per-message ids as keys; one hide timer, so a newer batch is not cleared by the older batch's timer (`FlashMessages.spec.js`)
- [x] CalendarGrid day buttons: `aria-expanded` + `aria-controls` for the History day detail instead of `aria-pressed` (`CalendarGrid.spec.js`)

## Done: Feature 0049 UI upgrade (reward chance visibility + design fixes)

Plan: `docs/features/0049_PLAN.md`. Branch `feature/0049-ui-upgrade` (worktree `.claude/worktrees/0049-ui-upgrade`).

- [x] 0 Worktree setup, `npm ci`, `uv sync`; vitest baseline 3 failing (Layout.spec)
- [x] 1 Login without app nav, logout button contract, mobile logout bar
- [x] 2 `--color-border` / `--color-track` tokens, muted contrast, contrast + drift tests
- [x] 3 Palette tokens: RewardCard, FlashMessages, BottomNav
- [x] 4 Palette tokens: Layout, UndoToast, animations.css
- [x] 5 Habit card layout (outcome line, meta line, no whole-card opacity)
- [x] 6 Backend `chance` curve + `nextStreak`
- [x] 7 `oddsStyle` theme config (additive)
- [x] 8 `OddsChip` component + spec
- [x] 9 Card uses `OddsChip`; retire `showOdds`
- [x] 10 Pass `chance` Dashboard → HabitCard → content
- [x] 11 Rewards: ACHIEVED first (web only), Claim size
- [x] 12 Streaks: "No streak right now" section
- [x] 13a Day-completion helper + spec
- [x] 13b History day detail, calendar buttons, counts
- [x] 14 Analytics: drop "Available days"
- [x] 15 Reduced motion + tap sizes
- [x] 16 RULES.md + project.md
- [ ] Owner review in the browser; commit / PR only on explicit instruction

## In progress: Feature 0048 PR A (formula + launch reset)

Plan: `docs/features/0048_PLAN.md`. Branch `feature/0048-streak-chance-formula`. Ships together with PR B (freeze); never merge alone.

- [x] `calculate_reward_chance(s)` + settings constants; remove old formula and its settings (deprecation warning)
- [x] `Habit.streak_epoch` + migration 0031 (per-user local date; no `HabitLog` writes)
- [x] Streak engine honours the epoch (predecessor rule, effective streak 1 on epoch day, recalc never below epoch)
- [x] Dashboard: chance from stored snapshot if completed today, else `calculate_reward_chance(next_streak)`; drop `Nw ·` badge
- [x] Bot: hide "No Reward Probability" setting, stale button answers with deprecation notice; weight prompt relabelled
- [x] Docs: README, RULES.md, `.env*.example`, TEST_CASES
- [ ] Deploy env files (`docker-compose.yml`, `.env.production`, `deploy-caddy.yml`) still set the removed vars: optional `chore`, harmless (only a DeprecationWarning)

## In progress: Feature 0048 PR B (streak freeze)

Branch `feature/0048-streak-freeze`, stacked on PR A. Released together with PR A.

- [x] 1. Schema + repos: 0032 (`freeze_count`, `HabitFreezeEvent`), 0033 (one log per habit/day), CAS + event repository
- [x] 2. Gap engine: `evaluate_gap`, `find_due_spend`, usable rule
- [x] 3. Transaction functions + completion (§4): lock, retry/`ServiceBusyError`, settle-first, catch-up, freeze roll. Backdate recalculation runs inside the transaction but is still streak-only (no returns/relocation) until slice 4
- [x] 4. Backdate/undo/settings reconciliation (§5, §6), shared revert helper (`_revert_log_sync`, also used by the admin action), `HabitService.update_habit` for API/bot edits, UTC-default callers fixed. Retry backoff now jittered (lockstep retries livelocked)
  - Gap with no counted predecessor: its SPENT events are left untouched (no streak to protect; avoids returning a freeze won by an undone first completion)
  - Admin `HabitAdmin` has no streak-settings fields, so nothing there needs routing through `update_habit` (checked in slice 7)
- [x] 5. Burn job + scheduler + `FREEZE_SPENT_NOTICE` (§3): `FreezeService.burn_due_freezes`, `src/bot/freeze_scheduler.py`, registered in webhook init and polling `main`. Notice date format `DD.MM` (language-neutral)
- [x] 6. Read paths: `trailing_streak_state` + `get_streak_states` (prediction, cache v3), single-habit streak calls on the gap engine, dashboard (`freezeCount`/`freezeUsedFor`/`freezeAtRisk`), web streaks + `/v1/streaks` (`freezeCount`/`freeze_count`, batched), API completion fields (`reward_chance`, `freeze_won/used/covered_date`), `HabitResponse.freeze_count` (raw)
  - Local-only audit tests still patched the old async `select_reward`; now patch `select_reward_sync`
- [x] 7. UI: bot strings, web flash/❄️/hints, admin grant/remove, read-only `HabitLogAdmin`
  - `ERROR_BUSY` via `format_service_error` in every bot `except (ValueError, ServiceBusyError)` block and the habit create/update/remove `except Exception` blocks
  - Admin write denials are scoped to the model's own admin views (`_on_own_view`): a blanket `has_delete_permission=False` would block Habit/User delete cascades
  - `HabitAdmin` exposes no streak settings, so there is nothing to route through `update_habit` there
  - kk freeze strings still need a native-speaker review
- [x] 8. Docs + manual check on a DB copy
  - [x] Docs: README (intro, Streak Freeze), RULES (Streak Freeze section, cache v3), API field descriptions
  - [x] Manual check on a DB copy (local dev DB, 0 duplicate logs; 0031-0033 applied): prediction before = after the job, catch-up spend, job notice once (silent for burned), web toast, undo keeps the spend, backdate returns the freeze, admin grant, web/bot ❄️ + legend, HabitLog admin read-only
  - Production: re-run the duplicate pre-flight before deploying 0033
  - Found, pre-existing: `format_streaks_message` hardcodes English "days" (RU/KK show "5 days")

## Follow-ups

### Adopt CHANGELOG.md convention

Raised by claude-review on PR #46 (P3 DOCS): user-facing changes should land in a `CHANGELOG.md`. No changelog file currently exists in the repo, so adopting one is a project-wide convention decision rather than per-PR scope. Decide whether to introduce `CHANGELOG.md` (Keep-a-Changelog format is the obvious default) and, if so, backfill recent user-facing entries.

### Dashboard.vue integration test for habit-completion flow

Raised by claude-review on PR #58 (P2 TESTING). Add a component-level test for `Dashboard.vue` `completeHabit` that asserts (1) `oldRect` is captured before the POST, (2) `nextTick` is awaited, (3) `triggerCompletionCelebration` is called with the correct `{ oldRect, gotReward }` payload, (4) the celebration popup is only opened when `gotReward` is true. Needs Inertia `router.post` mocking plus stubs for `useTheme`, `useThemeAnimation`, `useRealtimeSync`, and child components — substantial enough to warrant its own focused PR.

### HabitCard.vue swipe-mode ref placement regression test

Raised by claude-review on PR #58 (P2 TESTING). Mount `HabitCard.vue` with `interactions.habitComplete: 'swipe-reveal'` and assert the exposed `cardRef` is a real DOM element with a callable `getBoundingClientRect`, not a Vue component proxy. Pins the fix from PR #58 (the swipe-mode `ref` was previously bound to the `<HabitDoneSwipe>` component, breaking `animate()` in swipe mode). Requires stubbing `useTheme` + child interaction components.

### Narrow broad `except Exception` to `telegram.error.TelegramError` in habit_management_handler

Raised by claude-review on PR #64 (P3 QUALITY). The deletion try/except at `src/bot/handlers/habit_management_handler.py:1494` uses a broad `except Exception`. The reviewer notes the change "should be applied consistently across the file, not just in this one location" — i.e. a file-wide refactor of every defensive `except Exception` block that wraps a `python-telegram-bot` API call (importing `from telegram import error` and catching `telegram.error.TelegramError`). Scope is much larger than this PR; deserves its own focused PR that audits all such blocks, decides whether `TelegramError` is genuinely the only expected class (vs. e.g. asyncio cancellation), and updates them uniformly.

### Translate "days" in `/streaks`

Pre-existing, found during the 0048 manual check and raised again by claude-review on PR #108 (P3 DOCS). `format_streaks_message` hardcodes English "days", so RU/KK users see "5 days". Add a `STREAK_DAYS_UNIT` key (with plural forms for ru/kk) to `messages.py` and use it in the formatter.

### Kazakh freeze strings review + kk formatter tests

0048 PR B (claude-review P2 TESTING on PR #108). The kk freeze strings (`FREEZE_*`, `INFO_STREAK_FREEZE_LEGEND`, `ERROR_BUSY`) are unreviewed. After a native-speaker pass, add `language="kk"` cases for `format_habit_completion_message` and `format_streaks_message`.

### Streaks API performance

claude-review on PR #108 (P1 PERFORMANCE, pre-existing on main). `GET /v1/streaks` calls `get_last_completed_date` once per habit (N+1); `GET /v1/streaks/{habit_id}` loads up to 1000 logs to take `max(streak_count)`. Return the last completed date from the `get_streak_states` batch and use `get_longest_streak_in_range` (one `MAX()`).

### Cap batch-complete size and validate exempt weekdays

claude-review on PR #108 (pre-existing on main). `BatchCompletionRequest.completions` is unbounded, and each item is a write transaction; add a `max_length` (API contract change, document it). The habit create/update endpoints accept duplicate `exempt_weekdays` values. `max_backdate_days = 7` is duplicated between `habit_service` and the bot backdate handler; move it to settings.

### Freeze code cleanups (0048 review P2/P3)

From the external review and claude-review on PR #108:
- Make `HabitService._revert_log_sync` public; the admin calls it directly.
- Optional `user_id` filter on `HabitLogRepository.get_log_for_habit_on_date_sync`, matching the async twin.
- Comment why `habit.freeze_count` stays stale in memory after `spend_sync` loses the uniqueness race.
- `settle_due_spend_sync` could return the last log so `_burn_one_sync` does not re-query it.
- One helper for the repeated `transaction.on_commit(partial(cache.delete, ...))`.
- Burn job ignores `user.is_active`; decide whether inactive users should still spend and get notices.
- Multi-date burn notice repeats the dates (in `{date}` and per habit).
- `/streaks` mixes uncached `get_all_streaks_for_user` with cached `get_streak_states`; subset calls overwrite the per-user cache key.
- Tests: direct `roll()` boundary / `should_roll` tests, the `max_daily_claims=1` + freeze-roll regression, job-vs-backdate contention on separate connections.
- PostgreSQL lock-marker tests in `is_lock_error`, if the app ever moves off SQLite.
