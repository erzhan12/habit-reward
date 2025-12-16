# Feature 0020: Backdate Habit Completion - Manual Test Scripts

## Prerequisites

Before running tests:
1. Bot is running (`make bot` or `./run_bot.sh`)
2. Test user is registered and active in the system
3. At least 2 active habits exist for the test user
4. Clean slate: no habit completions for the past 7 days (or use fresh test habits)

## Test Environment Setup

```bash
# Start the bot
make bot

# Or via Django shell, create test fixtures:
python manage.py shell

>>> from src.core.models import User, Habit, HabitLog
>>> from datetime import date, timedelta
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> # Create a test habit for backdate testing
>>> habit = Habit.objects.create(
...     user=user,
...     name='Backdate Test Habit',
...     weight=10,
...     category='testing',
...     active=True
... )
>>> print(f"Created habit ID: {habit.id}")
```

---

## Test Scenarios

### Scenario 1: Quick "Log for Today" (Baseline)

**Goal**: Verify existing today-completion still works after changes.

**Steps**:
1. Open Telegram, send `/habit_done`
2. Select "Backdate Test Habit" from the list
3. Click "✅ Today" button
4. Observe completion message

**Expected**:
- Success message: "✅ Habit completed: Backdate Test Habit"
- Streak shows: "🔥 Streak: 1 days"
- Date in completion is today's date

**Verification**:
```bash
python manage.py shell
>>> from src.core.models import HabitLog
>>> from datetime import date
>>> HabitLog.objects.filter(habit__name='Backdate Test Habit', last_completed_date=date.today()).exists()
True
```

---

### Scenario 2: Quick "Log for Yesterday" Button

**Goal**: Test quick yesterday completion without full date picker.

**Preconditions**:
- Create a NEW test habit (no completions)

**Steps**:
1. Send `/habit_done`
2. Select the new habit
3. Click "📅 Yesterday" button
4. Observe confirmation prompt
5. Confirm the backdated completion

**Expected**:
- Confirmation message shows yesterday's date
- Success message: "✅ Habit backdated: [habit_name]" with "📅 Date: [yesterday's date]"
- Streak: 1 day

**Verification**:
```bash
python manage.py shell
>>> from datetime import date, timedelta
>>> yesterday = date.today() - timedelta(days=1)
>>> HabitLog.objects.filter(habit__name='NEW_HABIT_NAME', last_completed_date=yesterday).exists()
True
```

---

### Scenario 3: Date Picker - Select 3 Days Ago

**Goal**: Test full date picker flow for arbitrary past date.

**Preconditions**:
- Fresh habit with no completions

**Steps**:
1. Send `/habit_done`
2. Select habit
3. Click "📆 Select Date" button
4. Verify 7-day calendar is displayed
5. Click the date that is 3 days ago
6. Verify confirmation dialog shows correct date
7. Confirm completion

**Expected**:
- Calendar shows dates from (today - 6) to today
- Selected date is highlighted in confirmation
- Success message shows the backdated date
- Log entry has correct `last_completed_date`

---

### Scenario 4: Date Picker Shows Already-Completed Dates

**Goal**: Verify calendar marks completed dates with ✓.

**Preconditions**:
- Complete a habit for today
- Complete same habit for 2 days ago (via admin or previous test)

**Steps**:
1. Send `/habit_done`
2. Select the habit with completions
3. Click "📆 Select Date"
4. Observe calendar

**Expected**:
- Today shows "✓" or different styling
- 2 days ago shows "✓"
- Other dates show no checkmark
- Clicking a completed date either:
  - Shows disabled button, or
  - Shows error "Already completed on this date"

---

### Scenario 5: Duplicate Prevention - Same Date Twice

**Goal**: Verify cannot complete same habit twice for same date.

**Preconditions**:
- Habit already completed for today

**Steps**:
1. Send `/habit_done`
2. Select the completed habit
3. Click "✅ Today"

**Expected**:
- Error message: "❌ You already logged [habit_name] on [today's date]"
- No new HabitLog entry created

**Verification**:
```bash
python manage.py shell
>>> from datetime import date
>>> HabitLog.objects.filter(habit_id=HABIT_ID, last_completed_date=date.today()).count()
1  # Should still be 1, not 2
```

---

### Scenario 6: Streak Calculation with Backdate

**Goal**: Verify backdated completion correctly affects streak count.

**Preconditions**:
- Fresh habit with no completions

**Steps**:
1. Complete habit for TODAY → verify streak = 1
2. Backdate completion to YESTERDAY
3. Check `/streaks`

**Expected**:
- After backdating yesterday, the today entry should show streak = 2
- Or, the streak display considers the continuous chain

**Verification**:
```bash
python manage.py shell
>>> logs = HabitLog.objects.filter(habit__name='TEST').order_by('last_completed_date')
>>> for log in logs:
...     print(f"{log.last_completed_date}: streak={log.streak_count}")
# Yesterday: streak=1
# Today: streak=2
```

---

### Scenario 7: Error - Backdate More Than 7 Days

**Goal**: Verify the 7-day limit is enforced.

**Steps**:
1. Send `/habit_done`
2. Select any habit
3. Click "📆 Select Date"
4. (If possible) try to navigate to 8+ days ago
5. Or, use direct API/service call to test:

