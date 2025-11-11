# Feature 0014 – Manual Test Plan

Manual regression checklist for verifying configurable daily reward frequency limits. Execute against the test database only: back up data first, and reset state between cases.

---

## Test Environment Prep
- Apply latest schema: `make sync && make migrate`
- Launch admin or shell for data setup: `uv run python manage.py shell_plus`
- Use these helpers during the session:
  ```python
  from datetime import timedelta
  from django.utils import timezone
  from src.core.models import User, Habit, Reward, HabitLog, RewardProgress
  from src.services.habit_service import habit_service
  from src.services.reward_service import reward_service

  test_user, _ = User.objects.get_or_create(
      telegram_id='999001',
      defaults={'name': 'Manual Tester', 'language': 'en', 'is_active': True},
  )
  test_habit, _ = Habit.objects.get_or_create(
      name='Test Habit',
      defaults={'weight': 50, 'active': True},
  )

  def ensure_only(reward):
      Reward.objects.exclude(id=reward.id).update(active=False)

  def reset_progress():
      HabitLog.objects.filter(user=test_user).delete()
      RewardProgress.objects.filter(user=test_user).update(pieces_earned=0, claimed=False)

  def run_completion():
      return habit_service.process_habit_completion(
          user_telegram_id=test_user.telegram_id,
          habit_name=test_habit.name,
      )

  def shift_logs(days):
      HabitLog.objects.filter(user=test_user).update(
          timestamp=timezone.now() - timedelta(days=days),
          last_completed_date=timezone.localdate() - timedelta(days=days),
      )
  ```
- After each case: call `reset_progress()` and, if needed, reactivate any rewards that were disabled with `Reward.objects.update(active=True)`.

---

## Test Cases

### TC-001 – Unlimited When `max_daily_claims` Is Blank
**Goal**: Verify absent limit allows unlimited awards in a day.  
**Setup**: `reward, _ = Reward.objects.update_or_create(name='Unlimited Blank', defaults={'weight': 100, 'pieces_required': 1, 'max_daily_claims': None, 'active': True})`; `ensure_only(reward)`; `reset_progress()`.  
**Steps**:
1. Execute `run_completion()` three times within the same day.
2. Inspect `HabitLog.objects.filter(user=test_user, reward=reward)`.
3. Load `RewardProgress.objects.get(user=test_user, reward=reward)` and `reward_service.get_todays_pieces_by_reward(test_user.id, reward.id)`.
**Expected**:
- All three runs award the reward (`got_reward=True`).
- Progress shows `pieces_earned=3`, `claimed=False`.
- Daily counter helper returns `3` pieces.
**Cleanup**: `reset_progress()`.

### TC-002 – Unlimited When `max_daily_claims` Equals `0`
**Goal**: Confirm explicit zero behaves like unlimited.  
**Setup**: Same as TC-001 but `max_daily_claims=0`.  
**Steps**:
1. `reset_progress()`.
2. Run `run_completion()` three times.
3. Re-check logs, progress, and helper count.  
**Expected**:
- Each completion awards the reward; progress reaches `pieces_earned=3`.
- Daily counter returns `3` (unlimited behaviour).  
**Cleanup**: `reset_progress()`.

### TC-003 – Limit `1` Blocks Second Award for Single-Piece Reward
**Goal**: Ensure daily limit prevents duplicate awards.  
**Setup**: `Reward.objects.update_or_create(name='Single Daily', defaults={'weight': 100, 'pieces_required': 1, 'max_daily_claims': 1, 'active': True})`; `ensure_only`; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` (expect reward).
2. Run `run_completion()` again the same day.
3. Review the two latest HabitLogs and reward progress.  
**Expected**:
- First run awards the reward and sets `pieces_earned=1`.
- Second run returns the "No reward" object (`got_reward=False`).
- Helper count is `1`.  
**Cleanup**: `reset_progress()`.

### TC-004 – Limit `1` Counts Pieces for Multi-Piece Reward
**Goal**: Validate piece-based counting when `pieces_required>1`.  
**Setup**: Reward `Multi Daily` with `pieces_required=3`, `max_daily_claims=1`; `ensure_only`; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` twice in one day.
2. Check `RewardProgress` after each run.
3. Call `shift_logs(1)` then run `run_completion()` a third time.  
**Expected**:
- First run awards piece (progress `1/3`).
- Second run yields "No reward".
- After shifting date, third run awards another piece (progress `2/3`).
- Helper count reports `1` per simulated day.  
**Cleanup**: `reset_progress()`.

