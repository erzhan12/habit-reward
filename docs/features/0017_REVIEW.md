# Feature 0017 Review

## Findings
1. **High – `calculate_streak` drops streaks whenever the habit lookup fails instead of falling back to the previous logic.**
   - Code reference: `src/services/streak_service.py:33-47`.
   - The code comments promise a fallback when `habit_repo.get_by_id` returns `None`, but the function immediately returns `1`. If the habit row was soft-deleted, temporarily unavailable, or the lookup simply hiccups, a user who actually logged yesterday/today will still be treated as if the streak broke.
   - Fix: Re-use the existing "today/yesterday" branches when `habit` is missing (i.e., keep the stored streak when last_date==today and increment when it was yesterday) instead of hard-resetting to `1`.

2. **Medium – The add-habit confirmation is wired to the remove-flow keyboard, so the Back button never works and there is no Cancel option.**
   - Code references: confirmation keyboard creation in `src/bot/handlers/habit_management_handler.py:372-389` and conversation state configuration in `src/bot/handlers/habit_management_handler.py:1518-1552`.
   - `build_remove_confirmation_keyboard()` renders `callback_data="remove_back_to_list"`, but the add-flow state only listens for `confirm_(yes|no)` and `cancel_habit_flow`. Tapping "Back" produces an unhandled callback, and there is no way to trigger the cancel handler at this step because the keyboard does not include `cancel_habit_flow`. The dedicated `build_habit_confirmation_keyboard()` already exposes the correct callbacks and should be used here.

3. **Medium – The exempt-day UX deviates from the plan and bypasses the centralized message catalog.**
   - Plan reference: `docs/features/0017_PLAN.md:49-57` specifies a keyboard with `None`, `Weekends (Sat/Sun)`, and `Custom` presets.
   - Implementation reference: `src/bot/keyboards.py:734-777` only renders `None`/`Weekends` buttons with hard-coded English labels, so the `exempt_days_custom` callback is unreachable and localization is impossible. The add/edit prompts and validation errors for custom input are also hard-coded in English (`src/bot/handlers/habit_management_handler.py:298-305`, `454-458`, `916-920`, `958-963`), even though `HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT` already exists in `Messages`.
   - Fix: Add the missing "Custom" button (hooked to the existing callback), source all prompt/validation strings from `src/bot/messages.py`, and surface localized labels for the preset buttons.

4. **Medium – New habit strings were never translated, so RU/KK users fall back to English and lose the new information in confirmations.**
   - English definitions live at `src/bot/messages.py:148-162`, but the RU and KK dictionaries around `src/bot/messages.py:350-364` and `548-562` still only cover the old keys (no entries for the new grace/exempt prompts and the confirmation text still lacks `{grace_days}`/`{exempt_days}`).
   - Result: Russian and Kazakh users see English prompts for grace/exempt days and the edit confirmation omits the new values entirely.
   - Fix: add localized strings for `HELP_ADD_HABIT_GRACE_DAYS_PROMPT`, `HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT`, `HELP_EDIT_HABIT_GRACE_DAYS_PROMPT`, `HELP_EDIT_HABIT_EXEMPT_DAYS_PROMPT`, and extend the translated confirmation templates with the new placeholders.

5. **Medium – `exempt_weekdays` uses ISO weekday numbers (1–7) even though the feature plan specifies 0-based days.**
   - Plan reference: `docs/features/0017_PLAN.md:13-41` calls out 0=Mon … 6=Sun (the example even labels Sat=5, Sun=6).
   - Implementation references: `src/core/models.py:98-107`, `src/models/habit.py:13-15`, `src/services/streak_service.py:55-61`, and the validation messages in `src/bot/handlers/habit_management_handler.py:454-458` all hard-code 1=Mon … 7=Sun.
   - Anyone integrating against the plan will submit 0-based values and watch them be misinterpreted (e.g., `6` meaning Saturday in the plan breaks because the code reads it as Sunday). Align on the contracted numbering or update the plan/example and all user-facing text to avoid data drift.
