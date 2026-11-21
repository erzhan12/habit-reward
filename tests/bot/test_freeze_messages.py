"""Bot freeze texts (feature 0048 UI): completion lines, streaks mark, busy text."""

from datetime import date
from unittest.mock import Mock

import pytest

from src.bot.formatters import (
    format_habit_completion_message,
    format_service_error,
    format_streaks_message,
)
from src.bot.messages import msg
from src.models.habit_completion_result import HabitCompletionResult
from src.services.transactions import ServiceBusyError

FREEZE_KEYS = [
    "FREEZE_WON", "FREEZE_USED", "FREEZE_BURNED", "FREEZE_RETURNED",
    "FREEZE_REVOKED", "INFO_STREAK_FREEZE_LEGEND", "ERROR_BUSY",
]


def _result(**kw):
    base = dict(habit_confirmed=True, habit_name="Walk", streak_count=4, total_weight_applied=70.0)
    base.update(kw)
    return HabitCompletionResult(**base)


@pytest.mark.parametrize("lang", ["en", "ru", "kk"])
@pytest.mark.parametrize("key", FREEZE_KEYS)
def test_freeze_keys_translated(lang, key):
    text = msg(key, lang, date="17.11")
    assert not text.startswith("[Missing message")
    if key in ("FREEZE_USED", "FREEZE_BURNED"):
        assert "17.11" in text


def test_completion_shows_freeze_used_with_short_date():
    text = format_habit_completion_message(
        _result(freeze_used=True, freeze_covered_date=date(2026, 11, 17)), "en"
    )
    assert msg("FREEZE_USED", "en", date="17.11") in text
    assert text.index("Freeze used") > text.index("4")  # after the streak line


def test_completion_shows_freeze_burned():
    text = format_habit_completion_message(
        _result(streak_count=1, freeze_burned=True, freeze_covered_date=date(2026, 11, 17)), "en"
    )
    assert msg("FREEZE_BURNED", "en", date="17.11") in text
    assert "Freeze used" not in text


def test_completion_shows_won_after_no_reward_line():
    text = format_habit_completion_message(_result(freeze_won=True), "en")
    assert text.index(msg("FREEZE_WON", "en")) > text.index(msg("INFO_NO_REWARD", "en"))


def test_completion_shows_returned():
    assert msg("FREEZE_RETURNED", "en") in format_habit_completion_message(_result(freeze_returned=True), "en")


def test_completion_without_freeze_has_no_freeze_lines():
    assert "❄️" not in format_habit_completion_message(_result(), "en")


def test_completion_ignores_truthy_mocks():
    result = Mock(habit_name="Walk", streak_count=2, got_reward=False, reward=None,
                  motivational_quote=None, freeze_covered_date=None)
    assert "❄️" not in format_habit_completion_message(result, "en")


def test_streaks_mark_and_legend_only_when_freeze_held():
    streaks = {1: ("Walk", 5), 2: ("Read", 3)}
    text = format_streaks_message(streaks, "en", {1: 1, 2: 0})
    assert "<b>Walk:</b> 5 days ❄️" in text
    assert "3 days ❄️" not in text
    assert msg("INFO_STREAK_FREEZE_LEGEND", "en") in text

    plain = format_streaks_message(streaks, "en", {1: 0})
    assert "❄️" not in plain
    assert "❄️" not in format_streaks_message(streaks, "en")


def test_service_error_busy_is_translated():
    assert format_service_error(ServiceBusyError("busy"), "ru") == msg("ERROR_BUSY", "ru")
    assert format_service_error(ValueError("boom"), "en") == msg("ERROR_GENERAL", "en", error="boom")


@pytest.mark.asyncio
async def test_streaks_command_marks_habit_holding_effective_freeze():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from src.bot.handlers import streak_handler
    from src.services.streak_service import StreakState

    update = Mock()
    update.effective_user = Mock(id=999, username="u")
    update.message.reply_text = AsyncMock()
    user = SimpleNamespace(id=1, is_active=True, timezone="UTC")
    walk, read = SimpleNamespace(id=1, name="Walk"), SimpleNamespace(id=2, name="Read")
    states = AsyncMock(return_value={1: StreakState(5, 6, 1, None, False), 2: StreakState(3, 4, 0, None, False)})

    with patch.object(streak_handler, "get_message_language_async", new=AsyncMock(return_value="en")), \
         patch.object(streak_handler.user_repository, "get_by_telegram_id", new=AsyncMock(return_value=user)), \
         patch.object(streak_handler.streak_service, "get_all_streaks_for_user", new=AsyncMock(return_value={1: 5, 2: 3})), \
         patch.object(streak_handler.streak_service, "get_streak_states", new=states), \
         patch.object(streak_handler.habit_repository, "get_by_id",
                      new=AsyncMock(side_effect=lambda hid: {1: walk, 2: read}[hid])):
        await streak_handler.streaks_command(update, Mock())

    text = update.message.reply_text.call_args.args[0]
    assert "<b>Walk:</b> 5 days ❄️" in text and "3 days ❄️" not in text
    assert msg("INFO_STREAK_FREEZE_LEGEND", "en") in text
    assert states.call_args.args[1] == [walk, read]
