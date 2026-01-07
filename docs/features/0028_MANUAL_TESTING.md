# Feature 0028: Manual Testing Plan - Configurable No Reward Probability

## Overview

This document provides a comprehensive manual testing plan for Feature 0028, which allows users to configure their personal "no reward" probability when completing habits. The feature includes:

1. **Database Migration**: Adds `no_reward_probability` field to User model (default: 50.0%)
2. **Settings UI**: New Telegram bot menu to configure probability (presets: 25%, 50%, 75%, or custom 0.01-99.99%)
3. **Reward Selection**: Uses user's personal setting or falls back to global `NO_REWARD_PROBABILITY_PERCENT` setting
4. **Edge Cases**: Handles 0% (always reward) and 100% (always no reward)

## Pre-Testing Setup

### 1. Database Migration

**Action**: Run the migration to add the new field
```bash
cd /Users/erzhan/Data/PROJ/habit_reward
uv run python manage.py migrate
```

**Expected Result**: 
- Migration `0012_add_no_reward_probability_to_user` runs successfully
- User table now has `no_reward_probability` field (FloatField, default=50.0)
- Reward.type field updated to remove 'none' option (only 'virtual' and 'real' remain)

**Verification**:
```bash
# Check migration status
uv run python manage.py showmigrations core

# Verify field exists in database
uv run python manage.py shell
>>> from src.core.models import User
>>> User._meta.get_field('no_reward_probability')
core.User.no_reward_probability
>>> field = User._meta.get_field('no_reward_probability')
>>> field.default
50.0
>>> type(field).__name__
'FloatField'
```

[X] **Expected Output**: 
- `core.User.no_reward_probability` - Confirms field exists
- `50.0` - Default value
- `'FloatField'` - Field type

### 2. Environment Configuration

**Action**: Verify `.env` has the global setting (optional, defaults to 50.0)
```bash
# Check .env.example for reference
NO_REWARD_PROBABILITY_PERCENT=50.0
```

[X] **Expected Result**: Setting is available in Django settings (defaults to 50.0 if not set)

### 3. Bot Setup

**Action**: Start the Telegram bot
```bash
make bot
# or
uv run python -m src.bot.main
```

**Expected Result**: Bot starts without errors, all handlers registered

---

## Test Scenarios

### Test Group 1: Settings UI - Menu Navigation

[X] #### TC1.1: Access Settings Menu
**Steps**:
1. Send `/settings` command to bot
2. Verify settings menu appears

**Expected Result**:
- Settings menu shows with options including "🎲 No Reward Probability"
- Menu is properly formatted with HTML
- All buttons are clickable

**Pass Criteria**: ✅ Menu displays correctly

---

[X] #### TC1.2: Open No Reward Probability Menu
**Steps**:
1. Send `/settings` command
2. Click "🎲 No Reward Probability" button

**Expected Result**:
- Menu shows current value (should be 50.0% for new users)
- Displays message: "🎲 **No Reward Probability**\n\nCurrent: **50.0%**\n\nChoose a preset or enter a custom value (0.01-99.99):"
- Shows buttons: [25%] [50%] [75%] in one row
- Shows "✏️ Custom" button
- Shows "← Back" button

**Pass Criteria**: ✅ Menu displays with correct current value and all buttons

---

[X] #### TC1.3: Navigate Back from No Reward Probability Menu
**Steps**:
1. Open No Reward Probability menu (TC1.2)
2. Click "← Back" button

**Expected Result**:
- Returns to main settings menu
- No errors in logs

**Pass Criteria**: ✅ Navigation works correctly

---

### Test Group 2: Settings UI - Preset Selection

[X] #### TC2.1: Select 25% Preset
**Steps**:
1. Open No Reward Probability menu
2. Click "25%" button

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **25%**"
- Returns to main settings menu
- Database updated: `user.no_reward_probability = 25.0`
- Log shows: `✅ Updated no_reward_probability to 25.0% for user {telegram_id}`

**Verification**:
```python
# In Django shell
from src.core.models import User
user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
assert user.no_reward_probability == 25.0
```

**Pass Criteria**: ✅ Value updated correctly in database and UI

---

[X] #### TC2.2: Select 50% Preset
**Steps**:
1. Open No Reward Probability menu
2. Click "50%" button

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **50%**"
- Database updated: `user.no_reward_probability = 50.0`

**Pass Criteria**: ✅ Value updated correctly

---

[X] #### TC2.3: Select 75% Preset
**Steps**:
1. Open No Reward Probability menu
2. Click "75%" button

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **75%**"
- Database updated: `user.no_reward_probability = 75.0`

