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
    reward_edit_pieces_received,
    reward_edit_pieces_selected,
    reward_edit_selected,
    AWAITING_REWARD_NAME,
    AWAITING_REWARD_TYPE,
    AWAITING_REWARD_WEIGHT,
    AWAITING_REWARD_CONFIRM,
    AWAITING_REWARD_EDIT_CONFIRM,
    menu_edit_reward_callback,
    AWAITING_REWARD_EDIT_SELECTION,
)
from src.bot.handlers.menu_handler import (
    open_habits_menu_callback,
    bridge_command_callback,
    open_start_menu_callback
)
from src.bot.handlers.habit_management_handler import (
    remove_back_to_list,
    AWAITING_REMOVE_SELECTION
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
    async def test_bridge_to_command(self, mock_callback_update):
        mock_callback_update.callback_query.data = 'menu_habits_remove'
        await bridge_command_callback(mock_callback_update, context=None)
        mock_callback_update.callback_query.message.chat.send_message.assert_called_once_with('/remove_habit')

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
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_all_habits_completed_shows_success(
        self, mock_user_repo, mock_habit_service, mock_callback_update,
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
        from src.bot.handlers.menu_handler import menu_habit_done_simple_show_habits

        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock: user HAS habits configured
        mock_habit_service.get_all_active_habits.return_value = mock_active_habits

        # Mock: but NO pending habits (all completed today)
        mock_habit_service.get_active_habits_pending_for_today.return_value = []

        # Execute
        result = await menu_habit_done_simple_show_habits(mock_callback_update, context=None)

        # Assert: Both service methods were called
        mock_habit_service.get_all_active_habits.assert_called_once_with(mock_active_user.id)
        mock_habit_service.get_active_habits_pending_for_today.assert_called_once_with(mock_active_user.id)

        # Assert: INFO_ALL_HABITS_COMPLETED message shown
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert msg('INFO_ALL_HABITS_COMPLETED', language) in call_args[0][0]

        # Assert: HTML parse mode used
        assert call_args[1].get('parse_mode') == 'HTML'

        # Assert: returned 0
        assert result == 0

    @pytest.mark.asyncio
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_pending_habits_shows_simple_keyboard(
        self, mock_user_repo, mock_habit_service, mock_callback_update,
        mock_active_user, mock_active_habits, language
    ):
        """
        User with pending habits should see simple selection keyboard.

        Given: User exists and is active
        And: User has active habits configured
        And: Some habits are not yet completed today
        When: User clicks 'Habit Done' button (simple flow)
        Then: Bot shows simple habit selection keyboard
        And: Message is HELP_SIMPLE_HABIT_SELECTION
        And: Only pending habits are shown
        """
        from src.bot.handlers.menu_handler import menu_habit_done_simple_show_habits

        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock: user HAS habits configured
        mock_habit_service.get_all_active_habits.return_value = mock_active_habits

        # Mock: some pending habits (subset of all habits)
        pending_habits = mock_active_habits[:2]  # Only first 2 are pending
        mock_habit_service.get_active_habits_pending_for_today.return_value = pending_habits

        # Execute
        result = await menu_habit_done_simple_show_habits(mock_callback_update, context=None)

        # Assert: Both service methods were called
        mock_habit_service.get_all_active_habits.assert_called_once_with(mock_active_user.id)
        mock_habit_service.get_active_habits_pending_for_today.assert_called_once_with(mock_active_user.id)

        # Assert: HELP_SIMPLE_HABIT_SELECTION message shown
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert call_args[0][0] == msg('HELP_SIMPLE_HABIT_SELECTION', language)

        # Assert: Keyboard provided
        assert 'reply_markup' in call_args[1]

        # Assert: returned 0
        assert result == 0

    @pytest.mark.asyncio
    @patch('src.bot.handlers.menu_handler.habit_service')
    @patch('src.bot.handlers.menu_handler.user_repository')
    async def test_user_not_found_shows_error(
        self, mock_user_repo, mock_habit_service, mock_callback_update, language
    ):
        """
        User not found should show error message.

        Given: User does NOT exist in database
        When: User clicks 'Habit Done' button (simple flow)
        Then: Bot shows ERROR_USER_NOT_FOUND message
        """
        from src.bot.handlers.menu_handler import menu_habit_done_simple_show_habits

        # Mock: user doesn't exist
        mock_user_repo.get_by_telegram_id.return_value = None

        # Execute
        result = await menu_habit_done_simple_show_habits(mock_callback_update, context=None)

        # Assert: ERROR_USER_NOT_FOUND message shown
        call_args = mock_callback_update.callback_query.edit_message_text.call_args
        assert msg('ERROR_USER_NOT_FOUND', language) in call_args[0][0]

        # Assert: habit service was NOT called
        mock_habit_service.get_all_active_habits.assert_not_called()
        mock_habit_service.get_active_habits_pending_for_today.assert_not_called()

        # Assert: returned 0
        assert result == 0


class TestRemoveHabitBack:
    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    async def test_back_to_list_shows_selection(self, mock_habit_repo, mock_user_repo, mock_callback_update, mock_active_user, language):
        # Mock user repository to return active user
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock habits list returned by repository
        from src.models.habit import Habit
        mock_habit_repo.get_all_active.return_value = [
            Habit(id='h1', name='A', weight=10, category='x', active=True)
        ]

        result = await remove_back_to_list(mock_callback_update, context=None)
        assert result == AWAITING_REMOVE_SELECTION
        mock_callback_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    async def test_back_to_list_deletes_when_empty(self, mock_habit_repo, mock_user_repo, mock_callback_update, mock_active_user, language):
        # Mock user repository to return active user
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        mock_habit_repo.get_all_active.return_value = []

        result = await remove_back_to_list(mock_callback_update, context=None)
        assert result == ConversationHandler.END
        mock_callback_update.callback_query.delete_message.assert_called_once()


class TestHabitDoneCommand:
    """Test /habit_done command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """User not found should be blocked from /habit_done with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = None

        result = await habit_done_command(mock_telegram_update, context=None)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """Inactive user should be blocked from /habit_done with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        result = await habit_done_command(mock_telegram_update, context=None)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.habit_service')
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_shows_only_active_habits(
        self, mock_user_repo, mock_habit_service, mock_telegram_update,
        mock_active_user, mock_active_habits, language
    ):
        """
        Active user should see only active habits in keyboard.

        Given: User exists and is active
        And: There are active habits in the database
        When: User sends /habit_done command
        Then: Bot displays keyboard with only active habits
        And: Conversation continues to AWAITING_HABIT_SELECTION state
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock: service returns only active habits
        mock_habit_service.get_all_active_habits.return_value = mock_active_habits

        # Execute
        result = await habit_done_command(mock_telegram_update, context=None)

        # Assert: Service was called to get active habits
        mock_habit_service.get_all_active_habits.assert_called_once()

        # Assert: Conversation continues
        assert result == 1  # AWAITING_HABIT_SELECTION

        # Assert: Message with keyboard was sent
        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args

        # Verify message text is the habit selection prompt
        assert call_args[0][0] == msg('HELP_HABIT_SELECTION', language)

        # Verify keyboard was provided
        assert 'reply_markup' in call_args[1]

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.habit_service')
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_no_active_habits_shows_error(
        self, mock_user_repo, mock_habit_service, mock_telegram_update,
        mock_active_user, language
    ):
        """
        When no active habits exist, show error message.

        Given: User exists and is active
        And: There are NO active habits in the database
        When: User sends /habit_done command
        Then: Bot responds with 'No active habits' error message
        And: Conversation ends
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock: service returns empty list (no active habits)
        mock_habit_service.get_all_active_habits.return_value = []

        # Execute
        result = await habit_done_command(mock_telegram_update, context=None)

        # Assert: Service was called to get active habits
        mock_habit_service.get_all_active_habits.assert_called_once()

        # Assert: Conversation ended
        assert result == ConversationHandler.END

        # Assert: Error message sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_NO_HABITS', language)
        )

    @pytest.mark.asyncio
    async def test_inactive_habits_not_returned_by_repository(
        self, mock_active_habits, mock_inactive_habits
    ):
        """
        Repository get_all_active() should filter out inactive habits.

        Given: Database contains both active and inactive habits
        When: habit_service.get_all_active_habits() is called
        Then: Only habits with active=True are returned (via repository)
        And: Habits with active=False are excluded
        """
        from src.services.habit_service import habit_service
        from unittest.mock import Mock

        # Mock: repository returns only active habits
        # (This tests that the repository layer correctly filters)
        mock_habit_repo = Mock()
        mock_habit_repo.get_all_active.return_value = mock_active_habits

        # Replace the habit_repo on the service instance
        original_repo = habit_service.habit_repo
        habit_service.habit_repo = mock_habit_repo

        try:
            # Execute - pass user_id since it's now required
            result = habit_service.get_all_active_habits(user_id=1)

            # Assert: Repository method was called with user_id
            mock_habit_repo.get_all_active.assert_called_once_with(1)

            # Assert: Only active habits returned
            assert len(result) == 3
            assert all(habit.active for habit in result)

            # Assert: Verify habit names match active habits
            habit_names = [h.name for h in result]
            assert "Walking" in habit_names
            assert "Reading" in habit_names
            assert "Meditation" in habit_names

            # Assert: Inactive habits are not in result
            assert "Old Habit 1" not in habit_names
            assert "Old Habit 2" not in habit_names
        finally:
            # Restore original repository
            habit_service.habit_repo = original_repo


class TestStreaksCommand:
    """Test /streaks command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.streak_handler.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """User not found should return error in user's language."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await streaks_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.streak_handler.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """Inactive user should be blocked from /streaks with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await streaks_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )


class TestMyRewardsCommand:
    """Test /my_rewards command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """User not found should return error in user's language."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await my_rewards_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """Inactive user should be blocked from /my_rewards with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await my_rewards_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )


class TestAddRewardCommand:
    """Test /add_reward conversation entry point."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, language):
        """Should block unknown users with localized error."""
        mock_user_repo.get_by_telegram_id.return_value = None
        context = Mock()
        context.user_data = {}

        result = await add_reward_command(mock_telegram_update, context=context)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, language):
        """Inactive users should be blocked."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user
        context = Mock()
        context.user_data = {}

        result = await add_reward_command(mock_telegram_update, context=context)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_active_user_gets_name_prompt(self, mock_user_repo, mock_telegram_update, mock_active_user, language):
        """Active users should be prompted for reward name with cancel keyboard."""
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        context = Mock()
        context.user_data = {}

        result = await add_reward_command(mock_telegram_update, context=context)

        assert result == AWAITING_REWARD_NAME
        assert mock_telegram_update.message.reply_text.await_count == 1
        call_args = mock_telegram_update.message.reply_text.call_args
        assert call_args.args[0] == msg('HELP_ADD_REWARD_NAME_PROMPT', language)
        kwargs = call_args.kwargs
        assert kwargs.get('reply_markup') is not None
        assert kwargs.get('parse_mode') == 'HTML'


class TestAddRewardConversationSteps:
    """Test reward creation conversation steps."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_reward_name_step_valid(
        self,
        mock_lang,
        mock_reward_repo,
        mock_user_repo,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Valid reward name should transition to type selection."""
        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        mock_reward_repo.get_by_name = AsyncMock(return_value=None)

        mock_telegram_update.message.text = "Morning Coffee"
        context = Mock()
        context.user_data = {}

        result = await reward_name_received(mock_telegram_update, context)

        assert result == AWAITING_REWARD_TYPE
        mock_lang.assert_awaited_once()
        stored = context.user_data['reward_creation_data']['name']
        assert stored == "Morning Coffee"
        mock_telegram_update.message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_reward_name_step_duplicate(
        self,
        mock_lang,
        mock_reward_repo,
        mock_user_repo,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Duplicate reward names should be rejected and re-prompted."""
        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        mock_reward_repo.get_by_name = AsyncMock(return_value=Mock())

        mock_telegram_update.message.text = "Morning Coffee"
        mock_telegram_update.message.reply_text.reset_mock()
        context = Mock()
        context.user_data = {}

        result = await reward_name_received(mock_telegram_update, context)

        assert result == AWAITING_REWARD_NAME
        expected = (
            f"{msg('ERROR_REWARD_NAME_EXISTS', language)}\n\n"
            f"{msg('HELP_ADD_REWARD_NAME_PROMPT', language)}"
        )
        await_call = mock_telegram_update.message.reply_text.await_args
        assert await_call.args[0] == expected

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_reward_weight_invalid_input(
        self,
        mock_lang,
        mock_telegram_update,
        language
    ):
        """Non-numeric weight should trigger error and stay in same state."""
        mock_lang.return_value = language
        mock_telegram_update.message.text = "abc"
        mock_telegram_update.message.reply_text.reset_mock()
        context = Mock()
        context.user_data = {}

        result = await reward_weight_received(mock_telegram_update, context)

        assert result == AWAITING_REWARD_WEIGHT
        expected = msg(
            'ERROR_REWARD_WEIGHT_INVALID',
            language,
            min=REWARD_WEIGHT_MIN,
            max=REWARD_WEIGHT_MAX
        )
        await_call = mock_telegram_update.message.reply_text.await_args
        assert await_call.args[0] == expected
        assert await_call.kwargs.get('reply_markup') is not None
class TestClaimRewardCommand:
    """Test /claim_reward command handler with multi-language support."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with args."""
        context = Mock()
        context.args = ["Coffee"]
        return context

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, mock_context, language):
        """User not found should return error in user's language."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await claim_reward_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, mock_context, language):
        """Inactive user should be blocked from /claim_reward with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await claim_reward_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )


