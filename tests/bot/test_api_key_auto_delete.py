"""Tests for API key auto-deletion scheduling."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.bot.handlers import settings_handler


async def _run_api_key_name_entered(raw_key: str = "hrk_test"):
    update = Mock()
    update.effective_user = Mock(id=999999999)

    message = Mock()
    message.text = "My API Key"
    key_message = Mock()
    key_message.chat_id = 111
    key_message.message_id = 222
    message.reply_text = AsyncMock(side_effect=[key_message, Mock()])
    update.message = message

    context = Mock()
    context.job_queue = Mock()
    context.job_queue.run_once = Mock()

    user = Mock()
    user.id = 123

    with patch(
        "src.bot.handlers.settings_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch(
        "src.bot.handlers.settings_handler.user_repository.get_by_telegram_id",
        new=AsyncMock(return_value=user),
    ), patch(
        "src.bot.handlers.settings_handler.api_key_service.create_api_key",
        new=AsyncMock(return_value=(Mock(), raw_key)),
    ):
        result = await settings_handler.api_key_name_entered(update, context)

    return update, context, key_message, result, raw_key


@pytest.mark.asyncio
async def test_api_key_message_deletion_scheduled():
    update, context, key_message, result, _ = await _run_api_key_name_entered()

    assert result == settings_handler.AWAITING_API_KEY_SELECTION

    context.job_queue.run_once.assert_called_once()
    args, kwargs = context.job_queue.run_once.call_args
    assert args[0] == settings_handler._delete_api_key_message
    assert kwargs["when"] == settings_handler.API_KEY_MESSAGE_DELETE_SECONDS
    assert kwargs["data"] == {
        "chat_id": key_message.chat_id,
        "message_id": key_message.message_id,
    }


@pytest.mark.asyncio
async def test_api_key_message_contains_raw_key():
    update, _, _, _, raw_key = await _run_api_key_name_entered(raw_key="hrk_visible")

    first_call_args = update.message.reply_text.call_args_list[0].args
    assert raw_key in first_call_args[0]


@pytest.mark.asyncio
async def test_delete_callback_deletes_message():
    context = Mock()
    context.job = Mock()
    context.job.data = {"chat_id": 1, "message_id": 2}
    context.bot = AsyncMock()

    await settings_handler._delete_api_key_message(context)

    context.bot.delete_message.assert_awaited_once_with(chat_id=1, message_id=2)


@pytest.mark.asyncio
async def test_delete_callback_handles_failure():
    context = Mock()
    context.job = Mock()
    context.job.data = {"chat_id": 1, "message_id": 2}
    context.bot = AsyncMock()
    context.bot.delete_message.side_effect = Exception("boom")

    with patch("src.bot.handlers.settings_handler.logger") as logger:
        await settings_handler._delete_api_key_message(context)

    logger.warning.assert_called_once()
