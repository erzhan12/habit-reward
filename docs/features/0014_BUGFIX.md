# Feature 0014: Daily Frequency Limits - Bug Fix

**Date**: 2025-11-05
**Status**: ✅ FIXED (blocking issue resolved)

## Summary

Fixed the critical blocking bug identified in the code review for Feature 0014. The `get_todays_pieces_by_reward()` function was incorrectly returning `0` when a reward's status was `CLAIMED`, allowing users to bypass `max_daily_claims` restrictions by claiming between completions.

## The Bug

### Original Issue (from 0014_REVIEW.md)
**Location**: `src/services/reward_service.py:273-281`

**Problem**: When a reward is claimed, `get_todays_pieces_by_reward()` returns `0` because it only checked for `PENDING` status. This meant:
1. User earns reward with `max_daily_claims=1` → daily counter = 1
2. User claims reward → status becomes `CLAIMED`
3. Function returns `0` for claimed rewards
4. User can earn the same reward again the same day → **spec violation**

### Reproduction Steps
1. Configure a reward with `max_daily_claims=1`
2. Complete a habit to earn that reward once (daily counter now 1)
3. Call `mark_reward_claimed()`
4. Complete the habit again the same day
5. `select_reward()` calls `get_todays_pieces_by_reward()`, sees status `CLAIMED`, returns `0`
6. Reward is drawn again → User received 2 pieces on the same day ❌

## The Fix

### Changed Behavior

**Before (Buggy)**:
```python
# If reward is claimed, those pieces don't count toward daily limit
current_status = progress.get_status()
if current_status == RewardStatus.CLAIMED:
    return 0  # ❌ This allowed bypass!
```

**After (Fixed)**:
```python
# Count ALL pieces awarded today from habit logs
count = sum(
    1 for log in todays_logs
    if log.got_reward and log.reward_id == reward_id
)
return count  # ✅ Counts all pieces regardless of claim status
```

### Key Changes

1. **Removed status check**: No longer checks if reward is `CLAIMED`
2. **Counts from logs**: Relies solely on habit logs to count pieces awarded today
3. **Includes claimed pieces**: ALL pieces awarded today count toward the daily limit

### Updated Logic Flow

The daily limit now works correctly:
1. User earns reward with `max_daily_claims=1` → habit log created
2. Function counts habit logs → returns `1`
3. User claims reward → status becomes `CLAIMED`
4. Function still counts habit logs → returns `1` (not `0`)
5. User tries to complete habit again → `select_reward()` sees count=1, limit=1 → **reward excluded** ✅

## Files Modified

### 1. `src/services/reward_service.py`
**Lines**: 224-271 (`get_todays_pieces_by_reward` function)

**Changes**:
- Removed status-based filtering (lines 273-281 deleted)
- Simplified to count ALL pieces from today's habit logs
- Updated docstring to reflect new behavior
- Updated log messages

### 2. `tests/test_reward_service.py`
**Lines**: 267-517 (new test class added)

**Changes**:
- Added `TestDailyLimitEnforcement` class with 8 comprehensive tests:
  1. `test_get_todays_pieces_by_reward_no_logs` - No logs case
  2. `test_get_todays_pieces_by_reward_counts_all` - Multiple pieces counting
  3. `test_get_todays_pieces_includes_claimed` - **KEY TEST**: Verifies claimed pieces count
  4. `test_select_reward_excludes_at_daily_limit` - Daily limit exclusion
  5. `test_select_reward_allows_unlimited` - Unlimited rewards (NULL/0)
  6. `test_select_reward_excludes_completed` - Completed rewards excluded
  7. `test_claim_reset_scenario_prevents_bypass` - **BLOCKING BUG TEST**: Reproduces and verifies fix
  8. `test_select_reward_multiple_limits` - Multi-piece daily limits
- Updated existing `test_mark_reward_claimed` to expect `pieces_earned=0` reset

### 3. `RULES.md`
**Lines**: 1257-1328 (Daily Frequency Control section)

**Changes**:
- Updated "Key Behaviors" to clarify ALL pieces count (not just unclaimed)
- Added **CRITICAL BUG FIX** note dated 2025-11-05
- Updated "Important Notes" to prevent future confusion
- Added "Bug Fix History" section documenting the issue and resolution

## Test Results

All tests pass successfully:

```bash
$ uv run pytest tests/test_reward_service.py::TestDailyLimitEnforcement -v
======================== 8 passed ========================

$ uv run pytest tests/test_reward_service.py -v
======================== 18 passed ========================
```

### Critical Test: Claim-Reset Scenario

The most important test `test_claim_reset_scenario_prevents_bypass` now verifies:
- Reward with `max_daily_claims=1`
- User earns 1 piece (limit reached)
- User claims the reward
- User tries to earn again same day
- **Result**: "No reward" returned (reward excluded) ✅

This test would have **FAILED** with the old buggy code.

## Impact Assessment

### Security Impact
- **HIGH**: Closed a bypass vulnerability where users could earn unlimited pieces per day by repeatedly claiming

### Behavior Changes
- Users can no longer "recycle" rewards within the same day by claiming them
- Daily limits now enforce the intended behavior from the Feature 0014 plan
- Once a reward reaches its daily limit, it stays excluded for the rest of the day

### Backward Compatibility
- ✅ No breaking changes to API or database schema
- ✅ Existing rewards with `max_daily_claims=NULL` (unlimited) work as before
- ✅ All other reward functionality unchanged

## Verification Steps

To verify the fix works in production:

1. **Setup**: Create a reward with `max_daily_claims=1`, `pieces_required=1`
2. **Test 1**: Complete a habit → Should earn the reward once
3. **Test 2**: Claim the reward immediately
4. **Test 3**: Complete another habit the same day → Should NOT earn the same reward
5. **Test 4**: Wait until next day → Should be able to earn the reward again

Expected result: Step 3 should return a different reward or "No reward", not the same reward.

## Lessons Learned

1. **Status-based logic is fragile**: Using status to determine eligibility created a loophole
2. **Source of truth matters**: Habit logs are the immutable source of truth for daily counts
3. **Test edge cases**: The claim-reset scenario was an edge case that should have been tested initially
4. **Document intent clearly**: The original plan ambiguously stated "unclaimed pieces" which led to the bug

## Next Steps

- [x] Bug fix implemented and tested
- [x] Documentation updated in RULES.md
- [ ] Manual testing in development environment (recommended)
- [ ] Deploy to production with monitoring
- [ ] Update Feature 0014 plan document if needed

## References

- Original Plan: `docs/features/0014_PLAN.md`
- Code Review: `docs/features/0014_REVIEW.md`
- Modified Files:
  - `src/services/reward_service.py:224-271`
  - `tests/test_reward_service.py:267-517`
  - `RULES.md:1257-1328`
