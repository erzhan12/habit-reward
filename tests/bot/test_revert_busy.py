"""Feature 0048: a busy database during undo answers with a retry message, not a crash."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.bot.handlers import habit_revert_handler
from src.services.transactions import ServiceBusyError


@pytest.mark.asyncio
async def test_revert_busy_answers_with_error_message():
    update = Mock()
    update.effective_user = Mock(id=999)
    update.callback_query = Mock(data="revert_habit_7")
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = Mock()
    context.user_data = {"revert_habit_map": {"7": SimpleNamespace(id=7, name="Walk")}}

    with patch.object(habit_revert_handler, "get_message_language_async", new=AsyncMock(return_value="en")), \
         patch.object(habit_revert_handler.habit_service, "revert_habit_completion",
                      new=AsyncMock(side_effect=ServiceBusyError("Database is busy, please try again"))):
        await habit_revert_handler.habit_revert_selected_callback(update, context)

    text = update.callback_query.edit_message_text.call_args.args[0]
    assert "try again" in text.lower()


@pytest.mark.asyncio
async def test_revert_mentions_revoked_freeze():
    from src.bot.messages import msg
    from src.models.habit_revert_result import HabitRevertResult

    update = Mock()
    update.effective_user = Mock(id=999)
    update.callback_query = Mock(data="revert_habit_7")
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    context = Mock()
    context.user_data = {"revert_habit_map": {"7": SimpleNamespace(id=7, name="Walk")}}
    result = HabitRevertResult(habit_id=7, habit_name="Walk", success=True, freeze_revoked=True)

    with patch.object(habit_revert_handler, "get_message_language_async", new=AsyncMock(return_value="en")), \
         patch.object(habit_revert_handler, "get_current_navigation", return_value=None), \
         patch.object(habit_revert_handler.habit_service, "revert_habit_completion",
                      new=AsyncMock(return_value=result)):
        await habit_revert_handler.habit_revert_selected_callback(update, context)

    text = update.callback_query.edit_message_text.call_args.args[0]
    assert msg("FREEZE_REVOKED", "en") in text
