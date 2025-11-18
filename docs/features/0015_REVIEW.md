# Feature 0015: Comprehensive Bot Audit Log System – Code Review

**Date**: 2025-11-19
**Reviewer**: Codex (GPT-5)
**Status**: ❌ CHANGES REQUIRED – core logging flows are incomplete

## Summary
The foundational data model, migration, and service scaffolding look good, but the integration layer falls short of the plan. Habit completions are logged, yet most user-facing commands and habit-management callbacks never record audit events, so the new trail still misses the majority of high-level interactions it was meant to capture. Several implementation bugs also prevent snapshots from containing the state needed to diagnose corruption.

## Blocking Findings

### ❌ Habit logs are never linked to audit entries
- **Location**: `src/services/habit_service.py:196-231`
- `habit_log` is instantiated and passed into `habit_log_repo.create()`, but the returned saved object (with its primary key) is discarded. The object handed to `audit_log_service.log_habit_completion()` therefore has `id=None`, so `BotAuditLog.habit_log_id` is always null. This breaks the plan’s requirement to trace audit events back to concrete habit log rows. Capture the saved record (or its ID) before logging.

### ❌ Command logging limited to /start and /help
- **Location**: `src/bot/handlers/reward_handlers.py:105-341`, `src/bot/handlers/streak_handler.py:17-63`, and other command modules
- The plan explicitly called for “start_command(), help_command(), and other command handlers” to record `COMMAND` events. Only `/start` and `/help` call `audit_log_service.log_command()`. Commands such as `/list_rewards`, `/my_rewards`, `/claim_reward`, `/add_reward`, `/streaks`, settings, etc., still perform zero audit logging, so most user activity never hits the audit trail.

### ❌ DB-changing button callbacks are never logged
- **Location**: `src/services/audit_log_service.py:223-256` defines `log_button_click`, but no handler calls it (grep shows no occurrences outside the service itself). Habit management confirmations such as `habit_confirmed`, `habit_edit_confirmed`, and `habit_remove_confirmed` (`src/bot/handlers/habit_management_handler.py:279-976`) perform the actual create/update/delete operations yet never write audit rows, so the DB mutations driven by inline buttons still leave no trace despite the updated requirement to log such events.

### ❌ Error handlers still bypass the audit trail
- **Location**: `src/bot/handlers/reward_handlers.py:547-731`
- The plan asked to “Wrap try-except blocks to call `audit_log_service.log_error()` on exceptions.” Only the ValueError branch inside `claim_reward_callback` does so. All other validation failures (invalid weight/pieces/piece value, reward creation errors, unexpected exceptions) merely log to stdout and return, so failures in those flows never show up in BotAuditLog.

### ❌ Reward-claim snapshots do not capture the pre-claim state
- **Location**: `src/bot/handlers/reward_handlers.py:300-319`
- `claim_snapshot["pieces_earned_before"]` is set to `updated_progress.get_pieces_required()`, i.e., the theoretical requirement, not the actual `pieces_earned` value before resetting. Because `mark_reward_claimed()` zeroes out the counter before returning, the real “before” value is now lost – precisely the scenario this audit log was meant to help debug. Capture the `RewardProgress` state (or at least `pieces_earned`) before calling `mark_reward_claimed()` and store both before/after values.

### ❌ Crash risk when reward metadata disappears
- **Location**: `src/bot/handlers/reward_handlers.py:300-319`, `src/services/audit_log_service.py:110-145`
- `reward_repository.get_by_id()` can legitimately return `None` (e.g., reward deleted after the keyboard was sent), yet the code blindly passes that value to `log_reward_claim()`, which immediately dereferences `reward.id`. The audit log path will raise `AttributeError`, the claim fails, and no error is surfaced to the user. Pass `reward_id` directly (or guard the lookup) so auditing can still proceed even if the FK target is missing.

## Additional Issues (Non-blocking but should be addressed)

### ⚠️ Timezone-naive retention logic
- **Location**: `src/services/audit_log_service.py:273-348`
- `get_user_timeline()` and `cleanup_old_logs()` both build cutoffs with `datetime.now()`. With `USE_TZ=True`, Django expects aware datetimes; filtering with naive values results in `RuntimeWarning` and potentially incorrect retention windows. Use `django.utils.timezone.now()` (or `timezone.now()` alias) instead.

### ⚠️ Admin detail view is inaccessible
- **Location**: `src/core/admin.py:168-204`
- `BotAuditLogAdmin.has_change_permission()` unconditionally returns `False`, which prevents staff from opening the detail page at all (Django uses the change permission for READ access). Marking the form fields as `readonly_fields` is sufficient; let `has_change_permission()` fall back to the default (or return `False` only for POST) so operators can inspect snapshots in admin.

## Next Steps
Please address the blocking items above (especially the missing instrumentation) and add tests or manual validation notes showing that command events, button clicks, errors, and reward claims now produce audit rows with the expected snapshots. Once those are in place, we can re-review the feature.
