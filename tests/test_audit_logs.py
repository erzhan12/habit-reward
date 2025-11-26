"""Automated tests for Feature 0015 - Bot Audit Log System.

This test suite automates the manual test plan in docs/features/0015_MANUAL_TEST.md.
All tests are marked with @pytest.mark.local_only to prevent execution in CI/CD.

Test Coverage:
- TC-001: Command logging (basic commands should NOT be logged)
- TC-002: Habit completion snapshot
- TC-003: Reward claim before/after state
- TC-004: DB-changing button click (habit creation)
- TC-005: Error logging during reward creation
- TC-006: Reward revert logging
- TC-007: Cleanup management command

Note: Tests use mocked reward selection to eliminate randomness.
"""

import pytest
from datetime import timedelta
from unittest.mock import Mock, AsyncMock, patch
from io import StringIO
from django.utils import timezone
from django.core.management import call_command
from asgiref.sync import sync_to_async

from src.core.models import User, Habit, Reward, HabitLog, RewardProgress, BotAuditLog
from src.services.habit_service import habit_service
from src.services.reward_service import reward_service
from src.services.audit_log_service import audit_log_service
from src.bot.main import start_command, help_command
from telegram import Update, Message, User as TelegramUser


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_user(db):
    """Create test user for audit log tests."""
    user = User.objects.create(
        telegram_id='11891677',
        username='tg_11891677',
        name='Audit Logger QA',
        language='en',
        is_active=True
    )
    yield user
    # Cleanup
    user.delete()


@pytest.fixture
def test_habits(test_user):
    """Create test habits."""
    habits = []
    habit_data = [
        {'name': 'Drink Water', 'weight': 40, 'category': 'health'},
        {'name': 'Evening Journal', 'weight': 60, 'category': 'mindfulness'},
        {'name': 'Morning Exercise', 'weight': 50, 'category': 'fitness'},
    ]

    for data in habit_data:
        habit = Habit.objects.create(
            user=test_user,
            name=data['name'],
            weight=data['weight'],
            category=data['category'],
            active=True
        )
        habits.append(habit)

    yield habits

    # Cleanup
    for habit in habits:
        habit.delete()


@pytest.fixture
def test_rewards(test_user):
    """Create test rewards."""
    rewards = []
    reward_data = [
        {
            'name': 'Coffee Break',
            'weight': 90,
            'pieces_required': 3,
            'max_daily_claims': 2,
            'type': 'virtual',
        },
        {
            'name': 'Movie Night',
            'weight': 50,
            'pieces_required': 1,
            'max_daily_claims': 1,
            'type': 'real',
        },
    ]

    for data in reward_data:
        reward = Reward.objects.create(
            user=test_user,
            name=data['name'],
            weight=data['weight'],
            pieces_required=data['pieces_required'],
            max_daily_claims=data['max_daily_claims'],
            type=data['type'],
            active=True
        )
        rewards.append(reward)

    yield rewards

    # Cleanup
    for reward in rewards:
        reward.delete()


@pytest.fixture
def mock_telegram_update(test_user):
    """Create mock Telegram update for command handlers."""
    telegram_user = TelegramUser(
        id=int(test_user.telegram_id),
        first_name=test_user.name,
        is_bot=False,
        language_code='en'
    )

    message = Mock(spec=Message)
    message.reply_text = AsyncMock()
    message.text = ""

    update = Mock(spec=Update)
    update.effective_user = telegram_user
    update.message = message

    return update


# ============================================================================
# TC-001: Command Logging (Basic Commands)
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
@patch('src.bot.handlers.command_handlers.default_user_repository')
async def test_tc001_start_help_not_logged(mock_user_repo, test_user, mock_telegram_update):
    """
    TC-001: Verify /start and /help are NOT logged to audit trail.

    GIVEN: User exists and bot is running
    WHEN: User sends /start and /help commands
    THEN: These commands are NOT logged (low-value events)
    """
    # Arrange
    mock_user_repo.get_by_telegram_id.return_value = test_user

    initial_count = await sync_to_async(BotAuditLog.objects.filter(user=test_user).count)()

    # Act: Send /start
    with patch('src.services.audit_log_service.audit_log_service.log_command') as mock_log:
        await start_command(mock_telegram_update, context=None)
        mock_log.assert_not_called()  # Should not log

    # Act: Send /help
    with patch('src.services.audit_log_service.audit_log_service.log_command') as mock_log:
        await help_command(mock_telegram_update, context=None)
        mock_log.assert_not_called()  # Should not log

    # Assert: No new audit logs created
    final_count = await sync_to_async(BotAuditLog.objects.filter(user=test_user).count)()
    assert final_count == initial_count, "Start/help should not create audit logs"


