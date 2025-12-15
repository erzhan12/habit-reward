# Feature 0024: Remove Habit Category from Telegram Interface — Code Review

**Review Date:** 2025-12-12  
**Reviewer:** ChatGPT  
**Plan Document:** `docs/features/0024_PLAN.md`

## Findings (ordered by severity)
1. **Category edit handlers now raise on missing context**  
   - `src/bot/handlers/habit_management_handler.py:896-944` still defines `habit_edit_category_skip/selected`, but `habit_edit_selected` no longer stores `old_habit_category`. If a stale `skip_category` or `category_*` callback ever reaches these helpers (e.g., from an older inline message), they will KeyError on `context.user_data['old_habit_category']` and abort the conversation. Either remove these handlers or guard against the absent field.
2. **Missing regression coverage for the shortened flows and bracket removal**  
   - Only `tests/test_habit_edit_skip.py` was adjusted. There are no new assertions in `tests/test_bot_handlers.py` (or elsewhere) to verify that `/add_habit` now jumps weight → grace days, that confirmations no longer mention category, that keyboards omit category brackets, or that Telegram creations default `category=None`. The plan called for unit coverage of the new UX and preserving API behavior; without it, the bot path is unverified.
3. **Docs still describe the old Telegram category step**  
   - The plan asked to update rules/test docs to state that Telegram no longer asks for category. No documentation changes landed, so internal guidance (e.g., `RULES.md` and test guides) still imply the category prompt exists, which can mislead future contributors.

## Plan compliance
- ✅ Telegram add/edit flows skip category and set creations to `category=None`; confirmation strings and keyboards no longer show category brackets (`src/bot/handlers/habit_management_handler.py`, `src/bot/keyboards.py`, `src/bot/messages.py`).
- ⚠️ Tests and documentation updates outlined in the plan are missing.

## Testing
- Not run (review only).
