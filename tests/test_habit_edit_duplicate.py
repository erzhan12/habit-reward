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

class TestEditHabitNameDuplicate:
    """Test duplicate habit name validation during EDIT flow."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_edit_duplicate_name_shows_friendly_error(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Entering an existing habit name (different from current) should show friendly error."""
        from src.bot.handlers.habit_management_handler import habit_edit_name_received, AWAITING_EDIT_NAME

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        
        # Current habit being edited
        current_habit_id = 1
        
        # Another habit that already exists
        existing_habit = Mock()
        existing_habit.id = 2  # Different ID
        existing_habit.name = "Other Existing Habit"
        existing_habit.active = True
        mock_habit_repo.get_by_name.return_value = existing_habit

        mock_telegram_update.message.text = "Other Existing Habit"
        
        context = Mock()
        context.user_data = {'editing_habit_id': current_habit_id}

        result = await habit_edit_name_received(mock_telegram_update, context)

        # Assert: Returns to same state (AWAITING_EDIT_NAME)
        assert result == AWAITING_EDIT_NAME
        
        # Assert: Friendly error message sent
        call_args = mock_telegram_update.message.reply_text.await_args
        message_text = call_args.args[0]
        
        # Verify message content
        expected_msg = msg('ERROR_HABIT_NAME_EXISTS', language, name="Other Existing Habit")
        assert message_text == expected_msg
        assert call_args.kwargs.get("parse_mode") == "HTML"
        assert call_args.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async', new_callable=AsyncMock)
    @patch('src.bot.handlers.habit_management_handler.habit_repository')
    @patch('src.bot.handlers.habit_management_handler.user_repository')
    async def test_edit_same_name_allowed(
        self,
        mock_user_repo,
        mock_habit_repo,
        mock_lang,
        mock_telegram_update,
        mock_active_user,
        language
    ):
        """Entering the SAME name as the habit being edited should be allowed."""
        from src.bot.handlers.habit_management_handler import habit_edit_name_received, AWAITING_EDIT_WEIGHT

        mock_lang.return_value = language
        mock_user_repo.get_by_telegram_id.return_value = mock_active_user
        
        # Current habit being edited
        current_habit_id = 1
        
        # get_by_name returns the habit itself
        existing_habit = Mock()
        existing_habit.id = 1  # Same ID
        existing_habit.name = "My Habit"
        existing_habit.active = True
        mock_habit_repo.get_by_name.return_value = existing_habit

        mock_telegram_update.message.text = "My Habit"
        
        context = Mock()
        context.user_data = {
            'editing_habit_id': current_habit_id,
            'old_habit_weight': 10
        }

        result = await habit_edit_name_received(mock_telegram_update, context)

        # Assert: Proceeds to next state (AWAITING_EDIT_WEIGHT)
        assert result == AWAITING_EDIT_WEIGHT
        
        # Assert: New name stored in context
        assert context.user_data['new_habit_name'] == "My Habit"