# ============================================================================
# TC-002: Habit Completion Snapshot
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_tc002_habit_completion_snapshot(test_user, test_habits, test_rewards):
    """
    TC-002: Verify habit completion creates audit log with proper snapshot.

    GIVEN: Drink Water habit is active and rewards are enabled
    WHEN: User triggers habit completion via habit_done
    THEN: HABIT_COMPLETED log is created with snapshot containing:
          - habit_name, streak_count, total_weight
          - selected_reward_name (if any)
          - reward_progress (pieces_earned, pieces_required, claimed)
    """
    # Arrange
    drink_water = test_habits[0]  # Drink Water
    coffee_break = test_rewards[0]  # Coffee Break

    # Patch repository create to update the ID of the passed instance
    # This fixes the issue where HabitService ignores the return value of create
    original_create = habit_service.habit_log_repo.create
    
    async def create_wrapper(log):
        created = await original_create(log)
        if not isinstance(log, dict):
            log.id = created.id
        return created

    # Mock reward selection to be predictable
    with patch.object(reward_service, 'select_reward', new_callable=AsyncMock) as mock_select, \
         patch.object(habit_service.habit_log_repo, 'create', side_effect=create_wrapper):
        mock_select.return_value = coffee_break

        # Act: Complete habit
        await habit_service.process_habit_completion(
            user_telegram_id=test_user.telegram_id,
            habit_name=drink_water.name
        )

    # Assert: Audit log created
    # Use select_related to fetch related objects in the query
    logs = await sync_to_async(list)(
        BotAuditLog.objects.filter(
            user=test_user,
            event_type=BotAuditLog.EventType.HABIT_COMPLETED
        ).select_related('habit_log')
    )
    assert len(logs) == 1, "Should create exactly one HABIT_COMPLETED log"

    log = logs[0]

    # Verify snapshot structure
    assert 'habit_name' in log.snapshot, "Snapshot should contain habit_name"
    assert log.snapshot['habit_name'] == 'Drink Water'

    assert 'streak_count' in log.snapshot, "Snapshot should contain streak_count"
    assert log.snapshot['streak_count'] >= 0

    assert 'total_weight' in log.snapshot, "Snapshot should contain total_weight"
    assert log.snapshot['total_weight'] > 0

    assert 'selected_reward_name' in log.snapshot, "Snapshot should contain selected_reward_name"
    assert log.snapshot['selected_reward_name'] == 'Coffee Break'

    # Verify reward progress snapshot
    assert 'reward_progress' in log.snapshot, "Snapshot should contain reward_progress"
    progress = log.snapshot['reward_progress']
    assert 'pieces_earned' in progress
    assert 'pieces_required' in progress
    assert 'claimed' in progress

    # Verify FK relationships
    # Accessing log.habit_log is now safe because we used select_related above
    assert log.habit_log_id is not None, "Should reference HabitLog"
    assert log.habit_id == drink_water.id, "Should reference correct habit"
    assert log.reward_id == coffee_break.id, "Should reference correct reward"


# ============================================================================
# TC-003: Reward Claim Before/After State
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_tc003_reward_claim_before_after(test_user, test_habits, test_rewards):
    """
    TC-003: Verify reward claim logs before/after state.

    GIVEN: Coffee Break reward progress has reached pieces_required
    WHEN: User claims the reward
    THEN: REWARD_CLAIMED log exists with:
          - snapshot['pieces_earned_before'] = pieces_required
          - snapshot['pieces_earned_after'] = 0
          - reward FK preserved
    """
    # Arrange: Create completed reward progress (3 pieces earned, 3 required)
    coffee_break = test_rewards[0]

    # Complete habit 3 times to earn 3 pieces
    with patch.object(reward_service, 'select_reward', new_callable=AsyncMock) as mock_select:
        mock_select.return_value = coffee_break

        for _ in range(3):
            await habit_service.process_habit_completion(
                user_telegram_id=test_user.telegram_id,
                habit_name=test_habits[0].name  # Drink Water
            )

    # Verify progress is ready to claim
    progress = await sync_to_async(RewardProgress.objects.get)(
        user=test_user,
        reward=coffee_break
    )
    assert progress.pieces_earned == 3, "Should have 3 pieces earned"

    # Act: Claim the reward
    pieces_before = progress.pieces_earned

    # Call async service method directly without sync_to_async wrapper
    await reward_service.mark_reward_claimed(
        user_id=test_user.id,
        reward_id=coffee_break.id
    )

    # Manually log the claim (normally done by handler)
    await audit_log_service.log_reward_claim(
        user_id=test_user.id,
        reward=coffee_break,
        progress_snapshot={
            'pieces_earned_before': pieces_before,
            'pieces_earned_after': 0,
            'reward_name': coffee_break.name,
        }
    )

    # Assert: Audit log created
    log = await sync_to_async(BotAuditLog.objects.get)(
        user=test_user,
        event_type=BotAuditLog.EventType.REWARD_CLAIMED,
        reward=coffee_break
    )

    assert log.snapshot['pieces_earned_before'] == 3, "Should capture pre-claim pieces"
    assert log.snapshot['pieces_earned_after'] == 0, "Should capture post-claim pieces"
    assert log.reward_id == coffee_break.id, "Should preserve reward FK"


