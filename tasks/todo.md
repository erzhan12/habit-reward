# Tasks

<!-- Track current work as checkable items. Validate plan before implementing. -->

## Follow-ups

### Adopt CHANGELOG.md convention

Raised by claude-review on PR #46 (P3 DOCS): user-facing changes should land in a `CHANGELOG.md`. No changelog file currently exists in the repo, so adopting one is a project-wide convention decision rather than per-PR scope. Decide whether to introduce `CHANGELOG.md` (Keep-a-Changelog format is the obvious default) and, if so, backfill recent user-facing entries.

### Dashboard.vue integration test for habit-completion flow

Raised by claude-review on PR #58 (P2 TESTING). Add a component-level test for `Dashboard.vue` `completeHabit` that asserts (1) `oldRect` is captured before the POST, (2) `nextTick` is awaited, (3) `triggerCompletionCelebration` is called with the correct `{ oldRect, gotReward }` payload, (4) the celebration popup is only opened when `gotReward` is true. Needs Inertia `router.post` mocking plus stubs for `useTheme`, `useThemeAnimation`, `useRealtimeSync`, and child components — substantial enough to warrant its own focused PR.

### HabitCard.vue swipe-mode ref placement regression test

Raised by claude-review on PR #58 (P2 TESTING). Mount `HabitCard.vue` with `interactions.habitComplete: 'swipe-reveal'` and assert the exposed `cardRef` is a real DOM element with a callable `getBoundingClientRect`, not a Vue component proxy. Pins the fix from PR #58 (the swipe-mode `ref` was previously bound to the `<HabitDoneSwipe>` component, breaking `animate()` in swipe mode). Requires stubbing `useTheme` + child interaction components.

### Narrow broad `except Exception` to `telegram.error.TelegramError` in habit_management_handler

Raised by claude-review on PR #64 (P3 QUALITY). The deletion try/except at `src/bot/handlers/habit_management_handler.py:1494` uses a broad `except Exception`. The reviewer notes the change "should be applied consistently across the file, not just in this one location" — i.e. a file-wide refactor of every defensive `except Exception` block that wraps a `python-telegram-bot` API call (importing `from telegram import error` and catching `telegram.error.TelegramError`). Scope is much larger than this PR; deserves its own focused PR that audits all such blocks, decides whether `TelegramError` is genuinely the only expected class (vs. e.g. asyncio cancellation), and updates them uniformly.
