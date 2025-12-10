# Feature 0022: REST API Implementation - Code Review

**Review Date:** 2025-12-10
**Reviewer:** Claude Code
**Plan Document:** `docs/features/0022_PLAN.md`

---

## Executive Summary

The REST API implementation is **substantially complete** for Phases 1, 2A, and 2B. The code quality is generally good with proper use of FastAPI patterns, Pydantic validation, and integration with existing services. However, there are **4 critical bugs** that need immediate attention and several medium/minor issues to address.

---

## Plan Compliance

### Implemented Correctly

| Component | Status | Notes |
|-----------|--------|-------|
| Project structure (`src/api/`) | ✅ | Matches plan exactly |
| JWT authentication | ✅ | Access + refresh tokens with proper expiration |
| Auth endpoints | ✅ | Login, refresh, logout |
| User endpoints | ✅ | GET /me, PATCH /me, GET /me/settings |
| Habit CRUD | ✅ | All endpoints present |
| Habit completion | ✅ | With backdate support |
| Batch completion | ✅ | With partial success handling |
| Reward CRUD | ✅ | All endpoints present |
| Reward claim | ✅ | With proper validation |
| Streak endpoints | ✅ | Current and longest streak |
| Habit logs endpoints | ✅ | List, get, revert |
| Exception handling | ✅ | Custom exceptions with standardized format |
| CORS middleware | ✅ | Configurable via env vars |
| Logging middleware | ✅ | Request ID and timing |
| ASGI entry point | ✅ | Django + FastAPI coexistence |

### Missing from Plan (Phase 3)

| Component | Status | Notes |
|-----------|--------|-------|
| Analytics endpoints | ⚠️ Not implemented | Phase 3 - `/api/v1/analytics/*` |
| Rate limiting middleware | ⚠️ Not implemented | Phase 3 |
| API tests | ⚠️ Not implemented | No `tests/api/` directory |
| `passlib[bcrypt]` dependency | ⚠️ Not added | Mentioned in plan for password auth |
| Webhooks | ⚠️ Not implemented | Phase 3, optional |

### Deviations from Plan

1. **Login endpoint** - Plan specified accepting either `telegram_id` OR `username/password`, but implementation only accepts `telegram_id`
   - Location: `src/api/v1/routers/auth.py:47-96`
   - Impact: Low (mobile app will use Telegram auth initially)

2. **Habit log revert endpoint** - Plan specified `DELETE /api/v1/habits/{habit_id}/logs/{log_id}` but implementation uses `DELETE /api/v1/habit-logs/{log_id}`
   - Location: `src/api/v1/routers/habit_logs.py:174`
   - Impact: Low (current design is more RESTful)

3. **Health check endpoint** - Added but not in plan
   - Location: `src/api/main.py:90-93`
   - Impact: Positive (good addition)

---

## Critical Bugs

### 1. Broken `active` Filter in List Habits Endpoint

**Location:** `src/api/v1/routers/habits.py:150-154`

```python
if active:
    habits = await maybe_await(habit_repository.get_all_active(current_user.id))
else:
    # For inactive habits, we need to fetch all and filter
    habits = await maybe_await(habit_repository.get_all_active(current_user.id))  # BUG: Same call!
```

**Problem:** When `active=False`, the code still calls `get_all_active()` which only returns active habits. The comment acknowledges the need to filter but doesn't actually implement different behavior.

**Fix:** Need to either:
- Add `get_all()` method to repository that returns all habits (active + inactive)
- Or add `get_all_inactive()` method

---

### 2. Habit Log Revert Uses Wrong Log

**Location:** `src/api/v1/routers/habit_logs.py:214-218`

```python
# Get habit for the revert operation
habit = await maybe_await(habit_repository.get_by_id(log.habit_id))
...
result = await maybe_await(
    habit_service.revert_habit_completion(
        user_telegram_id=current_user.telegram_id,
        habit_id=habit.id  # BUG: Passes habit_id, not log_id!
    )
)
```

**Problem:** The endpoint accepts a specific `log_id` to revert, but then calls `habit_service.revert_habit_completion()` which **reverts the MOST RECENT log** for that habit. If a user has multiple logs for the same habit, this will revert the wrong one!

**Example scenario:**
- User completes Habit A on Dec 8 (log_id=100)
- User completes Habit A on Dec 9 (log_id=101)
- User requests to delete log_id=100
- API actually deletes log_id=101 (most recent)

**Fix:** Need to either:
- Modify `habit_service.revert_habit_completion()` to accept `log_id` parameter
- Or implement direct log deletion in the endpoint (bypassing the service)

---

### 3. Inefficient Log Lookup Pattern

**Location:** `src/api/v1/routers/habit_logs.py:150-151` and `199-200`

```python
logs = await maybe_await(habit_log_repository.get_logs_by_user(current_user.id, limit=1000))
log = next((l for l in logs if l.id == log_id), None)
```

**Problem:** Fetches up to 1000 logs from database just to find one by ID. This is O(n) instead of O(1), and will cause performance issues for active users.

**Fix:** Add `get_by_id()` method to `habit_log_repository` and use it directly:
```python
log = await maybe_await(habit_log_repository.get_by_id(log_id))
if log is None or log.user_id != current_user.id:
    raise NotFoundException(...)
```

---

### 4. JWT Secret Key Regenerates on Restart

**Location:** `src/api/config.py:11`

```python
api_secret_key: str = secrets.token_urlsafe(32)
```

**Problem:** If `API_SECRET_KEY` is not set in environment variables, a new random key is generated on every application restart. This invalidates all existing JWT tokens after each deployment.

**Fix:** Either:
- Remove the default and require explicit configuration
- Or generate and persist the key to a file on first run