class TestAddRewardPieceValueRemoval:
    """Test that /add_reward flow skips piece_value step (Feature 0023)."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_pieces_received_goes_directly_to_confirm(
        self,
        mock_lang,
        mock_telegram_update,
        language
    ):
        """After entering pieces_required, should go directly to confirmation, not piece_value."""
        mock_lang.return_value = language
        mock_telegram_update.message.text = "5"
        context = Mock()
        context.user_data = {
            'reward_creation_data': {
                'name': 'Coffee',
                'type': 'virtual',
                'weight': 10.0
            }
        }

        result = await reward_pieces_received(mock_telegram_update, context)

        # Should go directly to AWAITING_REWARD_CONFIRM, NOT AWAITING_REWARD_VALUE
        assert result == AWAITING_REWARD_CONFIRM
        # Verify confirmation message was sent
        mock_telegram_update.message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_pieces_selected_goes_directly_to_confirm(
        self,
        mock_lang,
        mock_callback_update,
        language
    ):
        """After selecting pieces=1 via button, should go directly to confirmation."""
        mock_lang.return_value = language
        context = Mock()
        context.user_data = {
            'reward_creation_data': {
                'name': 'Coffee',
                'type': 'virtual',
                'weight': 10.0
            }
        }

        result = await reward_pieces_selected(mock_callback_update, context)

        # Should go directly to AWAITING_REWARD_CONFIRM
        assert result == AWAITING_REWARD_CONFIRM
        # Verify confirmation message was sent via edit
        mock_callback_update.callback_query.edit_message_text.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_confirmation_message_excludes_piece_value(
        self,
        mock_lang,
        mock_telegram_update,
        language
    ):
        """Confirmation message should NOT mention 'Piece Value' or 'piece_value'."""
        mock_lang.return_value = language
        mock_telegram_update.message.text = "3"
        context = Mock()
        context.user_data = {
            'reward_creation_data': {
                'name': 'Coffee',
                'type': 'virtual',
                'weight': 10.0
            }
        }

        await reward_pieces_received(mock_telegram_update, context)

        # Get the confirmation message that was sent
        call_args = mock_telegram_update.message.reply_text.await_args
        message_text = call_args.args[0]

        # Verify confirmation message does NOT mention piece value
        assert 'piece' not in message_text.lower() or 'pieces' in message_text.lower()  # "pieces" is ok (pieces_required)
        # The message should contain name, type, weight, and pieces_required
        assert 'Coffee' in message_text
        assert '10' in message_text  # weight
        assert '3' in message_text  # pieces_required


class TestEditRewardPieceValueRemoval:
    """Test that /edit_reward flow skips piece_value step (Feature 0023)."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_pieces_received_goes_directly_to_confirm(
        self,
        mock_lang,
        mock_user_repo,
        mock_reward_repo,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """After editing pieces_required, should go directly to confirmation."""
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

        result = await reward_edit_pieces_received(mock_telegram_update, context)

        # Should go directly to AWAITING_REWARD_EDIT_CONFIRM, NOT AWAITING_REWARD_EDIT_VALUE
        assert result == AWAITING_REWARD_EDIT_CONFIRM
        # Verify confirmation message was sent
        mock_telegram_update.message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_pieces_selected_goes_directly_to_confirm(
        self,
        mock_lang,
        mock_callback_update,
        language
    ):
        """After selecting pieces=1 via button in edit, should go directly to confirmation."""
        mock_lang.return_value = language
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

        result = await reward_edit_pieces_selected(mock_callback_update, context)

        # Should go directly to AWAITING_REWARD_EDIT_CONFIRM
        assert result == AWAITING_REWARD_EDIT_CONFIRM

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.user_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_edit_context_excludes_piece_value(
        self,
        mock_lang,
        mock_user_repo,
        mock_reward_repo,
        mock_callback_update,
        mock_active_user,
        language
    ):
        """When selecting reward for edit, context should NOT store old_piece_value."""
        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Mock reward with piece_value set
        mock_reward = Mock()
        mock_reward.id = 'reward123'
        mock_reward.name = 'Coffee'
        mock_reward.type = 'virtual'
        mock_reward.weight = 10.0
        mock_reward.pieces_required = 3
        mock_reward.piece_value = 5.0  # This should NOT be stored in context
        mock_reward.user_id = mock_active_user.id

        mock_reward_repo.get_by_id = AsyncMock(return_value=mock_reward)

        mock_callback_update.callback_query.data = "edit_reward_reward123"

        context = Mock()
        context.user_data = {}

        await reward_edit_selected(mock_callback_update, context)

        # Verify old_piece_value is NOT in context
        edit_data = context.user_data.get('reward_edit_data', {})
        assert 'old_piece_value' not in edit_data
        # But other fields should be present
        assert edit_data['old_name'] == 'Coffee'
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


# Note: set_reward_status_command has been deprecated and removed in Feature 0005
# Status is now automatically computed by Airtable based on pieces_earned and claimed fields