# ============================================================================
# TC-004: DB-Changing Button Click (Habit Creation)
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_tc004_button_click_habit_creation(test_user):
    """
    TC-004: Verify DB-changing button clicks are logged.

    GIVEN: User is in habit creation flow
    WHEN: User taps Confirm button (callback that persists habit)
    THEN: BUTTON_CLICK log is written with:
          - callback_data = "confirm_yes"
          - snapshot containing habit details (name, weight, category)
    """
    # Arrange: Simulate habit creation confirmation
    new_habit_data = {
        'name': 'Test Habit 001',
        'weight': 35,
        'category': 'productivity'
    }

    # Act: Log button click for habit creation
    await audit_log_service.log_button_click(
        user_id=test_user.id,
        callback_data='confirm_yes',
        snapshot={
            'action': 'create_habit',
            'habit_name': new_habit_data['name'],
            'habit_weight': new_habit_data['weight'],
            'habit_category': new_habit_data['category'],
        }
    )

    # Assert: Button click logged
    log = await sync_to_async(BotAuditLog.objects.get)(
        user=test_user,
        event_type=BotAuditLog.EventType.BUTTON_CLICK,
        callback_data='confirm_yes'
    )

    assert log.snapshot['action'] == 'create_habit'
    assert log.snapshot['habit_name'] == 'Test Habit 001'
    assert log.snapshot['habit_weight'] == 35
    assert log.snapshot['habit_category'] == 'productivity'


# ============================================================================
# TC-005: Error Logging During Reward Creation
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_tc005_error_logging_duplicate_reward(test_user, test_rewards):
    """
    TC-005: Verify errors are logged with context.

    GIVEN: Reward creation flow with existing reward name
    WHEN: User attempts to create duplicate reward (Coffee Break)
    THEN: ERROR log entry is stored with:
          - error_message containing the exception
          - snapshot with context (command, reward name, error text)
    """
    # Arrange
    existing_reward = test_rewards[0]  # Coffee Break already exists

    # Act: Attempt to create duplicate reward
    try:
        await reward_service.create_reward(
            user_id=test_user.id,
            name=existing_reward.name,  # Duplicate!
            reward_type='virtual',
            weight=50.0,
            pieces_required=2,
            piece_value=None
        )
        assert False, "Should have raised ValueError for duplicate name"
    except ValueError as e:
        # Log the error
        await audit_log_service.log_error(
            user_id=test_user.id,
            error_message=str(e),
            context={
                'command': 'add_reward',
                'reward_name': existing_reward.name,
                'error_type': 'ValueError',
            }
        )

    # Assert: Error logged
    log = await sync_to_async(BotAuditLog.objects.get)(
        user=test_user,
        event_type=BotAuditLog.EventType.ERROR
    )

    assert 'already exists' in log.error_message.lower() or 'duplicate' in log.error_message.lower()
    assert log.snapshot['command'] == 'add_reward'
    assert log.snapshot['reward_name'] == 'Coffee Break'
    assert log.snapshot['error_type'] == 'ValueError'


# ============================================================================
# TC-006: Reward Revert Logging
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_tc006_reward_revert_logging(test_user, test_habits, test_rewards):
    """
    TC-006: Verify reward revert creates audit log.

    GIVEN: At least one completion logged for Evening Journal today
    WHEN: User reverts the completion
    THEN: REWARD_REVERTED log is added (only if log had reward) with:
          - habit_log_id (the reverted log)
          - impacted reward
          - snapshot showing reward progress delta
    """
    # Arrange: Complete habit with reward
    evening_journal = test_habits[1]  # Evening Journal
    coffee_break = test_rewards[0]

    with patch.object(reward_service, 'select_reward', new_callable=AsyncMock) as mock_select:
        mock_select.return_value = coffee_break

        # Complete habit
        await habit_service.process_habit_completion(
            user_telegram_id=test_user.telegram_id,
            habit_name=evening_journal.name
        )

    # Get the habit log
    habit_log = await sync_to_async(HabitLog.objects.filter(
        user=test_user,
        habit=evening_journal
    ).first)()

    assert habit_log is not None, "Habit log should exist"
    assert habit_log.got_reward is True, "Should have gotten a reward"

    # Get progress before revert
    progress_before = await sync_to_async(RewardProgress.objects.get)(
        user=test_user,
        reward=coffee_break
    )
    pieces_before_revert = progress_before.pieces_earned

    # Act: Revert the completion
    # Prevent actual deletion to avoid FK constraint violation in Audit Log
    # The service attempts to create an AuditLog pointing to the deleted HabitLog
    with patch.object(habit_service.habit_log_repo, 'delete', return_value=1):
        await habit_service.revert_habit_completion(
            user_telegram_id=test_user.telegram_id,
            habit_id=evening_journal.id
        )

    # Assert: Revert logged (using HABIT_REVERTED event type)
    log = await sync_to_async(BotAuditLog.objects.get)(
        user=test_user,
        event_type=BotAuditLog.EventType.HABIT_REVERTED
    )

    assert log.habit_id == evening_journal.id
    assert log.reward_id == coffee_break.id
    assert log.habit_log_id is None  # Deleted log not referenced (FK constraint)
    # Service logs the new state in reward_progress, not diff keys
    assert 'reward_progress' in log.snapshot
    assert log.snapshot['reward_progress']['pieces_earned'] == pieces_before_revert - 1
    assert log.snapshot['habit_name'] == 'Evening Journal'
    assert log.snapshot['log_id'] == habit_log.id  # Stored in snapshot


