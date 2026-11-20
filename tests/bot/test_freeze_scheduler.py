"""Freeze burn job registration and notices (feature 0048 §3)."""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
from django.conf import settings
from telegram.error import Forbidden

from src.bot import freeze_scheduler
from src.bot.messages import msg
from src.services.freeze_service import FreezeSpend


def test_register_without_job_queue_warns_and_returns():
    app = Mock(job_queue=None)
    with patch.object(freeze_scheduler, "logger") as log:
        freeze_scheduler.register_freeze_jobs(app)
    assert "JobQueue" in log.warning.call_args.args[0]


def test_register_schedules_repeating_job_once():
    jq = Mock()
    jq.get_jobs_by_name.return_value = []
    app = Mock(job_queue=jq)
    freeze_scheduler.register_freeze_jobs(app)
    jq.run_repeating.assert_called_once()
    kwargs = jq.run_repeating.call_args.kwargs
    assert kwargs["interval"] == settings.FREEZE_JOB_INTERVAL_SECONDS
    assert kwargs["name"] == "freeze_burn_tick"
    assert jq.run_repeating.call_args.args[0] is freeze_scheduler.burn_due_freezes_job

    jq.get_jobs_by_name.return_value = [Mock()]
    freeze_scheduler.register_freeze_jobs(app)
    jq.run_repeating.assert_called_once()  # not registered twice


def _spend(tg="111", habit="Walk", covered=date(2026, 11, 17), notify=True, lang="en", habit_id=1):
    return FreezeSpend(habit_id=habit_id, user_id=1, telegram_id=tg, language=lang,
                       habit_name=habit, covered_date=covered, notify=notify)


async def _run(spends, send=None):
    bot = Mock()
    bot.send_message = send or AsyncMock()
    context = Mock(bot=bot)
    with patch.object(freeze_scheduler.freeze_service, "burn_due_freezes", new=AsyncMock(return_value=spends)):
        await freeze_scheduler.burn_due_freezes_job(context)
    return bot.send_message


@pytest.mark.asyncio
async def test_one_message_per_user_listing_habits():
    send = await _run([_spend(habit="Walk", habit_id=1), _spend(habit="Read", habit_id=2),
                       _spend(tg="222", habit="Run", habit_id=3)])
    assert send.await_count == 2
    first = send.await_args_list[0].kwargs
    assert first["chat_id"] == "111" and first["parse_mode"] == "HTML"
    assert "Walk" in first["text"] and "Read" in first["text"] and "17.11" in first["text"]


@pytest.mark.asyncio
async def test_no_message_when_streak_already_broken_or_no_telegram_id():
    send = await _run([_spend(notify=False), _spend(tg=None, habit_id=2)])
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_message_when_nothing_spent():
    send = await _run([])
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_forbidden_is_logged_and_others_still_sent():
    send = AsyncMock(side_effect=[Forbidden("bot was blocked"), None])
    with patch.object(freeze_scheduler, "logger") as log:
        send = await _run([_spend(tg="111"), _spend(tg="222", habit_id=2)], send=send)
    assert send.await_count == 2
    assert "bot was blocked" in str(log.warning.call_args)


@pytest.mark.parametrize("lang", ["en", "ru", "kk"])
def test_notice_translated(lang):
    text = msg("FREEZE_SPENT_NOTICE", lang, date="17.11", habits="Walk")
    assert not text.startswith("[Missing message")
    assert "17.11" in text and "Walk" in text
