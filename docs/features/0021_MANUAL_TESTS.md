# Feature 0021: Split Habit Completion Flows - Manual Test Scripts

## Prerequisites

Before running tests:
1. Bot is running (`make bot` or `./run_bot.sh`)
2. Test user is registered and active in the system
3. Access to Django admin or shell to manipulate test data

## Test Environment Setup

```bash
# Start the bot
make bot

# Or via Django shell, prepare test data:
python manage.py shell

>>> from src.core.models import User, Habit, HabitLog
>>> from datetime import date
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>>
>>> # Create test habits
>>> habit1 = Habit.objects.create(
...     user=user,
...     name='Morning Exercise',
...     weight=10,
...     category='health',
...     active=True
... )
>>> habit2 = Habit.objects.create(
...     user=user,
...     name='Read Book',
...     weight=5,
...     category='learning',
...     active=True
... )
>>> print(f"Created habits: {habit1.id}, {habit2.id}")
```

---

## Test Scenarios

### Scenario 1: Simple Flow - No Habits Configured (Bug Fix Verification)

**Goal**: Verify that new users with zero habits see the correct error message.

**Setup**:
```python
# In Django shell, deactivate all habits for test user
>>> from src.core.models import User, Habit
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> Habit.objects.filter(user=user, active=True).update(active=False)
```

**Steps**:
1. Open Telegram bot
2. Click main menu "Habit Done" button
3. Observe the response message

**Expected**:
- ❌ Message: "You don't have any active habits. Add your first habit to start tracking!"
- Shows "« Back to Menu" button
- **NOT** "All habits completed today" message

**Cleanup**:
```python
>>> Habit.objects.filter(user=user).update(active=True)
```

---

### Scenario 2: Simple Flow - Pending Habits Available

**Goal**: Verify simple flow shows only pending habits with one-click completion.

**Setup**:
```python
# Ensure habits exist and nothing completed today
>>> from src.core.models import User, Habit, HabitLog
>>> from datetime import date
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> HabitLog.objects.filter(user=user, completion_date=date.today()).delete()
```

**Steps**:
1. Click main menu "Habit Done" button
2. Observe the habit list
3. Click "Morning Exercise" habit
4. Observe completion message

**Expected**:
- Message: "Which habit did you complete today? 🎯"
- Shows only habits not completed today
- After clicking habit:
  - Success message with habit name
  - Streak count displayed
  - Date format: "09 Dec 2025" (not "December 09, 2025" or "2025-12-09")
  - Shows "« Back to Menu" button

**Verify**:
- No date selection shown (immediate completion)
- Only 2-3 clicks total to complete

---

### Scenario 3: Simple Flow - All Habits Completed Today

**Goal**: Verify correct message when all habits are completed.

**Setup**:
```python
# Complete all habits for today
>>> from src.core.models import User, Habit, HabitLog
>>> from datetime import date
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> habits = Habit.objects.filter(user=user, active=True)
>>> for habit in habits:
...     HabitLog.objects.get_or_create(
...         user=user,
...         habit=habit,
...         completion_date=date.today()
...     )
```

**Steps**:
1. Click main menu "Habit Done" button
2. Observe the response

**Expected**:
- ✅ Message: "All habits completed today! Great job! 🎉"
- Shows "« Back to Menu" button
- **NOT** "You don't have any active habits" error

**Cleanup**:
```python
>>> HabitLog.objects.filter(user=user, completion_date=date.today()).delete()
```

---

### Scenario 4: Advanced Flow - Date Selection Available

**Goal**: Verify advanced flow shows all habits with date selection options.

**Setup**:
```python
# Clean slate - no completions today
>>> from src.core.models import User, HabitLog
>>> from datetime import date
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> HabitLog.objects.filter(user=user, completion_date=date.today()).delete()
```

**Steps**:
1. Click main menu "Habits" button
2. Click "📅 Habit Done for Date" button (should be below "Revert Habit")
3. Observe habit list
4. Select "Morning Exercise"
5. Observe date options
6. Click "✅ Today"
7. Observe completion message

**Expected**:
- Step 3: Shows ALL active habits (both completed and pending for today)
- Step 5: Shows three buttons: "✅ Today", "📅 Yesterday", "📆 Select Date"
- Step 7: Success message with date in format "09 Dec 2025"
- Total clicks: 5-6 (more than simple flow)