---

## Medium Issues

### 5. Inconsistent Async Pattern in Rewards Router

**Location:** `src/api/v1/routers/rewards.py:313-317, 391-392, 450-451`

```python
from asgiref.sync import sync_to_async
await sync_to_async(RewardModel.objects.filter(pk=reward.id).update)(...)
```

**Problem:** Uses `sync_to_async` directly instead of going through the repository pattern used everywhere else. This breaks consistency and bypasses any repository-level logic.

**Fix:** Add `update()` method to `reward_repository` and use it consistently.

---

### 6. Redundant Ownership Checks

**Location:** `src/api/v1/routers/habit_logs.py:156-157`, `205-206`

```python
logs = await maybe_await(habit_log_repository.get_logs_by_user(current_user.id, limit=1000))
log = next((l for l in logs if l.id == log_id), None)
...
if log.user_id != current_user.id:  # Always passes - we already filtered by user!
    raise ForbiddenException(...)
```

**Problem:** The ownership check is redundant because `get_logs_by_user()` already filters by user_id. The check will never fail.

**Fix:** Remove the redundant check, or better yet, use a proper `get_by_id()` query and then check ownership.

---

### 7. Cannot Clear `piece_value` on Reward Update

**Location:** `src/api/v1/routers/rewards.py:383-384`

```python
if request.piece_value is not None:
    update_dict["piece_value"] = request.piece_value
```

**Problem:** There's no way to explicitly clear `piece_value` back to `None` because the check prevents `None` values from being applied.

**Fix:** Use a sentinel value pattern or separate "clear" endpoint/field.

---

### 8. Wrong Exception Type for Weekday Validation

**Location:** `src/api/v1/routers/habits.py:244-247, 316-319`

```python
raise ConflictException(
    message=f"Invalid weekday numbers: {invalid_days}. Must be 1-7 (Mon-Sun)",
    code="INVALID_WEEKDAYS"
)
```

**Problem:** Invalid weekday values should be a `ValidationException` (422), not `ConflictException` (409). Conflict is for resource state conflicts like duplicates.

---

## Minor Issues

### 9. Code Duplication in Completion Response Building

**Location:** `src/api/v1/routers/habits.py:434-464` and `516-543`

**Problem:** The logic to build `HabitCompletionResponse` from service result is duplicated in both `complete_habit()` and `batch_complete_habits()`.

**Fix:** Extract to helper function:
```python
def _build_completion_response(result) -> HabitCompletionResponse:
    ...
```

---

### 10. Inline Imports in Functions

**Location:** `src/api/v1/routers/rewards.py:313, 391, 450`

**Problem:** `from asgiref.sync import sync_to_async` is imported inside functions instead of at the top of the file.

---

### 11. Large File Size

**Location:** `src/api/v1/routers/habits.py` (555 lines)

**Problem:** File is getting large. Consider extracting batch operations to separate module.

---

### 12. Undocumented Weekday Convention

**Location:** Various files

**Problem:** The API uses ISO weekday numbers (1=Monday, 7=Sunday) but this isn't documented in the OpenAPI schema descriptions. Clients might assume 0-6 (Sunday-Saturday) convention.

---

## Data Alignment Issues

### 13. Reward Type String vs Enum

**Location:** `src/api/v1/routers/rewards.py:69`

```python
type: str = Field(default="virtual", pattern="^(virtual|real|none)$")
```

The API accepts/returns type as lowercase string, which matches Django model's `RewardType` enum values. However, some internal code accesses `.value` suggesting potential inconsistency.

**Recommendation:** Add explicit documentation that type values are always lowercase strings.

---

### 14. Progress Percent Calculation Inconsistency

**Location:** `src/api/v1/routers/habits.py:450-451`, `src/api/v1/routers/rewards.py:117`

Two different methods used to get `progress_percent`:
- `progress.progress_percent` (attribute)
- `progress.get_progress_percent()` (method)

The code defensively tries both, but this suggests the model interface isn't consistent.

---

## Positive Observations

1. **Clean architecture** - Good separation between routers, dependencies, middleware
2. **Proper Pydantic usage** - Request/response models with validation
3. **Comprehensive error handling** - Custom exceptions with standardized format
4. **Good logging** - Request IDs, timing, operation logging
5. **Service layer reuse** - Properly delegates to existing services
6. **Auth abstraction** - Clean dependency injection for authentication
7. **OpenAPI documentation** - Will be auto-generated from Pydantic models

---

## Recommended Priority Order for Fixes

### P0 - Critical (Fix Before Production)
1. Bug #2: Habit log revert uses wrong log
2. Bug #4: JWT secret regenerates on restart

### P1 - High (Fix Soon)
3. Bug #1: Broken active filter in list habits
4. Bug #3: Inefficient log lookup pattern
5. Issue #5: Inconsistent async pattern

### P2 - Medium (Tech Debt)
6. Issue #6-8: Various validation and consistency issues
7. Missing Phase 3 features (analytics, rate limiting)
8. API tests

### P3 - Low (Nice to Have)
9. Issues #9-12: Code cleanup and documentation

---

## Testing Recommendations

Before deployment, add tests for:

1. **Auth flow** - Login, token refresh, logout, expired token handling
2. **Habit completion** - Today, backdate, duplicate prevention
3. **Reward claim** - Claim achieved reward, reject unclaimed, reject already claimed
4. **Ownership checks** - Cannot access other users' resources
5. **Edge cases** - Empty lists, invalid IDs, max pagination limits

---

## Summary

The API implementation is **80% complete** and follows good practices. The critical bugs around log revert and JWT secret key should be fixed before any production use. The remaining issues are mostly code quality improvements that can be addressed incrementally.
