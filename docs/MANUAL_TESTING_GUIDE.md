# Manual Testing Guide - Django Migration

## Overview
This guide will walk you through testing the Django-based habit reward bot to ensure all functionality works correctly after the migration from Airtable.

---

## Phase 1: Environment Setup & Database Check

### 1.1 Verify Django Installation

```bash
# Check if Django is installed
python3 -c "import django; print(f'Django version: {django.get_version()}')"
```

**Expected output:** `Django version: 5.x.x`

If you get `ModuleNotFoundError`, install dependencies:
```bash
uv sync
# or
pip install -r requirements.txt
```

### 1.2 Check Database Migrations

```bash
# Check migration status
python3 manage.py showmigrations

# Expected output should show:
# core
#  [X] 0001_initial
```

If migrations are not applied:
```bash
python3 manage.py migrate
```

### 1.3 Verify Database Tables

```bash
# List all tables in SQLite database
sqlite3 db.sqlite3 ".tables"
```

**Expected tables:**
- `users`
- `habits`
- `rewards`
- `reward_progress`
- `habit_logs`
- Plus Django's built-in tables (auth_user, django_migrations, etc.)

### 1.4 Check Database Contents

```bash
# Count records in each table
sqlite3 db.sqlite3 "SELECT 'Users:', COUNT(*) FROM users;"
sqlite3 db.sqlite3 "SELECT 'Habits:', COUNT(*) FROM habits;"
sqlite3 db.sqlite3 "SELECT 'Rewards:', COUNT(*) FROM rewards;"
sqlite3 db.sqlite3 "SELECT 'Habit Logs:', COUNT(*) FROM habit_logs;"
sqlite3 db.sqlite3 "SELECT 'Reward Progress:', COUNT(*) FROM reward_progress;"
```

**Note:** If you have 0 records, you'll need to create test data (see Phase 2).

---

## Phase 2: Django Admin Interface Testing

### 2.1 Create Superuser (if not exists)

```bash
python3 manage.py createsuperuser
```

**Prompts:**
- Username: (your choice, e.g., `admin`)
- Email: (optional, can skip)
- Password: (choose a secure password)

### 2.2 Start Development Server

```bash
python3 manage.py runserver
```

**Expected output:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### 2.3 Test Django Admin

1. **Open browser:** http://127.0.0.1:8000/admin/
2. **Login** with superuser credentials
3. **Verify admin sections exist:**
   - ✅ Users
   - ✅ Habits
   - ✅ Rewards
   - ✅ Reward progress
   - ✅ Habit logs

### 2.4 Create Test Data via Admin

#### Create a Test User
1. Go to **Users** → **Add User**
2. Fill in:
   - **Telegram ID:** `123456789` (your real Telegram ID if you know it)
   - **Name:** `Test User`
   - **Active:** ✅ Check this (IMPORTANT!)
   - **Language:** `en`
3. Click **Save**

#### Create Test Habits
1. Go to **Habits** → **Add Habit**
2. Create 3 habits:

   **Habit 1:**
   - Name: `Morning Exercise`
   - Weight: `20`
   - Category: `health`
   - Active: ✅

   **Habit 2:**
   - Name: `Read 30 minutes`
   - Weight: `15`
   - Category: `learning`
   - Active: ✅

   **Habit 3:**
   - Name: `Drink 8 glasses of water`
   - Weight: `10`
   - Category: `health`
   - Active: ✅

#### Create Test Rewards
1. Go to **Rewards** → **Add Reward**
2. Create 2 rewards:

   **Reward 1:**
   - Name: `Coffee treat`
   - Type: `Real`
   - Weight: `1.0`
   - Pieces required: `5`
   - Piece value: `2.00` (optional)
   - Active: ✅

   **Reward 2:**
   - Name: `Achievement Badge`
   - Type: `Virtual`
   - Weight: `1.5`
   - Pieces required: `1`
   - Active: ✅

3. Click **Save** for each

### 2.5 Verify Admin Features