**Verify**:
- Advanced flow is in Habits submenu (NOT main menu)
- Button label: "📅 Habit Done for Date"

---

### Scenario 5: Advanced Flow - No Habits Configured

**Goal**: Verify advanced flow also handles zero habits correctly.

**Setup**:
```python
>>> from src.core.models import User, Habit
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> Habit.objects.filter(user=user, active=True).update(active=False)
```

**Steps**:
1. Click main menu "Habits" button
2. Click "📅 Habit Done for Date" button
3. Observe the response

**Expected**:
- Error message: "You don't have any active habits. Add your first habit to start tracking!"
- Shows "« Back to Menu" button

**Cleanup**:
```python
>>> Habit.objects.filter(user=user).update(active=True)
```

---

### Scenario 6: Date Format Consistency Verification

**Goal**: Verify all date displays use "09 Dec 2025" format.

**Steps**:
1. Use advanced flow to complete a habit for yesterday
2. Use backdate flow (`/backdate`) to complete a habit for a past date
3. Check all success messages

**Expected Date Format**: `09 Dec 2025` (pattern: `DD MMM YYYY`)
**NOT**:
- ❌ `December 09, 2025` (old verbose format)
- ❌ `2025-12-09` (ISO format)

**Files to Verify**:
- `menu_handler.py` - All menu flow messages
- `habit_done_handler.py` - Yesterday/backdate messages
- `backdate_handler.py` - All backdate messages

---

### Scenario 7: Multi-Language Support

**Goal**: Verify messages work in all supported languages.

**Setup**:
```python
# Change user language via Django admin or shell
>>> from src.core.models import User
>>> user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
>>> user.language = 'ru'  # or 'kk' for Kazakh
>>> user.save()
```

**Steps**:
1. Test Scenario 1 (no habits) in Russian
2. Test Scenario 3 (all completed) in Russian
3. Repeat for Kazakh language

**Expected**:
- `BUTTON_HABIT_DONE_DATE`: "📅 Отметить за дату" (ru) / "📅 Күнге белгілеу" (kk)
- `HELP_SIMPLE_HABIT_SELECTION`: "Какую привычку вы выполнили сегодня? 🎯" (ru) / "Бүгін қай әдетті орындадыңыз? 🎯" (kk)
- All other messages translated correctly

**Cleanup**:
```python
>>> user.language = 'en'
>>> user.save()
```

---

## Callback Data Verification

**Goal**: Verify correct callback routing between flows.

### Simple Flow Callbacks:
- `menu_habit_done` → `menu_habit_done_simple_show_habits`
- `simple_habit_{id}` → `simple_habit_selected_callback`

### Advanced Flow Callbacks:
- `menu_habit_done_date` → `menu_habit_done_show_habits`
- `habit_{id}` → `habit_selected_standalone_callback`
- `habit_{id}_today` → `menu_habit_today_callback`
- `habit_{id}_yesterday` → `menu_habit_yesterday_callback`

**Verification Method**:
Check bot logs for correct handler routing when buttons are clicked.

---

## Performance Notes

**Simple Flow**: Optimized for 90% use case
- 2-3 clicks to completion
- Shows only relevant habits (pending for today)
- No unnecessary date selection

**Advanced Flow**: For power users
- 5-6 clicks to completion
- Shows all habits (including completed)
- Full date selection (Today/Yesterday/Custom)

---

## Common Issues to Watch For

1. **Wrong error message for new users**: Should show "No habits configured", not "All completed"
2. **Date format inconsistency**: All dates should use "09 Dec 2025" format
3. **Wrong menu placement**: "Habit Done for Date" should be in Habits submenu, not main menu
4. **Callback conflicts**: Ensure `simple_habit_` pattern doesn't conflict with `habit_` pattern
5. **Translation missing**: All new messages should have ru/kk translations

---

## Success Criteria

- ✅ All scenarios pass without errors
- ✅ Date format is consistent across all flows
- ✅ Simple flow requires 2-3 clicks maximum
- ✅ Advanced flow provides full date selection
- ✅ New users see correct error message (not "all completed")
- ✅ All languages display correctly
- ✅ No callback routing conflicts
