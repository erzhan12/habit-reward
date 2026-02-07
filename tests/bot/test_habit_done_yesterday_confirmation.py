"""Tests for yesterday confirmation flow in habit_done handler."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update
from telegram.ext import ConversationHandler

from src.bot.handlers import habit_done_handler
from src.bot.messages import msg


def _build_callback_update():
    user = Mock()
    user.id = 999999999
    user.username = "tester"

    query = Mock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.data = ""

    update = Mock(spec=Update)
    update.effective_user = user
    update.callback_query = query
    return update


def _message_text_from_call(call_args):
    if "text" in call_args.kwargs:
        return call_args.kwargs["text"]
    return call_args.args[0]


@pytest.mark.asyncio
async def test_yesterday_selection_shows_confirmation():
    update = _build_callback_update()
    context = Mock()
    context.user_data = {"habit_name": "Reading", "habit_id": "42"}

    yesterday = date.today() - timedelta(days=1)
    date_display = yesterday.strftime("%d %b %Y")

    with patch(
        "src.bot.handlers.habit_done_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch(
        "src.bot.handlers.habit_done_handler.get_user_timezone",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await habit_done_handler.handle_yesterday_selection(update, context)

    assert result == habit_done_handler.CONFIRMING_BACKDATE
    assert context.user_data["backdate_date"] == yesterday

    call_args = update.callback_query.edit_message_text.call_args
    assert call_args.args[0] == msg(
        "HELP_BACKDATE_CONFIRM",
        "en",
        habit_name="Reading",
        date=date_display,
    )

    keyboard = call_args.kwargs.get("reply_markup")
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
    ]
    assert f"backdate_confirm_42_{yesterday.isoformat()}" in callbacks
    assert "backdate_cancel" in callbacks


@pytest.mark.asyncio
async def test_yesterday_confirmation_processes_completion():
    update = _build_callback_update()
    context = Mock()

    yesterday = date.today() - timedelta(days=1)
    context.user_data = {
        "habit_name": "Reading",
        "habit_id": "42",
        "backdate_date": yesterday,
    }

    result_mock = Mock(streak_count=5)

    with patch(
        "src.bot.handlers.habit_done_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch(
        "src.bot.handlers.habit_done_handler.get_user_timezone",
        new=AsyncMock(return_value="UTC"),
    ), patch(
        "src.bot.handlers.habit_done_handler.habit_service.process_habit_completion",
        new=AsyncMock(return_value=result_mock),
    ) as process_mock, patch(
        "src.bot.handlers.habit_done_handler.format_habit_completion_message",
        return_value="STREAK",
    ):
        result = await habit_done_handler.handle_backdate_confirmation(update, context)

    process_mock.assert_awaited_once_with(
        user_telegram_id=str(update.effective_user.id),
        habit_name="Reading",
        target_date=yesterday,
        user_timezone="UTC",
    )
    assert result == ConversationHandler.END

    call_args = update.callback_query.edit_message_text.call_args
    message_text = _message_text_from_call(call_args)
    expected_prefix = msg(
        "SUCCESS_BACKDATE_COMPLETED",
        "en",
        habit_name="Reading",
        date=yesterday.strftime("%d %b %Y"),
    )
    assert expected_prefix in message_text
    assert "STREAK" in message_text

    assert "habit_id" not in context.user_data
    assert "habit_name" not in context.user_data
    assert "backdate_date" not in context.user_data


@pytest.mark.asyncio
async def test_yesterday_confirmation_duplicate_shows_error():
    update = _build_callback_update()
    context = Mock()

    yesterday = date.today() - timedelta(days=1)
    context.user_data = {
        "habit_name": "Reading",
        "habit_id": "42",
        "backdate_date": yesterday,
    }

    with patch(
        "src.bot.handlers.habit_done_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch(
        "src.bot.handlers.habit_done_handler.get_user_timezone",
        new=AsyncMock(return_value="UTC"),
    ), patch(
        "src.bot.handlers.habit_done_handler.habit_service.process_habit_completion",
        new=AsyncMock(side_effect=ValueError("already completed")),
    ):
        result = await habit_done_handler.handle_backdate_confirmation(update, context)

    assert result == ConversationHandler.END

    call_args = update.callback_query.edit_message_text.call_args
    message_text = _message_text_from_call(call_args)
    assert message_text == msg(
        "ERROR_BACKDATE_DUPLICATE",
        "en",
        habit_name="Reading",
        date=yesterday.strftime("%d %b %Y"),
    )

    assert "habit_id" not in context.user_data
    assert "habit_name" not in context.user_data
    assert "backdate_date" not in context.user_data


@pytest.mark.asyncio
async def test_yesterday_cancel_cleans_context():
    update = _build_callback_update()

    context = Mock()
    context.user_data = {
        "habit_name": "Reading",
        "habit_id": "42",
        "backdate_date": date.today() - timedelta(days=1),
    }

    with patch(
        "src.bot.handlers.habit_done_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch(
        "src.bot.handlers.habit_done_handler.habit_service.process_habit_completion",
        new=AsyncMock(),
    ) as process_mock:
        result = await habit_done_handler.cancel_handler(update, context)

    process_mock.assert_not_called()
    assert result == ConversationHandler.END
    assert "habit_id" not in context.user_data
    assert "habit_name" not in context.user_data
    assert "backdate_date" not in context.user_data
    call_args = update.callback_query.edit_message_text.call_args
    assert call_args.args[0] == msg("INFO_CANCELLED", "en")
    assert call_args.kwargs.get("reply_markup") is not None
