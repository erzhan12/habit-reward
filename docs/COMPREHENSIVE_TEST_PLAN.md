# Comprehensive Test Plan - Habit Reward Bot

**Version:** 1.0
**Date:** 2025-10-20
**Current Coverage:** ~15%
**Target Coverage:** 95%+

---

## Table of Contents

1. [Overview](#overview)
2. [Test Strategy](#test-strategy)
3. [Test Environments](#test-environments)
4. [Phase 1: Bot Handler Tests](#phase-1-bot-handler-tests)
5. [Phase 2: Service Layer Tests](#phase-2-service-layer-tests)
6. [Phase 3: Repository Layer Tests](#phase-3-repository-layer-tests)
7. [Phase 4: Model Validation Tests](#phase-4-model-validation-tests)
8. [Phase 5: Integration Tests](#phase-5-integration-tests)
9. [Phase 6: Edge Cases & Error Handling](#phase-6-edge-cases--error-handling)
10. [Test Execution Schedule](#test-execution-schedule)
11. [Success Criteria](#success-criteria)

---

## Overview

This document provides a comprehensive test plan covering both **automated** and **manual** testing for the Habit Reward Telegram Bot. The plan is organized by layers (Handlers → Services → Repositories → Models) and includes integration and edge case testing.

### Current Test Status

**✅ Tested (Automated):**
- Basic bot handler flows (user validation, language support)
- Streak service core logic
- Reward service basic flows
- Habit service basic flows

**⚠️ Partially Tested:**
- Advanced bot handler flows (missing 60+ test cases)
- Service layer edge cases

**❌ Not Tested:**
- Repository layer (0% coverage)
- Model validation (0% coverage)
- NLP service (0% coverage)
- Settings handler (0% coverage)
- Integration tests (0% coverage)

---

## Test Strategy

### Automated Tests (pytest)

- **Location:** `tests/` directory
- **Framework:** pytest with async support
- **Mocking:** unittest.mock for repositories and external dependencies
- **Coverage Target:** 95%+
- **Run Command:** `uv run pytest tests/ -v --cov=src`

### Manual Tests (Telegram Bot)

- **Environment:** Test Telegram bot instance
- **Test Users:** Multiple test users with different languages (en, ru, kk)
- **Test Data:** Airtable test database with sample habits and rewards
- **Documentation:** Step-by-step manual test scripts below

### Test Types

1. **Unit Tests (Automated):** Test individual functions/methods in isolation
2. **Integration Tests (Automated + Manual):** Test complete workflows across layers
3. **User Acceptance Tests (Manual):** Test real user scenarios via Telegram
4. **Edge Case Tests (Automated):** Test boundary conditions and error handling
5. **Performance Tests (Manual):** Test response times and concurrency

---

## Test Environments

### Automated Test Environment

```yaml
Framework: pytest
Python Version: 3.13
Dependencies: uv-managed
Mock Strategy: unittest.mock for all external dependencies
Test Database: Mocked Airtable responses
```

### Manual Test Environment

```yaml
Bot Instance: Test Telegram bot (@test_habit_reward_bot)
Test Users:
  - User 1 (English, telegram_id: TEST_USER_1)
  - User 2 (Russian, telegram_id: TEST_USER_2)
  - User 3 (Kazakh, telegram_id: TEST_USER_3)
  - User 4 (Inactive, telegram_id: TEST_USER_INACTIVE)
Airtable Base: Test database with sample data
Test Habits: Walking, Reading, Meditation, Pushups, Water
Test Rewards: Coffee, Book, Movie, Massage (multi-piece)
```

---

## Phase 1: Bot Handler Tests

### TC-BOT-001: /start Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestStartCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC1.1 | User not found (all languages) | ✅ Implemented | High |
| TC1.2 | Active user success (all languages) | ✅ Implemented | High |
| TC1.3 | Inactive user blocked (all languages) | ✅ Implemented | High |
| TC1.4 | User with missing language field (fallback to 'en') | ❌ Missing | Medium |
| TC1.5 | User with unsupported language (fallback to 'en') | ❌ Missing | Medium |
| TC1.6 | Telegram user with no language_code set | ❌ Missing | Medium |
| TC1.7 | First-time user registration flow | ❌ Missing | Low |
| TC1.8 | HTML formatting verification (bold tags) | ❌ Missing | Low |

**Implementation Example (TC1.4):**

```python
@pytest.mark.asyncio
@patch('src.bot.main.user_repository')
async def test_user_missing_language_field(mock_user_repo, mock_telegram_update):
    """User with missing language field should fallback to 'en'."""
    # Create user without language field
    user_no_lang = User(
        id="user123",
        telegram_id="999999999",
        name="Test User",
        active=True,
        language=None  # Missing language
    )
    mock_user_repo.get_by_telegram_id.return_value = user_no_lang

    await start_command(mock_telegram_update, context=None)

    # Assert: Welcome message sent in English (fallback)
    call_args = mock_telegram_update.message.reply_text.call_args
    message_text = call_args[0][0]
    assert msg('HELP_START_MESSAGE', 'en') == message_text
```

#### Manual Tests

**Test Script: MAN-TC1-001 - First Time User Onboarding**

**Prerequisites:**
- New Telegram account not registered in system
- Test bot running

**Steps:**
1. Open Telegram and search for test bot
2. Send `/start` command
3. Observe welcome message
4. Verify language matches Telegram app language
5. Verify all command buttons are clickable
6. Take screenshot of welcome message

**Expected Result:**
- Welcome message displays in correct language
- All commands listed: /habit_done, /streaks, /my_rewards, /claim_reward, /settings
- HTML formatting renders correctly (bold text visible)
- No error messages

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-002: /help Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestHelpCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC2.1 | User not found (all languages) | ✅ Implemented | High |
| TC2.2 | Active user success (all languages) | ✅ Implemented | High |
| TC2.3 | Inactive user blocked (all languages) | ✅ Implemented | High |
| TC2.4 | Command list completeness | ❌ Missing | Medium |
| TC2.5 | HTML formatting verification | ❌ Missing | Low |
| TC2.6 | Multi-language help text accuracy | ❌ Missing | Medium |

**Implementation Example (TC2.4):**

```python
@pytest.mark.asyncio
@patch('src.bot.main.user_repository')
async def test_help_command_completeness(mock_user_repo, mock_telegram_update, mock_active_user):
    """Help message should contain all available commands."""
    mock_user_repo.get_by_telegram_id.return_value = mock_active_user

    await help_command(mock_telegram_update, context=None)

    call_args = mock_telegram_update.message.reply_text.call_args
    message_text = call_args[0][0]

    # Verify all commands are present
    required_commands = ['/habit_done', '/streaks', '/my_rewards', '/claim_reward', '/settings']
    for command in required_commands:
        assert command in message_text, f"Command {command} missing from help"
```

#### Manual Tests

**Test Script: MAN-TC2-001 - Help Command Multilingual Verification**

**Prerequisites:**
- 3 test users registered (English, Russian, Kazakh)
- Test bot running

**Steps:**
1. User 1 (English): Send `/help`
2. Verify help text is in English
3. Take screenshot
4. User 2 (Russian): Send `/help`
5. Verify help text is in Russian (Cyrillic characters)
6. Take screenshot
7. User 3 (Kazakh): Send `/help`
8. Verify help text is in Kazakh
9. Take screenshot

**Expected Result:**
- Each user receives help in their configured language
- All 5 commands listed with descriptions
- Formatting is consistent across languages

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-003: /habit_done Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestHabitDoneCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC3.1 | User not found | ✅ Implemented | High |
| TC3.2 | Inactive user blocked | ✅ Implemented | High |
| TC3.3 | Shows only active habits | ✅ Implemented | High |
| TC3.4 | No active habits error | ✅ Implemented | High |
| TC3.5 | Repository filters inactive habits | ✅ Implemented | High |
| TC3.6 | Custom text input flow (conversation state) | ❌ Missing | High |
| TC3.7 | NLP classification success | ❌ Missing | High |
| TC3.8 | NLP classification failure (no match) | ❌ Missing | High |
| TC3.9 | NLP service timeout/error handling | ❌ Missing | Medium |
| TC3.10 | Habit selection from keyboard | ❌ Missing | High |
| TC3.11 | Reward earned notification | ❌ Missing | High |
| TC3.12 | No reward (NONE type) flow | ❌ Missing | Medium |
| TC3.13 | Multi-piece reward progress tracking | ❌ Missing | High |
| TC3.14 | Streak increment display | ❌ Missing | High |
| TC3.15 | Same-day duplicate logging prevention | ❌ Missing | High |
| TC3.16 | Conversation cancellation | ❌ Missing | Low |
| TC3.17 | Multi-language habit names | ❌ Missing | Medium |

**Implementation Example (TC3.10):**

```python
@pytest.mark.asyncio
@patch('src.bot.handlers.habit_done_handler.habit_service')
@patch('src.bot.handlers.habit_done_handler.user_repository')
async def test_habit_selection_from_keyboard(
    mock_user_repo, mock_habit_service, mock_telegram_update, mock_active_user, mock_active_habits
):
    """User selects habit from keyboard and completes logging."""
    from src.models.habit_completion_result import HabitCompletionResult
    from src.models.reward import Reward, RewardType

    # Setup
    mock_user_repo.get_by_telegram_id.return_value = mock_active_user
    mock_habit_service.get_all_active_habits.return_value = mock_active_habits

    # Mock habit completion result
    reward = Reward(id="r1", name="Coffee", weight=10, type=RewardType.REAL, pieces_required=1)
    result = HabitCompletionResult(
        habit_confirmed=True,
        habit_name="Walking",
        streak_count=5,
        got_reward=True,
        reward=reward,
        total_weight_applied=15.0
    )
    mock_habit_service.process_habit_completion.return_value = result

    # Execute: Start conversation
    conversation_state = await habit_done_command(mock_telegram_update, context=None)
    assert conversation_state == 1  # AWAITING_HABIT_SELECTION

    # Execute: User selects "Walking" from keyboard
    from telegram import CallbackQuery
    callback_query = Mock(spec=CallbackQuery)
    callback_query.answer = AsyncMock()
    callback_query.data = "habit_Walking"

    update_with_callback = Mock(spec=Update)
    update_with_callback.callback_query = callback_query
    update_with_callback.effective_user = mock_telegram_update.effective_user

    # Import handler for habit selection
    from src.bot.handlers.habit_done_handler import handle_habit_selection

    await handle_habit_selection(update_with_callback, context=None)

    # Verify habit service was called
    mock_habit_service.process_habit_completion.assert_called_once_with(
        user_telegram_id="999999999",
        habit_name="Walking"
    )

    # Verify success message sent
    callback_query.edit_message_text.assert_called_once()
    call_args = callback_query.edit_message_text.call_args[0][0]
    assert "Walking" in call_args
    assert "Coffee" in call_args
    assert "5" in call_args  # Streak count
```

#### Manual Tests

**Test Script: MAN-TC3-001 - Complete Habit Logging Flow (Keyboard Selection)**

**Prerequisites:**
- Active user with habits: Walking, Reading, Meditation
- Test bot running

**Steps:**
1. Send `/habit_done` command
2. Verify keyboard displays with 3 habit buttons + "Custom Text" button
3. Tap "Walking" button
4. Observe success message with:
   - Habit name confirmation
   - Streak count
   - Reward information (if earned)
5. Verify conversation ends automatically
6. Take screenshot of completion message

**Expected Result:**
- Keyboard shows all active habits
- Success message confirms habit logged
- Streak count displayed
- Reward notification appears if earned
- Message uses HTML formatting

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC3-002 - Custom Text Input with NLP**

**Prerequisites:**
- Active user with habits: Walking, Reading, Meditation, Pushups, Drinking Water
- Test bot running

**Steps:**
1. Send `/habit_done` command
2. Tap "Custom Text" button
3. Type "I did 50 pushups today" and send
4. Observe bot response
5. Verify "Pushups" habit was logged
6. Check success message shows correct habit and streak

**Test Cases:**
- Input: "went for a walk" → Expected: Logs "Walking"
- Input: "read 30 pages" → Expected: Logs "Reading"
- Input: "meditated for 10 minutes" → Expected: Logs "Meditation"
- Input: "drank water" → Expected: Logs "Drinking Water"
- Input: "xyz random text" → Expected: Shows error or habit selection keyboard

**Expected Result:**
- NLP correctly identifies habit from natural language
- Habit logged automatically
- Success message confirms correct habit
- If no match, shows helpful error message

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC3-003 - Same Day Duplicate Logging Prevention**

**Prerequisites:**
- Active user
- Habit "Walking" already logged today

**Steps:**
1. Send `/habit_done` command
2. Select "Walking" habit (already logged today)
3. Observe bot response
4. Verify streak count remains same (not incremented)
5. Check if duplicate logging is prevented or allowed

**Expected Result:**
- Bot either:
  - (Option A) Prevents duplicate: "You already logged Walking today"
  - (Option B) Allows duplicate: Streak stays same, no increment

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-004: /streaks Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestStreaksCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC4.1 | User not found (all languages) | ✅ Implemented | High |
| TC4.2 | Inactive user blocked (all languages) | ✅ Implemented | High |
| TC4.3 | Single habit streak display | ❌ Missing | High |
| TC4.4 | Multiple habits with different streaks | ❌ Missing | High |
| TC4.5 | No habits logged yet (empty state) | ❌ Missing | Medium |
| TC4.6 | Broken streak display | ❌ Missing | Medium |
| TC4.7 | High streak count (>100 days) | ❌ Missing | Low |
| TC4.8 | Multi-language streak formatting | ❌ Missing | Medium |
| TC4.9 | HTML formatting verification | ❌ Missing | Low |

**Implementation Example (TC4.4):**

```python
@pytest.mark.asyncio
@patch('src.bot.handlers.streak_handler.streak_service')
@patch('src.bot.handlers.streak_handler.user_repository')
async def test_multiple_habits_different_streaks(
    mock_user_repo, mock_streak_service, mock_telegram_update, mock_active_user
):
    """Display multiple habits with different streak counts."""
    mock_user_repo.get_by_telegram_id.return_value = mock_active_user

    # Mock streaks for multiple habits
    mock_streaks = {
        "habit_walking": 5,
        "habit_reading": 12,
        "habit_meditation": 1
    }
    mock_streak_service.get_all_streaks_for_user.return_value = mock_streaks

    # Mock habit names
    from src.models.habit import Habit
    mock_habits = [
        Habit(id="habit_walking", name="Walking", weight=10, active=True),
        Habit(id="habit_reading", name="Reading", weight=10, active=True),
        Habit(id="habit_meditation", name="Meditation", weight=10, active=True)
    ]

    with patch('src.bot.handlers.streak_handler.habit_repository') as mock_habit_repo:
        mock_habit_repo.get_by_id.side_effect = lambda hid: next(h for h in mock_habits if h.id == hid)

        await streaks_command(mock_telegram_update, context=None)

    # Verify message contains all habits and their streaks
    call_args = mock_telegram_update.message.reply_text.call_args[0][0]
    assert "Walking" in call_args
    assert "5" in call_args
    assert "Reading" in call_args
    assert "12" in call_args
    assert "Meditation" in call_args
    assert "1" in call_args
```

#### Manual Tests

**Test Script: MAN-TC4-001 - Multi-Habit Streak Display**

**Prerequisites:**
- Active user
- Logged habits:
  - Walking: 7 days streak
  - Reading: 3 days streak
  - Meditation: 1 day streak (logged today for first time)

**Steps:**
1. Send `/streaks` command
2. Observe streaks list
3. Verify each habit shows correct streak count
4. Verify fire emoji (🔥) appears
5. Check HTML formatting (bold habit names)
6. Take screenshot

**Expected Result:**
```
🔥 Your Current Streaks:

Walking: 7 days 🔥
Reading: 3 days 🔥
Meditation: 1 day 🔥
```

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC4-002 - No Streaks Yet (Empty State)**

**Prerequisites:**
- Active user with NO habits logged yet
- Test bot running

**Steps:**
1. Send `/streaks` command
2. Observe bot response
3. Verify appropriate empty state message

**Expected Result:**
- Message: "You haven't logged any habits yet. Use /habit_done to start!"
- No error shown
- Helpful guidance provided

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-005: /my_rewards Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestMyRewardsCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC5.1 | User not found (all languages) | ✅ Implemented | High |
| TC5.2 | Inactive user blocked (all languages) | ✅ Implemented | High |
| TC5.3 | No rewards progress (empty state) | ❌ Missing | High |
| TC5.4 | Single reward with progress | ❌ Missing | High |
| TC5.5 | Multiple rewards (pending, achieved, claimed) | ❌ Missing | High |
| TC5.6 | Achieved reward (claimable notification) | ❌ Missing | High |
| TC5.7 | Claimed reward display | ❌ Missing | Medium |
| TC5.8 | Multi-piece reward progress (3/10 pieces) | ❌ Missing | High |
| TC5.9 | Piece value calculation display | ❌ Missing | Medium |
| TC5.10 | HTML formatting verification | ❌ Missing | Low |
| TC5.11 | Multi-language reward display | ❌ Missing | Medium |

**Implementation Example (TC5.5):**

```python
@pytest.mark.asyncio
@patch('src.bot.handlers.reward_handlers.reward_service')
@patch('src.bot.handlers.reward_handlers.user_repository')
async def test_multiple_rewards_different_statuses(
    mock_user_repo, mock_reward_service, mock_telegram_update, mock_active_user
):
    """Display multiple rewards with different statuses."""
    from src.models.reward import Reward, RewardType
    from src.models.reward_progress import RewardProgress, RewardStatus

    mock_user_repo.get_by_telegram_id.return_value = mock_active_user

    # Create rewards
    reward1 = Reward(id="r1", name="Coffee", weight=10, type=RewardType.REAL, pieces_required=1)
    reward2 = Reward(id="r2", name="Book", weight=10, type=RewardType.REAL, pieces_required=10)
    reward3 = Reward(id="r3", name="Massage", weight=10, type=RewardType.REAL, pieces_required=10)

    # Create progress entries
    progress_list = [
        RewardProgress(
            id="p1", user_id=mock_active_user.id, reward_id="r1",
            pieces_earned=5, pieces_required=10, status=RewardStatus.PENDING, claimed=False
        ),
        RewardProgress(
            id="p2", user_id=mock_active_user.id, reward_id="r2",
            pieces_earned=10, pieces_required=10, status=RewardStatus.ACHIEVED, claimed=False
        ),
        RewardProgress(
            id="p3", user_id=mock_active_user.id, reward_id="r3",
            pieces_earned=10, pieces_required=10, status=RewardStatus.CLAIMED, claimed=True
        )
    ]

    mock_reward_service.get_all_progress_for_user.return_value = progress_list
    mock_reward_service.reward_repo.get_by_id.side_effect = lambda rid: {
        "r1": reward1, "r2": reward2, "r3": reward3
    }[rid]

    await my_rewards_command(mock_telegram_update, context=None)

    # Verify message contains all rewards with correct status
    call_args = mock_telegram_update.message.reply_text.call_args[0][0]

    # Pending reward
    assert "Coffee" in call_args
    assert "5/10" in call_args or "5 / 10" in call_args
    assert "🕒" in call_args  # Pending emoji

    # Achieved reward
    assert "Book" in call_args
    assert "⏳" in call_args  # Achieved emoji

    # Claimed reward
    assert "Massage" in call_args
    assert "✅" in call_args  # Claimed emoji
```

#### Manual Tests

**Test Script: MAN-TC5-001 - Rewards Progress Display**

**Prerequisites:**
- Active user
- Reward progress:
  - Coffee (instant, 1 piece): ACHIEVED (ready to claim)
  - Book (10 pieces): PENDING (3/10 pieces earned)
  - Massage (10 pieces): CLAIMED (already claimed)

**Steps:**
1. Send `/my_rewards` command
2. Observe rewards list
3. Verify each reward shows:
   - Name
   - Status emoji (🕒 pending, ⏳ achieved, ✅ claimed)
   - Progress (X/Y pieces)
   - Piece value (if applicable)
4. Take screenshot

**Expected Result:**
```
🎁 Your Rewards Progress:

⏳ Coffee - Ready to claim!
Use: /claim_reward Coffee

🕒 Book - 3/10 pieces ($3.00 / $10.00)
Keep going! 7 more pieces to unlock.

✅ Massage - Claimed!
```

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-006: /claim_reward Command

#### Automated Tests

**File:** `tests/test_bot_handlers.py::TestClaimRewardCommand`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC6.1 | User not found (all languages) | ✅ Implemented | High |
| TC6.2 | Inactive user blocked (all languages) | ✅ Implemented | High |
| TC6.3 | Missing reward name argument | ❌ Missing | High |
| TC6.4 | Reward not found | ❌ Missing | High |
| TC6.5 | Reward not achieved yet (still pending) | ❌ Missing | High |
| TC6.6 | Successful claim (ACHIEVED → CLAIMED) | ❌ Missing | High |
| TC6.7 | Already claimed reward (error) | ❌ Missing | High |
| TC6.8 | Partial name match handling | ❌ Missing | Medium |
| TC6.9 | Multi-language reward name handling | ❌ Missing | Medium |
| TC6.10 | Case-insensitive reward lookup | ❌ Missing | Medium |

**Implementation Example (TC6.6):**

```python
@pytest.mark.asyncio
@patch('src.bot.handlers.reward_handlers.reward_service')
@patch('src.bot.handlers.reward_handlers.user_repository')
async def test_successful_claim(
    mock_user_repo, mock_reward_service, mock_telegram_update, mock_active_user
):
    """Successfully claim an achieved reward."""
    from src.models.reward import Reward, RewardType
    from src.models.reward_progress import RewardProgress, RewardStatus

    mock_user_repo.get_by_telegram_id.return_value = mock_active_user

    reward = Reward(id="r1", name="Coffee", weight=10, type=RewardType.REAL, pieces_required=1)

    # Before claim: ACHIEVED
    achieved_progress = RewardProgress(
        id="p1", user_id=mock_active_user.id, reward_id="r1",
        pieces_earned=1, pieces_required=1, status=RewardStatus.ACHIEVED, claimed=False
    )

    # After claim: CLAIMED
    claimed_progress = RewardProgress(
        id="p1", user_id=mock_active_user.id, reward_id="r1",
        pieces_earned=1, pieces_required=1, status=RewardStatus.CLAIMED, claimed=True
    )

    mock_reward_service.reward_repo.get_by_name.return_value = reward
    mock_reward_service.progress_repo.get_by_user_and_reward.return_value = achieved_progress
    mock_reward_service.mark_reward_claimed.return_value = claimed_progress

    # Create context with args
    context = Mock()
    context.args = ["Coffee"]

    await claim_reward_command(mock_telegram_update, context=context)

    # Verify claim service was called
    mock_reward_service.mark_reward_claimed.assert_called_once_with(
        mock_active_user.id, "r1"
    )

    # Verify success message
    call_args = mock_telegram_update.message.reply_text.call_args[0][0]
    assert "Coffee" in call_args
    assert "claimed" in call_args.lower() or "🎉" in call_args
```

#### Manual Tests

**Test Script: MAN-TC6-001 - Successful Reward Claim**

**Prerequisites:**
- Active user
- Reward "Coffee" is ACHIEVED (ready to claim)

**Steps:**
1. Send `/my_rewards` to verify Coffee is claimable
2. Send `/claim_reward Coffee`
3. Observe success message
4. Send `/my_rewards` again
5. Verify Coffee now shows as CLAIMED (✅)

**Expected Result:**
- Step 3: Success message "🎉 Congratulations! You claimed: Coffee"
- Step 5: Coffee shows status ✅ CLAIMED

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC6-002 - Claim Pending Reward (Should Fail)**

**Prerequisites:**
- Active user
- Reward "Book" is PENDING (only 3/10 pieces earned)

**Steps:**
1. Send `/claim_reward Book`
2. Observe error message

**Expected Result:**
- Error message: "❌ Reward 'Book' is not yet achieved. You have 3/10 pieces. Keep logging habits!"
- Reward status remains PENDING

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC6-003 - Missing Reward Name**

**Prerequisites:**
- Active user

**Steps:**
1. Send `/claim_reward` (without reward name)
2. Observe error message

**Expected Result:**
- Error message: "❌ Usage: /claim_reward <reward_name>"
- Example provided

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-BOT-007: /settings Command ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_settings_handler.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC7.1 | User not found | ❌ Missing | High |
| TC7.2 | Inactive user blocked | ❌ Missing | High |
| TC7.3 | Settings menu display | ❌ Missing | High |
| TC7.4 | Language selection button callback | ❌ Missing | High |
| TC7.5 | Change language success (en → ru) | ❌ Missing | High |
| TC7.6 | Change language success (ru → kk) | ❌ Missing | High |
| TC7.7 | Change language success (kk → en) | ❌ Missing | High |
| TC7.8 | Back to settings button | ❌ Missing | Medium |
| TC7.9 | Invalid callback data handling | ❌ Missing | Medium |
| TC7.10 | Language update failure handling | ❌ Missing | Medium |
| TC7.11 | Conversation state management | ❌ Missing | Low |

**Implementation Example (TC7.5):**

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery, User as TelegramUser

from src.bot.handlers.settings_handler import (
    settings_command,
    select_language_callback,
    change_language_callback,
    AWAITING_SETTINGS_SELECTION,
    AWAITING_LANGUAGE_SELECTION
)
from src.models.user import User

@pytest.mark.asyncio
@patch('src.bot.handlers.settings_handler.set_user_language')
@patch('src.bot.handlers.settings_handler.user_repository')
async def test_change_language_en_to_ru(mock_user_repo, mock_set_language):
    """Test changing language from English to Russian."""
    # Setup user with English language
    user = User(
        id="user123",
        telegram_id="999999999",
        name="Test User",
        active=True,
        language="en"
    )
    mock_user_repo.get_by_telegram_id.return_value = user
    mock_set_language.return_value = True  # Success

    # Create callback query for language change
    telegram_user = TelegramUser(id=999999999, first_name="Test", is_bot=False)
    callback_query = Mock(spec=CallbackQuery)
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    callback_query.data = "lang_ru"  # Select Russian

    update = Mock(spec=Update)
    update.callback_query = callback_query
    update.effective_user = telegram_user

    # Execute
    result = await change_language_callback(update, context=None)

    # Verify language update was called
    mock_set_language.assert_called_once_with("999999999", "ru")

    # Verify conversation continues
    assert result == AWAITING_SETTINGS_SELECTION

    # Verify message was edited with Russian text
    callback_query.edit_message_text.assert_called_once()
    call_args = callback_query.edit_message_text.call_args

    # The message should now be in Russian
    from src.bot.messages import msg
    expected_text = msg('SETTINGS_MENU', 'ru')
    assert call_args[1]['text'] == expected_text
```

#### Manual Tests

**Test Script: MAN-TC7-001 - Complete Language Change Flow**

**Prerequisites:**
- Active user currently set to English language
- Test bot running

**Steps:**
1. Send `/settings` command
2. Verify settings menu appears in English
3. Tap "Select Language" button
4. Verify language selection menu appears with 3 options:
   - 🇬🇧 English
   - 🇷🇺 Русский
   - 🇰🇿 Қазақша
5. Tap "🇷🇺 Русский" button
6. Verify settings menu reappears now in Russian (Cyrillic text)
7. Send `/help` command
8. Verify help text is now in Russian
9. Send `/settings` again
10. Change back to English
11. Verify all messages return to English

**Expected Result:**
- Settings menu displays correctly
- Language selection shows 3 options with flags
- After selection, ALL bot messages switch to selected language
- Language persists across sessions (stored in database)

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-TC7-002 - Back Button Navigation**

**Prerequisites:**
- Active user
- Test bot running

**Steps:**
1. Send `/settings`
2. Tap "Select Language" button
3. Tap "⬅️ Back to Settings" button
4. Verify returns to main settings menu
5. Verify no language change occurred

**Expected Result:**
- Back button successfully returns to settings menu
- No unintended language changes
- Message edited (not new message sent)

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

## Phase 2: Service Layer Tests

### TC-SVC-001: HabitService

#### Automated Tests

**File:** `tests/test_habit_service.py::TestHabitCompletion`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC1.1 | Successful habit completion with reward | ✅ Implemented | High |
| TC1.2 | User not found error | ✅ Implemented | High |
| TC1.3 | Habit not found error | ✅ Implemented | High |
| TC1.4 | No reward completion (NONE type) | ✅ Implemented | High |
| TC1.5 | Get all active habits | ✅ Implemented | High |
| TC1.6 | Inactive user processing attempt | ❌ Missing | High |
| TC1.7 | Inactive habit processing attempt | ❌ Missing | High |
| TC1.8 | Same-day duplicate logging | ❌ Missing | High |
| TC1.9 | Multiple completions in one day | ❌ Missing | Medium |
| TC1.10 | Reward progress update verification | ❌ Missing | High |
| TC1.11 | Virtual reward handling | ❌ Missing | Medium |
| TC1.12 | Real reward handling | ❌ Missing | Medium |
| TC1.13 | Edge case: habit weight = 0 | ❌ Missing | Low |
| TC1.14 | Edge case: habit weight = 100 | ❌ Missing | Low |
| TC1.15 | Multi-piece reward progress | ❌ Missing | High |

**Implementation Example (TC1.6):**

```python
@patch('src.services.habit_service.user_repository')
def test_inactive_user_processing(mock_user_repo, habit_service):
    """Test that inactive user cannot log habits."""
    # Create inactive user
    inactive_user = User(
        id="user123",
        telegram_id="123456789",
        name="Inactive User",
        active=False  # User is inactive
    )
    mock_user_repo.get_by_telegram_id.return_value = inactive_user

    with patch.object(habit_service, 'user_repo', mock_user_repo):
        with pytest.raises(ValueError, match="inactive|not active"):
            habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking"
            )
```

**Implementation Example (TC1.8):**

```python
@patch('src.services.habit_service.user_repository')
@patch('src.services.habit_service.habit_repository')
@patch('src.services.habit_service.streak_service')
@patch('src.services.habit_service.habit_log_repository')
def test_same_day_duplicate_logging(
    mock_log_repo, mock_streak_service, mock_habit_repo,
    mock_user_repo, habit_service, mock_user, mock_habit
):
    """Test logging same habit twice in one day."""
    from datetime import date
    from src.models.habit_log import HabitLog

    # Setup
    mock_user_repo.get_by_telegram_id.return_value = mock_user
    mock_habit_repo.get_by_name.return_value = mock_habit

    # Mock: Habit already logged today
    today = date.today()
    existing_log = HabitLog(
        user_id=mock_user.id,
        habit_id=mock_habit.id,
        streak_count=5,
        habit_weight=10,
        total_weight_applied=15.0,
        last_completed_date=today
    )
    mock_log_repo.get_last_log_for_habit.return_value = existing_log

    # Mock streak service returns same streak (no increment)
    mock_streak_service.calculate_streak.return_value = 5

    with patch.object(habit_service, 'user_repo', mock_user_repo), \
         patch.object(habit_service, 'habit_repo', mock_habit_repo), \
         patch.object(habit_service, 'streak_service', mock_streak_service), \
         patch.object(habit_service, 'habit_log_repo', mock_log_repo):

        result = habit_service.process_habit_completion(
            user_telegram_id="123456789",
            habit_name="Walking"
        )

    # Verify: Streak did not increment (still 5, not 6)
    assert result.streak_count == 5

    # Verify: habit_log_repo.create() should NOT be called again
    # (Or should be called but with same streak - depends on implementation)
    # Document current behavior
```

#### Manual Tests

**Test Script: MAN-SVC1-001 - Multi-Piece Reward Progress**

**Prerequisites:**
- Active user
- Reward "Massage" requires 10 pieces
- User has 0 pieces currently

**Steps:**
1. Log habit 10 times (across multiple days)
2. After each logging, check progress:
   - Day 1: `/my_rewards` → Verify "Massage: 1/10"
   - Day 2: `/my_rewards` → Verify "Massage: 2/10"
   - ...
   - Day 10: `/my_rewards` → Verify "Massage: 10/10 ⏳ ACHIEVED"
3. Claim reward: `/claim_reward Massage`
4. Verify status changes to CLAIMED

**Expected Result:**
- Progress increments correctly after each habit logging
- Status changes from PENDING → ACHIEVED → CLAIMED at correct thresholds

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-SVC-002: StreakService

#### Automated Tests

**File:** `tests/test_streak_service.py::TestStreakCalculation`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC2.1 | First-time completion (streak = 1) | ✅ Implemented | High |
| TC2.2 | Same-day completion (no increment) | ✅ Implemented | High |
| TC2.3 | Consecutive day completion (increment) | ✅ Implemented | High |
| TC2.4 | Broken streak reset | ✅ Implemented | High |
| TC2.5 | Get last completed date (exists) | ✅ Implemented | High |
| TC2.6 | Get last completed date (none) | ✅ Implemented | High |
| TC2.7 | Multi-habit different completion dates | ✅ Implemented | High |
| TC2.8 | Streak after 2-day gap (reset to 1) | ❌ Missing | Medium |
| TC2.9 | Streak after 1-week gap | ❌ Missing | Low |
| TC2.10 | Streak persistence after midnight | ❌ Missing | Medium |
| TC2.11 | Timezone boundary testing | ❌ Missing | Low |
| TC2.12 | Leap year date handling | ❌ Missing | Low |
| TC2.13 | Year boundary (Dec 31 → Jan 1) | ❌ Missing | Medium |
| TC2.14 | Max streak calculation (999+ days) | ❌ Missing | Low |
| TC2.15 | get_current_streak() vs calculate_streak() | ❌ Missing | High |
| TC2.16 | Multiple habits same user | ❌ Missing | High |
| TC2.17 | Empty habit logs for user | ❌ Missing | Medium |

**Implementation Example (TC2.13):**

```python
def test_year_boundary_streak(streak_service, mock_habit_log_repo):
    """Test streak continues across year boundary (Dec 31 → Jan 1)."""
    from datetime import date

    # Dec 31, 2024
    dec_31 = date(2024, 12, 31)
    mock_log = HabitLog(
        user_id="user123",
        habit_id="habit123",
        streak_count=100,
        habit_weight=10,
        total_weight_applied=20.0,
        last_completed_date=dec_31
    )
    mock_habit_log_repo.get_last_log_for_habit.return_value = mock_log

    # Mock "today" as Jan 1, 2025
    with patch('src.services.streak_service.date') as mock_date:
        mock_date.today.return_value = date(2025, 1, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        with patch.object(streak_service, 'habit_log_repo', mock_habit_log_repo):
            streak = streak_service.calculate_streak("user123", "habit123")

    # Verify: Streak incremented (consecutive day despite year change)
    assert streak == 101
```

#### Manual Tests

**Test Script: MAN-SVC2-001 - Midnight Streak Persistence**

**Prerequisites:**
- Active user
- Habit "Walking" has a 5-day streak

**Steps:**
1. At 11:50 PM: Check `/streaks` → Verify "Walking: 5 days"
2. Wait until 12:01 AM (next day)
3. Check `/streaks` again → Verify "Walking: 5 days" (still shows 5, not reset)
4. Log "Walking" habit after midnight
5. Check `/streaks` → Verify "Walking: 6 days"

**Expected Result:**
- Streak persists across midnight
- Streak increments correctly when logged next day
- No unintended reset at midnight

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-SVC-003: RewardService

#### Automated Tests

**File:** `tests/test_reward_service.py`

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC3.1 | Basic weight calculation | ✅ Implemented | High |
| TC3.2 | Weight with high streak | ✅ Implemented | High |
| TC3.3 | Weight with habit multiplier | ✅ Implemented | High |
| TC3.4 | Select reward from multiple | ✅ Implemented | High |
| TC3.5 | Select reward empty list (fallback NONE) | ✅ Implemented | High |
| TC3.6 | Create new progress | ✅ Implemented | High |
| TC3.7 | Achieve cumulative reward | ✅ Implemented | High |
| TC3.8 | Mark reward claimed | ✅ Implemented | High |
| TC3.9 | Weight calculation with streak=0 | ❌ Missing | Medium |
| TC3.10 | Weight with max streak (999) | ❌ Missing | Low |
| TC3.11 | Reward selection probability distribution | ❌ Missing | Medium |
| TC3.12 | NONE type reward has highest weight | ❌ Missing | Medium |
| TC3.13 | VIRTUAL vs REAL reward selection | ❌ Missing | Medium |
| TC3.14 | Today's awarded rewards filtering | ❌ Missing | High |
| TC3.15 | Progress update idempotency | ❌ Missing | Medium |
| TC3.16 | Claim already claimed reward (error) | ❌ Missing | High |
| TC3.17 | Claim non-existent progress (error) | ❌ Missing | Medium |
| TC3.18 | Multi-piece edge case (exactly at pieces_required) | ❌ Missing | Medium |
| TC3.19 | Piece value calculation accuracy | ❌ Missing | Low |
| TC3.20 | Get all rewards for user | ❌ Missing | Medium |
| TC3.21 | Filter rewards by status | ❌ Missing | Medium |

**Implementation Example (TC3.14):**

```python
@patch('src.services.reward_service.reward_repository')
@patch('src.services.reward_service.habit_log_repository')
def test_todays_awarded_rewards_filtering(
    mock_log_repo, mock_reward_repo, reward_service
):
    """Test that rewards awarded today are filtered correctly."""
    from datetime import date
    from src.models.habit_log import HabitLog
    from src.models.reward import Reward, RewardType

    today = date.today()

    # Mock: Rewards already awarded today
    today_logs = [
        HabitLog(
            user_id="user123",
            habit_id="habit1",
            streak_count=5,
            habit_weight=10,
            total_weight_applied=15.0,
            last_completed_date=today,
            reward_id="r1"  # Coffee already awarded today
        ),
        HabitLog(
            user_id="user123",
            habit_id="habit2",
            streak_count=3,
            habit_weight=10,
            total_weight_applied=13.0,
            last_completed_date=today,
            reward_id="r2"  # Book already awarded today
        )
    ]
    mock_log_repo.get_logs_by_user_and_date.return_value = today_logs

    # Available rewards
    all_rewards = [
        Reward(id="r1", name="Coffee", weight=20, type=RewardType.REAL, pieces_required=1),
        Reward(id="r2", name="Book", weight=20, type=RewardType.REAL, pieces_required=1),
        Reward(id="r3", name="Movie", weight=20, type=RewardType.REAL, pieces_required=1),
        Reward(id="r_none", name="No reward", weight=40, type=RewardType.NONE, pieces_required=1)
    ]
    mock_reward_repo.get_all_active.return_value = all_rewards

    with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
         patch.object(reward_service, 'habit_log_repo', mock_log_repo):

        # Get today's awarded rewards
        awarded_today = reward_service.get_todays_awarded_rewards("user123")

        # Select reward (should exclude Coffee and Book)
        selected = reward_service.select_reward(total_weight=15.0, user_id="user123")

    # Verify: Coffee and Book were filtered out
    assert len(awarded_today) == 2
    assert "r1" in [r.id for r in awarded_today]
    assert "r2" in [r.id for r in awarded_today]

    # Verify: Selected reward is NOT Coffee or Book
    assert selected.id not in ["r1", "r2"]
    # Should be either Movie or None
    assert selected.id in ["r3", "r_none"]
```

#### Manual Tests

**Test Script: MAN-SVC3-001 - Reward Selection Probability**

**Prerequisites:**
- Active user
- Rewards configured:
  - Coffee (REAL): weight = 10
  - Book (REAL): weight = 10
  - Movie (REAL): weight = 10
  - No reward (NONE): weight = 70

**Steps:**
1. Log 100 habits (across multiple days)
2. Track which reward was earned each time
3. Calculate distribution:
   - Coffee: X times (expect ~10%)
   - Book: X times (expect ~10%)
   - Movie: X times (expect ~10%)
   - No reward: X times (expect ~70%)

**Expected Result:**
- Distribution matches configured weights (within reasonable variance)
- No reward is most common (~70% of the time)
- Each REAL reward appears roughly equally

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-SVC-004: NLPService ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_nlp_service.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC4.1 | Exact habit name match | ❌ Missing | High |
| TC4.2 | Partial habit name match | ❌ Missing | High |
| TC4.3 | Case-insensitive matching | ❌ Missing | High |
| TC4.4 | Synonym matching | ❌ Missing | High |
| TC4.5 | No match found (confidence < threshold) | ❌ Missing | High |
| TC4.6 | Multi-word habit names | ❌ Missing | Medium |
| TC4.7 | Special characters in input | ❌ Missing | Medium |
| TC4.8 | Empty input handling | ❌ Missing | Medium |
| TC4.9 | Very long input (>1000 chars) | ❌ Missing | Low |
| TC4.10 | Multi-language text classification | ❌ Missing | Medium |

**Implementation Example (TC4.1 - TC4.5):**

```python
import pytest
from src.services.nlp_service import nlp_service
from src.models.habit import Habit

@pytest.fixture
def sample_habits():
    """Sample habits for NLP testing."""
    return [
        Habit(id="h1", name="Walking", weight=10, category="fitness", active=True),
        Habit(id="h2", name="Reading", weight=10, category="education", active=True),
        Habit(id="h3", name="Meditation", weight=10, category="wellness", active=True),
        Habit(id="h4", name="Drinking Water", weight=10, category="health", active=True),
        Habit(id="h5", name="Pushups", weight=10, category="fitness", active=True)
    ]

def test_exact_habit_name_match(sample_habits):
    """Test exact match of habit name."""
    matched_habit = nlp_service.classify_habit_text("Walking", sample_habits)
    assert matched_habit is not None
    assert matched_habit.name == "Walking"

def test_partial_habit_name_match(sample_habits):
    """Test partial match (e.g., 'walk' matches 'Walking')."""
    matched_habit = nlp_service.classify_habit_text("went for a walk", sample_habits)
    assert matched_habit is not None
    assert matched_habit.name == "Walking"

def test_case_insensitive_matching(sample_habits):
    """Test case-insensitive matching."""
    test_cases = ["WALKING", "walking", "WaLkInG", "WALK"]
    for text in test_cases:
        matched_habit = nlp_service.classify_habit_text(text, sample_habits)
        assert matched_habit is not None
        assert matched_habit.name == "Walking"

def test_synonym_matching(sample_habits):
    """Test synonym detection."""
    # Walking synonyms
    assert nlp_service.classify_habit_text("I went for a stroll", sample_habits).name == "Walking"
    assert nlp_service.classify_habit_text("took a walk", sample_habits).name == "Walking"

    # Reading synonyms
    assert nlp_service.classify_habit_text("read a book", sample_habits).name == "Reading"
    assert nlp_service.classify_habit_text("I was reading", sample_habits).name == "Reading"

    # Meditation synonyms
    assert nlp_service.classify_habit_text("I meditated", sample_habits).name == "Meditation"

    # Water synonyms
    assert nlp_service.classify_habit_text("drank water", sample_habits).name == "Drinking Water"
    assert nlp_service.classify_habit_text("hydrated", sample_habits).name == "Drinking Water"

def test_no_match_found(sample_habits):
    """Test when no habit matches the input text."""
    matched_habit = nlp_service.classify_habit_text("xyz random text", sample_habits)
    assert matched_habit is None

def test_multi_word_habit_names(sample_habits):
    """Test matching multi-word habit names."""
    matched_habit = nlp_service.classify_habit_text("I drank water", sample_habits)
    assert matched_habit is not None
    assert matched_habit.name == "Drinking Water"

def test_special_characters_in_input(sample_habits):
    """Test input with special characters."""
    matched_habit = nlp_service.classify_habit_text("I did 50 pushups!!!", sample_habits)
    assert matched_habit is not None
    assert matched_habit.name == "Pushups"

def test_empty_input(sample_habits):
    """Test empty input handling."""
    matched_habit = nlp_service.classify_habit_text("", sample_habits)
    assert matched_habit is None

def test_very_long_input(sample_habits):
    """Test very long input text."""
    long_text = "I went for a very long walk today " * 100  # 600+ chars
    matched_habit = nlp_service.classify_habit_text(long_text, sample_habits)
    assert matched_habit is not None
    assert matched_habit.name == "Walking"
```

#### Manual Tests

**Test Script: MAN-SVC4-001 - NLP Natural Language Understanding**

**Prerequisites:**
- Active user
- Habits: Walking, Reading, Meditation, Pushups, Drinking Water

**Steps:**
Test the following inputs and verify correct habit detection:

| Input Text | Expected Habit Matched |
|------------|----------------------|
| "I went for a 30 minute walk" | Walking |
| "walked 5000 steps" | Walking |
| "took a stroll in the park" | Walking |
| "read 20 pages" | Reading |
| "finished chapter 5" | Reading |
| "meditated for 10 minutes" | Meditation |
| "did 50 pushups" | Pushups |
| "completed my pushup routine" | Pushups |
| "drank 8 glasses of water" | Drinking Water |
| "stayed hydrated" | Drinking Water |
| "xyz random nonsense" | No match (show error) |

**Expected Result:**
- NLP correctly identifies habits from natural language
- Handles variations, synonyms, and context
- Gracefully handles no match

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

## Phase 3: Repository Layer Tests

### TC-REPO-001: UserRepository ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_user_repository.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC1.1 | Get by telegram_id (exists) | ❌ Missing | High |
| TC1.2 | Get by telegram_id (not found) | ❌ Missing | High |
| TC1.3 | Get by id (exists) | ❌ Missing | High |
| TC1.4 | Get by id (not found) | ❌ Missing | High |
| TC1.5 | Create new user | ❌ Missing | High |
| TC1.6 | Update user (name change) | ❌ Missing | Medium |
| TC1.7 | Update user (language change) | ❌ Missing | High |
| TC1.8 | Update user (active status change) | ❌ Missing | High |
| TC1.9 | Get all users | ❌ Missing | Low |
| TC1.10 | Filter active users only | ❌ Missing | Medium |
| TC1.11 | Duplicate telegram_id handling | ❌ Missing | Medium |

**Implementation Example:**

```python
import pytest
from unittest.mock import Mock, patch
from src.airtable.repositories import UserRepository
from src.models.user import User

@pytest.fixture
def user_repository():
    """Create user repository instance."""
    return UserRepository()

@pytest.fixture
def mock_airtable_table():
    """Mock Airtable table."""
    return Mock()

def test_get_by_telegram_id_exists(user_repository, mock_airtable_table):
    """Test getting user by telegram_id when exists."""
    # Mock Airtable response
    mock_record = {
        'id': 'rec123',
        'fields': {
            'telegram_id': '123456789',
            'name': 'Test User',
            'active': True,
            'language': 'en'
        }
    }
    mock_airtable_table.all.return_value = [mock_record]

    with patch.object(user_repository, 'table', mock_airtable_table):
        user = user_repository.get_by_telegram_id('123456789')

    assert user is not None
    assert user.telegram_id == '123456789'
    assert user.name == 'Test User'
    assert user.active is True
    assert user.language == 'en'

def test_get_by_telegram_id_not_found(user_repository, mock_airtable_table):
    """Test getting user by telegram_id when not found."""
    mock_airtable_table.all.return_value = []

    with patch.object(user_repository, 'table', mock_airtable_table):
        user = user_repository.get_by_telegram_id('999999999')

    assert user is None

def test_create_new_user(user_repository, mock_airtable_table):
    """Test creating a new user."""
    new_user = User(
        id=None,  # Will be assigned by Airtable
        telegram_id='999999999',
        name='New User',
        active=True,
        language='en'
    )

    # Mock Airtable create response
    mock_record = {
        'id': 'rec456',
        'fields': {
            'telegram_id': '999999999',
            'name': 'New User',
            'active': True,
            'language': 'en'
        }
    }
    mock_airtable_table.create.return_value = mock_record

    with patch.object(user_repository, 'table', mock_airtable_table):
        created_user = user_repository.create(new_user)

    assert created_user.id == 'rec456'
    assert created_user.telegram_id == '999999999'
    assert created_user.name == 'New User'

def test_update_user_language(user_repository, mock_airtable_table):
    """Test updating user language."""
    user_id = 'rec123'

    # Mock Airtable update response
    mock_record = {
        'id': user_id,
        'fields': {
            'telegram_id': '123456789',
            'name': 'Test User',
            'active': True,
            'language': 'ru'  # Updated to Russian
        }
    }
    mock_airtable_table.update.return_value = mock_record

    with patch.object(user_repository, 'table', mock_airtable_table):
        updated_user = user_repository.update(user_id, {'language': 'ru'})

    assert updated_user.language == 'ru'
    mock_airtable_table.update.assert_called_once_with(user_id, {'language': 'ru'})
```

#### Manual Tests

**Test Script: MAN-REPO1-001 - User Language Persistence**

**Prerequisites:**
- Access to Airtable test database
- Test user exists

**Steps:**
1. Via Telegram: User changes language to Russian using `/settings`
2. Open Airtable → Users table
3. Find user record by telegram_id
4. Verify "language" field = "ru"
5. Restart bot
6. User sends `/help`
7. Verify message is still in Russian (language persisted)

**Expected Result:**
- Language change reflected in Airtable immediately
- Language persists after bot restart
- Database record matches user's selected language

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-REPO-002: HabitRepository ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_habit_repository.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC2.1 | Get by id (exists) | ❌ Missing | High |
| TC2.2 | Get by id (not found) | ❌ Missing | High |
| TC2.3 | Get by name (exact match) | ❌ Missing | High |
| TC2.4 | Get by name (case-insensitive) | ❌ Missing | High |
| TC2.5 | Get by name (not found) | ❌ Missing | Medium |
| TC2.6 | Get all active habits | ❌ Missing | High |
| TC2.7 | Get all habits (including inactive) | ❌ Missing | Medium |
| TC2.8 | Create new habit | ❌ Missing | Low |
| TC2.9 | Update habit (weight change) | ❌ Missing | Low |
| TC2.10 | Update habit (active status) | ❌ Missing | Medium |
| TC2.11 | Filter by category | ❌ Missing | Low |

**Implementation Example:**

```python
import pytest
from unittest.mock import Mock, patch
from src.airtable.repositories import HabitRepository
from src.models.habit import Habit

@pytest.fixture
def habit_repository():
    """Create habit repository instance."""
    return HabitRepository()

def test_get_all_active_habits(habit_repository):
    """Test getting only active habits."""
    mock_table = Mock()

    # Mock Airtable response with both active and inactive habits
    mock_records = [
        {
            'id': 'rec1',
            'fields': {
                'name': 'Walking',
                'weight': 10,
                'category': 'fitness',
                'active': True
            }
        },
        {
            'id': 'rec2',
            'fields': {
                'name': 'Old Habit',
                'weight': 10,
                'category': 'other',
                'active': False
            }
        },
        {
            'id': 'rec3',
            'fields': {
                'name': 'Reading',
                'weight': 15,
                'category': 'education',
                'active': True
            }
        }
    ]
    mock_table.all.return_value = mock_records

    with patch.object(habit_repository, 'table', mock_table):
        active_habits = habit_repository.get_all_active()

    # Should only return active habits
    assert len(active_habits) == 2
    assert all(habit.active for habit in active_habits)
    habit_names = [h.name for h in active_habits]
    assert 'Walking' in habit_names
    assert 'Reading' in habit_names
    assert 'Old Habit' not in habit_names

def test_get_by_name_case_insensitive(habit_repository):
    """Test getting habit by name (case-insensitive)."""
    mock_table = Mock()

    mock_record = {
        'id': 'rec1',
        'fields': {
            'name': 'Walking',
            'weight': 10,
            'category': 'fitness',
            'active': True
        }
    }
    mock_table.all.return_value = [mock_record]

    with patch.object(habit_repository, 'table', mock_table):
        # Test various cases
        habit1 = habit_repository.get_by_name('Walking')
        habit2 = habit_repository.get_by_name('walking')
        habit3 = habit_repository.get_by_name('WALKING')

    assert habit1 is not None
    assert habit2 is not None
    assert habit3 is not None
    assert habit1.name == 'Walking'
    assert habit2.name == 'Walking'
    assert habit3.name == 'Walking'
```

---

### TC-REPO-003: HabitLogRepository ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_habit_log_repository.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC3.1 | Create new log | ❌ Missing | High |
| TC3.2 | Get last log for habit (exists) | ❌ Missing | High |
| TC3.3 | Get last log for habit (not found) | ❌ Missing | High |
| TC3.4 | Get logs by user (multiple logs) | ❌ Missing | High |
| TC3.5 | Get logs by user (empty) | ❌ Missing | Medium |
| TC3.6 | Get logs by date range | ❌ Missing | Medium |
| TC3.7 | Get logs for specific habit | ❌ Missing | Medium |
| TC3.8 | Count logs per habit | ❌ Missing | Low |
| TC3.9 | Sort by date (ascending/descending) | ❌ Missing | Low |
| TC3.10 | Filter by streak count | ❌ Missing | Low |

---

### TC-REPO-004: RewardRepository ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_reward_repository.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC4.1 | Get by id (exists) | ❌ Missing | High |
| TC4.2 | Get by id (not found) | ❌ Missing | High |
| TC4.3 | Get by name (exact match) | ❌ Missing | High |
| TC4.4 | Get by name (case-insensitive) | ❌ Missing | High |
| TC4.5 | Get all active rewards | ❌ Missing | High |
| TC4.6 | Get all rewards (including inactive) | ❌ Missing | Medium |
| TC4.7 | Filter by type (REAL/VIRTUAL/NONE) | ❌ Missing | Medium |
| TC4.8 | Create new reward | ❌ Missing | Low |
| TC4.9 | Update reward (weight change) | ❌ Missing | Low |
| TC4.10 | Update reward (pieces_required change) | ❌ Missing | Low |
| TC4.11 | Sort by weight | ❌ Missing | Low |

---

### TC-REPO-005: RewardProgressRepository ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_reward_progress_repository.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC5.1 | Get by user and reward (exists) | ❌ Missing | High |
| TC5.2 | Get by user and reward (not found) | ❌ Missing | High |
| TC5.3 | Get all progress for user | ❌ Missing | High |
| TC5.4 | Get all progress for reward | ❌ Missing | Medium |
| TC5.5 | Create new progress | ❌ Missing | High |
| TC5.6 | Update progress (increment pieces_earned) | ❌ Missing | High |
| TC5.7 | Update progress (mark claimed) | ❌ Missing | High |
| TC5.8 | Filter by status (PENDING/ACHIEVED/CLAIMED) | ❌ Missing | Medium |
| TC5.9 | Get achieved (claimable) rewards | ❌ Missing | High |
| TC5.10 | Computed field handling (pieces_required) | ❌ Missing | High |
| TC5.11 | Status formula verification | ❌ Missing | High |

**Implementation Example (TC5.10):**

```python
def test_computed_field_readonly(reward_progress_repository):
    """Test that computed field pieces_required is not set manually."""
    from src.models.reward_progress import RewardProgress, RewardStatus

    mock_table = Mock()

    progress = RewardProgress(
        id=None,
        user_id='user123',
        reward_id='reward456',
        pieces_earned=5,
        pieces_required=10,  # This is computed, should NOT be sent to Airtable
        status=RewardStatus.PENDING,
        claimed=False
    )

    # Mock Airtable create
    mock_table.create.return_value = {
        'id': 'rec789',
        'fields': {
            'user_id': ['user123'],
            'reward_id': ['reward456'],
            'pieces_earned': 5,
            'pieces_required': 10,  # Computed by Airtable formula
            'status': '🕒 Pending',
            'claimed': False
        }
    }

    with patch.object(reward_progress_repository, 'table', mock_table):
        created = reward_progress_repository.create(progress)

    # Verify: pieces_required was NOT included in create call
    call_args = mock_table.create.call_args[0][0]
    assert 'pieces_required' not in call_args
    assert 'pieces_earned' in call_args
    assert call_args['pieces_earned'] == 5
```

---

## Phase 4: Model Validation Tests

### TC-MODEL-001: User Model ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/test_models.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC1.1 | Valid user creation | ❌ Missing | High |
| TC1.2 | Missing required field (telegram_id) | ❌ Missing | High |
| TC1.3 | Invalid telegram_id format | ❌ Missing | Medium |
| TC1.4 | Default values (active=True, language='en') | ❌ Missing | Medium |
| TC1.5 | Language validation (supported languages only) | ❌ Missing | Medium |
| TC1.6 | Field type validation | ❌ Missing | Low |

**Implementation Example:**

```python
import pytest
from pydantic import ValidationError
from src.models.user import User

def test_valid_user_creation():
    """Test creating a valid user."""
    user = User(
        id='rec123',
        telegram_id='123456789',
        name='Test User',
        active=True,
        language='en'
    )

    assert user.telegram_id == '123456789'
    assert user.name == 'Test User'
    assert user.active is True
    assert user.language == 'en'

def test_missing_required_field():
    """Test that missing required field raises error."""
    with pytest.raises(ValidationError):
        User(
            id='rec123',
            # telegram_id missing!
            name='Test User',
            active=True,
            language='en'
        )

def test_default_values():
    """Test default values for optional fields."""
    user = User(
        id='rec123',
        telegram_id='123456789',
        name='Test User'
        # active and language not provided
    )

    assert user.active is True  # Default
    assert user.language == 'en'  # Default

def test_language_validation():
    """Test that only supported languages are allowed."""
    # Valid languages
    for lang in ['en', 'ru', 'kk']:
        user = User(
            id='rec123',
            telegram_id='123456789',
            name='Test User',
            language=lang
        )
        assert user.language == lang

    # Invalid language (if validation implemented)
    # with pytest.raises(ValidationError):
    #     User(
    #         id='rec123',
    #         telegram_id='123456789',
    #         name='Test User',
    #         language='xyz'  # Invalid
    #     )
```

---

### TC-MODEL-002: Habit Model ⚠️ NOT TESTED

#### Automated Tests

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC2.1 | Valid habit creation | ❌ Missing | High |
| TC2.2 | Missing required fields | ❌ Missing | High |
| TC2.3 | Weight validation (must be positive) | ❌ Missing | Medium |
| TC2.4 | Category validation | ❌ Missing | Low |
| TC2.5 | Active default value | ❌ Missing | Low |

---

### TC-MODEL-003: Reward Model ⚠️ NOT TESTED

#### Automated Tests

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC3.1 | Valid reward creation | ❌ Missing | High |
| TC3.2 | pieces_required validation (>= 1) | ❌ Missing | High |
| TC3.3 | RewardType enum validation | ❌ Missing | Medium |
| TC3.4 | piece_value optional handling | ❌ Missing | Low |
| TC3.5 | Weight validation | ❌ Missing | Low |

---

### TC-MODEL-004: RewardProgress Model ⚠️ NOT TESTED

#### Automated Tests

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC4.1 | Valid progress creation | ❌ Missing | High |
| TC4.2 | RewardStatus enum validation | ❌ Missing | Medium |
| TC4.3 | pieces_earned validation (>= 0) | ❌ Missing | Medium |
| TC4.4 | claimed default (False) | ❌ Missing | Low |
| TC4.5 | Field relationships validation | ❌ Missing | Low |

---

## Phase 5: Integration Tests

### TC-INT-001: Complete Habit Logging Flow ⚠️ NOT TESTED

#### Automated Tests

**File:** `tests/integration/test_habit_logging_flow.py` (NEW FILE NEEDED)

| Test ID | Description | Status | Priority |
|---------|-------------|--------|----------|
| TC1.1 | User logs habit → gets reward → progress updated | ❌ Missing | High |
| TC1.2 | User logs habit → no reward → only streak tracked | ❌ Missing | High |
| TC1.3 | Multi-day consecutive logging → streak increments | ❌ Missing | High |
| TC1.4 | Missed day → streak resets | ❌ Missing | High |
| TC1.5 | Multi-piece reward completion (10 logs → claim) | ❌ Missing | High |

**Implementation Example (TC1.1):**

```python
import pytest
from unittest.mock import patch, Mock
from datetime import date

@pytest.mark.asyncio
@patch('src.airtable.repositories.user_repository')
@patch('src.airtable.repositories.habit_repository')
@patch('src.airtable.repositories.habit_log_repository')
@patch('src.airtable.repositories.reward_repository')
@patch('src.airtable.repositories.reward_progress_repository')
async def test_complete_habit_logging_with_reward_flow(
    mock_progress_repo, mock_reward_repo, mock_log_repo,
    mock_habit_repo, mock_user_repo
):
    """
    Integration test: User logs habit → earns reward → progress updated.

    Flow:
    1. User sends /habit_done
    2. Selects "Walking" habit
    3. Habit logged to database
    4. Streak calculated (first time = 1)
    5. Reward selected (Coffee, instant reward)
    6. Reward progress created/updated
    7. Success message sent with reward info
    """
    from src.models.user import User
    from src.models.habit import Habit
    from src.models.reward import Reward, RewardType
    from src.models.reward_progress import RewardProgress, RewardStatus
    from src.services.habit_service import habit_service

    # Setup: User exists
    user = User(
        id='user123',
        telegram_id='123456789',
        name='Test User',
        active=True,
        language='en'
    )
    mock_user_repo.get_by_telegram_id.return_value = user

    # Setup: Habit exists
    habit = Habit(
        id='habit123',
        name='Walking',
        weight=10,
        category='fitness',
        active=True
    )
    mock_habit_repo.get_by_name.return_value = habit

    # Setup: No previous logs (first time)
    mock_log_repo.get_last_log_for_habit.return_value = None
    mock_log_repo.create.return_value = Mock()  # Log created successfully

    # Setup: Reward available
    reward = Reward(
        id='reward123',
        name='Coffee',
        weight=20,
        type=RewardType.REAL,
        pieces_required=1
    )
    mock_reward_repo.get_all_active.return_value = [reward]

    # Setup: No progress yet
    mock_progress_repo.get_by_user_and_reward.return_value = None

    # Mock progress creation
    def mock_create_progress(progress):
        progress.id = 'prog123'
        return progress
    mock_progress_repo.create.side_effect = mock_create_progress

    # Mock progress update
    def mock_update_progress(prog_id, updates):
        return RewardProgress(
            id=prog_id,
            user_id=user.id,
            reward_id=reward.id,
            pieces_earned=updates['pieces_earned'],
            pieces_required=1,
            status=RewardStatus.ACHIEVED,
            claimed=False
        )
    mock_progress_repo.update.side_effect = mock_update_progress

    # Execute: Process habit completion
    result = habit_service.process_habit_completion(
        user_telegram_id='123456789',
        habit_name='Walking'
    )

    # Verify: Habit logged
    assert result.habit_confirmed is True
    assert result.habit_name == 'Walking'

    # Verify: Streak = 1 (first time)
    assert result.streak_count == 1

    # Verify: Reward earned
    assert result.got_reward is True
    assert result.reward.name == 'Coffee'

    # Verify: Habit log created
    mock_log_repo.create.assert_called_once()

    # Verify: Reward progress updated
    mock_progress_repo.update.assert_called_once()
```

#### Manual Tests

**Test Script: MAN-INT1-001 - Complete 10-Day Streak with Multi-Piece Reward**

**Prerequisites:**
- Fresh test user (no previous logs)
- Habit: "Walking"
- Reward: "Massage" (requires 10 pieces)

**Steps:**

**Day 1:**
1. Send `/habit_done`
2. Select "Walking"
3. Verify success message shows: Streak = 1
4. Note if reward was earned
5. Send `/my_rewards`
6. Verify "Massage" progress: 1/10 pieces (if reward was Coffee, this might be 0/10)

**Day 2:**
7. Send `/habit_done`
8. Select "Walking"
9. Verify success message shows: Streak = 2
10. Send `/my_rewards`
11. Track Massage progress

**Days 3-9:**
Repeat logging "Walking" each day, tracking:
- Streak increments correctly (3, 4, 5, 6, 7, 8, 9)
- Massage progress increments (if earned each time)

**Day 10:**
12. Send `/habit_done`
13. Select "Walking"
14. Verify Streak = 10
15. Send `/my_rewards`
16. Verify "Massage" status:
    - If 10 pieces earned: Status = ⏳ ACHIEVED
    - If less: Continue logging until achieved

**After Achievement:**
17. Send `/claim_reward Massage`
18. Verify success message
19. Send `/my_rewards`
20. Verify "Massage" status = ✅ CLAIMED

**Expected Result:**
- Streak increments daily without issues
- Reward progress tracked accurately
- Status transitions: PENDING → ACHIEVED → CLAIMED
- No data loss or inconsistencies

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-INT-002: Reward Claiming Flow ⚠️ NOT TESTED

#### Manual Tests

**Test Script: MAN-INT2-001 - Multiple Rewards Claimable Simultaneously**

**Prerequisites:**
- Active user
- 3 rewards all ACHIEVED:
  - Coffee (1 piece)
  - Book (10 pieces)
  - Movie (5 pieces)

**Steps:**
1. Send `/my_rewards`
2. Verify all 3 rewards show status ⏳ ACHIEVED
3. Claim Coffee: `/claim_reward Coffee`
4. Verify success message
5. Send `/my_rewards`
6. Verify Coffee = ✅ CLAIMED, others still ⏳ ACHIEVED
7. Claim Book: `/claim_reward Book`
8. Verify success
9. Send `/my_rewards`
10. Verify Coffee and Book = ✅ CLAIMED, Movie still ⏳ ACHIEVED
11. Claim Movie: `/claim_reward Movie`
12. Verify all 3 now ✅ CLAIMED

**Expected Result:**
- Can claim multiple rewards in any order
- Each claim updates status independently
- No interference between rewards

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-INT-003: Multi-Language Flow ⚠️ NOT TESTED

#### Manual Tests

**Test Script: MAN-INT3-001 - Language Change Mid-Session**

**Prerequisites:**
- Active user in English
- Habit logged today (streak = 5)
- Reward "Coffee" is ACHIEVED

**Steps:**
1. Send `/streaks` (English) → Verify streak shows in English
2. Send `/my_rewards` (English) → Verify rewards in English
3. Send `/settings`
4. Change language to Russian
5. Send `/streaks` (Russian) → Verify streak shows in Russian (Cyrillic)
6. Send `/my_rewards` (Russian) → Verify rewards in Russian
7. Claim reward: `/claim_reward Coffee` (command in English, response in Russian)
8. Verify success message in Russian
9. Change language to Kazakh
10. Send `/help` (Kazakh) → Verify help in Kazakh
11. Change back to English
12. Verify all messages return to English

**Expected Result:**
- All messages instantly switch to selected language
- Data remains intact (streaks, rewards, progress)
- Commands work regardless of language
- No crashes or errors during language switches

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-INT-004: NLP Habit Classification Flow ⚠️ NOT TESTED

#### Manual Tests

**Test Script: MAN-INT4-001 - Custom Text to Habit Logging**

**Prerequisites:**
- Active user
- Habits: Walking, Reading, Meditation, Pushups, Drinking Water

**Steps:**
1. Send `/habit_done`
2. Tap "Custom Text" button
3. Type: "I went for a 30 minute walk today"
4. Verify bot correctly identifies "Walking" and logs it
5. Check success message shows "Walking" and correct streak

Repeat with:
- "read 20 pages of a book" → Should log "Reading"
- "meditated for 10 min" → Should log "Meditation"
- "did 50 pushups" → Should log "Pushups"
- "drank 8 glasses of water" → Should log "Drinking Water"

**Failure Case:**
6. Send `/habit_done`
7. Tap "Custom Text"
8. Type: "xyz random nonsense"
9. Verify bot shows error: "Could not identify habit. Please select from the list:"
10. Verify keyboard appears with habit buttons

**Expected Result:**
- NLP successfully matches natural language to habits
- Logs correct habit automatically
- Gracefully handles no-match with helpful error

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

## Phase 6: Edge Cases & Error Handling

### TC-EDGE-001: Boundary Conditions

#### Automated & Manual Tests

| Test ID | Description | Type | Status | Priority |
|---------|-------------|------|--------|----------|
| TC1.1 | Streak = 999+ days | Automated | ❌ Missing | Low |
| TC1.2 | Weight = 0 | Automated | ❌ Missing | Medium |
| TC1.3 | pieces_required = 1 (instant) | Automated | ❌ Missing | High |
| TC1.4 | pieces_required = 1000 | Automated | ❌ Missing | Low |
| TC1.5 | Empty strings in fields | Automated | ❌ Missing | Medium |
| TC1.6 | Very long text inputs (>10,000 chars) | Manual | ❌ Missing | Low |
| TC1.7 | Special characters in names (emojis) | Manual | ❌ Missing | Medium |

**Manual Test Script: MAN-EDGE1-001 - Special Characters in Habit Names**

**Prerequisites:**
- Admin access to Airtable
- Test bot running

**Steps:**
1. In Airtable, create habit with emoji: "🏃 Running"
2. Activate habit
3. Via Telegram: Send `/habit_done`
4. Verify "🏃 Running" appears in keyboard
5. Select it
6. Verify habit logs successfully
7. Send `/streaks`
8. Verify "🏃 Running" displays correctly with emoji

**Expected Result:**
- Emojis and special characters handled correctly
- No encoding errors
- Display renders properly in Telegram

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-EDGE-002: Concurrent Operations

#### Manual Tests

**Test Script: MAN-EDGE2-001 - Rapid Successive Commands**

**Prerequisites:**
- Active user
- Test bot running

**Steps:**
1. Send commands rapidly (within 1 second):
   - `/habit_done`
   - `/streaks`
   - `/my_rewards`
   - `/help`
2. Verify all commands respond correctly
3. Verify no crashes or errors
4. Verify responses arrive in order

**Expected Result:**
- Bot handles rapid commands gracefully
- All responses sent correctly
- No queue overflow or crashes

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

**Test Script: MAN-EDGE2-002 - Same User Multiple Devices**

**Prerequisites:**
- Same user logged in on 2 devices (phone + desktop Telegram)

**Steps:**
1. Device 1: Send `/habit_done` → Select "Walking"
2. Simultaneously, Device 2: Send `/habit_done` → Select "Reading"
3. Verify both habits logged correctly
4. Check `/streaks` on both devices
5. Verify streaks are consistent across devices

**Expected Result:**
- Both habit logs created
- No data corruption
- Consistent state across devices

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

### TC-EDGE-003: Data Consistency

#### Manual Tests

**Test Script: MAN-EDGE3-001 - Airtable Formula Field Verification**

**Prerequisites:**
- Access to Airtable
- User with reward progress

**Steps:**
1. Via Telegram: Log habit and earn reward "Coffee" (1 piece)
2. Open Airtable → RewardProgress table
3. Find user's Coffee progress record
4. Verify fields:
   - `pieces_earned`: 1 (editable field, set by bot)
   - `pieces_required`: 1 (computed field, from Reward lookup)
   - `status`: "⏳ Achieved" (computed formula)
   - `claimed`: false (editable field)
5. Manually try to edit `pieces_required` in Airtable
6. Verify error: "Field is computed"
7. Via Telegram: `/claim_reward Coffee`
8. Refresh Airtable
9. Verify:
   - `claimed`: true (set by bot)
   - `status`: "✅ Claimed" (updated by formula automatically)

**Expected Result:**
- Computed fields (pieces_required, status) are readonly
- Bot never attempts to set computed fields
- Formula correctly calculates status based on claimed flag

**Actual Result:** _[To be filled during testing]_

**Pass/Fail:** _[To be marked]_

---

## Test Execution Schedule

### Week 1: Critical Priority Tests

**Day 1-2: Settings Handler (TC-BOT-007)**
- Implement all automated tests for `/settings` command
- Run manual tests for language selection
- Fix any bugs found

**Day 3-4: NLP Service (TC-SVC-004)**
- Implement automated tests for NLP classification
- Run manual tests with natural language inputs
- Tune confidence thresholds if needed

**Day 5: Repository Layer - Users & Habits (TC-REPO-001, TC-REPO-002)**
- Implement automated tests for UserRepository
- Implement automated tests for HabitRepository
- Verify data access patterns

---

### Week 2: High Priority Tests

**Day 6-7: Complete Bot Handler Tests (TC-BOT-003)**
- Implement missing habit_done tests (TC3.6 - TC3.17)
- Test NLP integration in handlers
- Test reward notification flow

**Day 8-9: Repository Layer - Logs & Rewards (TC-REPO-003, TC-REPO-004, TC-REPO-005)**
- Implement automated tests for HabitLogRepository
- Implement automated tests for RewardRepository
- Implement automated tests for RewardProgressRepository
- Verify computed field handling

**Day 10: Integration Tests - Habit Logging (TC-INT-001)**
- Implement complete habit logging flow test
- Run 10-day manual test
- Verify streak and reward accuracy

---

### Week 3: Medium Priority Tests

**Day 11-12: Service Layer Edge Cases (TC-SVC-001 to TC-SVC-003)**
- Complete all missing service layer tests
- Test boundary conditions
- Test error handling

**Day 13-14: Integration Tests - Rewards & Languages (TC-INT-002, TC-INT-003)**
- Test reward claiming flows
- Test multi-language scenarios
- Verify data consistency across languages

**Day 15: Model Validation Tests (TC-MODEL-001 to TC-MODEL-004)**
- Implement Pydantic model validation tests
- Test all field validators
- Test default values

---

### Week 4: Edge Cases & Final Verification

**Day 16-17: Edge Cases (TC-EDGE-001 to TC-EDGE-003)**
- Implement boundary condition tests
- Run concurrent operation tests
- Verify data consistency in Airtable

**Day 18-19: Full Regression Testing**
- Run ALL automated tests: `uv run pytest tests/ -v --cov=src`
- Verify >95% code coverage
- Run all manual tests from start to finish

**Day 20: Bug Fixes & Documentation**
- Fix any bugs discovered during testing
- Update RULES.md with findings
- Document any new patterns or pitfalls

---

## Success Criteria

### Automated Testing

- ✅ **95%+ Code Coverage**: All critical paths tested
- ✅ **All Tests Pass**: Zero failures in pytest suite
- ✅ **Test Execution Time**: < 30 seconds for full suite
- ✅ **No Flaky Tests**: Tests are deterministic and reliable

### Manual Testing

- ✅ **All Manual Scripts Completed**: Every manual test executed and documented
- ✅ **Zero Critical Bugs**: No P0/P1 bugs remaining
- ✅ **User Flows Verified**: All user journeys work end-to-end
- ✅ **Multi-Language Verified**: All 3 languages (en, ru, kk) tested

### Quality Metrics

- ✅ **No Regressions**: Existing functionality still works
- ✅ **Performance**: Bot responds within 2 seconds for all commands
- ✅ **Data Integrity**: No data loss or corruption in Airtable
- ✅ **Error Handling**: All errors have helpful user messages

---

## Test Documentation Standards

### For Each Test

1. **Test ID**: Unique identifier (e.g., TC-BOT-001)
2. **Description**: What is being tested
3. **Prerequisites**: Setup required before test
4. **Steps**: Clear, numbered steps to execute
5. **Expected Result**: What should happen
6. **Actual Result**: What actually happened (filled during testing)
7. **Pass/Fail**: Test outcome
8. **Screenshots**: Visual evidence (for manual tests)
9. **Date Executed**: When test was run
10. **Tester**: Who ran the test

### Test Results Tracking

Create a Google Sheet or Excel file with columns:
- Test ID
- Description
- Type (Automated/Manual)
- Priority
- Status (Not Started/In Progress/Pass/Fail)
- Date Executed
- Bugs Found
- Notes

---

## Appendix

### Running Automated Tests

```bash
# Run all tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bot_handlers.py -v

# Run specific test
uv run pytest tests/test_bot_handlers.py::TestStartCommand::test_user_not_found -v

# Run tests matching pattern
uv run pytest tests/ -k "test_language" -v

# View coverage report
open htmlcov/index.html
```

### Manual Test Environment Setup

1. **Create Test Airtable Base**: Copy production schema
2. **Create Test Telegram Bot**: Use @BotFather, get test token
3. **Configure Test Users**:
   - test_user_en@example.com (English)
   - test_user_ru@example.com (Russian)
   - test_user_kk@example.com (Kazakh)
   - test_user_inactive@example.com (Inactive)
4. **Seed Test Data**:
   - 5 active habits
   - 5 active rewards (including multi-piece)
   - Sample habit logs for streak testing

### Bug Reporting Template

```markdown
## Bug Report

**Bug ID:** BUG-001
**Severity:** Critical/High/Medium/Low
**Test Case:** TC-BOT-003
**Date Found:** 2025-10-20

**Description:**
Brief description of the bug.

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen.

**Actual Behavior:**
What actually happened.

**Screenshots:**
[Attach screenshots]

**Environment:**
- Bot version: 1.0
- Python version: 3.13
- Telegram client: iOS/Android/Desktop

**Logs:**
```
Relevant log output
```

**Assigned To:** Developer Name
**Status:** Open/In Progress/Fixed/Closed
```

---

**End of Comprehensive Test Plan**

**Next Steps:**
1. Review this plan with the team
2. Set up test environment
3. Begin Week 1 implementation
4. Track progress in test results spreadsheet
5. Update RULES.md with findings

