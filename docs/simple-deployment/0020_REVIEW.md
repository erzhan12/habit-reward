# Feature 0020: Backdate Habit Completion – Code Review

## Findings
- Critical: `process_habit_completion()` will raise `UnboundLocalError` on the first `if target_date is None` because `_impl` reassigns `target_date` without `nonlocal`, making the variable local and undefined before assignment (src/services/habit_service.py:167-235). This blocks all habit completions.
- Major: The “Select Date” button emits `backdate_habit_{id}` but no handler is registered for that pattern, so the date-picker path is dead and users can’t reach the backdate conversation from `/habit_done` (src/bot/handlers/habit_done_handler.py:438-447; src/bot/handlers/backdate_handler.py entrypoints/states).
- Major: Backdating doesn’t refresh streaks on existing future logs. Adding a past completion leaves later `streak_count` values untouched (e.g., today logged as 1, backdate yesterday leaves today at 1 instead of 2), so streak history stays inconsistent with the new completion (src/services/habit_service.py:221-277; no post-insert recompute).
- Major: Tests are mostly placeholders. `tests/test_backdate_habit.py` asserts boundaries and mocks but doesn’t execute the happy-path service logic or cover the handler flows; repo tests are marked “placeholder”, leaving the feature effectively untested (tests/test_backdate_habit.py).
- Minor: Success copy still says “Habit logged” instead of “Habit backdated”, and help text doesn’t mention `/backdate`, diverging from the plan/manual expectations (src/bot/messages.py:187-205).

## Additional Notes
- Streak calculation now queries `get_last_log_before_date`, fixing the prior “pass” gap, but without reapplying streaks to later logs the user-visible streak chain remains stale after backdating.
