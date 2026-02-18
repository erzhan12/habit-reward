# Feature 0034 Code Review: My Rewards Filtering & Ordering

## Verdict
Status: Approved.

Functional behavior is correct for the My Rewards flow, and prior cross-module regression risk is addressed by keeping repository behavior generic and applying filtering in the service layer.

## Findings
No feature-specific findings remain.

## Plan Implementation Checklist

| Requirement | Status | Notes |
| --- | --- | --- |
| Hide claimed rewards in My Rewards | ✅ Done | Implemented in `src/services/reward_service.py:550` |
| Reorder unclaimed rewards (pending by %, then achieved, then never-won) | ✅ Done | Implemented in `src/services/reward_service.py:553` |
| Remove status + "Ready to claim" lines in bot formatter | ✅ Done | Implemented in `src/bot/formatters.py:75` |
| Add TODO entry for claimed rewards menu button | ✅ Done | Added in `TODO.md:70` |
| Add unit tests for filtering/ordering scenarios | ✅ Done | Added in `tests/test_reward_filtering.py` |

## Data Alignment Review
No snake_case/camelCase or nested payload-shape issues were found in this feature path.

## Over-Engineering / File Size
No over-engineering introduced in the changed code paths.

## Validation Performed
- `uv run pytest tests/test_reward_filtering.py tests/test_reward_service.py tests/api/test_rewards.py tests/services/test_reward_service_async.py -q` (56 passed)
- `uv run ruff check src/services/reward_service.py src/bot/formatters.py tests/test_reward_filtering.py`
  - No new lint findings in feature tests.
  - Pre-existing non-feature lint issues remain in `src/services/reward_service.py:57`, `src/services/reward_service.py:269`, `src/services/reward_service.py:299` (`F821` for `'date'` annotation).
