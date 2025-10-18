"""Unit tests for Telegram bot handlers."""

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


@pytest.fixture
def mock_telegram_user():
    """Create mock Telegram user."""
    return TelegramUser(
        id=999999999,
        first_name="Test",
        last_name="User",
        is_bot=False
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
def mock_active_user():
    """Create mock active user from Airtable."""
    return User(
        id="user123",
        telegram_id="999999999",
        name="Test User",
        weight=1.0,
        active=True
    )


@pytest.fixture
def mock_inactive_user():
    """Create mock inactive user from Airtable."""
    return User(
        id="user456",
        telegram_id="999999999",
        name="Inactive User",
        weight=1.0,
        active=False
    )


class TestStartCommand:
    """Test /start command handler."""

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update):
        """
        TC1.1: User not found should return error message.

        Given: User telegram_id does NOT exist in Airtable Users table
        When: User sends /start command
        Then: Bot responds with 'User not found. Please contact admin to register.'
        """
        # Mock: user doesn't exist in Airtable
        mock_user_repo.get_by_telegram_id.return_value = None

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Error message sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user):
        """
        TC1.3: Inactive user should be blocked.

        Given: User exists in Airtable but active=False
        When: User sends /start command
        Then: Bot responds with 'Your account is not active. Please contact admin.'
        """
        # Mock: user exists but is inactive
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Inactive error message sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_telegram_update, mock_active_user):
        """
        TC1.2: Active user should see welcome message.

        Given: User exists in Airtable and active=True
        When: User sends /start command
        Then: Bot responds with welcome message and command list
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Execute
        await start_command(mock_telegram_update, context=None)

        # Assert: Welcome message sent
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0]

        assert "Welcome to Habit Reward System" in message_text
        assert "/habit_done" in message_text
        assert "/streaks" in message_text
        assert call_args[1].get("parse_mode") == "Markdown"


class TestHelpCommand:
    """Test /help command handler."""

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update):
        """
        User not found should return error message for /help.

        Given: User telegram_id does NOT exist in Airtable Users table
        When: User sends /help command
        Then: Bot responds with 'User not found. Please contact admin to register.'
        """
        # Mock: user doesn't exist in Airtable
        mock_user_repo.get_by_telegram_id.return_value = None

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Error message sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user):
        """
        Inactive user should be blocked from /help command.

        Given: User exists in Airtable but active=False
        When: User sends /help command
        Then: Bot responds with 'Your account is not active. Please contact admin.'
        """
        # Mock: user exists but is inactive
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Inactive error message sent
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )

    @pytest.mark.asyncio
    @patch('src.bot.main.user_repository')
    async def test_user_active_success(self, mock_user_repo, mock_telegram_update, mock_active_user):
        """
        Active user should see help message.

        Given: User exists in Airtable and active=True
        When: User sends /help command
        Then: Bot responds with help message and command descriptions
        """
        # Mock: user exists and is active
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user

        # Execute
        await help_command(mock_telegram_update, context=None)

        # Assert: Help message sent
        call_args = mock_telegram_update.message.reply_text.call_args
        message_text = call_args[0][0]

        assert "Habit Reward System Help" in message_text
        assert "Core Commands" in message_text
        assert "/habit_done" in message_text
        assert call_args[1].get("parse_mode") == "HTML"


class TestHabitDoneCommand:
    """Test /habit_done command handler."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update):
        """Inactive user should be blocked from /habit_done."""
        mock_user_repo.get_by_telegram_id.return_value = None

        result = await habit_done_command(mock_telegram_update, context=None)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_done_handler.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user):
        """Inactive user should be blocked from /habit_done."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        result = await habit_done_command(mock_telegram_update, context=None)

        assert result == ConversationHandler.END
        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )


class TestStreaksCommand:
    """Test /streaks command handler."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.streak_handler.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update):
        """User not found should return error."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await streaks_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.streak_handler.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user):
        """Inactive user should be blocked from /streaks."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await streaks_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )


class TestMyRewardsCommand:
    """Test /my_rewards command handler."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update):
        """User not found should return error."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await my_rewards_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user):
        """Inactive user should be blocked from /my_rewards."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await my_rewards_command(mock_telegram_update, context=None)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )


class TestClaimRewardCommand:
    """Test /claim_reward command handler."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with args."""
        context = Mock()
        context.args = ["Coffee"]
        return context

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, mock_context):
        """User not found should return error."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await claim_reward_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, mock_context):
        """Inactive user should be blocked from /claim_reward."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await claim_reward_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )


class TestSetRewardStatusCommand:
    """Test /set_reward_status command handler."""

    @pytest.fixture
    def mock_context(self):
        """Create mock context with args."""
        context = Mock()
        context.args = ["Coffee", "achieved"]
        return context

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_not_found(self, mock_user_repo, mock_telegram_update, mock_context):
        """User not found should return error."""
        mock_user_repo.get_by_telegram_id.return_value = None

        await set_reward_status_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ User not found. Please contact admin to register."
        )

    @pytest.mark.asyncio
    @patch('src.bot.handlers.reward_handlers.user_repository')
    async def test_user_inactive(self, mock_user_repo, mock_telegram_update, mock_inactive_user, mock_context):
        """Inactive user should be blocked from /set_reward_status."""
        mock_user_repo.get_by_telegram_id.return_value = mock_inactive_user

        await set_reward_status_command(mock_telegram_update, context=mock_context)

        mock_telegram_update.message.reply_text.assert_called_once_with(
            "❌ Your account is not active. Please contact admin."
        )
