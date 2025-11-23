"""Unit tests for habit edit skip functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, CallbackQuery

from src.bot.handlers.habit_management_handler import (
    habit_edit_name_skip,
    habit_edit_weight_skip,
    habit_edit_category_skip,
    habit_edit_grace_days_skip,
    habit_edit_exempt_days_skip,
    AWAITING_EDIT_WEIGHT,
    AWAITING_EDIT_CATEGORY,
    AWAITING_EDIT_GRACE_DAYS,
    AWAITING_EDIT_EXEMPT_DAYS,
    AWAITING_EDIT_CONFIRMATION
)
from src.bot.keyboards import (
    build_skip_cancel_keyboard,
    build_weight_selection_keyboard,
    build_category_selection_keyboard,
    build_grace_days_keyboard,
    build_exempt_days_keyboard
)
from src.bot.messages import msg
from src.config import settings


@pytest.fixture(params=settings.supported_languages)
def language(request):
    """Parameterized fixture for testing all supported languages."""
    return request.param


@pytest.fixture
def mock_callback_query():
    """Create mock callback query."""
    query = Mock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = ''
    return query


@pytest.fixture
def mock_update_with_callback(mock_callback_query):
    """Create mock update with callback_query."""
    update = Mock(spec=Update)
    update.effective_user = Mock()
    update.effective_user.id = 999999999
    update.callback_query = mock_callback_query
    return update


@pytest.fixture
def mock_context():
    """Create mock context with user_data."""
    context = Mock()
    context.user_data = {}
    return context


@pytest.fixture
def mock_habit_data():
    """Create mock habit data for testing."""
    return {
        'old_habit_name': 'Test Habit',
        'old_habit_weight': 30,
        'old_habit_category': 'health',
        'old_habit_grace_days': 2,
        'old_habit_exempt_days': [6, 7]
    }


class TestHabitEditNameSkip:
    """Test skip functionality for habit name editing."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_weight_selection_keyboard')
    async def test_habit_edit_name_skip_preserves_old_name(
        self, mock_build_keyboard, mock_get_lang, 
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC1: Skipping name edit preserves old name and advances to weight selection.
        
        Given: User clicks Skip on name edit prompt
        When: habit_edit_name_skip() is called
        Then: new_habit_name = old_habit_name, state advances to AWAITING_EDIT_WEIGHT
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_keyboard = Mock()
        mock_build_keyboard.return_value = mock_keyboard
        
        # Execute
        result = await habit_edit_name_skip(mock_update_with_callback, mock_context)
        
        # Assert
        assert result == AWAITING_EDIT_WEIGHT
        assert mock_context.user_data['new_habit_name'] == 'Test Habit'
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_build_keyboard.assert_called_once_with(
            current_weight=30,
            language=language,
            skip_callback="skip_weight"
        )
        mock_update_with_callback.callback_query.edit_message_text.assert_called_once()


class TestHabitEditWeightSkip:
    """Test skip functionality for habit weight editing."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_category_selection_keyboard')
    async def test_habit_edit_weight_skip_preserves_old_weight(
        self, mock_build_keyboard, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC2: Skipping weight edit preserves old weight and advances to category selection.
        
        Given: User clicks Skip on weight selection
        When: habit_edit_weight_skip() is called
        Then: new_habit_weight = old_habit_weight, state advances to AWAITING_EDIT_CATEGORY
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_keyboard = Mock()
        mock_build_keyboard.return_value = mock_keyboard
        
        # Execute
        result = await habit_edit_weight_skip(mock_update_with_callback, mock_context)
        
        # Assert
        assert result == AWAITING_EDIT_CATEGORY
        assert mock_context.user_data['new_habit_weight'] == 30
        mock_build_keyboard.assert_called_once_with(
            current_category='health',
            language=language,
            skip_callback="skip_category"
        )


class TestHabitEditCategorySkip:
    """Test skip functionality for habit category editing."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_grace_days_keyboard')
    async def test_habit_edit_category_skip_preserves_old_category(
        self, mock_build_keyboard, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC3: Skipping category edit preserves old category and advances to grace days selection.
        
        Given: User clicks Skip on category selection
        When: habit_edit_category_skip() is called
        Then: new_habit_category = old_habit_category, state advances to AWAITING_EDIT_GRACE_DAYS
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_keyboard = Mock()
        mock_build_keyboard.return_value = mock_keyboard
        
        # Execute
        result = await habit_edit_category_skip(mock_update_with_callback, mock_context)
        
        # Assert
        assert result == AWAITING_EDIT_GRACE_DAYS
        assert mock_context.user_data['new_habit_category'] == 'health'
        mock_build_keyboard.assert_called_once_with(
            current_grace_days=2,
            language=language,
            skip_callback="skip_grace_days"
        )


class TestHabitEditGraceDaysSkip:
    """Test skip functionality for habit grace days editing."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_exempt_days_keyboard')
    @patch('src.bot.handlers.habit_management_handler.msg')
    async def test_habit_edit_grace_days_skip_preserves_old_grace_days(
        self, mock_msg, mock_build_keyboard, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC4: Skipping grace days edit preserves old grace days and advances to exempt days selection.
        
        Given: User clicks Skip on grace days selection
        When: habit_edit_grace_days_skip() is called
        Then: new_habit_grace_days = old_habit_grace_days, state advances to AWAITING_EDIT_EXEMPT_DAYS
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_keyboard = Mock()
        mock_build_keyboard.return_value = mock_keyboard
        mock_msg.side_effect = lambda key, lang, **kwargs: f"{key}_{lang}"
        
        # Execute
        result = await habit_edit_grace_days_skip(mock_update_with_callback, mock_context)
        
        # Assert
        assert result == AWAITING_EDIT_EXEMPT_DAYS
        assert mock_context.user_data['new_habit_grace_days'] == 2
        mock_build_keyboard.assert_called_once_with(
            current_exempt_days=[6, 7],
            language=language,
            skip_callback="skip_exempt_days"
        )


class TestHabitEditExemptDaysSkip:
    """Test skip functionality for habit exempt days editing."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_habit_confirmation_keyboard')
    @patch('src.bot.handlers.habit_management_handler.msg')
    async def test_habit_edit_exempt_days_skip_preserves_old_exempt_days(
        self, mock_msg, mock_build_keyboard, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC5: Skipping exempt days edit preserves old exempt days and advances to confirmation.
        
        Given: User clicks Skip on exempt days selection
        When: habit_edit_exempt_days_skip() is called
        Then: new_habit_exempt_days = old_habit_exempt_days, state advances to AWAITING_EDIT_CONFIRMATION
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_keyboard = Mock()
        mock_build_keyboard.return_value = mock_keyboard
        mock_msg.side_effect = lambda key, lang, **kwargs: f"{key}_{lang}"
        
        # Execute
        result = await habit_edit_exempt_days_skip(mock_update_with_callback, mock_context)
        
        # Assert
        assert result == AWAITING_EDIT_CONFIRMATION
        assert mock_context.user_data['new_habit_exempt_days'] == [6, 7]
        mock_build_keyboard.assert_called_once_with(language=language)


class TestSkipAllFields:
    """Test skipping all fields preserves all original values."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_weight_selection_keyboard')
    @patch('src.bot.handlers.habit_management_handler.build_category_selection_keyboard')
    @patch('src.bot.handlers.habit_management_handler.build_grace_days_keyboard')
    @patch('src.bot.handlers.habit_management_handler.build_exempt_days_keyboard')
    @patch('src.bot.handlers.habit_management_handler.build_habit_confirmation_keyboard')
    @patch('src.bot.handlers.habit_management_handler.msg')
    async def test_skip_all_fields_preserves_original_values(
        self, mock_msg, mock_build_confirmation, mock_build_exempt, mock_build_grace,
        mock_build_category, mock_build_weight, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC6: Skipping all fields preserves all original values.
        
        Given: User skips all fields during edit
        When: All skip handlers are called sequentially
        Then: All new_habit_* values match old_habit_* values
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        mock_msg.side_effect = lambda key, lang, **kwargs: f"{key}_{lang}"
        
        # Mock keyboards
        for mock_build in [mock_build_weight, mock_build_category, mock_build_grace, 
                          mock_build_exempt, mock_build_confirmation]:
            mock_build.return_value = Mock()
        
        # Execute: Skip all fields sequentially
        await habit_edit_name_skip(mock_update_with_callback, mock_context)
        await habit_edit_weight_skip(mock_update_with_callback, mock_context)
        await habit_edit_category_skip(mock_update_with_callback, mock_context)
        await habit_edit_grace_days_skip(mock_update_with_callback, mock_context)
        await habit_edit_exempt_days_skip(mock_update_with_callback, mock_context)
        
        # Assert: All values preserved
        assert mock_context.user_data['new_habit_name'] == mock_context.user_data['old_habit_name']
        assert mock_context.user_data['new_habit_weight'] == mock_context.user_data['old_habit_weight']
        assert mock_context.user_data['new_habit_category'] == mock_context.user_data['old_habit_category']
        assert mock_context.user_data['new_habit_grace_days'] == mock_context.user_data['old_habit_grace_days']
        assert mock_context.user_data['new_habit_exempt_days'] == mock_context.user_data['old_habit_exempt_days']


class TestSkipMixedWithChanges:
    """Test skipping some fields while changing others."""

    @pytest.mark.asyncio
    @patch('src.bot.handlers.habit_management_handler.get_message_language_async')
    @patch('src.bot.handlers.habit_management_handler.build_weight_selection_keyboard')
    @patch('src.bot.handlers.habit_management_handler.build_category_selection_keyboard')
    async def test_skip_some_fields_mixed_with_changes(
        self, mock_build_category, mock_build_weight, mock_get_lang,
        mock_update_with_callback, mock_context, mock_habit_data, language
    ):
        """
        TC7: Skipping some fields while changing others works correctly.
        
        Given: User skips name and weight, changes category
        When: Skip handlers called for name/weight, category changed manually
        Then: Skipped fields preserve old values, changed field has new value
        """
        # Setup
        mock_context.user_data = mock_habit_data.copy()
        mock_get_lang.return_value = language
        
        # Execute: Skip name and weight
        await habit_edit_name_skip(mock_update_with_callback, mock_context)
        await habit_edit_weight_skip(mock_update_with_callback, mock_context)
        
        # Manually set new category (simulating user selection)
        mock_context.user_data['new_habit_category'] = 'productivity'
        
        # Assert: Skipped fields preserved, changed field updated
        assert mock_context.user_data['new_habit_name'] == mock_context.user_data['old_habit_name']
        assert mock_context.user_data['new_habit_weight'] == mock_context.user_data['old_habit_weight']
        assert mock_context.user_data['new_habit_category'] == 'productivity'
        assert mock_context.user_data['new_habit_category'] != mock_context.user_data['old_habit_category']


class TestSkipButtonTranslations:
    """Test skip button translations across languages."""

    def test_skip_button_translations(self, language):
        """
        TC8: Skip button text matches BUTTON_SKIP translation for each language.
        
        Given: Keyboard builder called with different languages
        When: build_skip_cancel_keyboard() is called
        Then: Skip button text matches msg('BUTTON_SKIP', language)
        """
        keyboard = build_skip_cancel_keyboard(language=language, skip_callback="skip_test")
        
        # Find Skip button
        skip_button = None
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "skip_test":
                    skip_button = button
                    break
        
        assert skip_button is not None
        expected_text = msg('BUTTON_SKIP', language)
        assert skip_button.text == expected_text


class TestKeyboardSkipCallbacks:
    """Test that keyboards include skip buttons when skip_callback is provided."""

    def test_weight_keyboard_includes_skip_button(self, language):
        """
        TC9: Weight selection keyboard includes Skip button when skip_callback provided.
        
        Given: build_weight_selection_keyboard called with skip_callback
        When: Keyboard is built
        Then: Skip button present with correct callback_data
        """
        keyboard = build_weight_selection_keyboard(
            current_weight=30,
            language=language,
            skip_callback="skip_weight"
        )
        
        # Find Skip button
        skip_button = None
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "skip_weight":
                    skip_button = button
                    break
        
        assert skip_button is not None
        assert skip_button.text == msg('BUTTON_SKIP', language)

    def test_category_keyboard_includes_skip_button(self, language):
        """Category selection keyboard includes Skip button when skip_callback provided."""
        keyboard = build_category_selection_keyboard(
            current_category='health',
            language=language,
            skip_callback="skip_category"
        )
        
        skip_button = None
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "skip_category":
                    skip_button = button
                    break
        
        assert skip_button is not None

    def test_grace_days_keyboard_includes_skip_button(self, language):
        """Grace days keyboard includes Skip button when skip_callback provided."""
        keyboard = build_grace_days_keyboard(
            current_grace_days=2,
            language=language,
            skip_callback="skip_grace_days"
        )
        
        skip_button = None
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "skip_grace_days":
                    skip_button = button
                    break
        
        assert skip_button is not None

    def test_exempt_days_keyboard_includes_skip_button(self, language):
        """Exempt days keyboard includes Skip button when skip_callback provided."""
        keyboard = build_exempt_days_keyboard(
            current_exempt_days=[6, 7],
            language=language,
            skip_callback="skip_exempt_days"
        )
        
        skip_button = None
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data == "skip_exempt_days":
                    skip_button = button
                    break
        
        assert skip_button is not None

    def test_keyboard_without_skip_callback_no_skip_button(self, language):
        """Keyboard without skip_callback does not include Skip button."""
        keyboard = build_weight_selection_keyboard(
            current_weight=30,
            language=language,
            skip_callback=None
        )
        
        # Check no skip button exists
        skip_buttons = [
            button for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data and 'skip' in button.callback_data
        ]
        
        assert len(skip_buttons) == 0