**Test List Views:**
- ✅ Users list shows telegram_id, name, active status
- ✅ Habits list shows name, weight, category
- ✅ Rewards list shows name, type, pieces_required

**Test Search:**
- In Users list, search for your test user's name
- In Habits list, search for "Exercise"

**Test Filters:**
- In Users, filter by "Active" status
- In Habits, filter by category
- In Rewards, filter by type

**Expected:** All filters and searches work correctly.

---

## Phase 3: Bot Testing (Polling Mode)

### 3.1 Verify Environment Variables

Check your `.env` file has:
```bash
cat .env | grep -E "(TELEGRAM_BOT_TOKEN|TELEGRAM_WEBHOOK_URL)"
```

**Expected:**
- `TELEGRAM_BOT_TOKEN=<your-bot-token>`
- `TELEGRAM_WEBHOOK_URL=` (empty for polling mode)

### 3.2 Start Bot in Polling Mode

```bash
python3 src/bot/main.py
```

**Expected output:**
```
INFO - ℹ️ TELEGRAM_WEBHOOK_URL not set - skipping webhook handler setup
INFO - ℹ️ Use polling mode for development: python src/bot/main.py
INFO - 🤖 Running bot in POLLING mode (development)
INFO - ℹ️ For production, use: uvicorn src.habit_reward_project.asgi:application
```

**If you see errors:** Note them down - we'll troubleshoot.

### 3.3 Test Bot Commands via Telegram

Open Telegram and find your bot. Test each command:

#### Test 1: /start Command
1. Send: `/start`
2. **Expected response:**
   - Welcome message with menu buttons
   - Language auto-detected if you set it in Telegram
3. **Check:**
   - ✅ Message received
   - ✅ Buttons displayed
   - ✅ No error messages

**Troubleshooting:**
- If "User not found": Make sure the telegram_id in admin matches your actual Telegram ID
- If "User inactive": Check the "Active" checkbox in admin for your user

#### Test 2: /help Command
1. Send: `/help`
2. **Expected response:**
   - Help message with available commands
   - "Back to Menu" button
3. **Check:**
   - ✅ Help text displayed
   - ✅ Button works

#### Test 3: Habit Done Flow
1. Click **"Habit Done"** from menu (or send `/habit_done`)
2. **Expected:**
   - List of your active habits with buttons
3. Click on a habit (e.g., "Morning Exercise")
4. **Expected:**
   - Confirmation message
   - Streak count
   - Reward earned (if applicable)
   - Updated progress

**Verify in Admin:**
1. Go to Django admin → **Habit Logs**
2. Check latest entry:
   - ✅ User matches
   - ✅ Habit matches
   - ✅ Timestamp is recent
   - ✅ Streak count is correct

#### Test 4: View Streaks
1. Send: `/streaks`
2. **Expected:**
   - List of habits with current streak counts
   - Last completion dates
3. **Check:**
   - ✅ Shows habits you've completed
   - ✅ Streak counts match expectations

#### Test 5: My Rewards
1. Send: `/my_rewards`
2. **Expected:**
   - List of your reward progress
   - Progress bars showing pieces earned
   - Percentage complete
3. **Check:**
   - ✅ Shows rewards
   - ✅ Progress is accurate

#### Test 6: List All Rewards
1. Send: `/list_rewards`
2. **Expected:**
   - All active rewards displayed
   - Shows pieces required for each
3. **Check:**
   - ✅ All rewards from admin shown

#### Test 7: Habit Management
1. Click **"Add Habit"** from menu
2. **Expected:**
   - Prompts for habit name
3. Enter: `Test New Habit`
4. **Expected:**
   - Confirmation message
   - Habit added

**Verify in Admin:**
1. Go to **Habits**
2. Check "Test New Habit" exists

**Test Edit Habit:**
1. Click **"Edit Habit"**
2. Select a habit
3. Change its weight or name
4. Verify changes in admin

**Test Remove Habit:**
1. Click **"Remove Habit"**
2. Select the test habit you just created
3. Confirm removal
4. Verify in admin it's marked as inactive (soft delete)