**Direct test via shell**:
```bash
python manage.py shell
>>> from src.services.habit_service import habit_service
>>> from datetime import date, timedelta
>>> import asyncio
>>> 
>>> target_date = date.today() - timedelta(days=8)
>>> try:
...     asyncio.run(habit_service.process_habit_completion(
...         user_telegram_id='YOUR_ID',
...         habit_name='Test Habit',
...         target_date=target_date
...     ))
... except ValueError as e:
...     print(f"Error: {e}")
Error: Cannot backdate more than 7 days
```

**Expected**:
- ValueError with message about 7-day limit
- No log entry created

---

### Scenario 8: Error - Backdate Before Habit Creation

**Goal**: Verify cannot backdate to before habit existed.

**Preconditions**:
- Create a new habit TODAY

**Steps**:
1. Send `/habit_done`
2. Select the newly created habit
3. Click "📆 Select Date"
4. Try to select yesterday

**Expected**:
- Error: "❌ Cannot backdate before habit was created ([creation date])"

**Direct test**:
```bash
python manage.py shell
>>> from src.core.models import Habit
>>> from src.services.habit_service import habit_service
>>> from datetime import date, timedelta
>>> import asyncio
>>> 
>>> # Create habit today
>>> habit = Habit.objects.create(name='NewTodayHabit', user_id=1, weight=10)
>>> yesterday = date.today() - timedelta(days=1)
>>> 
>>> try:
...     asyncio.run(habit_service.process_habit_completion(
...         user_telegram_id='YOUR_ID',
...         habit_name='NewTodayHabit',
...         target_date=yesterday
...     ))
... except ValueError as e:
...     print(f"Error: {e}")
Error: Cannot backdate before habit was created
```

---

### Scenario 9: Error - Future Date

**Goal**: Verify cannot complete habits for future dates.

**Steps**:
1. Use shell to test directly:

```bash
python manage.py shell
>>> from src.services.habit_service import habit_service
>>> from datetime import date, timedelta
>>> import asyncio
>>> 
>>> tomorrow = date.today() + timedelta(days=1)
>>> try:
...     asyncio.run(habit_service.process_habit_completion(
...         user_telegram_id='YOUR_ID',
...         habit_name='Test Habit',
...         target_date=tomorrow
...     ))
... except ValueError as e:
...     print(f"Error: {e}")
Error: Cannot log habits for future dates
```

**Expected**:
- ValueError with clear message
- UI should not even show future dates in picker

---

### Scenario 10: Reward Selection Still Works with Backdate

**Goal**: Verify backdated completions still trigger reward selection.

**Preconditions**:
- Active rewards configured for user
- Fresh habit with no completions

**Steps**:
1. Backdate habit completion to 2 days ago
2. Observe completion message

**Expected**:
- Either "🎁 Reward: [name]" with progress
- Or "❌ No reward this time"
- Reward progress is updated if won

**Verification**:
```bash
python manage.py shell
>>> log = HabitLog.objects.filter(habit__name='TEST').latest('timestamp')
>>> print(f"got_reward: {log.got_reward}, reward: {log.reward}")
```

---

### Scenario 11: Backdate with Grace Days

**Goal**: Verify streak calculation respects habit's grace days setting.

**Preconditions**:
- Habit with `allowed_skip_days=1`
- Complete habit 3 days ago

**Steps**:
1. Backdate completion to TODAY (skipping yesterday and day before)
2. Check streak

**Expected**:
- With 1 grace day, gap of 2 days breaks streak → streak = 1
- Or adjust test to have 1-day gap which should preserve streak

**Setup and test**:
```bash
python manage.py shell
>>> habit = Habit.objects.get(name='Grace Days Habit')
>>> habit.allowed_skip_days = 1
>>> habit.save()
>>> 
>>> # Complete 2 days ago
>>> # Then complete today
>>> # Expected: streak = 2 (1 gap day is within grace)
```

---

### Scenario 12: Backdate with Exempt Weekdays

**Goal**: Verify streak calculation respects exempt weekdays.

**Preconditions**:
- Habit with `exempt_weekdays=[6, 7]` (weekends exempt)
- Today is Monday, last completion was Friday

**Steps**:
1. Complete habit for today (Monday)
2. Verify streak accounts for exempt weekend

**Expected**:
- Streak continues from Friday (Saturday/Sunday don't count as missed)

---

## Cleanup After Tests

```bash
python manage.py shell
>>> from src.core.models import Habit, HabitLog
>>> # Remove test habits and their logs
>>> Habit.objects.filter(name__icontains='Test').delete()
>>> Habit.objects.filter(name='Backdate Test Habit').delete()
```

---

## Test Result Template

| Scenario | Status | Notes |
|----------|--------|-------|
| 1. Log for Today | ⬜ Pass / ⬜ Fail | |
| 2. Log for Yesterday | ⬜ Pass / ⬜ Fail | |
| 3. Date Picker 3 Days | ⬜ Pass / ⬜ Fail | |
| 4. Calendar Shows Completed | ⬜ Pass / ⬜ Fail | |
| 5. Duplicate Prevention | ⬜ Pass / ⬜ Fail | |
| 6. Streak with Backdate | ⬜ Pass / ⬜ Fail | |
| 7. Error: >7 Days | ⬜ Pass / ⬜ Fail | |
| 8. Error: Before Created | ⬜ Pass / ⬜ Fail | |
| 9. Error: Future Date | ⬜ Pass / ⬜ Fail | |
| 10. Rewards with Backdate | ⬜ Pass / ⬜ Fail | |
| 11. Grace Days | ⬜ Pass / ⬜ Fail | |
| 12. Exempt Weekdays | ⬜ Pass / ⬜ Fail | |

**Tester**: _______________  
**Date**: _______________  
**Build/Commit**: _______________
















