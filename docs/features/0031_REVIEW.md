# Feature 0031 Code Review: Auto-Delete API Key Message After 5 Minutes

## Summary

**Status: MINOR CHANGE REQUIRED**

All core logic, guard clause, webhook lifecycle, message translations, and unit tests are in place. One remaining issue: `uv.lock` was not regenerated after adding the `[job-queue]` extra, so APScheduler is not resolved and the feature will silently no-op in production.

## Implementation Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Capture API key reply `Message` and schedule deletion | ✅ Done | `settings_handler.py:356-370` |
| Scheduled callback deletes the message with try/except | ✅ Done | `settings_handler.py:31-38` |
| Guard when `job_queue` is `None` | ✅ Done | `settings_handler.py:362-370` (`getattr` + `if` guard) |
| Inform user the message auto-deletes in 5 minutes | ✅ Done | `messages.py` — EN (:312), RU (:624), KZ (:935) |
| `python-telegram-bot[job-queue]` in pyproject.toml | ✅ Done | `pyproject.toml:21` |
| Start JobQueue in webhook mode | ✅ Done | `webhook_handler.py:113-117` |
| Unit tests for scheduling + deletion | ✅ Done | `tests/bot/test_api_key_auto_delete.py` (4 tests) |

## Previous Review Issues — Resolution

| Issue | Status |
|-------|--------|
| JobQueue dependency not configured | ✅ Fixed — `pyproject.toml:21` has `[job-queue]` extra; handler guards with `getattr` |
| JobQueue not running in webhook mode | ✅ Fixed — `webhook_handler.py:113-114` starts job queue on init |
| Unit tests missing | ✅ Fixed — 4 tests added covering scheduling, raw key in message, callback deletion, failure handling |
| Import ordering (`html` after project modules) | ✅ Fixed — `html` now at line 3 with stdlib imports |

## Remaining Issue

1. **`uv.lock` not regenerated — APScheduler not resolved**
   - `pyproject.toml:21` correctly specifies `python-telegram-bot[job-queue]>=20.6`, but `uv.lock:432` resolves `python-telegram-bot` without the extra, and `uv.lock:1172-1174` lists only `httpx` as a dependency (no `apscheduler`).
   - At runtime `context.job_queue` will be `None`, the guard clause will log a warning, and the message will **not** be auto-deleted.
   - **Fix:** run `uv lock` to regenerate the lock file with the `[job-queue]` extra resolved.

## Data Alignment Issues

None found.

## Over-Engineering Assessment

No over-engineering detected.

## Code Style Consistency

No issues. Import ordering is correct (stdlib → third-party → project).

## Conclusion

The implementation is functionally complete and well-guarded. Run `uv lock` to resolve APScheduler and the feature is ready.