#### Test 8: Settings
1. Click **"Settings"** from menu
2. **Expected:**
   - Option to change language
3. Select a different language (e.g., Russian)
4. **Check:**
   - ✅ Messages now in selected language
   - ✅ Language persists (check admin)

---

## Phase 4: Database Verification

### 4.1 Check Repository Methods Work

Open a Python shell:
```bash
python3 manage.py shell
```

Run these tests:
```python
# Import repositories
from src.core.repositories import (
    user_repository,
    habit_repository,
    reward_repository,
    habit_log_repository,
    reward_progress_repository
)

# Test 1: Get user by telegram_id
user = user_repository.get_by_telegram_id("123456789")
print(f"User found: {user.name if user else 'None'}")

# Test 2: Get all active habits
habits = habit_repository.get_all_active()
print(f"Active habits: {len(habits)}")
for h in habits:
    print(f"  - {h.name} (weight: {h.weight})")

# Test 3: Get all active rewards
rewards = reward_repository.get_all_active()
print(f"Active rewards: {len(rewards)}")
for r in rewards:
    print(f"  - {r.name} (pieces: {r.pieces_required})")

# Test 4: Get user's habit logs
if user:
    logs = habit_log_repository.get_logs_by_user(user.id, limit=5)
    print(f"Recent logs: {len(logs)}")
    for log in logs:
        print(f"  - {log.habit.name} on {log.last_completed_date}")

# Test 5: Get user's reward progress
if user:
    progress = reward_progress_repository.get_all_by_user(user.id)
    print(f"Reward progress entries: {len(progress)}")
    for p in progress:
        print(f"  - {p.reward.name}: {p.pieces_earned}/{p.pieces_required}")

# Exit shell
exit()
```

**Expected:** All queries return data without errors.

### 4.2 Check Model Computed Properties

```bash
python3 manage.py shell
```

```python
from src.core.models import RewardProgress, User, Reward

# Get a reward progress entry
user = User.objects.first()
reward = Reward.objects.first()

if user and reward:
    # Create or get progress
    progress, created = RewardProgress.objects.get_or_create(
        user=user,
        reward=reward,
        defaults={'pieces_earned': 3}
    )

    # Test computed properties
    print(f"Status: {progress.status}")  # Should show PENDING/ACHIEVED/CLAIMED
    print(f"Pieces required: {progress.pieces_required}")  # Should match reward
    print(f"Progress percent: {progress.progress_percent}%")
    print(f"Status emoji: {progress.status_emoji}")
else:
    print("No user or reward found - create test data first")

exit()
```

**Expected:** Properties calculate correctly without errors.

---

## Phase 5: Service Layer Testing

### 5.1 Test Habit Service

```bash
python3 manage.py shell
```

```python
from src.services.habit_service import habit_service
from src.core.repositories import user_repository

# Get test user
user = user_repository.get_by_telegram_id("123456789")

if user:
    # Test: Complete a habit
    habit_name = "Morning Exercise"
    result = habit_service.log_habit_completion(user.id, habit_name)

    print(f"Habit logged: {result}")
    print(f"Streak count: {result.get('streak_count', 'N/A')}")
    print(f"Reward: {result.get('reward', {}).get('name', 'None')}")
else:
    print("User not found")

exit()
```

**Expected:** Habit logs successfully, streak increments.

### 5.2 Test Reward Service

```python
from src.services.reward_service import reward_service
from src.core.repositories import user_repository

user = user_repository.get_by_telegram_id("123456789")

if user:
    # Test: Get user progress
    progress = reward_service.get_user_progress(user.id)
    print(f"User has {len(progress)} reward progress entries")

    # Test: Get achieved rewards
    achieved = reward_service.get_achieved_rewards(user.id)
    print(f"Achieved rewards: {len(achieved)}")

exit()
```

---

## Phase 6: Webhook Mode Testing (Optional)

**Only if you have a public HTTPS URL for testing.**

### 6.1 Setup Webhook

