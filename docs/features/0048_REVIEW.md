# Feature 0048 Review

## External review trail (2026-11-21)

Scope: `git diff 2297806` on `feature/0048-streak-freeze` (PR A commit d22029c + PR B, 77 files). Criteria: `commands/code_review.md`.

| Round | Engines | Raised | Accepted (fixed) | Rejected / accepted gap |
|---|---|---|---|---|
| 1 | codex × 5 aspects, cursor | 9 | 6 | 3 |
| 2 | codex × 4 aspects + whole, cursor | 4 | 2 | 2 |
| 3 | codex bugs + whole, Claude Opus subagent | 14 (all P3) | 0 | 14 P3 left as gaps |

### Fixed

- Burn job notice: one message per user per run; habits with different covered days carry their own date (`src/bot/freeze_scheduler.py`). Plan §3 step 5.
- Burn sweep: a habit deleted after the candidate read, or any other per-habit error, is skipped instead of aborting the run and dropping notices for earlier spends (`FreezeService.burn_due_freezes`).
- Backdate reconcile: a freeze returned and then re-spent on the trailing gap is no longer reported as `freeze_returned` (`HabitService._reconcile_sync`).
- Stale "No Reward Probability" button (also a conversation entry point) now validates that the user exists and is active (`settings_handler.no_reward_prob_deprecated_callback`).
- `RewardProgressRepository.decrement_pieces_earned` delegates to its sync twin (no duplicated claimed/times_claimed logic).
- Type annotations on `update_habit`, `select_reward_sync`, `return_spend_sync`, `move_spend_sync`.
- RULES.md streak service / cache sections updated to `trailing_streak_state` and `streaks:v3`.

Each code fix has a regression test that fails on the pre-fix code.

### Rejected or accepted as gaps

- "Stale caller `habit.freeze_count` cached for 5 min" (codex, P1): general invalidate-on-commit cache race; the window is between the request's habit load and its reads. Self-heals on the next write. Accepted gap.
- Backdate / settings-edit trailing settle spends are not reported or notified (cursor, P2): same as undo; documented in the plan as-built notes.
- API responses lack `freeze_returned` / `freeze_revoked` (P3). Later fixed during claude-review: `freeze_burned` and `freeze_count` added, and batch complete reports `SERVICE_BUSY`.
- `/streaks` hides streak-0 habits, so a reserve freeze on a broken habit shows no ❄️ (pre-existing filter, P3).
- Round 3 P3s (Opus): no direct `roll()` boundary / `should_roll` test file; missing `max_daily_claims=1` + freeze-roll regression; duplicated dates in the multi-date notice; `/streaks` mixes uncached streaks with cached freeze state; subset calls overwrite the per-user cache key; burn job ignores `user.is_active`; redundant `cache.adelete` after revert; repeated `on_commit(cache.delete)` instead of one helper; `STREAK_SETTINGS` placement; admin calls private `_revert_log_sync`; stale `process_habit_completion` docstring.
- Codex P3: concurrency tests use `asyncio.gather` on one executor instead of separate connections.

### Final status

`uv run pytest tests/ -m "not local_only"`: 1144 passed. `ruff check src/ tests/` (project-pinned 0.14.1): only the pre-existing E402 in settings. Note: the worktree venv resolved ruff 0.17.6, whose defaults report ~350 unrelated hits; use the pinned version.

## External review trail, pass 2 (2026-11-21, after claude-review fixes)

Scope: same diff, now including ce97c10, 8226490 and c4e3e99. Engines: codex × 5 aspects and a Claude Opus subagent (cursor dropped at the user's request).

Round 1: zero P1/P2 from both engines. Tests 1145 passed; ruff (pinned 0.14.1) only the pre-existing E402. No code changes.

P3s left as gaps:
- `update_reward_progress_sync` duplicates the async `update_reward_progress` rules. The async version has no production caller left; its tests mock its async repositories, so it is not a drop-in delegate.
- `_update_settings_sync` compares `exempt_weekdays` as lists, so a reordered list triggers a full settle and recompute. The result is correct but the work is unneeded.
- `calculate_streak`, `calculate_streak_for_date` and `recalculate_streaks_after_backdate` have only test callers.
- The reconcile engine (`_reconcile_sync`, `_reconcile_gap_sync`) could move out of `habit_service.py` (971 lines).
- Cached `StreakState` does not record its `today`, so it can be up to 5 minutes stale across local midnight.
- Untyped `habit` / bare `list` in the reconcile helpers; `S = sync_to_async` alias in two test files.
