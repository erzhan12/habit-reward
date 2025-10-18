# COMPREHENSIVE TEST CASES - HABIT REWARD SYSTEM

**Testing Date**: _______________
**Tester Name**: _______________
**Version**: 1.0

---

## TABLE OF CONTENTS

1. [Pre-Test Setup & Mock Data](#1-pre-test-setup--mock-data)
2. [Test Case 1: User Management](#test-case-1-user-management)
3. [Test Case 2: Habit Management](#test-case-2-habit-management)
4. [Test Case 3: Reward Management](#test-case-3-reward-management)
5. [Test Case 4: Basic Habit Completion Flow](#test-case-4-basic-habit-completion-flow)
6. [Test Case 5: Streak Calculation Logic](#test-case-5-streak-calculation-logic)
7. [Test Case 6: Weight Calculation & Multipliers](#test-case-6-weight-calculation--multipliers)
8. [Test Case 7: Cumulative Rewards System](#test-case-7-cumulative-rewards-system)
9. [Test Case 8: Reward Status Lifecycle](#test-case-8-reward-status-lifecycle)
10. [Test Case 9: Telegram Bot Commands](#test-case-9-telegram-bot-commands)
11. [Test Case 10: NLP Habit Classification](#test-case-10-nlp-habit-classification)
12. [Test Case 11: Dashboard Functionality](#test-case-11-dashboard-functionality)
13. [Test Case 12: Edge Cases & Error Handling](#test-case-12-edge-cases--error-handling)
14. [Test Case 13: Data Persistence & Integrity](#test-case-13-data-persistence--data-integrity)
15. [Test Case 14: Performance & Stress Testing](#test-case-14-performance--stress-testing)

---

## 1. PRE-TEST SETUP & MOCK DATA

### 1.1 Airtable Setup Instructions

Before starting tests, populate your Airtable base with this mock data:

#### **USERS Table** - Add these records:

| telegram_id | name | weight | active |
|-------------|------|--------|--------|
| 123456789 | Test User | 1.0 | ✓ |
| 987654321 | Power User | 2.0 | ✓ |
| 111222333 | Inactive User | 1.0 | (unchecked) |

**Setup Instructions:**
1. Open Airtable → Your Base → Users table
2. Click "+ Add record" for each user above
3. Fill in all fields exactly as shown
4. Ensure "active" checkbox is checked/unchecked as indicated

---

#### **HABITS Table** - Add these records:

| name | weight | category | active |
|------|--------|----------|--------|
| Morning Exercise | 2.0 | health | ✓ |
| Reading | 1.5 | learning | ✓ |
| Meditation | 1.0 | wellness | ✓ |
| Coding Practice | 2.0 | productivity | ✓ |
| Drinking Water | 1.0 | health | ✓ |
| Journaling | 1.0 | wellness | ✓ |
| Inactive Habit Test | 1.0 | test | (unchecked) |

**Setup Instructions:**
1. Go to Habits table
2. Add each habit with exact names (case-sensitive)
3. Set weight values as numbers (not text)
4. Verify "active" checkbox status

---

#### **REWARDS Table** - Add these records:

| name | weight | type | is_cumulative | pieces_required | piece_value |
|------|--------|------|---------------|-----------------|-------------|
| Free Coffee | 1.0 | cumulative | ✓ | 10 | 5.00 |
| Movie Ticket | 1.0 | cumulative | ✓ | 20 | 10.00 |
| Pizza Delivery | 3.0 | real | (unchecked) | (blank) | (blank) |
| Virtual Badge | 2.0 | virtual | (unchecked) | (blank) | (blank) |
| No Reward | 5.0 | none | (unchecked) | (blank) | (blank) |
| Book Purchase | 1.0 | cumulative | ✓ | 15 | 8.00 |

**Setup Instructions:**
1. Go to Rewards table
2. Add each reward with exact names
3. Set "type" field to EXACT values: cumulative/real/virtual/none
4. For cumulative rewards: check box AND fill pieces_required + piece_value
5. For non-cumulative: leave pieces fields blank

**Important Notes:**
- Weights affect probability (higher = more likely selected)
- "No Reward" with weight 5.0 means ~50% of completions give no reward
- piece_value is monetary value for dashboard stats

---

#### **REWARD PROGRESS Table** - Leave Empty Initially

This table will populate automatically when users complete habits. For some tests, you'll manually add records here.

---

#### **HABIT LOG Table** - Leave Empty Initially

This is the audit trail that populates automatically.

---

### 1.2 Environment Setup Verification

**Before Testing, Verify:**

- [X] `.env` file contains valid AIRTABLE_API_KEY
- [X] `.env` file contains valid AIRTABLE_BASE_ID
- [X] `.env` file contains valid TELEGRAM_BOT_TOKEN
- [X] `.env` file contains valid LLM_API_KEY (OpenAI)
- [X] `.env` DEFAULT_USER_TELEGRAM_ID = 123456789
- [ ] Telegram bot is running (`python src/bot/telegram_bot.py`)
- [X] Can access bot in Telegram by username
- [ ] Streamlit dashboard accessible (`streamlit run src/dashboard/app.py`)

**Your Setup Notes:**
```
[Space for your notes on setup issues or configurations]







```

---

### 1.3 Test Data Tracking Sheet

Use this to track which data you've created during testing:

| Test Case # | Data Created | Airtable Table | Record ID | Notes |
|-------------|--------------|----------------|-----------|-------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

## TEST CASE 1: USER MANAGEMENT

**Objective**: Test the **application's user management logic** - Does the code correctly retrieve users from Airtable, enforce the active flag, and apply user weight multipliers in calculations?

**What We're Testing**: The Python repository/service layer (`src/repositories/user_repository.py`, `src/services/user_service.py`, `src/services/reward_service.py`), NOT your data entry skills in Airtable

**Important**: These tests use YOUR Telegram account. You'll test different user states by modifying YOUR user record in Airtable.

---

### TC1.1: User Not Found Error (Before Creating User)

**What This Tests**:
- ✅ Does the app handle missing users gracefully?
- ✅ Does `user_repository.py` properly detect when a user doesn't exist?
- ✅ Does the bot show a helpful error message instead of crashing?

**Preconditions**:
- Your telegram account exists
- Your telegram_id does NOT exist in Airtable Users table yet
- Bot is running

**Test Steps**:
1. Get your telegram_id:
   - Open Telegram
   - Message @userinfobot
   - Note the ID it gives you (e.g., 123456789)
2. Set `.env` DEFAULT_USER_TELEGRAM_ID to YOUR telegram_id
3. Make sure NO user with your telegram_id exists in Airtable Users table
4. Restart bot: `python src/bot/telegram_bot.py`
5. Send `/start` command to your bot from YOUR Telegram account
6. Observe response

**Expected Results**:
- ✓ Bot responds with error: "User not found" or "Please contact admin"
- ✓ No crash or stack trace
- ✓ Application detects missing user and handles gracefully

**Actual Results**:
```
Your telegram_id: __________

Bot response:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC1.2: Active User Can Use Bot (Create and Test)

**What This Tests**:
- ✅ Does the app successfully retrieve an active user from Airtable?
- ✅ Does the bot work when user exists with active=true?
- ✅ Can you complete the normal user flow?

**Preconditions**:
- TC1.1 completed (you know your telegram_id)
- Bot is running

**Test Steps**:
1. Open Airtable → Users table
2. Click "+ Add record"
3. Fill in:
   - **telegram_id**: YOUR telegram_id from TC1.1
   - **name**: Your name (e.g., "Erzhan")
   - **weight**: 1.0
   - **active**: ✓ (checked)
4. Restart bot: `python src/bot/telegram_bot.py`
5. Send `/start` command from YOUR Telegram account
6. Observe response
7. Try sending `/habit_done` to verify full access

**Expected Results**:
- ✓ Bot responds with welcome message
- ✓ Message includes your name or telegram_id
- ✓ No "user not found" error
- ✓ `/habit_done` command works (shows habit keyboard)
- ✓ Application successfully retrieved your user from Airtable

**Actual Results**:
```
Bot /start response:





Bot /habit_done response:





```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC1.3: Inactive User is Blocked (Test Business Logic)

**What This Tests**:
- ✅ Does `user_service.py` enforce the `active` flag?
- ✅ Are inactive users prevented from completing habits?
- ✅ Does the system validate user status before operations?

**Preconditions**:
- TC1.2 completed (your user exists in Airtable)
- Bot is running

**Test Steps**:
1. Open Airtable → Users table
2. Find YOUR user record
3. **Uncheck** the `active` checkbox
4. Restart bot: `python src/bot/telegram_bot.py`
5. Send `/habit_done` command from YOUR Telegram account
6. Observe bot response
7. Check Airtable → Habit Log table (verify no new entries created)

**Expected Results**:
- ✓ Bot responds with error: "User is not active" or similar
- ✓ No habit logging occurs (Habit Log table has no new entries)
- ✓ System enforces the active flag

**Actual Results**:
```
Bot response:




Habit Log checked: [ ] No new entries [ ] Entries created (BUG!)

```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[IMPORTANT: Open Airtable Users table and CHECK the active box for your user again]
[Restart bot]
```

---

### TC1.4: User Weight Affects Calculations (Modify Your Weight)

**What This Tests**:
- ✅ Does `reward_service.py` use user weight in the formula?
- ✅ Is the math correct: `habit_weight × user_weight × streak_multiplier`?
- ✅ Does changing your weight in Airtable affect calculations?

**Preconditions**:
- Your user is active (active=checked) in Airtable
- Bot is running

**Test Steps**:

**Part A: Baseline with weight=1.0**
1. Make sure your user has weight=1.0 in Airtable
2. Send `/habit_done` → select "Meditation" (weight 1.0)
3. Open Airtable → Habit Log table
4. Find the entry you just created
5. Note the `total_weight_applied` value (should be 1.1 for streak=1)

**Part B: Change weight to 2.0**
6. Open Airtable → Users table
7. Find YOUR user record
8. Change `weight` from 1.0 to **2.0**
9. Restart bot: `python src/bot/telegram_bot.py`
10. Send `/habit_done` → select "Meditation" again (same habit)
11. Check new entry in Habit Log
12. Note new `total_weight_applied`

**Expected Results**:
- ✓ First completion (weight 1.0): total_weight_applied = 1.0 × 1.0 × 1.1 = **1.1**
- ✓ Second completion (weight 2.0): total_weight_applied = 1.0 × 2.0 × 1.1 = **2.2**
- ✓ User weight change reflected in calculations
- ✓ Higher weight increases reward probability

**Actual Results**:
```
Part A Results:
First completion total_weight_applied: __________
Expected: 1.1
Match: [ ] YES [ ] NO

Part B Results:
Second completion total_weight_applied: __________
Expected: 2.2
Match: [ ] YES [ ] NO

Weight change working: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[IMPORTANT: Set your user weight back to 1.0 in Airtable Users table]
[Restart bot]
```

---

**Summary of TC1**:
TC1 validates that the **Python application code** correctly:
- ✅ Detects missing users and shows errors
- ✅ Retrieves active users from Airtable
- ✅ Enforces business rules (active flag)
- ✅ Applies user weight in mathematical calculations

**Advantages of this approach**:
- Uses YOUR real Telegram account (no need for multiple accounts)
- Tests realistic user lifecycle: not exists → active → inactive → weight changes
- Each test builds on the previous state
- Easy to execute and verify

---

## TEST CASE 2: HABIT MANAGEMENT

**Objective**: Test the **application's habit management logic** - Does the code correctly retrieve active habits, filter inactive ones, and use habit weights in calculations?

**What We're Testing**: The Python repository/service layer for habits (`src/repositories/habit_repository.py`), NOT your Airtable data entry





```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 2: HABIT MANAGEMENT

**Objective**: Verify habits are correctly configured and selectable

---

### TC2.1: Verify All Active Habits Appear in Bot

**Preconditions**:
- All habits from mock data added to Airtable
- DEFAULT_USER_TELEGRAM_ID = 123456789
- Bot running

**Test Steps**:
1. Open Telegram bot
2. Send `/habit_done` command
3. Observe inline keyboard buttons

**Expected Results**:
- ✓ Keyboard shows exactly 6 active habits:
  - Morning Exercise
  - Reading
  - Meditation
  - Coding Practice
  - Drinking Water
  - Journaling
- ✓ "Inactive Habit Test" does NOT appear
- ✓ Buttons are clickable

**Actual Results**:
```
Habits shown:
1. ________________
2. ________________
3. ________________
4. ________________
5. ________________
6. ________________

Missing/Extra habits:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC2.2: Test Habit Weight Configuration

**Preconditions**:
- Habits exist in Airtable with different weights
- Access to Airtable

**Test Steps**:
1. Open Airtable → Habits table
2. Verify weights:
   - Morning Exercise = 2.0
   - Reading = 1.5
   - Meditation = 1.0
   - Coding Practice = 2.0
   - Drinking Water = 1.0
   - Journaling = 1.0

**Expected Results**:
- ✓ All weight values are numbers (not text)
- ✓ Higher weights (2.0) will contribute to higher total_weight in calculations

**Actual Results**:
```
All weights correct: [ ] YES [ ] NO

Discrepancies:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC2.3: Test Inactive Habit is Hidden

**Preconditions**:
- "Inactive Habit Test" exists with active=unchecked

**Test Steps**:
1. Open Telegram bot
2. Send `/habit_done`
3. Look for "Inactive Habit Test" in keyboard

**Expected Results**:
- ✓ "Inactive Habit Test" does NOT appear in keyboard
- ✓ Cannot select it

**Actual Results**:
```
Appears in keyboard: [ ] YES [ ] NO

If YES, this is a BUG




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC2.4: Test Habit Category Display

**Preconditions**:
- Habits have categories assigned
- Dashboard running

**Test Steps**:
1. Open Streamlit dashboard
2. Navigate to "Habit Logs" section
3. Complete at least one habit via bot first
4. Refresh dashboard
5. Check "Category" column in logs table

**Expected Results**:
- ✓ Category shows correct value (health/learning/wellness/productivity)
- ✓ Categories match Airtable Habits table

**Actual Results**:
```
Categories displaying correctly: [ ] YES [ ] NO

Issues:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 3: REWARD MANAGEMENT

**Objective**: Verify rewards are configured correctly with proper types and weights

---

### TC3.1: Verify All Rewards Exist in Airtable

**Preconditions**:
- Mock reward data added to Airtable

**Test Steps**:
1. Open Airtable → Rewards table
2. Verify 6 rewards exist:
   - Free Coffee (cumulative)
   - Movie Ticket (cumulative)
   - Pizza Delivery (real)
   - Virtual Badge (virtual)
   - No Reward (none)
   - Book Purchase (cumulative)

**Expected Results**:
- ✓ All 6 rewards present
- ✓ Types are exactly: cumulative/real/virtual/none (case-sensitive)
- ✓ Cumulative rewards have pieces_required filled
- ✓ Non-cumulative rewards have blank pieces_required

**Actual Results**:
```
All rewards present: [ ] YES [ ] NO

Type field issues:




Cumulative configuration issues:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC3.2: Test Reward Type Icons Display

**Preconditions**:
- Rewards exist
- Bot running

**Test Steps**:
1. Open Telegram bot
2. Send `/list_rewards` command

**Expected Results**:
- ✓ Command returns list of rewards with emojis:
  - 📦 Free Coffee (cumulative, 10 pieces)
  - 📦 Movie Ticket (cumulative, 20 pieces)
  - 🎁 Pizza Delivery (real)
  - ⭐ Virtual Badge (virtual)
  - ❌ No Reward (none)
  - 📦 Book Purchase (cumulative, 15 pieces)

**Actual Results**:
```
[Paste bot response here]











```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC3.3: Test Reward Weight Distribution

**Preconditions**:
- Rewards have different weights
- Access to Airtable

**Test Steps**:
1. Open Airtable → Rewards table
2. Note weights:
   - Free Coffee: 1.0
   - Movie Ticket: 1.0
   - Pizza Delivery: 3.0
   - Virtual Badge: 2.0
   - No Reward: 5.0
   - Book Purchase: 1.0
3. Calculate total weight: 1+1+3+2+5+1 = 13.0
4. Expected probabilities (at base total_weight=1.0):
   - Free Coffee: ~7.7%
   - Movie Ticket: ~7.7%
   - Pizza Delivery: ~23%
   - Virtual Badge: ~15.4%
   - No Reward: ~38.5%
   - Book Purchase: ~7.7%

**Expected Results**:
- ✓ "No Reward" has highest probability (~38%)
- ✓ "Pizza Delivery" second highest (~23%)
- ✓ This creates variable ratio reward schedule

**Actual Results**:
```
This is theoretical - will test empirically in TC4.5

Notes on weight configuration:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC3.4: Test Cumulative Reward Configuration

**Preconditions**:
- Cumulative rewards configured in Airtable

**Test Steps**:
1. Open Airtable → Rewards table
2. For each cumulative reward, verify:

| Reward | is_cumulative | pieces_required | piece_value |
|--------|---------------|-----------------|-------------|
| Free Coffee | ✓ | 10 | 5.00 |
| Movie Ticket | ✓ | 20 | 10.00 |
| Book Purchase | ✓ | 15 | 8.00 |

**Expected Results**:
- ✓ All three have is_cumulative checked
- ✓ pieces_required is number (not text)
- ✓ piece_value is number (can have decimals)

**Actual Results**:
```
Configuration correct: [ ] YES [ ] NO

Issues:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 4: BASIC HABIT COMPLETION FLOW

**Objective**: Test end-to-end habit logging with reward selection

---

### TC4.1: First-Time Habit Completion

**Preconditions**:
- DEFAULT_USER_TELEGRAM_ID = 123456789
- Habit Log table is EMPTY for Test User
- Bot running

**Test Steps**:
1. Clear any existing logs for Test User in Habit Log table (if any)
2. Open Telegram bot
3. Send `/habit_done`
4. Click "Morning Exercise" from keyboard
5. Observe bot response
6. Open Airtable → Habit Log table
7. Find new entry

**Expected Results**:
- ✓ Bot confirms: "Great job! You completed 'Morning Exercise'"
- ✓ Shows streak: "🔥 Streak: 1 day"
- ✓ Shows reward received (or "No reward this time")
- ✓ Habit Log entry created with:
  - user_id = Test User's record ID
  - habit_id = Morning Exercise record ID
  - streak_count = 1
  - timestamp = current date/time
  - got_reward = true/false (depending on random selection)
  - reward_id = selected reward's record ID

**Actual Results**:
```
Bot response:







Habit Log entry created: [ ] YES [ ] NO

streak_count value: __________
Expected: 1
Match: [ ] YES [ ] NO

Field verification:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC4.2: Same Habit, Same Day (No Streak Increment)

**Preconditions**:
- TC4.1 completed successfully
- Same day as TC4.1

**Test Steps**:
1. Immediately after TC4.1, send `/habit_done` again
2. Select "Morning Exercise" again
3. Observe bot response
4. Check Habit Log table for new entry

**Expected Results**:
- ✓ Bot confirms habit completion
- ✓ Streak STILL shows "🔥 Streak: 1 day" (not incremented)
- ✓ New log entry created
- ✓ New entry also has streak_count = 1
- ✓ Both entries have same last_completed_date (today)

**Actual Results**:
```
Streak shown in bot: __________
Expected: 1

New log entry streak_count: __________
Expected: 1

Same-day duplicate handling: [ ] CORRECT [ ] INCORRECT

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC4.3: Different Habit, Same Day

**Preconditions**:
- TC4.1 and TC4.2 completed
- Same day
- Bot running

**Test Steps**:
1. Send `/habit_done`
2. Select "Reading" (different habit)
3. Observe bot response
4. Check Habit Log table

**Expected Results**:
- ✓ Bot confirms "Reading" completion
- ✓ Streak shows "🔥 Streak: 1 day" (first time for this habit)
- ✓ New log entry for Reading habit
- ✓ Morning Exercise logs unchanged

**Actual Results**:
```
Reading streak: __________
Expected: 1

Separate streak tracking confirmed: [ ] YES [ ] NO

Total log entries now: __________
Expected: 3 (2 Morning Exercise + 1 Reading)




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC4.4: Verify Reward Assignment

**Preconditions**:
- At least one habit completed (TC4.1)

**Test Steps**:
1. Open Airtable → Habit Log table
2. Find entry from TC4.1
3. Check `reward_id` field
4. Click linked reward to see which reward was assigned
5. Check `got_reward` field

**Expected Results**:
- ✓ reward_id links to one of the 6 rewards
- ✓ If reward type = "none": got_reward = false
- ✓ If reward type = real/virtual/cumulative: got_reward = true

**Actual Results**:
```
Reward assigned: ________________

Reward type: ________________

got_reward value: [ ] true [ ] false

Logic correct: [ ] YES [ ] NO




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC4.5: Multiple Completions to Test Reward Distribution

**Preconditions**:
- Bot running
- Clean start recommended (clear previous logs or use spreadsheet to track)

**Test Steps**:
1. Complete "Meditation" habit 20 times (you can script this or manual)
2. After each completion, note which reward was given
3. Tally results

**Expected Results**:
- ✓ "No Reward" appears most frequently (~30-50% of time)
- ✓ All reward types appear at least once in 20 completions
- ✓ Distribution roughly matches weight ratios
- ✓ Cumulative rewards increment piece count

**Actual Results**:
```
Track your results here:

Completion # | Reward Given | Type | Got Reward?
-------------|--------------|------|------------
1            |              |      |
2            |              |      |
3            |              |      |
4            |              |      |
5            |              |      |
6            |              |      |
7            |              |      |
8            |              |      |
9            |              |      |
10           |              |      |
11           |              |      |
12           |              |      |
13           |              |      |
14           |              |      |
15           |              |      |
16           |              |      |
17           |              |      |
18           |              |      |
19           |              |      |
20           |              |      |

Summary:
- No Reward: ____ / 20 (____ %)
- Pizza Delivery: ____ / 20 (____ %)
- Virtual Badge: ____ / 20 (____ %)
- Free Coffee: ____ / 20 (____ %)
- Movie Ticket: ____ / 20 (____ %)
- Book Purchase: ____ / 20 (____ %)

Distribution looks reasonable: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 5: STREAK CALCULATION LOGIC

**Objective**: Verify per-habit streak tracking across different time scenarios

---

### TC5.1: Consecutive Day Streak Increment

**Preconditions**:
- Habit completed yesterday (you'll need to manually set last_completed_date in Airtable OR wait until next day)
- Bot running

**Test Steps**:

**Option A (Manual Date Manipulation)**:
1. Complete "Coding Practice" habit today
2. Open Airtable → Habit Log table
3. Find the entry you just created
4. Manually change `last_completed_date` to YESTERDAY's date
5. Change `timestamp` to yesterday as well
6. Restart bot (important for cache clearing)
7. Send `/habit_done` → select "Coding Practice" again
8. Observe streak in bot response

**Option B (Wait Until Next Day)**:
1. Complete "Coding Practice" habit today
2. Note the time
3. Wait until tomorrow (next calendar day)
4. Complete "Coding Practice" again
5. Observe streak

**Expected Results**:
- ✓ First completion: Streak = 1
- ✓ Next day completion: Streak = 2
- ✓ Streak increments by exactly 1
- ✓ Habit Log shows streak_count = 2 for second entry

**Actual Results**:
```
Method used: [ ] Option A [ ] Option B

First completion date: __________
First streak: __________

Second completion date: __________
Second streak: __________

Streak incremented correctly: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC5.2: Streak Resets After Missing a Day

**Preconditions**:
- A habit with streak ≥ 2 exists (from TC5.1)

**Test Steps**:
1. Find a Habit Log entry with streak_count ≥ 2
2. Note the habit_id
3. Manually change `last_completed_date` to 3 days ago
4. Restart bot
5. Complete that same habit today
6. Check streak in bot response

**Expected Results**:
- ✓ Streak resets to 1 (not 3)
- ✓ Bot shows "🔥 Streak: 1 day"
- ✓ New log entry has streak_count = 1

**Actual Results**:
```
Previous streak: __________
Days skipped: __________

New streak after gap: __________
Expected: 1

Streak reset correctly: [ ] YES [ ] NO




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC5.3: Verify Streak Multiplier Calculation

**Preconditions**:
- Can create habit with specific streak
- STREAK_MULTIPLIER_RATE = 0.1 (default)

**Test Steps**:
1. Complete a habit to establish streak = 1
2. Check Habit Log → `total_weight_applied`
3. Calculate: habit_weight × user_weight × (1 + 1 × 0.1) = expected
4. Repeat for streak = 5 (manipulate date to create)
5. Calculate: habit_weight × user_weight × (1 + 5 × 0.1) = expected

**Expected Results**:
- ✓ Streak 1: multiplier = 1.1
- ✓ Streak 5: multiplier = 1.5
- ✓ Streak 10: multiplier = 2.0
- ✓ total_weight_applied matches formula

**Actual Results**:
```
Test Case: Habit "Meditation" (weight 1.0), User weight 1.0

Streak | Expected Multiplier | Expected Total Weight | Actual Total Weight | Match?
-------|--------------------|-----------------------|---------------------|-------
1      | 1.1                | 1.1                   |                     |
5      | 1.5                | 1.5                   |                     |
10     | 2.0                | 2.0                   |                     |

All calculations correct: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC5.4: Independent Streak Tracking Per Habit

**Preconditions**:
- Multiple habits available
- Clean state or tracking sheet

**Test Steps**:
1. Day 1: Complete "Morning Exercise" (streak = 1)
2. Day 1: Complete "Reading" (streak = 1)
3. Day 2: Complete ONLY "Morning Exercise" (should be streak = 2)
4. Day 2: Do NOT complete "Reading"
5. Day 3: Complete "Morning Exercise" (should be streak = 3)
6. Day 3: Complete "Reading" (should be streak = 1, reset)
7. Check `/streaks` command output

**Expected Results**:
- ✓ Morning Exercise shows streak = 3
- ✓ Reading shows streak = 1 (reset because skipped Day 2)
- ✓ Streaks are independent per habit

**Actual Results**:
```
/streaks command output:









Independent tracking confirmed: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC5.5: Streak Display in /streaks Command

**Preconditions**:
- At least 3 habits completed with different streaks

**Test Steps**:
1. Create varied streaks (e.g., one habit streak 5, another streak 2, another streak 1)
2. Send `/streaks` command in Telegram
3. Observe output format and sorting

**Expected Results**:
- ✓ Shows all habits with current streaks
- ✓ Sorted by streak count (highest first)
- ✓ Shows fire emoji (🔥) - count increases with streak (max 5 emojis)
- ✓ Format: "Habit Name: X days 🔥🔥🔥"

**Actual Results**:
```
[Paste /streaks output here]











Sorted correctly: [ ] YES [ ] NO
Fire emoji display correct: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 6: WEIGHT CALCULATION & MULTIPLIERS

**Objective**: Verify total weight formula: habit_weight × user_weight × streak_multiplier

---

### TC6.1: Base Weight Calculation (Streak = 1)

**Preconditions**:
- Test User (weight 1.0)
- Fresh habit completion (streak = 1)

**Test Steps**:
1. Complete "Morning Exercise" (weight 2.0) for first time
2. Open Airtable → Habit Log
3. Find entry and check fields:
   - habit_weight
   - total_weight_applied
4. Calculate expected: 2.0 × 1.0 × 1.1 = 2.2

**Expected Results**:
- ✓ habit_weight = 2.0
- ✓ total_weight_applied = 2.2

**Actual Results**:
```
habit_weight: __________
total_weight_applied: __________
Expected: 2.2

Match: [ ] YES [ ] NO

Calculation correct: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC6.2: High Streak Weight Boost

**Preconditions**:
- Ability to create streak = 10 (manual date manipulation)

**Test Steps**:
1. Complete "Meditation" (weight 1.0) and manipulate to create streak = 10
2. Complete habit again
3. Check total_weight_applied
4. Expected: 1.0 × 1.0 × (1 + 10 × 0.1) = 1.0 × 1.0 × 2.0 = 2.0

**Expected Results**:
- ✓ total_weight_applied = 2.0
- ✓ Streak 10 doubles the base weight

**Actual Results**:
```
total_weight_applied: __________
Expected: 2.0

Doubling effect confirmed: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC6.3: Power User Weight Multiplier

**Preconditions**:
- Switch to "Power User" (telegram_id 987654321, weight 2.0)

**Test Steps**:
1. Change .env DEFAULT_USER_TELEGRAM_ID = 987654321
2. Restart bot
3. Complete "Coding Practice" (weight 2.0) for first time (streak = 1)
4. Check total_weight_applied
5. Expected: 2.0 × 2.0 × 1.1 = 4.4

**Expected Results**:
- ✓ total_weight_applied = 4.4
- ✓ User weight of 2.0 doubles the result

**Actual Results**:
```
total_weight_applied: __________
Expected: 4.4

Match: [ ] YES [ ] NO

Power User multiplier working: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC6.4: Combined High Weights Scenario

**Preconditions**:
- Power User (weight 2.0)
- High-weight habit
- High streak

**Test Steps**:
1. Using Power User (weight 2.0)
2. Complete "Morning Exercise" (weight 2.0)
3. Manipulate to create streak = 5
4. Complete habit again
5. Expected: 2.0 × 2.0 × (1 + 5 × 0.1) = 2.0 × 2.0 × 1.5 = 6.0

**Expected Results**:
- ✓ total_weight_applied = 6.0
- ✓ All multipliers combine correctly

**Actual Results**:
```
total_weight_applied: __________
Expected: 6.0

Combined multipliers correct: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Reminder: Set .env back to DEFAULT_USER_TELEGRAM_ID=123456789]
```

---

## TEST CASE 7: CUMULATIVE REWARDS SYSTEM

**Objective**: Test piece accumulation and reward achievement

---

### TC7.1: First Cumulative Reward Piece Awarded

**Preconditions**:
- Cumulative rewards configured
- Reward Progress table EMPTY for Test User
- Bot running

**Test Steps**:
1. Complete any habit 20 times (to ensure hitting cumulative rewards through randomness)
2. During completions, watch for message: "You earned 1 piece toward 'Free Coffee'!" (or similar)
3. When you see cumulative reward message, open Airtable → Reward Progress table
4. Find entry for (Test User, Free Coffee)

**Expected Results**:
- ✓ Bot message confirms piece awarded
- ✓ Reward Progress entry created with:
  - user_id = Test User record ID
  - reward_id = Free Coffee record ID
  - pieces_earned = 1
  - pieces_required = 10
  - status = "🕒 Pending"
  - actionable_now = false

**Actual Results**:
```
Bot message received: [ ] YES [ ] NO

Message text:




Reward Progress entry created: [ ] YES [ ] NO

pieces_earned: __________
status: __________
actionable_now: [ ] true [ ] false

All correct: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.2: Accumulating Multiple Pieces

**Preconditions**:
- TC7.1 completed (1 piece earned)

**Test Steps**:
1. Continue completing habits until Free Coffee piece count increases
2. After each piece, check Reward Progress table
3. Observe pieces_earned incrementing: 1 → 2 → 3 → ... → 9

**Expected Results**:
- ✓ Each piece increments pieces_earned by 1
- ✓ status remains "🕒 Pending" while < 10 pieces
- ✓ actionable_now remains false
- ✓ Progress shown in bot: "You have X/10 pieces"

**Actual Results**:
```
Track progress:

Completion # | Pieces Earned | Status | Actionable Now
-------------|---------------|--------|---------------
[Start]      | 1             |        |
             |               |        |
             |               |        |
             |               |        |
             |               |        |
[Before 10]  | 9             |        |

All increments correct: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.3: Achieving Cumulative Reward (10 Pieces)

**Preconditions**:
- Free Coffee has 9 pieces earned

**Test Steps**:
1. Continue completing habits until Free Coffee is awarded again
2. Watch bot message when 10th piece is earned
3. Immediately check Reward Progress table

**Expected Results**:
- ✓ Bot message: "🎉 You've earned enough pieces for 'Free Coffee'! It's ready to claim!"
- ✓ Reward Progress entry updated:
  - pieces_earned = 10 (or more if random gave extra)
  - status = "⏳ Achieved"
  - actionable_now = true

**Actual Results**:
```
Bot message:




pieces_earned: __________
status: __________
actionable_now: [ ] true [ ] false

Achievement triggered correctly: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.4: Achieved Reward Shows in /my_rewards

**Preconditions**:
- Free Coffee status = "⏳ Achieved"

**Test Steps**:
1. Send `/my_rewards` command in Telegram
2. Observe output

**Expected Results**:
- ✓ Free Coffee appears in list
- ✓ Shows status: "⏳ Achieved (Ready to claim!)"
- ✓ Shows pieces: "10/10 pieces"

**Actual Results**:
```
[Paste /my_rewards output here]







Free Coffee shown as achieved: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.5: Claiming Achieved Reward

**Preconditions**:
- Free Coffee status = "⏳ Achieved"

**Test Steps**:
1. Send `/claim_reward Free Coffee` in Telegram
2. Observe bot response
3. Check Reward Progress table

**Expected Results**:
- ✓ Bot confirms: "Congratulations! You've claimed your 'Free Coffee' reward!"
- ✓ Reward Progress updated:
  - status = "✅ Completed"
  - actionable_now = false
  - pieces_earned remains 10 (doesn't reset)

**Actual Results**:
```
Bot response:




status after claim: __________
actionable_now after claim: [ ] true [ ] false

Claim successful: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.6: Cannot Claim Already Completed Reward

**Preconditions**:
- Free Coffee status = "✅ Completed"

**Test Steps**:
1. Send `/claim_reward Free Coffee` again
2. Observe bot response

**Expected Results**:
- ✓ Bot responds with error: "This reward is not ready to claim" or "Already claimed"
- ✓ No changes to Reward Progress table

**Actual Results**:
```
Bot response:




Prevented duplicate claim: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.7: Multiple Cumulative Rewards in Progress

**Preconditions**:
- At least 2 cumulative rewards configured (Free Coffee, Movie Ticket, Book Purchase)

**Test Steps**:
1. Complete habits until you have pieces in all three cumulative rewards
2. Target state:
   - Free Coffee: 5/10 pieces (🕒 Pending)
   - Movie Ticket: 3/20 pieces (🕒 Pending)
   - Book Purchase: 15/15 pieces (⏳ Achieved)
3. Send `/my_rewards` command

**Expected Results**:
- ✓ Shows all three rewards
- ✓ Correct status emojis for each
- ✓ Correct piece counts
- ✓ Only Book Purchase shows "Ready to claim"

**Actual Results**:
```
[Paste /my_rewards output here]











All rewards showing correctly: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC7.8: Continuing to Earn Pieces After Achievement

**Preconditions**:
- One cumulative reward is "⏳ Achieved" but not yet claimed

**Test Steps**:
1. Have Free Coffee at exactly 10/10 pieces, status "⏳ Achieved"
2. Complete habits until Free Coffee is randomly awarded again
3. Check pieces_earned

**Expected Results**:
- ✓ pieces_earned increments to 11 (allows over-achievement)
- ✓ status remains "⏳ Achieved"
- ✓ Can still claim with /claim_reward

**Actual Results**:
```
pieces_earned after additional award: __________

Over-achievement allowed: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 8: REWARD STATUS LIFECYCLE

**Objective**: Verify status transitions: 🕒 Pending → ⏳ Achieved → ✅ Completed

---

### TC8.1: Pending Status Initial State

**Preconditions**:
- Fresh cumulative reward with 0 pieces

**Test Steps**:
1. Note a cumulative reward you haven't earned yet (e.g., "Movie Ticket")
2. Complete habits until Movie Ticket is awarded for the first time
3. Check Reward Progress table

**Expected Results**:
- ✓ New entry created on first award
- ✓ Initial status = "🕒 Pending"
- ✓ actionable_now = false
- ✓ pieces_earned = 1
- ✓ pieces_required = 20

**Actual Results**:
```
Entry created on first piece: [ ] YES [ ] NO

Initial status: __________
Expected: 🕒 Pending

Initial actionable_now: [ ] true [ ] false
Expected: false

Correct initial state: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC8.2: Pending → Achieved Transition

**Preconditions**:
- Movie Ticket at 19/20 pieces

**Test Steps**:
1. Ensure Movie Ticket has exactly 19 pieces
2. Complete habits until Movie Ticket awarded again (to hit 20)
3. Immediately check Reward Progress table

**Expected Results**:
- ✓ status changes from "🕒 Pending" to "⏳ Achieved"
- ✓ actionable_now changes from false to true
- ✓ Bot message includes celebration/notification

**Actual Results**:
```
Status before: __________
Status after: __________

actionable_now before: __________
actionable_now after: __________

Transition correct: [ ] YES [ ] NO

Bot notification received: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC8.3: Achieved → Completed Transition

**Preconditions**:
- Movie Ticket status = "⏳ Achieved"

**Test Steps**:
1. Verify Movie Ticket is in "⏳ Achieved" state
2. Send `/claim_reward Movie Ticket`
3. Check Reward Progress table

**Expected Results**:
- ✓ status changes from "⏳ Achieved" to "✅ Completed"
- ✓ actionable_now changes from true to false
- ✓ pieces_earned remains unchanged (doesn't reset)

**Actual Results**:
```
Status before claim: __________
Status after claim: __________

actionable_now before claim: __________
actionable_now after claim: __________

pieces_earned before: __________
pieces_earned after: __________

Transition correct: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC8.4: Manual Status Reset (Admin Function)

**Preconditions**:
- Movie Ticket status = "✅ Completed"
- Bot has /set_reward_status command

**Test Steps**:
1. Send `/set_reward_status Movie Ticket pending` in Telegram
2. Check Reward Progress table
3. Check /my_rewards output

**Expected Results**:
- ✓ status changes to "🕒 Pending"
- ✓ actionable_now = false
- ✓ pieces_earned MAY reset to 0 (depending on implementation)
- ✓ Bot confirms change

**Actual Results**:
```
Bot response:




Status after reset: __________
actionable_now: __________
pieces_earned: __________

Manual reset working: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC8.5: Dashboard Reflects Status Correctly

**Preconditions**:
- Rewards in all three states exist:
  - Free Coffee: 🕒 Pending
  - Movie Ticket: ⏳ Achieved
  - Book Purchase: ✅ Completed

**Test Steps**:
1. Open Streamlit dashboard
2. Navigate to Reward Progress section
3. Observe status grouping/tabs

**Expected Results**:
- ✓ Rewards grouped by status into tabs/sections
- ✓ Pending tab shows Free Coffee
- ✓ Achieved tab shows Movie Ticket (with "Claim" button)
- ✓ Completed tab shows Book Purchase
- ✓ Progress bars show correct percentages

**Actual Results**:
```
Dashboard displays three status groups: [ ] YES [ ] NO

Pending section correct: [ ] YES [ ] NO
Achieved section correct: [ ] YES [ ] NO
Completed section correct: [ ] YES [ ] NO

Visual layout:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 9: TELEGRAM BOT COMMANDS

**Objective**: Test all bot commands and interactions

---

### TC9.1: /start Command

**Preconditions**:
- Bot running
- User exists in Airtable

**Test Steps**:
1. Open Telegram bot
2. Send `/start` command

**Expected Results**:
- ✓ Bot responds with welcome message
- ✓ Message includes user's name or telegram_id
- ✓ Message lists available commands
- ✓ Friendly/encouraging tone

**Actual Results**:
```
[Paste /start response here]











Welcome message appropriate: [ ] YES [ ] NO
Lists commands: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.2: /help Command

**Preconditions**:
- Bot running

**Test Steps**:
1. Send `/help` command

**Expected Results**:
- ✓ Shows detailed help text
- ✓ Lists and explains each command:
  - /habit_done
  - /streaks
  - /list_rewards
  - /my_rewards
  - /claim_reward
  - /set_reward_status (if admin)
- ✓ Includes usage examples

**Actual Results**:
```
[Paste /help response here]

















All commands documented: [ ] YES [ ] NO
Examples provided: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.3: /habit_done with Inline Keyboard

**Preconditions**:
- At least 3 active habits exist

**Test Steps**:
1. Send `/habit_done`
2. Observe inline keyboard
3. Click one habit button
4. Observe response

**Expected Results**:
- ✓ Keyboard appears with all active habits
- ✓ Buttons are clickable
- ✓ After clicking, keyboard disappears
- ✓ Bot confirms habit completion
- ✓ Shows streak and reward info

**Actual Results**:
```
Keyboard displayed: [ ] YES [ ] NO
Number of buttons: __________

Button clicked: __________
Response time: __________

Confirmation received: [ ] YES [ ] NO
Streak shown: [ ] YES [ ] NO
Reward shown: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.4: /streaks Command

**Preconditions**:
- At least 3 habits completed with different streaks

**Test Steps**:
1. Send `/streaks`
2. Observe output

**Expected Results**:
- ✓ Lists all habits user has completed at least once
- ✓ Shows current streak for each
- ✓ Sorted by streak count (highest first)
- ✓ Includes fire emoji (🔥) visualization
- ✓ Format readable and clear

**Actual Results**:
```
[Paste /streaks output here]











Sorted correctly: [ ] YES [ ] NO
Fire emoji count increases with streak: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.5: /list_rewards Command

**Preconditions**:
- All 6 mock rewards exist in Airtable

**Test Steps**:
1. Send `/list_rewards`

**Expected Results**:
- ✓ Shows all active rewards
- ✓ Each reward has correct type emoji:
  - 📦 for cumulative
  - 🎁 for real
  - ⭐ for virtual
  - ❌ for none
- ✓ Cumulative rewards show pieces_required
- ✓ Non-cumulative don't show pieces

**Actual Results**:
```
[Paste /list_rewards output here]













All 6 rewards shown: [ ] YES [ ] NO
Type emojis correct: [ ] YES [ ] NO
Cumulative pieces shown: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.6: /my_rewards Command

**Preconditions**:
- User has progress on at least 2 cumulative rewards

**Test Steps**:
1. Send `/my_rewards`

**Expected Results**:
- ✓ Shows only rewards user has progress on
- ✓ Shows current status for each (🕒/⏳/✅)
- ✓ Shows piece count (X/Y pieces)
- ✓ Indicates which are ready to claim
- ✓ If no progress, says "No rewards in progress"

**Actual Results**:
```
[Paste /my_rewards output here]











Shows correct rewards: [ ] YES [ ] NO
Status emojis correct: [ ] YES [ ] NO
Piece counts accurate: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.7: /claim_reward Command (Success Case)

**Preconditions**:
- At least one reward in "⏳ Achieved" status

**Test Steps**:
1. Identify achieved reward (e.g., "Free Coffee")
2. Send `/claim_reward Free Coffee`

**Expected Results**:
- ✓ Bot confirms claim: "Congratulations! You've claimed..."
- ✓ Reward status changes to "✅ Completed"
- ✓ actionable_now becomes false

**Actual Results**:
```
Command sent: /claim_reward Free Coffee

Bot response:




Status changed to Completed: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.8: /claim_reward Command (Error Cases)

**Preconditions**:
- Various reward states exist

**Test Steps**:
1. Try to claim a "🕒 Pending" reward: `/claim_reward Movie Ticket` (if pending)
2. Try to claim a "✅ Completed" reward: `/claim_reward Free Coffee` (if completed)
3. Try to claim a non-existent reward: `/claim_reward Fake Reward`

**Expected Results**:
- ✓ Pending reward: "This reward is not ready to claim yet"
- ✓ Completed reward: "This reward has already been claimed"
- ✓ Non-existent: "Reward not found" or similar error

**Actual Results**:
```
Test 1 (Pending) - Bot response:




Test 2 (Completed) - Bot response:




Test 3 (Non-existent) - Bot response:




All error messages appropriate: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC9.9: Unknown Command Handling

**Preconditions**:
- Bot running

**Test Steps**:
1. Send `/unknown_command`
2. Send random text: "hello bot"

**Expected Results**:
- ✓ Bot responds with helpful message
- ✓ Suggests using /help
- ✓ Doesn't crash or give error stack trace

**Actual Results**:
```
Response to /unknown_command:




Response to "hello bot":




Graceful handling: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 10: NLP HABIT CLASSIFICATION

**Objective**: Test OpenAI integration for custom habit text matching

---

### TC10.1: Basic Custom Text Classification

**Preconditions**:
- OpenAI API key configured
- Bot running
- Habits: "Morning Exercise", "Reading", "Meditation" exist

**Test Steps**:
1. Send `/habit_done`
2. Instead of clicking a button, type: "I went for a run today"
3. Observe bot response

**Expected Results**:
- ✓ Bot processes text with OpenAI
- ✓ Matches to "Morning Exercise" habit
- ✓ Confirms: "Matched to 'Morning Exercise'"
- ✓ Logs habit completion for Morning Exercise

**Actual Results**:
```
Text sent: "I went for a run today"

Bot response:




Matched habit: __________
Expected: Morning Exercise

Correct match: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC10.2: Multiple Possible Matches

**Preconditions**:
- Habits include both "Reading" and "Coding Practice"

**Test Steps**:
1. Send `/habit_done`
2. Type: "I read a programming book"

**Expected Results**:
- ✓ Bot identifies potential matches: Reading AND Coding Practice
- ✓ Selects one (likely Reading due to explicit "read")
- ✓ MAY notify user of alternative match
- ✓ Logs the selected habit

**Actual Results**:
```
Text sent: "I read a programming book"

Bot response:




Matched to: __________

Alternative suggested: [ ] YES [ ] NO

Reasonable match: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC10.3: No Clear Match

**Preconditions**:
- Existing habits don't cover certain activities

**Test Steps**:
1. Send `/habit_done`
2. Type: "I cooked a gourmet meal"

**Expected Results**:
- ✓ Bot responds: "Couldn't match your text to any habit"
- ✓ Suggests using the habit selection keyboard
- ✓ No habit logged

**Actual Results**:
```
Text sent: "I cooked a gourmet meal"

Bot response:




Handled gracefully: [ ] YES [ ] NO
Suggested keyboard: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC10.4: Partial/Misspelled Text

**Preconditions**:
- Habit "Meditation" exists

**Test Steps**:
1. Send `/habit_done`
2. Type: "meditated" (lowercase, verb form)

**Expected Results**:
- ✓ OpenAI understands semantic similarity
- ✓ Matches to "Meditation" habit
- ✓ Confirms match

**Actual Results**:
```
Text sent: "meditated"

Bot response:




Matched correctly: [ ] YES [ ] NO

Notes on NLP robustness:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC10.5: OpenAI API Failure Handling

**Preconditions**:
- Can simulate API failure (temporarily set wrong API key or disable internet)

**Test Steps**:
1. Temporarily invalidate OpenAI API key in .env
2. Restart bot
3. Send `/habit_done`
4. Type custom text: "went for a walk"
5. Observe error handling

**Expected Results**:
- ✓ Bot doesn't crash
- ✓ Shows user-friendly error: "Unable to process custom text right now"
- ✓ Suggests using keyboard selection
- ✓ Logs error (check console)

**Actual Results**:
```
Bot response:




User-friendly error: [ ] YES [ ] NO
Crash: [ ] YES [ ] NO

Error logged in console: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Reminder: Restore valid OpenAI API key in .env]
```

---

## TEST CASE 11: DASHBOARD FUNCTIONALITY

**Objective**: Test Streamlit dashboard visual components and interactions

---

### TC11.1: Dashboard Loads Successfully

**Preconditions**:
- Dashboard running: `streamlit run src/dashboard/app.py`
- Browser access to localhost

**Test Steps**:
1. Open browser to dashboard URL (usually http://localhost:8501)
2. Observe initial load

**Expected Results**:
- ✓ Dashboard loads without errors
- ✓ Shows title: "Habit Reward System Dashboard" (or similar)
- ✓ All components visible:
  - Stats overview
  - Reward progress cards
  - Streak chart
  - Habit logs table

**Actual Results**:
```
Dashboard loads: [ ] YES [ ] NO

Load time: __________ seconds

All components visible: [ ] YES [ ] NO

Errors in browser console: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.2: Stats Overview Component

**Preconditions**:
- User has some habit completions and reward progress

**Test Steps**:
1. In dashboard, locate Stats Overview section
2. Note displayed metrics:
   - Total Earned Value
   - Claimed Value
   - Pending Pieces
   - Completion Rate

**Expected Results**:
- ✓ All 4 metrics display numeric values
- ✓ Values are non-negative
- ✓ Completion Rate is percentage (0-100%)
- ✓ Metrics update when data changes

**Actual Results**:
```
Metrics displayed:

Total Earned Value: __________
Claimed Value: __________
Pending Pieces: __________
Completion Rate: __________ %

All metrics reasonable: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.3: Reward Progress Cards Display

**Preconditions**:
- User has rewards in all three states (Pending, Achieved, Completed)

**Test Steps**:
1. Navigate to Reward Progress section
2. Check if rewards are grouped by status
3. Click through tabs/sections

**Expected Results**:
- ✓ Three sections/tabs: 🕒 Pending, ⏳ Achieved, ✅ Completed
- ✓ Each reward shows:
  - Name
  - Progress bar
  - Pieces X/Y
  - Status emoji
- ✓ Progress bars visually represent percentage

**Actual Results**:
```
Three status groups exist: [ ] YES [ ] NO

Pending rewards count: __________
Achieved rewards count: __________
Completed rewards count: __________

Progress bars showing correctly: [ ] YES [ ] NO

Example card details:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.4: Actionable Rewards Section

**Preconditions**:
- At least one reward in "⏳ Achieved" status

**Test Steps**:
1. Find "Actionable Rewards" section (may be highlighted/top of page)
2. Observe displayed rewards

**Expected Results**:
- ✓ Shows only "⏳ Achieved" rewards
- ✓ Each has "Claim Now" button or similar
- ✓ Clicking button calls claim function
- ✓ After claim, reward moves to Completed section

**Actual Results**:
```
Actionable section exists: [ ] YES [ ] NO

Achieved rewards shown: __________

"Claim" button present: [ ] YES [ ] NO

Test claim functionality:
  Reward claimed: __________
  Button clicked: [ ] YES [ ] NO
  Status updated: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.5: Streak Chart Visualization

**Preconditions**:
- User has completed multiple habits with varying streaks

**Test Steps**:
1. Locate Streak Chart (likely a bar chart)
2. Observe visualization

**Expected Results**:
- ✓ Chart shows all habits with current streaks
- ✓ X-axis: habit names
- ✓ Y-axis: streak count
- ✓ Bars sorted by streak (descending)
- ✓ Color coding or labels clear

**Actual Results**:
```
Chart displays: [ ] YES [ ] NO

Chart type: [ ] Bar [ ] Line [ ] Other: __________

Sorted correctly: [ ] YES [ ] NO

Visual clarity (1-5): __________

Screenshot attached: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.6: Habit Logs Table

**Preconditions**:
- User has at least 10 habit completions logged

**Test Steps**:
1. Scroll to Habit Logs section
2. Observe table

**Expected Results**:
- ✓ Shows recent habit completions (default: last 50)
- ✓ Columns: Date, Habit Name, Streak, Reward, Category
- ✓ Sorted by date (newest first)
- ✓ Streak shows fire emoji (🔥)
- ✓ Reward column shows Y/N or reward name

**Actual Results**:
```
Table displays: [ ] YES [ ] NO

Number of rows shown: __________

Columns present:
  [ ] Date
  [ ] Habit Name
  [ ] Streak
  [ ] Reward
  [ ] Category

Sorted newest first: [ ] YES [ ] NO

Data matches Airtable Habit Log: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.7: Dashboard Refresh/Real-time Update

**Preconditions**:
- Dashboard open in browser
- Bot running in Telegram

**Test Steps**:
1. Keep dashboard open
2. Complete a habit via Telegram bot
3. Return to dashboard and refresh page
4. Observe if new data appears

**Expected Results**:
- ✓ After refresh, new habit completion appears in logs
- ✓ Streak chart updates if streak changed
- ✓ Stats overview updates
- ✓ Reward progress updates if cumulative piece earned

**Actual Results**:
```
Completed habit via bot: __________
Timestamp: __________

Dashboard refreshed: [ ] YES [ ] NO

New entry in logs: [ ] YES [ ] NO
Streak chart updated: [ ] YES [ ] NO
Stats updated: [ ] YES [ ] NO
Reward progress updated: [ ] YES [ ] NO

Real-time data sync working: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC11.8: Dashboard with No Data

**Preconditions**:
- Create a new user with no habit completions (or use .env to switch to new user)

**Test Steps**:
1. Change DEFAULT_USER_TELEGRAM_ID to new user (e.g., 999888777)
2. Ensure this user has NO logs, NO rewards
3. Restart dashboard
4. Observe empty state handling

**Expected Results**:
- ✓ Dashboard loads without errors
- ✓ Shows "No data" messages or empty states gracefully
- ✓ No crashes or stack traces
- ✓ Suggests completing habits to see data

**Actual Results**:
```
Dashboard loads with no data: [ ] YES [ ] NO

Empty state messages shown: [ ] YES [ ] NO

Any errors: [ ] YES [ ] NO

User experience with no data (1-5): __________

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 12: EDGE CASES & ERROR HANDLING

**Objective**: Test system behavior under unusual conditions

---

### TC12.1: User Not Found Error

**Preconditions**:
- Bot running

**Test Steps**:
1. Change .env DEFAULT_USER_TELEGRAM_ID to non-existent ID: `000000000`
2. Restart bot
3. Send `/habit_done` command

**Expected Results**:
- ✓ Bot responds with error: "User not found. Please contact admin."
- ✓ No habit logged
- ✓ No crash

**Actual Results**:
```
Bot response:




Error handled gracefully: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Set .env back to valid user ID: 123456789]
```

---

### TC12.2: Habit Not Found Error

**Preconditions**:
- All habits are inactive OR habit deleted from Airtable

**Test Steps**:
1. Deactivate all habits in Airtable (uncheck "active")
2. Restart bot
3. Send `/habit_done`

**Expected Results**:
- ✓ Bot responds: "No active habits available" or shows empty keyboard
- ✓ No crash

**Actual Results**:
```
Bot response:




Handled gracefully: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Reactivate all habits]
```

---

### TC12.3: No Active Rewards

**Preconditions**:
- All rewards deactivated OR all deleted

**Test Steps**:
1. Delete all rewards from Airtable Rewards table (or mark all inactive if field exists)
2. Restart bot
3. Complete a habit

**Expected Results**:
- ✓ Bot allows habit completion
- ✓ Shows message: "No reward this time" or similar
- ✓ Habit logged with null reward_id
- ✓ No crash

**Actual Results**:
```
Habit completion allowed: [ ] YES [ ] NO

Bot message:




Reward logged as null: [ ] YES [ ] NO

System continues functioning: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Re-add all 6 mock rewards]
```

---

### TC12.4: Extremely High Streak (100 days)

**Preconditions**:
- Ability to manually edit Habit Log

**Test Steps**:
1. Complete a habit once
2. Manually edit Habit Log entry:
   - Set streak_count = 100
   - Set last_completed_date = yesterday
3. Restart bot
4. Complete same habit again today

**Expected Results**:
- ✓ New streak = 101
- ✓ Streak multiplier = 1 + (101 × 0.1) = 11.1
- ✓ total_weight_applied = habit_weight × user_weight × 11.1
- ✓ Very high reward probability
- ✓ No overflow errors

**Actual Results**:
```
New streak: __________
Expected: 101

total_weight_applied: __________

No errors: [ ] YES [ ] NO

System handles high streaks: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC12.5: Concurrent Habit Completions

**Preconditions**:
- Can send multiple bot commands rapidly

**Test Steps**:
1. Send `/habit_done` → select habit A
2. IMMEDIATELY send `/habit_done` again → select habit B (within 1 second)
3. Check Habit Log table

**Expected Results**:
- ✓ Both habits logged correctly
- ✓ No race conditions
- ✓ Separate log entries
- ✓ Correct timestamps

**Actual Results**:
```
Both logged: [ ] YES [ ] NO

Separate entries: [ ] YES [ ] NO

Any duplicates or errors: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC12.6: Airtable Connection Failure

**Preconditions**:
- Can simulate Airtable failure (disconnect internet or invalid API key)

**Test Steps**:
1. Temporarily set invalid AIRTABLE_API_KEY in .env
2. Restart bot
3. Send `/habit_done`

**Expected Results**:
- ✓ Bot shows error: "Database connection error. Please try again."
- ✓ Doesn't crash
- ✓ Error logged in console

**Actual Results**:
```
Bot response:




Graceful error message: [ ] YES [ ] NO
Bot crashed: [ ] YES [ ] NO

Console error logged: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Restore valid AIRTABLE_API_KEY]
```

---

### TC12.7: Special Characters in Habit Names

**Preconditions**:
- Can add custom habit to Airtable

**Test Steps**:
1. Add habit with name: "Morning Coffee ☕ & Tea"
2. Activate it
3. Restart bot
4. Send `/habit_done`
5. Select the special character habit

**Expected Results**:
- ✓ Habit appears in keyboard with emojis intact
- ✓ Clickable
- ✓ Logs correctly
- ✓ Dashboard displays correctly

**Actual Results**:
```
Habit displayed correctly in keyboard: [ ] YES [ ] NO

Logging successful: [ ] YES [ ] NO

Special characters preserved: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC12.8: Very Long Habit Name

**Preconditions**:
- Can add custom habit

**Test Steps**:
1. Add habit with name: "This is an extremely long habit name that should test the display limits of the telegram keyboard and dashboard interface to see how it handles overflow"
2. Complete this habit via bot
3. Check dashboard display

**Expected Results**:
- ✓ Telegram keyboard may truncate with "..." (acceptable)
- ✓ Habit logs correctly
- ✓ Dashboard shows full name or truncates gracefully
- ✓ No layout breaking

**Actual Results**:
```
Telegram display:




Dashboard display:




Handled gracefully: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 13: DATA PERSISTENCE & DATA INTEGRITY

**Objective**: Verify data is correctly saved and maintained in Airtable

---

### TC13.1: Habit Log Audit Trail Completeness

**Preconditions**:
- Complete 10 different habits over time

**Test Steps**:
1. Complete 10 habit instances via bot
2. Open Airtable → Habit Log table
3. Count entries
4. Verify each entry has all required fields filled

**Expected Results**:
- ✓ Exactly 10 entries exist
- ✓ Every entry has:
  - user_id (linked)
  - habit_id (linked)
  - timestamp
  - reward_id (linked or null)
  - got_reward (true/false)
  - streak_count (≥1)
  - habit_weight
  - total_weight_applied
  - last_completed_date

**Actual Results**:
```
Total entries: __________
Expected: 10

All fields populated: [ ] YES [ ] NO

Missing fields (if any):




Data integrity: [ ] PASS [ ] FAIL
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC13.2: Reward Progress Persistence

**Preconditions**:
- Cumulative reward progress exists

**Test Steps**:
1. Note current pieces_earned for "Free Coffee" (e.g., 5)
2. Restart bot (simulates system restart)
3. Complete habits until "Free Coffee" awarded again
4. Check pieces_earned

**Expected Results**:
- ✓ pieces_earned increments from previous value (e.g., 5 → 6)
- ✓ Not reset to 1
- ✓ Progress persisted across restarts

**Actual Results**:
```
pieces_earned before restart: __________
pieces_earned after restart + new award: __________

Progress persisted: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC13.3: User Weight Changes Affect Future Calculations

**Preconditions**:
- Test User with weight 1.0

**Test Steps**:
1. Complete "Meditation" (weight 1.0) with streak 1
2. Check total_weight_applied (should be 1.1)
3. Open Airtable → Users table
4. Change Test User weight to 2.0
5. Restart bot
6. Complete "Meditation" again (assuming same day, so streak still 1)
7. Check new total_weight_applied

**Expected Results**:
- ✓ First completion: 1.0 × 1.0 × 1.1 = 1.1
- ✓ After user weight change: 1.0 × 2.0 × 1.1 = 2.2
- ✓ Weight change reflected in calculations

**Actual Results**:
```
First total_weight_applied: __________
Expected: 1.1

Second total_weight_applied: __________
Expected: 2.2

Weight change effective: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Set Test User weight back to 1.0]
```

---

### TC13.4: Habit Weight Changes Affect Future Calculations

**Preconditions**:
- Habit "Reading" with weight 1.5

**Test Steps**:
1. Complete "Reading" with user weight 1.0, streak 1
2. Check total_weight_applied (should be 1.65)
3. Change "Reading" habit weight to 3.0 in Airtable
4. Restart bot
5. Complete "Reading" again (next day for streak 2)
6. Check new total_weight_applied

**Expected Results**:
- ✓ First: 1.5 × 1.0 × 1.1 = 1.65
- ✓ Second: 3.0 × 1.0 × 1.2 = 3.6
- ✓ Habit weight change reflected

**Actual Results**:
```
First total_weight_applied: __________
Expected: 1.65

Second total_weight_applied: __________
Expected: 3.6

Change effective: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

**Restore After Test**:
```
[Set Reading habit weight back to 1.5]
```

---

### TC13.5: Data Consistency Between Bot and Dashboard

**Preconditions**:
- Bot and dashboard both running

**Test Steps**:
1. Complete a habit via bot
2. Note streak shown in bot response
3. Immediately refresh dashboard
4. Check streak chart for same habit

**Expected Results**:
- ✓ Streak value matches between bot and dashboard
- ✓ Habit log entry shows in dashboard table
- ✓ All data consistent

**Actual Results**:
```
Habit completed: __________
Streak in bot: __________
Streak in dashboard: __________

Match: [ ] YES [ ] NO

Data consistency: [ ] PASS [ ] FAIL
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC13.6: Timestamp Accuracy

**Preconditions**:
- Access to Airtable and system time

**Test Steps**:
1. Note current system time: HH:MM
2. Complete a habit via bot
3. Immediately check Habit Log entry timestamp
4. Compare

**Expected Results**:
- ✓ Timestamp within 1 minute of completion time
- ✓ Correct date
- ✓ Timezone correct (or consistent)

**Actual Results**:
```
System time at completion: __________
Logged timestamp: __________

Difference (seconds): __________

Accurate: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

## TEST CASE 14: PERFORMANCE & STRESS TESTING

**Objective**: Test system under load and edge conditions

---

### TC14.1: Large Number of Habits (20+)

**Preconditions**:
- Can add many habits to Airtable

**Test Steps**:
1. Add 20 active habits to Airtable
2. Restart bot
3. Send `/habit_done`
4. Observe keyboard

**Expected Results**:
- ✓ Telegram keyboard displays all 20 (or uses pagination if implemented)
- ✓ No performance lag
- ✓ All habits selectable

**Actual Results**:
```
Number of habits added: __________

Keyboard displayed correctly: [ ] YES [ ] NO

Performance issues: [ ] YES [ ] NO

Notes on display:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC14.2: Large Number of Rewards (50+)

**Preconditions**:
- Can add many rewards

**Test Steps**:
1. Add 50 active rewards with varying weights
2. Restart bot
3. Complete a habit
4. Measure response time

**Expected Results**:
- ✓ Reward selected from all 50
- ✓ Response time < 3 seconds
- ✓ No errors

**Actual Results**:
```
Number of rewards: __________

Response time: __________ seconds

Reward selected: __________

Performance acceptable: [ ] YES [ ] NO
```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC14.3: Large Habit Log History (1000+ entries)

**Preconditions**:
- Can generate many log entries (script or manual over time)

**Test Steps**:
1. Create 1000+ habit log entries in Airtable (can duplicate and modify timestamps)
2. Restart dashboard
3. Observe load time and performance

**Expected Results**:
- ✓ Dashboard loads within 10 seconds
- ✓ Displays recent logs (last 50 by default)
- ✓ No crashes
- ✓ Charts render correctly

**Actual Results**:
```
Total log entries: __________

Dashboard load time: __________ seconds

Displays correctly: [ ] YES [ ] NO

Performance issues: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC14.4: Rapid Sequential Commands

**Preconditions**:
- Bot running

**Test Steps**:
1. Send 10 commands rapidly (within 10 seconds):
   - /habit_done → select habit
   - /streaks
   - /my_rewards
   - /list_rewards
   - (repeat)

**Expected Results**:
- ✓ All commands processed
- ✓ Responses in correct order
- ✓ No commands ignored
- ✓ No rate limiting errors (or graceful rate limit message)

**Actual Results**:
```
Commands sent: __________
Responses received: __________

All processed: [ ] YES [ ] NO

Any errors: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED

---

### TC14.5: Dashboard Concurrent Users (if multi-user)

**Preconditions**:
- Multiple users in system OR multiple browser sessions

**Test Steps**:
1. Open dashboard in 2 different browsers (or incognito mode)
2. Each session for different user (via .env or dashboard selection if available)
3. Interact with both simultaneously

**Expected Results**:
- ✓ Both sessions function independently
- ✓ No data mixing between users
- ✓ No conflicts

**Actual Results**:
```
Multi-user support: [ ] YES [ ] NO [ ] NOT APPLICABLE

If tested:
  Sessions independent: [ ] YES [ ] NO
  No data leakage: [ ] YES [ ] NO

Notes:




```

**Status**: [ ] PASS [ ] FAIL [ ] BLOCKED [ ] N/A

---

---

## END OF TEST CASES

---

## SUMMARY & SIGN-OFF

**Total Test Cases**: 80+
**Test Cases Passed**: __________
**Test Cases Failed**: __________
**Test Cases Blocked**: __________

**Overall System Quality Assessment (1-5)**: __________

**Critical Issues Found**:
```
1.


2.


3.


```

**Recommendations**:
```
1.


2.


3.


```

**Tester Sign-off**:

Name: ___________________________
Date: ___________________________
Signature: ___________________________

**Notes for Developers**:
```









```

---

## APPENDIX: QUICK REFERENCE

### Airtable Table Relationships
```
Users (1) ──→ (Many) Habit Logs
Habits (1) ──→ (Many) Habit Logs
Rewards (1) ──→ (Many) Habit Logs
Users (1) ──→ (Many) Reward Progress
Rewards (1) ──→ (Many) Reward Progress
```

### Key Formulas
- **Streak Multiplier**: `1 + (streak_count × 0.1)`
- **Total Weight**: `habit_weight × user_weight × streak_multiplier`
- **Progress Percent**: `(pieces_earned / pieces_required) × 100`

### Status Emoji Legend
- 🕒 Pending (not enough pieces)
- ⏳ Achieved (ready to claim)
- ✅ Completed (claimed)
- 🔥 Streak fire emoji
- 📦 Cumulative reward
- 🎁 Real reward
- ⭐ Virtual reward
- ❌ No reward

---

**END OF DOCUMENT**
