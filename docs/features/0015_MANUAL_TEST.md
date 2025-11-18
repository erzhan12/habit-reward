# Feature 0015 – Manual Test Plan (Bot Audit Log System)

Manual checklist for verifying the comprehensive audit logging feature. Run all cases against a local test environment; never run against production data.

---

## Test Environment Prep

1. Apply the latest code and schema:
   ```bash
   make sync
   make migrate
   ```
2. Seed reference data via Django shell (`uv run python manage.py shell_plus`):
   ```python
   from datetime import timedelta
   from django.utils import timezone
   from src.core.models import User, Habit, Reward
   from src.services.habit_service import habit_service
   from src.services.reward_service import reward_service

   TEST_TELEGRAM_ID = '800015'

   user, _ = User.objects.update_or_create(
       telegram_id=TEST_TELEGRAM_ID,
       defaults={
           'username': f'tg_{TEST_TELEGRAM_ID}',
           'name': 'Audit Logger QA',
           'language': 'en',
           'is_active': True,
       }
   )

   drink_water, _ = Habit.objects.update_or_create(
       name='Drink Water',
       defaults={'weight': 40, 'active': True, 'category': 'health'}
   )
   journal, _ = Habit.objects.update_or_create(
       name='Evening Journal',
       defaults={'weight': 60, 'active': True, 'category': 'mindfulness'}
   )

   coffee_break, _ = Reward.objects.update_or_create(
       name='Coffee Break',
       defaults={
           'weight': 90,
           'pieces_required': 3,
           'max_daily_claims': 2,
           'type': 'virtual',
           'active': True,
       }
   )
   movie_night, _ = Reward.objects.update_or_create(
       name='Movie Night',
       defaults={
           'weight': 50,
           'pieces_required': 1,
           'max_daily_claims': 1,
           'type': 'real',
           'active': True,
       }
   )
   ```
3. Start the Telegram bot locally with `make bot` (or `./run_bot.sh`). Use Telegram’s test chat tied to the seeded user ID.
4. Keep a second terminal open with `uv run python manage.py shell_plus` to inspect `BotAuditLog` entries quickly:
   ```python
   from src.core.models import BotAuditLog, RewardProgress

   def recent_logs(type=None):
       qs = BotAuditLog.objects.filter(user=user)
       if type:
           qs = qs.filter(event_type=type)
       return list(qs.order_by('-timestamp')[:5])
   ```

---

## Test Cases (GIVEN / WHEN / THEN)

### TC-001 – Command Logging (/start and /help)
- **GIVEN** user `Audit Logger QA` exists and bot is running.
- **WHEN** you send `/start` followed by `/help` from the Telegram chat tied to `TEST_TELEGRAM_ID`.
- **THEN** the audit table stores two new `COMMAND` entries (`command="/start"` and `command="/help"`) with snapshots that include the resolved language; `recent_logs('command')` shows the commands in chronological order.

### TC-002 – Habit Completion Snapshot
- **GIVEN** `Drink Water` habit is active and rewards are enabled.
- **WHEN** you trigger a completion via `/habit_done` (choose "Drink Water" when prompted).
- **THEN** a `HABIT_COMPLETED` log is created referencing the saved `HabitLog` row, with a snapshot capturing `habit_name`, `streak_count`, `total_weight`, selected reward name (if any), and `reward_progress` (pieces earned, required, claimed). Verify `recent_logs('habit_completed')[0].habit_log` is not `None` and snapshot keys match the plan.

### TC-003 – Reward Claim Before/After State
- **GIVEN** the `Coffee Break` reward progress has reached `pieces_required` (repeat `/habit_done` until achieved).
- **WHEN** you run `/claim_reward`, select "Coffee Break", and confirm the claim.
- **THEN** a `REWARD_CLAIMED` log exists with `snapshot['pieces_earned_before']` equal to the pre-claim value (should equal `pieces_required`) and `snapshot['pieces_earned_after'] == 0`. The entry should store the `reward` foreign key even if the reward metadata changes later.

### TC-004 – DB-Changing Button Click (Habit Creation)
- **GIVEN** `/add_habit` flow is available.
- **WHEN** you walk through `/add_habit`, enter details for a throwaway habit (e.g., "Test Habit 001"), and tap **Confirm** (the callback that actually persists the habit).
- **THEN** a `BUTTON_CLICK` log is written for the confirm callback with `callback_data="confirm_yes"` (or equivalent) and a snapshot summarizing the habit that was created (name, weight, category). Button steps that only display prompts are not logged, but the confirmation that writes to DB must be present.

### TC-005 – Error Logging During Reward Creation
- **GIVEN** reward creation flow is available and you attempt to create a duplicate reward name.
- **WHEN** you start `/add_reward`, enter an existing reward name (e.g., "Coffee Break"), and proceed to confirmation.
- **THEN** the handler raises a `ValueError` and surfaces a user-friendly error, **and** a matching `ERROR` log entry is stored with context containing `command:"add_reward"`, the conflicting reward name, and error text. Verify via `recent_logs('error')[0].snapshot`.

### TC-006 – Reward Revert Logging
- **GIVEN** at least one completion has been logged for `Evening Journal` today.
- **WHEN** you run `/habit_revert`, select "Evening Journal", and confirm the revert.
- **THEN** a `REWARD_REVERTED` log is added (only if the reverted log had a reward) containing `habit_log_id`, the impacted reward, and a snapshot showing the reward progress delta after decrement.

### TC-007 – Cleanup Management Command
- **GIVEN** multiple audit rows exist.
- **WHEN** you open the Django shell and age a few rows manually: 
  ```python
  cutoff = timezone.now() - timedelta(days=95)
  BotAuditLog.objects.filter(user=user).update(timestamp=cutoff)
  ```
  then run `uv run python manage.py cleanup_audit_logs --days 90`.
- **THEN** the command reports the number of deleted rows, those older-than-cutoff entries disappear, and newer entries remain intact. No warnings about naive timestamps should appear.

---

## Post-Test Checklist
- Delete any throwaway habits/rewards created during testing.
- Review `django.log` (or console output) to ensure no unhandled exceptions occurred.
- Reset the seeded user’s reward progress if future tests need a clean state.