**Pass Criteria**: ✅ Value updated correctly

---

### Test Group 3: Settings UI - Custom Value Entry

[X] #### TC3.1: Enter Valid Custom Value (10%)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Bot prompts: "📝 **Enter custom probability**\n\nEnter a value between 0.01 and 99.99:"
4. Send message: `10`

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **10%**"
- Database updated: `user.no_reward_probability = 10.0`
- Returns to settings menu

**Pass Criteria**: ✅ Custom value accepted and saved

---

[X] #### TC3.2: Enter Valid Custom Value (90%)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `90`

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **90%**"
- Database updated: `user.no_reward_probability = 90.0`

**Pass Criteria**: ✅ Custom value accepted

---

[X] #### TC3.3: Enter Valid Custom Value (0.01% - Minimum)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `0.01`

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **0.01%**"
- Database updated: `user.no_reward_probability = 0.01`

**Pass Criteria**: ✅ Minimum value accepted

---

[X] #### TC3.4: Enter Valid Custom Value (99.99% - Maximum)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `99.99`

**Expected Result**:
- Bot responds: "✅ No reward probability updated to **99.99%**"
- Database updated: `user.no_reward_probability = 99.99`

**Pass Criteria**: ✅ Maximum value accepted

---

[X] #### TC3.5: Enter Invalid Value - Too Low (0.00)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `0.00`

