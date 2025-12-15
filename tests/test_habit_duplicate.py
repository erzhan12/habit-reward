import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User as TelegramUser
from src.bot.messages import msg
from src.config import settings
from src.models.user import User

@pytest.fixture(params=settings.supported_languages)
def language(request):
    return request.param

@pytest.fixture
def mock_telegram_user(language):
    return TelegramUser(
        id=999999999,
        first_name="Test",
        last_name="User",
        is_bot=False,
        language_code=language
    )

@pytest.fixture
def mock_telegram_update(mock_telegram_user):
    message = Mock(spec=Message)
    message.reply_text = AsyncMock()
    update = Mock(spec=Update)
    update.effective_user = mock_telegram_user
    update.message = message
    return update

@pytest.fixture
def mock_active_user(language):
    return User(
        id=123,
        telegram_id="999999999",
        name="Test User",
        is_active=True,
        language=language
    )

class TestHabitNameDuplicate:
    """Test duplicate habit name validation (Feature: Friendly duplicate handling)."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_duplicate_name_shows_friendly_error(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Entering an existing habit name should show friendly error and prompt again."""
        from src.bot.handlers.habit_management_handler import habit_name_received, AWAITING_HABIT_NAME

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        
        # Mock that habit ALREADY exists
        existing_habit = Mock()
        existing_habit.name = "Existing Habit"
        existing_habit.active = True
        mock_habit_repo.get_by_name.return_value = existing_habit

        mock_telegram_update.message.text = "Existing Habit"
        
        context = Mock()
        context.user_data = {}

        result = await habit_name_received(mock_telegram_update, context)

        # Assert: Returns to same state (AWAITING_HABIT_NAME) to try again
        assert result == AWAITING_HABIT_NAME
        
        # Assert: Friendly error message sent
        call_args = mock_telegram_update.message.reply_text.await_args
        message_text = call_args.args[0]
        
        # Verify message content
        expected_msg = msg('ERROR_HABIT_NAME_EXISTS', language, name="Existing Habit")
        assert message_text == expected_msg
        assert call_args.kwargs.get("parse_mode") == "HTML"
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_duplicate_name_updates_active_message(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """When duplicate error is sent, active_msg_id should be updated so it can be replaced later."""
        from src.bot.handlers.habit_management_handler import habit_name_received
        
        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        
        # Mock existing habit
        existing_habit = Mock()
        existing_habit.name = "Existing Habit"
        existing_habit.active = True
        mock_habit_repo.get_by_name.return_value = existing_habit

        mock_telegram_update.message.text = "Existing Habit"
        
        # Mock reply_text return value (the error message)
        mock_error_message = Mock(spec=Message)
        mock_error_message.chat_id = 12345
        mock_error_message.message_id = 67890
        mock_telegram_update.message.reply_text.return_value = mock_error_message
        
        context = Mock()
        context.user_data = {}

        await habit_name_received(mock_telegram_update, context)
        
        # Assert: Context was updated with the ID of the ERROR message
        assert context.user_data.get('active_msg_chat_id') == 12345
        assert context.user_data.get('active_msg_id') == 67890

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_new_name_proceeds(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Entering a new unique name should proceed to weight selection."""
        from src.bot.handlers.habit_management_handler import habit_name_received, AWAITING_HABIT_WEIGHT

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        
        # Mock that habit does NOT exist
        mock_habit_repo.get_by_name.return_value = None

        mock_telegram_update.message.text = "New Unique Habit"
        
        context = Mock()
        context.user_data = {}

        result = await habit_name_received(mock_telegram_update, context)

        # Assert: Proceeds to next state (AWAITING_HABIT_WEIGHT)
        assert result == AWAITING_HABIT_WEIGHT
        
        # Assert: Name stored in context
        assert context.user_data['habit_name'] == "New Unique Habit"
