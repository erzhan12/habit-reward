# Feature 0027 Code Review: Remove `RewardType.NONE`, keep “no reward” at 50%

## Scope reviewed

- `src/services/reward_service.py`
- `src/services/habit_service.py`
- `src/models/reward.py`
- `src/core/models.py`
- `src/api/v1/routers/rewards.py`
- `src/bot/keyboards.py`
- `src/bot/handlers/reward_handlers.py`
- `src/airtable/repositories.py`
- `src/airtable/reward_repository.py`
- `src/models/habit_log.py`
- `tests/test_reward_service.py`
- `tests/test_habit_service.py`
- `tests/api/test_rewards.py`

## Implementation coverage vs plan

- ✅ `RewardType.NONE` removed from shared enums (`src/models/reward.py`, `src/core/models.py`).
- ✅ Reward selection now includes an implicit “no reward” option with weight equal to the sum of other weights (`src/services/reward_service.py`).
- ✅ API validation allows only `virtual|real` (`src/api/v1/routers/rewards.py`).
- ✅ Habit completion uses `Reward | None` instead of `RewardType.NONE` (`src/services/habit_service.py`).
- ⚠️ Bot handlers still reference/accept `none` even though enums and keyboards removed it.
- ⚠️ Airtable adapters still default to `type="none"` and cast to `RewardType`, which no longer supports it.
- ⚠️ No evidence of deactivating existing `type="none"` records or hiding them from list UIs.
- ⚠️ Tests called out in the plan (API rejection for `none`, weight assertions, legacy handling) are still missing.

## Findings

### Critical

1. **Bot reward handlers reference `RewardType.NONE`, which no longer exists**
   - `src/bot/handlers/reward_handlers.py:730` still builds a mapping with `RewardType.NONE`.
   - This will raise an `AttributeError` during module import, preventing the bot from starting.

### High

2. **Airtable repositories still default `type` to `"none"` and cast to `RewardType`**
   - `src/airtable/repositories.py:192`, `src/airtable/reward_repository.py:67`.
   - With `RewardType.NONE` removed, any legacy record or missing `type` will throw a `ValueError` and break reward reads.

### Medium

3. **Edit flow still accepts `none` and can write it back into the DB**
   - `src/bot/handlers/reward_handlers.py:1502` allows `"none"` in callback validation and later writes it to the update payload.
   - Because Django `update()` bypasses model validation, this can reintroduce a banned type even though the keyboard no longer shows it.

4. **Existing `type="none"` rewards are not deactivated or hidden**
   - The requirement says legacy `none` rewards should be deactivated; current code only filters them out during selection (`src/services/reward_service.py`).
   - List endpoints and bot UIs still fetch all active rewards without excluding `type="none"`.

### Low / Maintenance

5. **Comment still references removed `none` reward type**
   - `src/models/habit_log.py:16` mentions “no reward or 'none' type reward,” which is now outdated.

6. **Test coverage gaps vs plan**
   - No API tests asserting `type="none"` is rejected in create/update (`tests/api/test_rewards.py`).
   - Reward selection tests don’t assert the “no reward” weight equals `sum(reward_weights)` or that `None` is added to the population (`tests/test_reward_service.py`).
   - No tests for legacy `type="none"` handling in Airtable adapters.

## Suggested follow-ups (prioritized)

1. Remove the `none` mapping/validation paths from `reward_handlers` and ensure callbacks only accept `virtual|real`.
2. Update Airtable adapters to handle missing/legacy types without raising (e.g., default to `real` or skip/flag legacy rewards).
3. Add a migration or cleanup path to deactivate existing `type="none"` rewards and hide them from list UIs.
4. Add tests for API validation, reward selection weights, and legacy type handling.
