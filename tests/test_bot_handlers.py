Total output lines: 1852

"""Unit tests for Telegram bot handlers with multi-language support."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User as TelegramUser
from telegram.ext import ConversationHandler

from src.bot.main import start_command, help_command
from src.bot.handlers.habit_done_handler import habit_done_command
from src.bot.handlers.streak_handler import streaks_command
from src.bot.handlers.reward_handlers import (
    my_rewards_command,
    claim_reward_command,
    add_reward_command,
    reward_name_received,
    reward_weight_received,
    reward_pieces_received,
    reward_pieces_selected,
    reward_recurring_yes,
    reward_edit_pieces_received,
    reward_edit_pieces_selected,
    reward_edit_recurring_skip,
    reward_edit_selected,
    AWAITING_REWARD_NAME,
    AWAITING_REWARD_WEIGHT,
    AWAITING_REWARD_RECURRING,
    # AWAITING_REWARD_CONFIRM,
    AWAITING_REWARD_EDIT_RECURRING,
    AWAITING_REWARD_EDIT_CONFIRM,
    menu_edit_reward_callback,
    AWAITING_REWARD_EDIT_SELECTION,
)
from src.bot.handlers.menu_handler import (
    open_habits_menu_callback,
    bridge_command_callback,
    open_start_menu_callback,
    get_menu_handlers,
)
from src.bot.handlers.habit_management_handler import (
    remove_back_to_list,
    AWAITING_REMOVE_SELECTION,
    AWAITING_HABIT_NAME,
    _schedule_message_delete,
    habit_remove_confirmed,
    edit_to_add_habit,
    remove_habit_conversation,
)
from src.bot.keyboards import build_start_menu_keyboard, build_rewards_menu_keyboard
from src.models.user import User
from src.models.habit import Habit
from src.bot.messages import msg
from src.config import settings, REWARD_WEIGHT_MIN, REWARD_WEIGHT_MAX


@pytest.fixture(params=settings.supported_languages)
def language(request):
    """Parameterized fixture for testing all supported languages from global settings."""
    return request.param


@pytest.fixture
def mock_telegram_user(language):
    """Create mock Telegram user with parameterized language."""
    return TelegramUser(
        id=999999999,
        first_name="Test",
        last_name="User",
        is_bot=False,
        language_code=language
    )


@pytest.fixture
def mock_telegram_update(mock_telegram_user):
    """Create mock Telegram update with message."""
    message = Mock(spec=Message)
    message.reply_text = AsyncMock()

    update = Mock(spec=Update)
    update.effective_user = mock_telegram_user
    update.message = message
    return update


@pytest.fixture
def mock_active_user(language):
    """Create mock active user from Airtable with language support."""
    return User(
        id=123,
        telegram_id="999999999",
        name="Test User",
        is_active=True,
        language=language
    )


@pytest.fixture
def mock_inactive_user(language):
    """Create mock inactive user from Airtable with language support."""
    return User(
        id=456,
        telegram_id="999999999",
        name="Inactive User",
        is_active=False,
        language=language
    )


@pytest.fixture
def mock_active_habits():
    """Create mock active habits for testing."""
    return [
        Habit(id=1, name="Walking", weight=10, category="health", active=True),
        Habit(id=2, name="Reading", weight=15, category="education", active=True),
        Habit(id=3, name="Meditation", weight=12, category="wellness", active=True)
    ]


@pytest.fixture
def mock_inactive_habits():
    """Create mock inactive habits for testing."""
    return [
        Habit(id=4, name="Old Habit 1", weight=10, category="other", active=False),
        Habit(id=5, name="Old Habit 2", weight=10, category="other", active=False)
    ]


class TestStartCommand:
    """Test /start command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """
        TC1.1: User not found should return error message in user's language.

        Given: User telegram_id does NOT exist in Airtable Users table
        When: User sends /start command
        Then: Bot responds with 'User not found' message in the correct language
        """
        # Mock: user doesn't exist in Airtable
        mock_user_repo.get_by_telegram_id.return_value = None

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Error message sent in correct language
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """
        TC1.3: Inactive user should be blocked with localized message.

        Given: User exists in Airtable but active=False
        When: User sends /start command
        Then: Bot responds with 'Your account is not active' message in the correct language
        """
        # Mock: user exists but is inactive
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Inactive error message sent in correct language
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )

    @pytest.mark.asyncio
    @patch('src.services.audit_log_service.audit_log_service')
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_audit_service, mock_telegram_update, mock_active_user, language):
        """
        TC1.2: Active user should see welcome message in their language.

        Given: User exists in Airtable and active=True
        When: User sends /start command
        Then: Bot responds with welcome message and command list in the correct language
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        # Mock: audit log service to prevent database writes
        mock_audit_service.log_command = AsyncMock()

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Start menu sent
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0]

        expected_title = msg('START_MENU_TITLE', language)
        assert message_text == expected_title
        assert 'reply_markup' in call_args[1]
        assert call_args[1].get("parse_mode") == "HTML"


class TestHelpCommand:
    """Test /help command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """
        User not found should return error message for /help in user's language.

        Given: User telegram_id does NOT exist in Airtable Users table
        When: User sends /help command
        Then: Bot responds with 'User not found' message in the correct language
        """
        # Mock: user doesn't exist in Airtable
        mock_user_repo.get_by_telegram_id.return_value = None

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Error message sent in correct language
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """
        Inactive user should be blocked from /help command with localized message.

        Given: User exists in Airtable but active=False
        When: User sends /help command
        Then: Bot responds with 'Your account is not active' message in the correct language
        """
        # Mock: user exists but is inactive
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Inactive error message sent in correct language
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )

    @pytest.mark.asyncio
    @patch('src.services.audit_log_service.audit_log_service')
    @patch('src.bot.handlers.command_handlers.default_user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_audit_service, mock_telegram_update, mock_active_user, language):
        """
        Active user should see help message in their language.

        Given: User exists in Airtable and active=True
        When: User sends /help command
        Then: Bot responds with help message and command descriptions in the correct language
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        # Mock: audit log service to prevent database writes
        mock_audit_service.log_command = AsyncMock()

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Help message sent in correct language
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0]

        # Verify expected help message content
        expected_help = msg('HELP_COMMAND_MESSAGE', language)
        assert message_text == expected_help
        assert "/habit_done" in message_text
        assert call_args[1].get("parse_mode") == "HTML"


class TestStartMenuKeyboard:
    """Tests for the Start menu keyboard layout."""

    def test_start_menu_contains_expected_buttons(self, language):
        keyboard = build_start_menu_keyboard(language)
        # InlineKeyboardMarkup stores keyboard in .inline_keyboard
        rows = keyboard.inline_keyboard
        # Expect at least 5 rows as designed
        assert len(rows) >= 5
        # Check presence of Close and Habits callbacks
        callbacks = [btn.callback_data for row in rows for btn in row]
        assert 'menu_habits' in callbacks
        assert 'menu_rewards' in callbacks
        assert 'menu_habit_done' in callbacks
        assert 'menu_close' in callbacks
        assert 'menu_back_start' not in callbacks  # not in root menu


class TestRewardsMenuKeyboard:
    """Tests for the Rewards submenu keyboard layout."""

    def test_rewards_menu_contains_edit_button(self, language):
        keyboard = build_rewards_menu_keyboard(language)
        rows = keyboard.inline_keyboard
        callbacks = [btn.callback_data for row in rows for btn in row]
        assert "menu_rewards_edit" in callbacks


@pytest.fixture
def mock_callback_update(mock_telegram_user):
    """Create a mock update with callback_query and chat for menu tests."""
    class DummyChat:
        def __init__(self):
            self.send_message = AsyncMock()

    query = Mock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.delete_message = AsyncMock()
    query.data = ''
    query.message = Mock()
    query.message.chat_id = 12345
    query.message.message_id = 67890
    query.message.chat = DummyChat()

    update = Mock(spec=Update)
    update.effective_user = mock_telegram_user
    update.callback_query = query
    return update


class TestMenuHandlers:
    @pytest.mark.asyncio
    async def test_open_habits_menu(self, mock_callback_update, language):
        mock_callback_update.callback_query.data = 'menu_habits'
        await open_habits_menu_callback(mock_callback_update, context=None)
        mock_callback_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_habit_menu_callback_is_not_bridged(self, mock_callback_update):
        """
        menu_habits_remove should be handled only by remove_habit_conversation.

        Fixes #59: the menu previously sent a visible '/remove_habit' message,
        because the group-1 bridge also handled the same callback.
        """
        bridge_handlers = [
            handler for handler in get_menu_handlers()
            if handler.callback == bridge_command_callback
        ]

        assert bridge_handlers
        for handler in bridge_handlers:
            assert handler.pattern.match("menu_habits_remove") is None

        remove_entry_points = [
            handler for handler in remove_habit_conversation.entry_points
            if getattr(handler, "pattern", None)
        ]
        assert any(
            handler.pattern.match("menu_habits_remove")
            for handler in remove_entry_points
        )

    @pytest.mark.asyncio
    async def test_back_to_start_menu(self, mock_callback_update, language):
        mock_callback_update.callback_query.data = 'menu_back_start'
        await open_start_menu_callback(mock_callback_update, context=None)
        mock_callback_update.callback_query.edit_message_text.assert_called_once()


class TestEditRewardFromMenu:
    """Unit tests for Rewards -> Edit flow entry point."""

    @pytest.mark.asyncio
    @patch("src.bot.handlers.reward_handlers.reward_repository")
    @patch("src.bot.handlers.reward_handlers.user_repository")
    async def test_no_rewards_shows_error(
        self, mock_user_repo, mock_reward_repo, mock_callback_update, mock_active_user, language
    ):
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        mock_reward_repo.get_all_active = AsyncMock(return_value=[])

        context = Mock()
        context.user_data = {}

        result = await menu_edit_reward_callback(mock_callback_update, context=context)

        assert result == ConversationHandler.END
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert msg("ERROR_NO_REWARDS_TO_EDIT", language) in call_args.args[0]
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    @patch("src.bot.handlers.reward_handlers.reward_repository")
    @patch("src.bot.handlers.reward_handlers.user_repository")
    async def test_rewards_present_shows_selection(
        self, mock_user_repo, mock_reward_repo, mock_callback_update, mock_active_user, language
    ):
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        reward1 = Mock()
        reward1.id = 1
        reward1.name = "Coffee"
        reward2 = Mock()
        reward2.id = 2
        reward2.name = "Walk"
        mock_reward_repo.get_all_active = AsyncMock(return_value=[reward1, reward2])

        context = Mock()
        context.user_data = {}

        result = await menu_edit_reward_callback(mock_callback_update, context=context)

        assert result == AWAITING_REWARD_EDIT_SELECTION
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert call_args.args[0] == msg("HELP_EDIT_REWARD_SELECT", language)
        assert call_args.kwargs.get("reply_markup") is not None


class TestSimpleHabitDoneFlow:
    """Test Feature 0021: Simple habit completion flow (menu_habit_done_simple_show_habits)."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_no_habits_configured_shows_error(
        self, mock_user_repo, mock_habit_service, mock_callback_update, mock_active_user, language
    ):
        """
        Bug Fix Verification: User with ZERO habits should see ERROR_NO_HABITS, not INFO_ALL_HABITS_COMPLETED.

        Given: User exists and is active
        And: User has NO habits configured
        When: User clicks 'Habit Done' button (simple flow)
        Then: Bot shows ERROR_NO_HABITS message
        And: Shows 'Back to Menu' button
        """
        from src.bot.handlers.menu_handler import menu_habit_done_simple_show_habits

        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock: NO habits exist (empty list from both calls)
        mock_habit_service.get_all_active_habits.return_value = []
        mock_habit_service.get_active_habits_pending_for_today.return_value = []

        # Execute
        result = await menu_habit_done_simple_show_habits(mock_callback_update, context=None)

        # Assert: get_all_active_habits was called first (for the check)
        mock_habit_service.get_all_active_habits.assert_called_once_with(mock_active_user.id)

        # Assert: ERROR_NO_HABITS message shown (NOT INFO_ALL_HABITS_COMPLETED)
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert msg('ERROR_NO_HABITS', language) in call_args[0][0]

        # Assert: Back button provided
        assert 'reply_markup' in call_args[1]

        # Assert: returned 0 (no conversation state)
        assert result == 0

    @pytest.mark.asyncio
    @patch('src.bot.handlers.menu_handler.get_user_today')
    @patch('src.bot.handlers.menu_handler.get_user_timezone', new_callable=AsyncMock)
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_all_habits_completed_shows_success(
        self, mock_user_repo, mock_habit_service, mock_get_tz, mock_get_today,
        mock_callback_update,
        mock_active_user, mock_active_habits, language
    ):
        """
        User with habits but all completed today should see INFO_ALL_HABITS_COMPLETED.

        Given: User exists and is active
        And: User has active habits configured
        And: All habits are already completed for today
        When: User clicks 'Habit Done' button (simple flow)
        Then: Bot shows INFO_ALL_HABITS_COMPLETED message
        And: Shows 'Back to Menu' button
        """
        from datetime import date
        from src.bot.handlers.menu_handler import menu_habit_done_simple_show_habits

        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock timezone helpers
        mock_get_tz.return_value = 'UTC'
        today = date.today()
        mock_get_today.return_value = today

        # Mock: user HAS habits configured
        mock_habit_service.get_all_active_habits.return_value = mock_active_habits

        # Mock: but NO pending habits (all completed today)
        mock_habit_service.get_active_habits_pending_for_today.return_value = []

        # Execute
        result = await menu_habit_done_simple_show_habits(mock_callback_update, context=None)

        # Assert: Both service methods were called
        mock_habit_service.get_all_active_habits.assert_called_once_with(mock_active_user.id)
        mock_habit_service.get_active_habits_pending_for_today.assert_called_once_with(mock_active_user.id, target_date=today)

        # Assert: INFO_ALL_HABITS_COMPLETED message shown
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert msg('INFO_ALL_HABITS_COMPLETED', language) in call_args[0][0]

        # Assert: HTML parse mode used
        assert call_args[1].get('parse_mode') == 'HTML'

        # Assert: returned 0
        assert result == 0

    @pytest.mark.asyncio
    @patch('src.bot.handlers.menu_handler.get_user_today')
    @patch('src.bot.handlers.menu_handler.get_user_timezone', new_callable=AsyncMock)
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_pending_habits_shows_simple_keyboard(
        self, mock_user_repo, mock_habit_s…8687 tokens truncated…     assert edit_data['old_name'] == 'Coffee'
        assert edit_data['old_weight'] == 10.0
        assert edit_data['old_pieces_required'] == 3

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_edit_confirmation_excludes_piece_value(
        self,
        mock_lang,
        mock_telegram_update,
        language
    ):
        """Edit confirmation message should NOT mention piece_value."""
        mock_lang.return_value = language
        mock_telegram_update.message.text = "5"

        context = Mock()
        context.user_data = {
            'reward_edit_data': {
                'reward_id': 'reward123',
                'old_name': 'Coffee',
                'old_type': 'virtual',
                'old_weight': 10.0,
                'old_pieces_required': 3,
                'new_name': 'Coffee',
                'new_type': 'virtual',
                'new_weight': 10.0
            }
        }

        await reward_edit_pieces_received(mock_telegram_update, context)

        # Get the confirmation message
        call_args = mock_telegram_update.message.reply_text.await_args
        message_text = call_args.args[0]

        # Should NOT mention piece value in any form
        assert 'piece_value' not in message_text.lower()
        assert 'piece value' not in message_text.lower()
        assert 'piece price' not in message_text.lower()


class TestCategoryRemovalFromTelegram:
    """Test that category field is removed from Telegram habit flows (Feature 0024).

    Verifies:
    1. Add/Edit habit flows skip category step
    2. Confirmation messages don't show category
    3. Keyboards don't show brackets after habit names
    4. Created habits have category=None
    """

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_add_habit_confirmation_no_category(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Add habit confirmation message should NOT mention category (Feature 0024)."""
        from src.bot.handlers.habit_management_handler import habit_exempt_days_selected

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Setup callback query
        mock_telegram_update.callback_query = Mock()
        mock_telegram_update.callback_query.answer = AsyncMock()
        mock_telegram_update.callback_query.edit_message_text = AsyncMock()
        mock_telegram_update.callback_query.data = "exempt_days_weekends"

        context = Mock()
        context.user_data = {
            'habit_name': 'Running',
            'habit_weight': 30,
            'habit_grace_days': 2
        }

        await habit_exempt_days_selected(mock_telegram_update, context)

        # Get the confirmation message
        call_args = mock_telegram_update.callback_query.edit_message_text.await_args
        message_text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should NOT mention category in any form
        assert 'category' not in message_text.lower()
        assert 'Category' not in message_text

        # Should show name, weight, grace days, exempt days
        assert 'name' in message_text.lower() or 'название' in message_text.lower() or 'аты' in message_text.lower()
        assert 'weight' in message_text.lower() or 'вес' in message_text.lower() or 'салмақ' in message_text.lower()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_edit_habit_confirmation_no_category(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Edit habit confirmation message should NOT mention category (Feature 0024)."""
        from src.bot.handlers.habit_management_handler import habit_edit_exempt_days_selected

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Setup callback query
        mock_telegram_update.callback_query = Mock()
        mock_telegram_update.callback_query.answer = AsyncMock()
        mock_telegram_update.callback_query.edit_message_text = AsyncMock()
        mock_telegram_update.callback_query.data = "exempt_days_weekends"

        context = Mock()
        context.user_data = {
            'old_habit_name': 'Running',
            'new_habit_name': 'Morning Run',
            'old_habit_weight': 30,
            'new_habit_weight': 40,
            'old_habit_grace_days': 1,
            'new_habit_grace_days': 2
        }

        await habit_edit_exempt_days_selected(mock_telegram_update, context)

        # Get the confirmation message
        call_args = mock_telegram_update.callback_query.edit_message_text.await_args
        message_text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')

        # Should NOT mention category in any form
        assert 'category' not in message_text.lower()
        assert 'Category' not in message_text

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_created_habit_has_no_category(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Habits created via Telegram should have category=None (Feature 0024)."""
        from src.bot.handlers.habit_management_handler import habit_confirmed

        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Setup callback query
        mock_telegram_update.callback_query = Mock()
        mock_telegram_update.callback_query.answer = AsyncMock()
        mock_telegram_update.callback_query.edit_message_text = AsyncMock()
        mock_telegram_update.callback_query.data = "confirm_yes"

        context = Mock()
        context.user_data = {
            'habit_name': 'Running',
            'habit_weight': 30,
            'habit_grace_days': 2,
            'habit_exempt_days': [6, 7]
        }

        await habit_confirmed(mock_telegram_update, context)

        # Verify habit was created WITHOUT category field
        create_call = mock_habit_repo.create.call_args
        habit_data = create_call[0][0] if create_call.args else create_call.kwargs

        # Category should either be absent or explicitly None
        assert habit_data.get('category') is None or 'category' not in habit_data

    def test_habit_keyboard_no_brackets(self, language):
        """Habit keyboards should NOT show brackets after habit names (Feature 0024)."""
        from src.bot.keyboards import build_habits_for_edit_keyboard

        # Create simple habit objects (not mocks, to avoid Mock attribute issues)
        class SimpleHabit:
            def __init__(self, id, name, category):
                self.id = id
                self.name = name
                self.category = category

        mock_habits = [
            SimpleHabit(id='1', name='Running', category='Health'),
            SimpleHabit(id='2', name='Reading', category=None),
            SimpleHabit(id='3', name='Meditation', category='Wellness')
        ]

        keyboard = build_habits_for_edit_keyboard(mock_habits, operation='edit', language=language)

        # Expected habit names (without category)
        expected_names = ['Running', 'Reading', 'Meditation']

        # Check that no button text contains brackets
        for row in keyboard.inline_keyboard:
            for button in row:
                # Skip the Back button
                if 'back' in button.callback_data.lower():
                    continue

                # Should NOT show "Habit Name (Category)" format
                assert '(' not in button.text, f"Button text '{button.text}' contains opening bracket"
                assert ')' not in button.text, f"Button text '{button.text}' contains closing bracket"

                # Buttons should just be habit names (no category suffix)
                if button.callback_data.startswith('edit_habit_'):
                    # Button text should be one of the habit names (no category suffix)
                    assert button.text in expected_names, f"Button text '{button.text}' not in expected names"


class TestClaimRewardHandlerRouting:
    """Test Feature 0029: Handler pattern matching order for claim_reward flow.

    Verifies that the fix for "Reward progress not found" error works correctly.
    The bug occurred when claim_reward_ pattern matched before claim_reward_back pattern.
    Fix: Reordered handlers so exact match (claim_reward_back$) comes first.

    CRITICAL: test_claim_reward_conversation_handler_order() validates the actual
    ConversationHandler configuration. If handlers are accidentally reordered,
    that test will fail even if the functional tests pass.
    """

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.build_rewards_menu_keyboard')
    @patch('src.bot.handlers.reward_handlers.pop_navigation')
    async def test_claim_back_callback_pattern_matching(
        self, mock_pop_nav, mock_build_keyboard, mock_callback_update, language
    ):
        """
        Test that callback_data "claim_reward_back" routes to claim_back_callback.

        Given: User is in the claim reward flow
        When: User clicks Back button (callback_data = "claim_reward_back")
        Then: claim_back_callback is invoked (NOT claim_reward_callback)
        And: User is returned to rewards menu
        And: No "Reward progress not found" error occurs
        """
        from src.bot.handlers.reward_handlers import claim_back_callback
        from telegram import InlineKeyboardMarkup

        # Setup callback data
        mock_callback_update.callback_query.data = "claim_reward_back"

        # Mock navigation state
        mock_pop_nav.return_value = {'lang': language}

        # Mock keyboard builder
        mock_keyboard = Mock(spec=InlineKeyboardMarkup)
        mock_build_keyboard.return_value = mock_keyboard

        # Mock context
        context = Mock()
        context.user_data = {}

        # Execute
        result = await claim_back_callback(mock_callback_update, context)

        # Assert: Conversation ended (returned to menu)
        assert result == ConversationHandler.END

        # Assert: Navigation was popped
        mock_pop_nav.assert_called_once()

        # Assert: Rewards menu was shown
        mock_callback_update.callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_update.callback_query.edit_message_text.call_args

        # Verify message contains rewards menu title
        assert 'REWARDS_MENU_TITLE' in str(call_args) or call_args.kwargs.get('reply_markup') == mock_keyboard

        # Assert: No error message shown (would contain "not found")
        message_text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')
        assert 'not found' not in message_text.lower()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.audit_log_service')
    @patch('src.bot.handlers.reward_handlers.reward_service')
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_claim_reward_callback_still_works(
        self, mock_user_repo, mock_reward_repo, mock_reward_service,
        mock_audit_service, mock_callback_update, mock_active_user, language
    ):
        """
        Test that callback_data "claim_reward_123" routes to claim_reward_callback.

        Given: User is in the claim reward flow
        When: User clicks on a reward (callback_data = "claim_reward_123")
        Then: claim_reward_callback is invoked
        And: reward_id is correctly extracted as "123"
        And: Normal reward claiming flow proceeds
        """
        from src.bot.handlers.reward_handlers import claim_reward_callback

        # Setup callback data with numeric reward ID
        mock_callback_update.callback_query.data = "claim_reward_123"

        # Mock user
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock reward
        mock_reward = Mock()
        mock_reward.id = "123"
        mock_reward.name = "Coffee Break"
        mock_reward.user_id = mock_active_user.id
        mock_reward.active = True
        mock_reward.is_recurring = True
        mock_reward_repo.get_by_id.return_value = mock_reward

        # Mock reward progress
        mock_progress = Mock()
        mock_progress.pieces_earned = 0
        mock_progress.get_pieces_required = Mock(return_value=5)
        mock_progress.get_status = Mock(return_value=Mock(value="✅ Claimed"))
        mock_progress.claimed = True
        mock_reward_service.mark_reward_claimed.return_value = mock_progress
        mock_reward_service.get_user_reward_progress.return_value = []

        # Mock audit log service
        mock_audit_service.log_reward_claim = AsyncMock()

        # Mock context
        context = Mock()
        context.user_data = {}

        # Execute
        await claim_reward_callback(mock_callback_update, context)

        # Assert: Reward repository was queried with correct ID
        # This is the key assertion - verifies reward_id was extracted correctly
        mock_reward_repo.get_by_id.assert_any_call("123")

        # Assert: No "Reward progress not found" error
        # (If handler matched incorrectly, it would try to find reward with id "back")
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        if call_args:
            message_text = call_args.args[0] if call_args.args else call_args.kwargs.get('text', '')
            assert 'not found' not in message_text.lower()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.audit_log_service')
    @patch('src.bot.handlers.reward_handlers.reward_service')
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_claim_reward_callback_with_uuid(
        self, mock_user_repo, mock_reward_repo, mock_reward_service,
        mock_audit_service, mock_callback_update, mock_active_user, language
    ):
        """
        Test that callback_data "claim_reward_abc-def-123" handles UUID-like IDs.

        Given: User is in the claim reward flow
        When: User clicks on a reward with UUID-like ID (callback_data = "claim_reward_abc-def-123")
        Then: claim_reward_callback is invoked
        And: reward_id is correctly extracted as "abc-def-123"
        And: UUID-like reward IDs work correctly
        """
        from src.bot.handlers.reward_handlers import claim_reward_callback

        # Setup callback data with UUID-like reward ID
        uuid_like_id = "abc-def-123"
        mock_callback_update.callback_query.data = f"claim_reward_{uuid_like_id}"

        # Mock user
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock reward with UUID-like ID
        mock_reward = Mock()
        mock_reward.id = uuid_like_id
        mock_reward.name = "Premium Reward"
        mock_reward.user_id = mock_active_user.id
        mock_reward.active = True
        mock_reward.is_recurring = True
        mock_reward_repo.get_by_id.return_value = mock_reward

        # Mock reward progress
        mock_progress = Mock()
        mock_progress.pieces_earned = 0
        mock_progress.get_pieces_required = Mock(return_value=10)
        mock_progress.get_status = Mock(return_value=Mock(value="✅ Claimed"))
        mock_progress.claimed = True
        mock_reward_service.mark_reward_claimed.return_value = mock_progress
        mock_reward_service.get_user_reward_progress.return_value = []

        # Mock audit log service
        mock_audit_service.log_reward_claim = AsyncMock()

        # Mock context
        context = Mock()
        context.user_data = {}

        # Execute
        await claim_reward_callback(mock_callback_update, context)

        # Assert: Reward repository was queried with correct UUID-like ID
        # This is the key assertion - verifies reward_id was extracted correctly
        mock_reward_repo.get_by_id.assert_any_call(uuid_like_id)

        # Assert: Handler extracted the ID correctly (everything after "claim_reward_")
        # If this fails, the string.replace() logic is broken
        first_call_arg = mock_reward_repo.get_by_id.call_args_list[0][0][0]
        assert first_call_arg == uuid_like_id

    def test_claim_reward_conversation_handler_order(self):
        """
        Test that ConversationHandler routes patterns in the correct order.

        CRITICAL: This test catches regressions if handlers are accidentally reordered.
        If this test fails, it means someone changed the handler order in
        claim_reward_conversation and broke the pattern matching fix.

        Given: claim_reward_conversation is configured
        When: We inspect the AWAITING_REWARD_SELECTION state handlers
        Then: First handler must match "^claim_reward_back$" (exact match)
        And: Second handler must match "^claim_reward_" (prefix match)
        And: First handler must route to claim_back_callback
        And: Second handler must route to claim_reward_callback
        """
        from telegram.ext import CallbackQueryHandler
        from src.bot.handlers.reward_handlers import (
            claim_reward_conversation,
            claim_back_callback,
            claim_reward_callback,
            AWAITING_REWARD_SELECTION
        )

        # Get handlers for the AWAITING_REWARD_SELECTION state
        handlers = claim_reward_conversation.states[AWAITING_REWARD_SELECTION]

        # Assert: Exactly 2 handlers
        assert len(handlers) == 2, f"Expected 2 handlers, got {len(handlers)}"

        # Assert: Both are CallbackQueryHandler instances
        assert isinstance(handlers[0], CallbackQueryHandler), \
            f"First handler is {type(handlers[0])}, expected CallbackQueryHandler"
        assert isinstance(handlers[1], CallbackQueryHandler), \
            f"Second handler is {type(handlers[1])}, expected CallbackQueryHandler"

        # Assert: First handler (exact match for "back") comes FIRST
        first_handler = handlers[0]
        assert first_handler.pattern.pattern == "^claim_reward_back$", \
            f"First handler pattern is '{first_handler.pattern.pattern}', expected '^claim_reward_back$'"
        assert first_handler.callback == claim_back_callback, \
            f"First handler callback is {first_handler.callback.__name__}, expected claim_back_callback"

        # Assert: Second handler (prefix match) comes SECOND
        second_handler = handlers[1]
        assert second_handler.pattern.pattern == "^claim_reward_", \
            f"Second handler pattern is '{second_handler.pattern.pattern}', expected '^claim_reward_'"
        assert second_handler.callback == claim_reward_callback, \
            f"Second handler callback is {second_handler.callback.__name__}, expected claim_reward_callback"


# Note: set_reward_status_command has been deprecated and removed in Feature 0005
# Status is now automatically computed by Airtable based on pieces_earned and claimed fields
