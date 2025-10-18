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
    set_reward_status_command
)
from src.models.user import User
from src.bot.messages import msg
from src.config import settings


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
        id="user123",
        telegram_id="999999999",
        name="Test User",
        weight=1.0,
        active=True,
        language=language
    )


@pytest.fixture
def mock_inactive_user(language):
    """Create mock inactive user from Airtable with language support."""
    return User(
        id="user456",
        telegram_id="999999999",
        name="Inactive User",
        weight=1.0,
        active=False,
        language=language
    )


class TestStartCommand:
    """Test /start command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
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
    @patch('src.bot.main.user_repository')
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
    @patch('src.bot.main.user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_telegram_update, mock_active_user, language):
        """
        TC1.2: Active user should see welcome message in their language.

        Given: User exists in Airtable and active=True
        When: User sends /start command
        Then: Bot responds with welcome message and command list in the correct language
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Welcome message sent
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0]

        # Language-specific assertions
        expected_welcome = msg('HELP_START_MESSAGE', language)
        assert message_text == expected_welcome
        assert "/habit_done" in message_text
        assert "/streaks" in message_text
        assert call_args[1].get("parse_mode") == "Markdown"


class TestHelpCommand:
    """Test /help command handler with multi-language support."""

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
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
    @patch('src.bot.main.user_repository')
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
    @patch('src.bot.main.user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_telegram_update, mock_active_user, language):
        """
        Active user should see help message in their language.

        Given: User exists in Airtable and active=True
        When: User sends /help command
        Then: Bot responds with help message and command descriptions in the correct language
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

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


class TestSetRewardStatusCommand:
    """Test /set_reward_status command handler with multi-language support."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with args."""
        context = Mock()
        context.args = ["Coffee", "achieved"]
        return context

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, mock_context, language):
        """User not found should return error in user's language."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await set_reward_status_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_NOT_FOUND', language)
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, mock_context, language):
        """Inactive user should be blocked from /set_reward_status with localized message."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await set_reward_status_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            msg('ERROR_USER_INACTIVE', language)
        )