1. Update `.env`:
   ```bash
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
   ```

2. Start ASGI server:
   ```bash
   uvicorn src.habit_reward_project.asgi:application --reload
   ```

3. Set webhook:
   ```bash
   python3 manage.py set_webhook
   ```

**Expected output:**
```
✅ Webhook set: https://your-domain.com/webhook/telegram
Pending updates: 0
```

### 6.2 Test Webhook Endpoint

Send a message to your bot via Telegram.

**Check server logs for:**
```
🔧 Initializing Telegram webhook handlers...
✅ All Telegram handlers registered
📨 Received webhook update: <update_id>
```

**Expected:** Bot responds to commands via webhook.

---

## Common Issues & Troubleshooting

### Issue 1: "User not found" error
**Solution:**
- Get your actual Telegram ID: Send `/start` to @userinfobot
- Update user in Django admin with correct telegram_id

### Issue 2: "User inactive" error
**Solution:**
- Go to Django admin → Users
- Edit your user
- Check ✅ "Active" checkbox
- Save

### Issue 3: Bot doesn't respond
**Check:**
1. Is bot running? (polling mode should show logs)
2. Is TELEGRAM_BOT_TOKEN correct in `.env`?
3. Check console for errors

### Issue 4: Database errors
**Solution:**
```bash
# Reset migrations if needed
python3 manage.py migrate core zero
python3 manage.py migrate
```

### Issue 5: Import errors
**Solution:**
```bash
# Reinstall dependencies
uv sync
# or
pip install -r requirements.txt
```

### Issue 6: "No module named 'src'"
**Solution:**
```bash
# Make sure you're in project root
pwd  # Should show .../habit_reward

# Try running with python -m
python3 -m src.bot.main
```

---

## Test Completion Checklist

### Database Layer ✅
- [ ] Django migrations applied successfully
- [ ] All 5 tables exist in database
- [ ] Test data created via admin
- [ ] Repository methods work in shell

### Admin Interface ✅
- [ ] Can login to /admin/
- [ ] All 5 models visible
- [ ] Can create/edit/delete records
- [ ] List views show correct data
- [ ] Filters and search work

### Bot Commands ✅
- [ ] /start command works
- [ ] /help command works
- [ ] Habit completion works
- [ ] /streaks shows correct data
- [ ] /my_rewards shows progress
- [ ] /list_rewards shows all rewards
- [ ] Add/Edit/Remove habits work
- [ ] Settings (language change) works

### Service Layer ✅
- [ ] habit_service.log_habit_completion() works
- [ ] reward_service functions work
- [ ] Streak calculations correct
- [ ] Reward progress updates correctly

### Integration ✅
- [ ] Bot commands update database
- [ ] Admin shows real-time data
- [ ] No error logs in console
- [ ] All features end-to-end work

---

## Success Criteria

**Your Django migration is successful if:**

1. ✅ All bot commands work without errors
2. ✅ Database records created/updated correctly
3. ✅ Admin interface shows accurate data
4. ✅ Habit logging creates proper entries
5. ✅ Streak counting works correctly
6. ✅ Reward progress updates properly
7. ✅ No Python tracebacks in console
8. ✅ Language switching persists

---

## Next Steps After Testing

Once testing is complete:

**If everything works:**
1. Document any issues found
2. Consider fixing remaining critical issues (RewardStatus enum)
3. Plan production deployment

**If issues found:**
1. Note specific error messages
2. Check which phase failed
3. Share errors for debugging help

**Ready for production:**
1. Switch to PostgreSQL database
2. Set up HTTPS domain
3. Configure webhook mode
4. Deploy with Uvicorn/Gunicorn

---

## Getting Help

If you encounter issues during testing:

1. **Check logs:** Look for error tracebacks in console
2. **Check admin:** Verify data exists and is correct
3. **Check .env:** Ensure all variables are set
4. **Django shell:** Use `python manage.py shell` to debug
5. **Ask for help:** Share specific error messages

Good luck with testing! 🚀