### TC-005 – Limit `2` Allows Two Awards but Blocks Third
**Goal**: Confirm caps greater than one function correctly.  
**Setup**: Reward `Two Daily` with `pieces_required=4`, `max_daily_claims=2`; `ensure_only`; `reset_progress()`.  
**Steps**:
1. Execute `run_completion()` three times.
2. Inspect HabitLogs and progress state.  
**Expected**:
- First two runs award the reward (progress `2/4`).
- Third run returns "No reward".
- Helper count equals `2`.  
**Cleanup**: `reset_progress()`.

### TC-006 – Reached Limit Removes Reward from Lottery
**Goal**: Ensure capped reward disappears from selection once limit hit.  
**Setup**: Reward A `Daily Limited` (`max_daily_claims=1`) and Reward B `Fallback Unlimited` (`max_daily_claims=None`); activate both; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` once (consumes Reward A for the day).
2. In the shell, execute:
   ```python
   for _ in range(5):
       picked = reward_service.select_reward(total_weight=10, user_id=test_user.id)
       print(picked.name)
   ```
3. Optionally run `run_completion()` additional times.  
**Expected**:
- Printed selections only show “Fallback Unlimited”.
- Subsequent completions award the fallback reward; no logs reference Reward A.
**Cleanup**: Reactivate other rewards as needed; `reset_progress()`.

### TC-007 – Claim Resets Pieces to `0`
**Goal**: Verify claiming achieved reward zeroes counters and marks claimed.  
**Setup**: Reward `Claimable` (`pieces_required=1`, `max_daily_claims=1`); `ensure_only`; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` once (progress achieves requirement).
2. Call `updated = reward_service.mark_reward_claimed(test_user.id, reward.id)`.
3. Reload progress from the database.  
**Expected**:
- Progress shows `pieces_earned=0`, `claimed=True`.
- `updated.get_status()` equals `RewardStatus.CLAIMED`.  
**Cleanup**: `reset_progress()`.

### TC-008 – Claim Frees Same-Day Slot
**Goal**: Confirm claimed reward can be earned again on the same day.  
**Setup**: Continue immediately after TC-007 (progress reset to zero by claim).  
**Steps**:
1. Run `run_completion()` without shifting logs.
2. Check progress and latest HabitLog entry.  
**Expected**:
- Reward awarded again; progress shows `pieces_earned=1`, `claimed=False`.
- Helper count reflects only the active unclaimed piece; flag discrepancy if claimed pieces still counted.  
**Cleanup**: `reset_progress()`.

### TC-009 – Daily Counter Resets on New Day
**Goal**: Ensure limit clears after date boundary.  
**Setup**: Reward with `max_daily_claims=1`; `ensure_only`; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` once.
2. Shift existing logs to yesterday via `shift_logs(1)`.
3. Run `run_completion()` again.  
**Expected**:
- Second run awards the reward anew.
- Helper count returns `1`, representing today’s entry only.  
**Cleanup**: `reset_progress()`.

### TC-010 – No Reward When All Eligible Rewards Exhausted
**Goal**: Validate fallback to "No reward" when every active reward hits its limit.  
**Setup**: Single reward `Daily Finished` (`max_daily_claims=1`); `ensure_only`; `reset_progress()`.  
**Steps**:
1. Run `run_completion()` twice in same day.
2. Capture both result objects and associated HabitLogs.  
**Expected**:
- First call returns the reward (`type != RewardType.NONE`).
- Second call returns the default "No reward" entry (`type == RewardType.NONE`, `got_reward=False`).  
**Cleanup**: `reset_progress()`.

---

## Post-Test Actions
- Document any failures with supporting logs and screenshots.
- Re-enable original reward configuration once verification completes.
- Optionally mirror any failing scenarios in automated tests (`tests/test_reward_service.py`, etc.).
