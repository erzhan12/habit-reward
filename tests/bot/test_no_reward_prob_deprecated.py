"""Feature 0048: the "No Reward Probability" setting is hidden and deprecated."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.bot import keyboards
from src.bot.handlers import settings_handler
from src.bot.messages import msg


@pytest.mark.parametrize("lang", ["en", "ru", "kk"])
def test_settings_keyboard_has_no_probability_button(lang):
    markup = keyboards.build_settings_keyboard(lang)
    callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "settings_no_reward_prob" not in callbacks
    assert "settings_language" in callbacks


def test_probability_keyboard_removed():
    assert not hasattr(keyboards, "build_no_reward_probability_keyboard")


@pytest.mark.parametrize("lang", ["en", "ru", "kk"])
def test_deprecation_notice_translated(lang):
    text = msg("NO_REWARD_PROB_DEPRECATED", lang)
    assert not text.startswith("[Missing message")
    assert "20%" in text and "50%" in text


def _stale_update():
    update = Mock()
    update.effective_user = Mock(id=999999999)
    update.callback_query = Mock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


async def _tap_stale_button(update, user):
    with patch(
        "src.bot.handlers.settings_handler.get_message_language_async",
        new=AsyncMock(return_value="en"),
    ), patch.object(
        settings_handler.user_repository, "get_by_telegram_id", new=AsyncMock(return_value=user)
    ):
        return await settings_handler.no_reward_prob_deprecated_callback(update, Mock())


@pytest.mark.asyncio
async def test_stale_button_answers_with_notice_and_settings_menu():
    update = _stale_update()
    result = await _tap_stale_button(update, Mock(is_active=True))

    assert result == settings_handler.AWAITING_SETTINGS_SELECTION
    kwargs = update.callback_query.edit_message_text.call_args.kwargs
    assert kwargs["text"].startswith(msg("NO_REWARD_PROB_DEPRECATED", "en"))
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
@pytest.mark.parametrize("user, error_key", [(None, "ERROR_USER_NOT_FOUND"), ("inactive", "ERROR_USER_INACTIVE")])
async def test_stale_button_rejects_unknown_or_inactive_user(user, error_key):
    update = _stale_update()
    user = Mock(is_active=False) if user == "inactive" else user
    result = await _tap_stale_button(update, user)
    assert result == settings_handler.ConversationHandler.END
    update.callback_query.edit_message_text.assert_awaited_once_with(msg(error_key, "en"))


def test_stale_button_registered_as_entry_point_and_in_settings_state():
    def patterns(handlers):
        return {getattr(getattr(h, "pattern", None), "pattern", None) for h in handlers}

    conv = settings_handler.settings_conversation
    assert "^settings_no_reward_prob$" in patterns(conv.entry_points)
    assert "^settings_no_reward_prob$" in patterns(
        conv.states[settings_handler.AWAITING_SETTINGS_SELECTION]
    )
