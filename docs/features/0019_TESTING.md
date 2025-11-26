# Manual Testing Guide: Custom Admin Action for Habit Log Reversion

## Overview
This guide provides step-by-step instructions for manually testing the new custom admin action that properly reverts habit logs and their associated reward progress.

## Prerequisites

1. **Django Admin Access**: You need superuser credentials
2. **Running Application**: Django app must be running
3. **Test User**: At least one active test user with habits and rewards configured

---

## Test Setup

### 1. Create Test User (if needed)

```bash
python manage.py createsuperuser
# or use existing admin credentials
```

### 2. Verify Test Data

Navigate to Django Admin at `http://localhost:8000/admin/` (or your configured URL)

**Check you have:**
- At least 1 active User (in `/admin/core/user/`)
- At least 2 active Habits for that user (in `/admin/core/habit/`)
- At least 2 active Rewards for that user (in `/admin/core/reward/`)

If not, create them via the Telegram bot or Django Admin.

---

## Test Case 1: Single Log Reversion with Reward

### Purpose
Verify that reverting a single habit log properly:
- Deletes the log
- Decrements reward progress
- Shows success message

### Steps

1. **Create a Habit Log with Reward**

   Via Telegram bot:
   ```
   /done
   [Select a habit]
   ```

   OR via Django Admin:
   - Go to `/admin/core/habitlog/add/`
   - Fill in:
     - User: [Select test user]
     - Habit: [Select test habit]
     - Reward: [Select test reward]
     - Got reward: ✓ (checked)
     - Streak count: 1
     - Habit weight: 10
     - Total weight applied: 10
     - Last completed date: [Today's date]
   - Click "Save"

2. **Note the Current Reward Progress**

   - Go to `/admin/core/rewardprogress/`
   - Find the RewardProgress entry for the user and reward
   - **Record**: Current `pieces_earned` value
   - Example: If it shows `pieces_earned: 3`, write this down

3. **Revert the Habit Log**

   - Go to `/admin/core/habitlog/`
   - Find the log you just created (check timestamp/user)
   - Check the checkbox next to the log entry
   - From the "Action" dropdown at the top, select:
     **"Revert selected habit logs (and reward progress)"**
   - Click **"Go"**

4. **Verify Success**

   **Expected Result:**
   - Green success message at top: `"Successfully reverted 1 habit log(s)."`
   - The log entry disappears from the list

5. **Verify Reward Progress was Decremented**

   - Go to `/admin/core/rewardprogress/`
   - Find the same RewardProgress entry
   - **Verify**: `pieces_earned` is now 1 less than before
   - Example: If it was 3 before, it should now be 2

6. **Verify Audit Log Entry**

   - Go to `/admin/core/botauditlog/`
   - Filter by Event type: "Reward Revert"
   - **Verify**: New entry exists with:
     - User: [Your test user]
     - Reward: [The reverted reward]
     - Timestamp: [Just now]

### ✅ Pass Criteria
- Success message appears
- Log is deleted
- Reward progress decremented by 1
- Audit log entry created

---

## Test Case 2: Batch Log Reversion (Multiple Logs)

### Purpose
Verify that reverting multiple habit logs works correctly

### Steps

1. **Create Multiple Habit Logs**

   Via Telegram bot, complete 3 different habits:
   ```
   /done → [Habit 1]
   /done → [Habit 2]
   /done → [Habit 3]
   ```

   OR create 3 logs manually in Django Admin

2. **Note All Reward Progress Values**

   - Go to `/admin/core/rewardprogress/`
   - **Record** the `pieces_earned` for each reward you received
   - Example:
     - Reward A: 5 pieces
     - Reward B: 2 pieces
     - Reward C: 8 pieces

3. **Select Multiple Logs for Reversion**

   - Go to `/admin/core/habitlog/`
   - Check the checkboxes for **all 3 logs** you created
   - From "Action" dropdown, select:
     **"Revert selected habit logs (and reward progress)"**
   - Click **"Go"**

4. **Verify Batch Success**

   **Expected Result:**
   - Success message: `"Successfully reverted 3 habit log(s)."`
   - All 3 log entries disappear from the list

5. **Verify All Reward Progress Decremented**

   - Go to `/admin/core/rewardprogress/`
   - **Verify** each reward's `pieces_earned`:
     - Reward A: 4 pieces (was 5)
     - Reward B: 1 piece (was 2)
     - Reward C: 7 pieces (was 8)

### ✅ Pass Criteria
- Success message shows correct count (3)
- All selected logs deleted
- All associated reward progress decremented
- Multiple audit log entries created

---

## Test Case 3: Error Handling - Already Reverted Log

### Purpose
Verify graceful error handling when trying to revert a log that doesn't exist

### Steps

1. **Create and Revert a Log**

   - Complete a habit via bot: `/done`
   - In admin, revert that log (see Test Case 1)
   - **Verify** it's successfully deleted

2. **Try to Revert Again (Simulated)**

   Since the log is already deleted, we'll test with a different approach:
   - Create a new log
   - Note its ID (e.g., log #45)
   - Revert it successfully
   - Try to access `/admin/core/habitlog/` and verify it's gone

3. **Alternative: Test with Missing Habit**

   - Create a HabitLog in admin
   - **Important**: Leave "Habit" field blank (if possible) or:
     - Create a log
     - Manually set `habit_id = NULL` in database:
       ```sql
       UPDATE habits_log SET habit_id = NULL WHERE id = <log_id>;
       ```
   - Try to revert this corrupted log

4. **Verify Error Message**

   **Expected Result:**
   - Red error message: `"Failed to revert all 1 log(s)."`
   - Error details show: `"Log #XX: Missing habit"` or similar

### ✅ Pass Criteria
- Error message appears (not success)
- Error is descriptive and helpful
- Application doesn't crash
- Log entry remains (for corrupted data) or is gone (for already-deleted)

---

## Test Case 4: Partial Batch Failure

### Purpose
Verify that when some logs fail to revert, the action continues and reports correctly

### Steps

1. **Create Mixed Scenario**

   - Create 3 valid habit logs (via `/done` command)
   - Create 1 corrupted log (set habit_id or user_id to NULL in database)

   ```sql
   -- Example: Make log #50 invalid
   UPDATE habits_log SET user_id = NULL WHERE id = 50;
   ```

2. **Select All 4 Logs**

   - Go to `/admin/core/habitlog/`
   - Check all 4 logs
   - Run "Revert selected habit logs" action

3. **Verify Partial Success Message**

   **Expected Result:**
   - Yellow/orange warning message:
     `"Reverted 3 log(s). Failed: 1."`
   - Error details shown:
     `"Log #50: Missing user"` (or similar)

4. **Verify Partial Results**

   - 3 valid logs are deleted
   - 1 corrupted log remains (or is deleted, depending on error type)
   - Reward progress decremented for the 3 successful reversions
   - No decrement for the failed one

### ✅ Pass Criteria
- Warning message shows correct success/failure counts
- Successfully reverted logs are processed
- Failed logs don't break the entire batch
- Clear error messages for failures

---

## Test Case 5: No Reward Log Reversion

### Purpose
Verify reverting logs that didn't award a reward

### Steps

1. **Create Log Without Reward**

   Option A - Via bot (if no reward selected):
   ```
   /done → [Select habit]
   → No reward awarded (lottery didn't give reward)
   ```

   Option B - Via admin:
   - Create HabitLog with `got_reward = False` and `reward = NULL`

2. **Revert the Log**

   - Go to `/admin/core/habitlog/`
   - Select the log with `got_reward = False`
   - Run revert action

3. **Verify Success (No Reward Change)**

   **Expected Result:**
   - Success message: `"Successfully reverted 1 habit log(s)."`
   - Log is deleted
   - **No reward progress change** (since no reward was awarded)
   - Audit log may or may not show reward revert event

### ✅ Pass Criteria
- Log deleted successfully
- No reward progress affected
- No errors

---

## Test Case 6: Revert Completed Reward (Edge Case)

### Purpose
Verify behavior when reverting a log that completed a multi-piece reward

### Steps

1. **Setup Multi-Piece Reward**

   - Go to `/admin/core/reward/`
   - Create or edit a reward:
     - Name: "Test Multi-Piece"
     - Type: Virtual
     - Pieces required: 5
     - Weight: 50 (high chance of selection)
     - Active: ✓

2. **Earn Pieces to Complete the Reward**

   - Via bot, complete habits until you have 5 pieces for this reward
   - Go to `/admin/core/rewardprogress/`
   - **Verify**: `pieces_earned: 5`, Status: "Achieved"

3. **Revert the Last Completion**

   - Go to `/admin/core/habitlog/`
   - Find the most recent log that awarded a piece for this reward
   - Revert it

4. **Verify Reward Status Reverts**

   **Expected Result:**
   - Log deleted
   - Reward progress now shows: `pieces_earned: 4`
   - Status changes from "Achieved" → "Pending"

### ✅ Pass Criteria
- pieces_earned decremented
- Status correctly updated to Pending
- Reward becomes available for lottery again

---

## Test Case 7: Verify Logging Output

### Purpose
Verify that detailed logs are written for debugging

### Steps

1. **Tail Application Logs**

   In a terminal:
   ```bash
   tail -f logs/app.log
   # or wherever your Django logs are configured
   ```

2. **Perform a Reversion**

   - In admin, revert 2 habit logs

3. **Verify Log Output**

   **Expected log entries:**
   ```
   [INFO] 🔄 Admin reverting log #123 for user 999999999, habit 45
   [INFO] ✅ Successfully reverted log #123 for habit 'Morning Exercise'
   [INFO] 🔄 Admin reverting log #124 for user 999999999, habit 46
   [INFO] ✅ Successfully reverted log #124 for habit 'Read Book'
   ```

4. **Verify Error Logs (if applicable)**

   If you create an error scenario:
   ```
   [WARNING] ⚠️ Log #125: Missing user
   [ERROR] ❌ Log #126: No habit completion found to revert
   ```

### ✅ Pass Criteria
- Logs contain emoji indicators (🔄, ✅, ⚠️, ❌)
- Each revert attempt logged
- User telegram_id and habit_id included
- Error details logged for failures

---

## Test Case 8: Large Batch Performance

### Purpose
Verify performance with many logs selected

### Steps

1. **Create Many Logs**

   - Complete 20-30 habits via the bot
   - OR use Django shell:
     ```python
     python manage.py shell

     from src.core.models import HabitLog, User, Habit, Reward
     from datetime import datetime, date

     user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
     habit = Habit.objects.filter(user=user, active=True).first()
     reward = Reward.objects.filter(user=user, active=True).first()

     for i in range(20):
         HabitLog.objects.create(
             user=user,
             habit=habit,
             reward=reward,
             got_reward=True,
             streak_count=1,
             habit_weight=10,
             total_weight_applied=10,
             last_completed_date=date.today()
         )
     ```

2. **Select All Logs**

   - Go to `/admin/core/habitlog/`
   - Check "Select all X habit logs" at top
   - Run revert action

3. **Measure Response Time**

   - Note how long it takes
   - **Expected**: Should complete within 10-30 seconds for 20-30 logs

4. **Verify All Processed**

   **Expected Result:**
   - Success message: `"Successfully reverted 20 habit log(s)."`
   - All logs deleted
   - Reward progress correctly updated

### ✅ Pass Criteria
- Completes without timeout
- All logs processed
- Performance acceptable (< 1-2 seconds per log)

---

## Expected Failure Scenarios

These scenarios should produce specific error messages:

### Scenario A: Missing User
**Setup**: Create log with `user_id = NULL`
**Expected**: `"Log #XX: Missing user"`
**Result**: Error message, log skipped

### Scenario B: Missing Habit
**Setup**: Create log with `habit_id = NULL`
**Expected**: `"Log #XX: Missing habit"`
**Result**: Error message, log skipped

### Scenario C: No Completion Found
**Setup**: Revert same log twice
**Expected**: `"Log #XX: No habit completion found to revert"`
**Result**: Error message, operation fails gracefully

### Scenario D: Inactive User
**Setup**: Set user `is_active = False`, try to revert their log
**Expected**: `"Log #XX: User is inactive"`
**Result**: Error message, revert prevented

---

## Checklist Summary

After completing all test cases, verify:

- [ ] Single log reversion works
- [ ] Batch reversion works (multiple logs)
- [ ] Reward progress decremented correctly
- [ ] Error messages clear and helpful
- [ ] Partial failures handled gracefully
- [ ] Audit logs created for reversions
- [ ] Application logs show detailed info with emojis
- [ ] No reward logs handled correctly
- [ ] Multi-piece reward status updates correctly
- [ ] Large batches perform acceptably
- [ ] No crashes or 500 errors during any test

---

## Troubleshooting

### Issue: Action doesn't appear in dropdown
**Solution**: Restart Django server after code changes

### Issue: "This action is not available"
**Solution**: Check that you're logged in as superuser or staff with proper permissions

### Issue: Timeout on large batches
**Solution**: Consider reducing batch size or increasing timeout settings in Django admin

### Issue: Reward progress not decrementing
**Solution**:
1. Check that the log had `got_reward=True` and a valid `reward_id`
2. Verify the reward progress entry exists
3. Check application logs for errors

### Issue: Audit log not created
**Solution**: Verify `audit_log_service` is properly configured and not disabled

---

## Clean Up After Testing

After completing all tests:

1. **Remove Test Data** (optional)
   ```python
   python manage.py shell

   from src.core.models import HabitLog
   # Delete any test logs you created
   ```

2. **Reset Reward Progress** (if needed)
   - Manually adjust `pieces_earned` values in admin if needed for continued testing

3. **Clear Audit Logs** (optional)
   ```python
   from src.core.models import BotAuditLog
   # Delete old audit logs if desired
   ```

---

## Reporting Issues

If you encounter bugs or unexpected behavior:

1. **Capture Details**:
   - Django admin URL you were on
   - Action you performed
   - Error message (copy full text)
   - Screenshot if applicable

2. **Check Logs**:
   - Application logs (`tail -f logs/app.log`)
   - Django error page (if 500 error)

3. **Include**:
   - Browser console errors (F12 → Console tab)
   - Network requests (F12 → Network tab)

4. **Create Issue** in GitHub with all above details

---

## Success Criteria

The feature is ready for production when:

✅ All 8 test cases pass
✅ No crashes or 500 errors
✅ Error messages are clear and actionable
✅ Audit logs properly created
✅ Reward progress correctly updated in all scenarios
✅ Performance acceptable for typical batch sizes (< 50 logs)
✅ Application logs show detailed debugging info
