# Tasks

<!-- Track current work as checkable items. Validate plan before implementing. -->

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
  - Admin `HabitAdmin` settings edits still write directly; routed through `update_habit` in slice 7
- [ ] 5. Burn job + scheduler + `FREEZE_SPENT_NOTICE` (§3)
- [ ] 6. Read paths: `get_streak_states`, prediction, cache v3, dashboard/streaks/API fields
  - Until then read paths ignore SPENT events (dashboard can show 0 where a completion gives prev + 1)
- [ ] 7. UI: bot strings, web flash/❄️/hints, admin grant/remove, read-only `HabitLogAdmin`
  - Bot busy text is English inside `ERROR_GENERAL`; add a translated `ERROR_BUSY`
- [ ] 8. Docs + manual check on a DB copy

## Follow-ups

### Adopt CHANGELOG.md convention

Raised by claude-review on PR #46 (P3 DOCS): user-facing changes should land in a `CHANGELOG.md`. No changelog file currently exists in the repo, so adopting one is a project-wide convention decision rather than per-PR scope. Decide whether to introduce `CHANGELOG.md` (Keep-a-Changelog format is the obvious default) and, if so, backfill recent user-facing entries.

### Dashboard.vue integration test for habit-completion flow

Raised by claude-review on PR #58 (P2 TESTING). Add a component-level test for `Dashboard.vue` `completeHabit` that asserts (1) `oldRect` is captured before the POST, (2) `nextTick` is awaited, (3) `triggerCompletionCelebration` is called with the correct `{ oldRect, gotReward }` payload, (4) the celebration popup is only opened when `gotReward` is true. Needs Inertia `router.post` mocking plus stubs for `useTheme`, `useThemeAnimation`, `useRealtimeSync`, and child components — substantial enough to warrant its own focused PR.

### HabitCard.vue swipe-mode ref placement regression test

Raised by claude-review on PR #58 (P2 TESTING). Mount `HabitCard.vue` with `interactions.habitComplete: 'swipe-reveal'` and assert the exposed `cardRef` is a real DOM element with a callable `getBoundingClientRect`, not a Vue component proxy. Pins the fix from PR #58 (the swipe-mode `ref` was previously bound to the `<HabitDoneSwipe>` component, breaking `animate()` in swipe mode). Requires stubbing `useTheme` + child interaction components.

### Narrow broad `except Exception` to `telegram.error.TelegramError` in habit_management_handler

Raised by claude-review on PR #64 (P3 QUALITY). The deletion try/except at `src/bot/handlers/habit_management_handler.py:1494` uses a broad `except Exception`. The reviewer notes the change "should be applied consistently across the file, not just in this one location" — i.e. a file-wide refactor of every defensive `except Exception` block that wraps a `python-telegram-bot` API call (importing `from telegram import error` and catching `telegram.error.TelegramError`). Scope is much larger than this PR; deserves its own focused PR that audits all such blocks, decides whether `TelegramError` is genuinely the only expected class (vs. e.g. asyncio cancellation), and updates them uniformly.