**Expected Result**:
- Bot responds: "❌ Invalid value. Please enter a number between 0.01 and 99.99."
- Bot remains in custom input state (doesn't exit)
- Database NOT updated
- User can try again

**Pass Criteria**: ✅ Invalid value rejected, user can retry
** TODO When user see the error message they should be able to return back to the previous menu (button 'Back' or 'Cancel')
---

[X] #### TC3.6: Enter Invalid Value - Too High (100)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `100`

**Expected Result**:
- Bot responds: "❌ Invalid value. Please enter a number between 0.01 and 99.99."
- Bot remains in custom input state
- Database NOT updated

**Pass Criteria**: ✅ Invalid value rejected

---

[X] #### TC3.7: Enter Invalid Value - Non-Numeric
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `abc`

**Expected Result**:
- Bot responds: "❌ Invalid value. Please enter a number between 0.01 and 99.99."
- Bot remains in custom input state

**Pass Criteria**: ✅ Non-numeric value rejected

---

[X] #### TC3.8: Enter Invalid Value - Negative
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send message: `-5`

**Expected Result**:
- Bot responds: "❌ Invalid value. Please enter a number between 0.01 and 99.99."
- Bot remains in custom input state

**Pass Criteria**: ✅ Negative value rejected

---

### Test Group 4: Reward Selection - Probability Testing

**Prerequisites for Test Group 4**:
- User has at least 1 active habit
- User has at least 2-3 active rewards with different weights
- Habit is not already completed today

**Quick Setup**: Use the provided script to create 20 habits and 3 rewards:
```bash
# Create test data for your telegram ID
uv run python scripts/setup_test_data_0028.py --telegram-id YOUR_TELEGRAM_ID

# Or clean up existing data first
uv run python scripts/setup_test_data_0028.py --telegram-id YOUR_TELEGRAM_ID --cleanup

# Dry run to see what would be created
uv run python scripts/setup_test_data_0028.py --telegram-id YOUR_TELEGRAM_ID --dry-run
```

[X] #### TC4.1: Test Default 50% Probability (New User)
**Steps**:
1. Create a new test user (or reset existing user's `no_reward_probability` to NULL/50.0)
2. Complete habit 20 times
3. Count how many times reward was given vs. no reward

**Expected Result**:
- Approximately 50% of completions result in no reward
- With 20 completions, expect 8-12 no-reward outcomes (40-60% range is acceptable for small sample)
- Logs show: `🎲 NO_REWARD_PROBABILITY_PERCENT from settings (fallback): 50.0%`

**Pass Criteria**: ✅ No-reward rate is approximately 50% (±10% acceptable for small sample)

---

#### TC4.2: Test 25% Probability
**Steps**:
1. Set user's `no_reward_probability` to 25.0 (via settings menu or directly in DB)
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Approximately 25% of completions result in no reward
- With 20 completions, expect 3-7 no-reward outcomes (15-35% range acceptable)
- Logs show: `🎲 no_reward_probability from user DB: 25.0%`

**Pass Criteria**: ✅ No-reward rate is approximately 25%

---

#### TC4.3: Test 75% Probability
**Steps**:
1. Set user's `no_reward_probability` to 75.0
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Approximately 75% of completions result in no reward
- With 20 completions, expect 13-17 no-reward outcomes (65-85% range acceptable)
- Logs show: `🎲 no_reward_probability from user DB: 75.0%`

**Pass Criteria**: ✅ No-reward rate is approximately 75%

---

#### TC4.4: Test 10% Probability (Low)
**Steps**:
1. Set user's `no_reward_probability` to 10.0
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Approximately 10% of completions result in no reward
- With 20 completions, expect 1-4 no-reward outcomes (5-20% range acceptable)
- Most completions should give rewards

**Pass Criteria**: ✅ No-reward rate is approximately 10%

---

#### TC4.5: Test 90% Probability (High)
**Steps**:
1. Set user's `no_reward_probability` to 90.0
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Approximately 90% of completions result in no reward
- With 20 completions, expect 16-19 no-reward outcomes (80-95% range acceptable)
- Most completions should give no reward

**Pass Criteria**: ✅ No-reward rate is approximately 90%

---

### Test Group 5: Edge Cases - Extreme Probabilities

#### TC5.1: Test 0.01% Probability (Minimum)
**Steps**:
1. Set user's `no_reward_probability` to 0.01
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Almost all completions give rewards
- Very few (0-1) no-reward outcomes
- Logs show: `🎲 p<=0: No 'None' in population (always reward)` (if exactly 0.0)
- OR logs show probability calculation for 0.01%

**Note**: 0.01% is technically > 0, so it should still allow no-reward outcomes (very rarely)

**Pass Criteria**: ✅ Almost always gives rewards

---

#### TC5.2: Test 99.99% Probability (Maximum)
**Steps**:
1. Set user's `no_reward_probability` to 99.99
2. Complete habit 20 times
3. Count outcomes

**Expected Result**:
- Almost all completions give no reward
- Very few (0-1) reward outcomes
- Logs show probability calculation

**Pass Criteria**: ✅ Almost always gives no reward

---

#### TC5.3: Test 0% Probability (Edge Case - Should Always Reward)
**Steps**:
1. Set user's `no_reward_probability` to 0.0 (via database directly, as UI doesn't allow this)
2. Complete habit 10 times
3. Count outcomes

**Expected Result**:
- ALL completions give rewards (100%)
- No "no reward" outcomes
- Logs show: `🎲 p<=0: No 'None' in population (always reward)`

**Verification**:
```python
# Set via Django shell
user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
user.no_reward_probability = 0.0
user.save()
```

**Pass Criteria**: ✅ Always gives rewards when probability is 0%

---

#### TC5.4: Test 100% Probability (Edge Case - Should Always No Reward)
**Steps**:
1. Set user's `no_reward_probability` to 100.0 (via database directly)
2. Complete habit 10 times
3. Count outcomes

**Expected Result**:
- ALL completions give no reward (100%)
- No reward outcomes
- Logs show: `🎲 p>=100: NO_REWARD_PROBABILITY_PERCENT=100.0 -> always no reward`

**Verification**:
```python
# Set via Django shell
user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
user.no_reward_probability = 100.0
user.save()
```

**Pass Criteria**: ✅ Always gives no reward when probability is 100%

---

### Test Group 6: Fallback to Global Setting

#### TC6.1: User Without Personal Setting (NULL)
**Steps**:
1. Set user's `no_reward_probability` to NULL (via database)
2. Ensure global `NO_REWARD_PROBABILITY_PERCENT` is set to 50.0 (default)
3. Complete habit 20 times
4. Count outcomes

**Expected Result**:
- Uses global setting (50.0%)
- Approximately 50% no-reward rate
- Logs show: `🎲 NO_REWARD_PROBABILITY_PERCENT from settings (fallback): 50.0%`

**Verification**:
```python
# Set to NULL
user = User.objects.get(telegram_id='YOUR_TELEGRAM_ID')
user.no_reward_probability = None
user.save()
```

**Pass Criteria**: ✅ Falls back to global setting correctly

---

#### TC6.2: User Without Personal Setting - Custom Global Setting
**Steps**:
1. Set user's `no_reward_probability` to NULL
2. Set global `NO_REWARD_PROBABILITY_PERCENT` to 30.0 (in `.env` or Django settings)
3. Restart bot
4. Complete habit 20 times
5. Count outcomes

**Expected Result**:
- Uses global setting (30.0%)
- Approximately 30% no-reward rate
- Logs show: `🎲 NO_REWARD_PROBABILITY_PERCENT from settings (fallback): 30.0%`

**Pass Criteria**: ✅ Falls back to custom global setting

---

### Test Group 7: Multi-Language Support

#### TC7.1: Test Settings Menu in English
**Steps**:
1. Set user language to English (`/settings` → Language → English)
2. Open No Reward Probability menu

**Expected Result**:
- All messages in English
- Buttons display correctly
- Current value shows correctly

**Pass Criteria**: ✅ English UI works correctly

---

#### TC7.2: Test Settings Menu in Russian
**Steps**:
1. Set user language to Russian (`/settings` → Language → Русский)
2. Open No Reward Probability menu

**Expected Result**:
- All messages in Russian
- Message: "🎲 **Вероятность без награды**\n\nТекущее значение: **50.0%**\n\nВыберите пресет или введите своё значение (0.01-99.99):"
- Buttons display correctly

**Pass Criteria**: ✅ Russian UI works correctly

---

#### TC7.3: Test Settings Menu in Kazakh
**Steps**:
1. Set user language to Kazakh (`/settings` → Language → Қазақша)
2. Open No Reward Probability menu

**Expected Result**:
- All messages in Kazakh
- Message: "🎲 **Сыйлықсыз ықтималдық**\n\nАғымдағы мән: **50.0%**\n\nПресетті таңдаңыз немесе өз мәніңізді енгізіңіз (0.01-99.99):"
- Buttons display correctly

**Pass Criteria**: ✅ Kazakh UI works correctly

---

### Test Group 8: Integration with Habit Completion Flow

#### TC8.1: Complete Habit with 50% Probability
**Steps**:
1. Set `no_reward_probability` to 50.0
2. Complete a habit using `/done` or menu
3. Observe reward selection outcome
4. Repeat 10 times

**Expected Result**:
- Habit completion works normally
- Reward selection respects the 50% probability
- Success messages display correctly
- Audit logs created correctly

**Pass Criteria**: ✅ Habit completion integrates correctly with probability setting

---

#### TC8.2: Complete Habit with 25% Probability
**Steps**:
1. Set `no_reward_probability` to 25.0
2. Complete a habit
3. Observe outcome (should get reward more often)

**Expected Result**:
- Habit completion works
- More rewards given than no-reward outcomes
- All messages display correctly

**Pass Criteria**: ✅ Integration works with different probabilities

---

### Test Group 9: Database and Migration

#### TC9.1: Verify Migration Applied
**Steps**:
1. Check migration status
2. Verify User model has `no_reward_probability` field

**Expected Result**:
- Migration `0012_add_no_reward_probability_to_user` is applied
- Field exists with correct type (FloatField)
- Default value is 50.0
- Validators: MinValueValidator(0.01), MaxValueValidator(99.99)

**Verification**:
```python
from src.core.models import User
field = User._meta.get_field('no_reward_probability')
assert field.default == 50.0
assert field.validators  # Should have min/max validators
```

**Pass Criteria**: ✅ Migration applied correctly

---

#### TC9.2: Verify Existing Users Get Default Value
**Steps**:
1. Check existing users in database
2. Verify `no_reward_probability` is set to 50.0

**Expected Result**:
- All existing users have `no_reward_probability = 50.0`
- No NULL values (unless explicitly set)

**Verification**:
```python
from src.core.models import User
users = User.objects.all()
for user in users:
    assert user.no_reward_probability == 50.0 or user.no_reward_probability is None
```

**Pass Criteria**: ✅ Existing users have default value

---

### Test Group 10: Error Handling and Edge Cases

#### TC10.1: Cancel Custom Input (Send Command)
**Steps**:
1. Open No Reward Probability menu
2. Click "✏️ Custom" button
3. Send `/settings` command (or any other command)

**Expected Result**:
- Conversation handler ends gracefully
- No errors in logs
- User can start fresh

**Pass Criteria**: ✅ Command cancels input gracefully

---

#### TC10.2: Rapid Button Clicks
**Steps**:
1. Open No Reward Probability menu
2. Rapidly click preset buttons (25%, 50%, 75%) multiple times

**Expected Result**:
- Each click is processed
- Last value is saved
- No race conditions or errors

**Pass Criteria**: ✅ Rapid clicks handled correctly

---

#### TC10.3: User Not Found During Update
**Steps**:
1. Open No Reward Probability menu
2. Delete user from database (in another session)
3. Try to select a preset

**Expected Result**:
- Bot responds: "❌ User not found. Please contact admin to register."
- Conversation ends gracefully
- No crashes

**Pass Criteria**: ✅ Error handling works correctly

---

## Statistical Testing (Optional)

For more rigorous probability testing, use the provided test script:

```bash
# Test with 10,000 iterations (default)
uv run python scripts/test_50_percent_no_reward.py

# Test with custom iterations
uv run python scripts/test_50_percent_no_reward.py --iterations 5000

# Verbose output
uv run python scripts/test_50_percent_no_reward.py --verbose
```

**Expected Result**: 
- For 50% probability: No-reward rate should be 47-53% (with 10K samples)
- Chi-square test should pass
- 95% confidence interval should include 50%

---

## Test Execution Checklist

### Pre-Testing
- [ ] Database migration applied successfully
- [ ] Bot is running and responsive
- [ ] Test user account created/available
- [ ] Test habits and rewards created

### Settings UI Tests
- [ ] TC1.1: Access Settings Menu
- [ ] TC1.2: Open No Reward Probability Menu
- [ ] TC1.3: Navigate Back
- [ ] TC2.1: Select 25% Preset
- [ ] TC2.2: Select 50% Preset
- [ ] TC2.3: Select 75% Preset
- [ ] TC3.1: Enter Valid Custom Value (10%)
- [ ] TC3.2: Enter Valid Custom Value (90%)
- [ ] TC3.3: Enter Valid Custom Value (0.01%)
- [ ] TC3.4: Enter Valid Custom Value (99.99%)
- [ ] TC3.5: Enter Invalid Value (0.00)
- [ ] TC3.6: Enter Invalid Value (100)
- [ ] TC3.7: Enter Invalid Value (non-numeric)
- [ ] TC3.8: Enter Invalid Value (negative)

### Probability Testing
- [ ] TC4.1: Test Default 50% Probability
- [ ] TC4.2: Test 25% Probability
- [ ] TC4.3: Test 75% Probability
- [ ] TC4.4: Test 10% Probability
- [ ] TC4.5: Test 90% Probability

### Edge Cases
- [ ] TC5.1: Test 0.01% Probability
- [ ] TC5.2: Test 99.99% Probability
- [ ] TC5.3: Test 0% Probability (always reward)
- [ ] TC5.4: Test 100% Probability (always no reward)

### Fallback Testing
- [ ] TC6.1: User Without Personal Setting (NULL)
- [ ] TC6.2: User Without Personal Setting - Custom Global

### Multi-Language
- [ ] TC7.1: English UI
- [ ] TC7.2: Russian UI
- [ ] TC7.3: Kazakh UI

### Integration
- [ ] TC8.1: Complete Habit with 50% Probability
- [ ] TC8.2: Complete Habit with 25% Probability

### Database
- [ ] TC9.1: Verify Migration Applied
- [ ] TC9.2: Verify Existing Users Get Default Value

### Error Handling
- [ ] TC10.1: Cancel Custom Input
- [ ] TC10.2: Rapid Button Clicks
- [ ] TC10.3: User Not Found During Update

---

## Known Limitations

1. **Statistical Variance**: With small sample sizes (20 completions), the actual no-reward rate may vary ±10% from the configured probability. This is normal statistical variance.

2. **UI Validation**: The UI only allows 0.01-99.99%, but the database/logic can handle 0% and 100% if set directly. This is intentional (edge cases for testing).

3. **Migration**: The migration also removes 'none' from Reward.type choices. This is part of Feature 0027 cleanup.

---

## Test Results Template

```
Feature: 0028 - Configurable No Reward Probability
Tester: [Your Name]
Date: [Date]
Environment: [Development/Staging/Production]

Summary:
- Total Test Cases: 40+
- Passed: ___
- Failed: ___
- Blocked: ___

Critical Issues Found:
1. [Issue description]

Minor Issues Found:
1. [Issue description]

Notes:
[Any additional observations]
```

---

## Quick Reference

### Bot Commands
- `/settings` - Open settings menu
- `/done` - Complete a habit (tests reward selection)

### Database Queries
```python
# Check user's probability
user = User.objects.get(telegram_id='123456789')
print(user.no_reward_probability)

# Set probability directly
user.no_reward_probability = 25.0
user.save()

# Reset to default
user.no_reward_probability = 50.0
user.save()
```

### Log Messages to Look For
- `🎲 no_reward_probability from user DB: X.X%` - Using user's personal setting
- `🎲 NO_REWARD_PROBABILITY_PERCENT from settings (fallback): X.X%` - Using global setting
- `🎲 p<=0: No 'None' in population (always reward)` - Probability is 0%
- `🎲 p>=100: NO_REWARD_PROBABILITY_PERCENT=X -> always no reward` - Probability is 100%

---

## Conclusion

This manual testing plan covers all aspects of Feature 0028:
- Settings UI functionality
- Probability configuration (presets and custom)
- Reward selection with different probabilities
- Edge cases and error handling
- Multi-language support
- Database migration

Execute tests systematically, document results, and report any issues found.