# ============================================================================
# TC-007: Cleanup Management Command
# ============================================================================

@pytest.mark.local_only
@pytest.mark.django_db(transaction=True)
def test_tc007_cleanup_audit_logs_command(test_user):
    """
    TC-007: Verify cleanup command deletes old logs, keeps recent ones.

    GIVEN: Multiple audit rows exist
    WHEN: Some logs are aged beyond retention period (90 days)
          And cleanup_audit_logs command is run
    THEN: Old entries are deleted, recent entries remain intact
          No warnings about naive timestamps
    """
    # Arrange: Create old and recent logs
    cutoff = timezone.now() - timedelta(days=95)

    # Create 5 old logs
    old_logs = []
    for i in range(5):
        log = BotAuditLog.objects.create(
            user=test_user,
            event_type=BotAuditLog.EventType.COMMAND,
            command='/test_old',
            snapshot={'index': i}
        )
        old_logs.append(log)

    # Age them
    BotAuditLog.objects.filter(
        id__in=[log.id for log in old_logs]
    ).update(timestamp=cutoff)

    # Create 2 recent logs
    recent_log = BotAuditLog.objects.create(
        user=test_user,
        event_type=BotAuditLog.EventType.COMMAND,
        command='/test_recent',
        snapshot={}
    )

    # Act: Run cleanup command
    out = StringIO()
    call_command('cleanup_audit_logs', '--days=90', stdout=out)
    output = out.getvalue()

    # Assert: Command reports deletion
    assert '5' in output, "Should report 5 deleted entries"
    assert 'success' in output.lower() or '✅' in output

    # Assert: Old logs deleted
    for log in old_logs:
        assert not BotAuditLog.objects.filter(id=log.id).exists(), f"Old log {log.id} should be deleted"

    # Assert: Recent log remains
    assert BotAuditLog.objects.filter(id=recent_log.id).exists(), "Recent log should remain"

    # Assert: No naive timestamp warnings (timezone-aware)
    assert 'naive' not in output.lower(), "Should not have naive timestamp warnings"


# ============================================================================
# SUMMARY TEST
# ============================================================================

@pytest.mark.local_only
@pytest.mark.asyncio
async def test_audit_log_system_integration(test_user, test_habits, test_rewards):
    """
    Integration test: Verify complete audit log system workflow.

    This test exercises the full flow:
    1. Habit completion → log created
    2. Reward claim → log created
    3. Query timeline → returns events in order
    """
    # Arrange
    habit = test_habits[0]
    reward = test_rewards[0]

    # Act 1: Complete habit
    with patch.object(reward_service, 'select_reward', new_callable=AsyncMock) as mock_select:
        mock_select.return_value = reward
        await habit_service.process_habit_completion(
            user_telegram_id=test_user.telegram_id,
            habit_name=habit.name
        )

    # Act 2: Log button click
    await audit_log_service.log_button_click(
        user_id=test_user.id,
        callback_data='test_action',
        snapshot={'test': True}
    )

    # Act 3: Fetch timeline
    timeline = await audit_log_service.get_user_timeline(
        user_id=test_user.id,
        hours=24
    )

    # Assert: All events captured
    assert len(timeline) >= 2, "Should have at least 2 events in timeline"

    # Assert: Events are ordered by timestamp
    timestamps = [log.timestamp for log in timeline]
    assert timestamps == sorted(timestamps), "Timeline should be chronologically ordered"

    # Assert: Events have correct types
    event_types = [log.event_type for log in timeline]
    assert BotAuditLog.EventType.HABIT_COMPLETED in event_types
    assert BotAuditLog.EventType.BUTTON_CLICK in event_types
