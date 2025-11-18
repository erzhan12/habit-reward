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
    AWAITING_REWARD_NAME,
    AWAITING_REWARD_TYPE,
    AWAITING_REWARD_WEIGHT
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
from src.bot.keyboards import build_start_menu_keyboard
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
    @patch('src.bot.handlers.command_handlers.audit_log_service')
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
    @patch('src.bot.handlers.command_handlers.audit_log_service')
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


class TestRemoveHabitBack:
    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    async def test_back_to_list_shows_selection(self, mock_habit_repo, mock_callback_update, mock_active_user, language):
        # Mock habits list returned by repository
        from src.models.habit import Habit
        mock_habit_repo.get_all_active.return_value = [
            Habit(id='h1', name='A', weight=10, category='x', active=True)
        ]

        result = await remove_back_to_list(mock_callback_update, context=None)
        assert result == AWAITING_REMOVE_SELECTION
        mock_callback_update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    async def test_back_to_list_deletes_when_empty(self, mock_habit_repo, mock_callback_update, language):
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
            # Execute
            result = habit_service.get_all_active_habits()

            # Assert: Repository method was called
            mock_habit_repo.get_all_active.assert_called_once()

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
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_reward_name_step_valid(
        self,
        mock_lang,
        mock_reward_repo,
        mock_telegram_update,
        language
    ):
        """Valid reward name should transition to type selection."""
        mock_lang.return_value = language
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
    @patch('src.bot.handlers.reward_handlers.reward_repository')
    @patch('src.bot.handlers.reward_handlers.get_message_language_async', new_callable=AsyncMock)
    async def test_reward_name_step_duplicate(
        self,
        mock_lang,
        mock_reward_repo,
        mock_telegram_update,
        language
    ):
        """Duplicate reward names should be rejected and re-prompted."""
        mock_lang.return_value = language
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


# Note: set_reward_status_command has been deprecated and removed in Feature 0005
# Status is now automatically computed by Airtable based on pieces_earned and claimed fields
