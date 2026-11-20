"""Periodic freeze burn job (feature 0048 §3), DB-backed.

``get_user_today`` is patched in freeze_service with a per-timezone mapping, so two
users in different timezones see their own local date.
"""

import asyncio
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async

from src.core.models import Habit, HabitFreezeEvent, HabitLog, User
from src.services.freeze_service import FreezeService

MON = date(2026, 11, 16)


def d(n):
    return MON + timedelta(days=n)


_tg = iter(range(4850001, 4859999))


def _user(tz="UTC", telegram=True):
    n = str(next(_tg))
    return User.objects.create_user(
        username=f"tg_{n}", telegram_id=n if telegram else None, name="J", language="ru", timezone=tz
    )


def _habit(user, name="Walk", allowed_skip_days=0, exempt=None, freeze=True, earned_on=None):
    h = Habit.objects.create(user=user, name=name, weight=0, allowed_skip_days=allowed_skip_days,
                             exempt_weekdays=exempt or [])
    if freeze:
        Habit.objects.filter(pk=h.pk).update(freeze_count=1)
        if earned_on is not None:
            HabitFreezeEvent.objects.create(user=user, habit=h, event_type="earned", earned_on=earned_on, state="held")
        h.refresh_from_db()
    return h


def _log(user, habit, day, streak=1):
    return HabitLog.objects.create(user=user, habit=habit, streak_count=streak, habit_weight=0,
                                   total_weight_applied=80.0, last_completed_date=day)


def today_by_tz(mapping):
    return patch("src.services.freeze_service.get_user_today", side_effect=lambda tz="UTC": mapping.get(tz or "UTC"))


def _spent(habit):
    return list(HabitFreezeEvent.objects.filter(habit=habit, event_type="spent").values_list("covered_date", "habit_log_id"))


S = sync_to_async


@pytest.mark.asyncio
async def test_spends_after_first_missed_day_ends():
    def _prep():
        u = _user()
        h = _habit(u, earned_on=d(0))
        _log(u, h, d(0))
        return h

    h = await S(_prep)()
    with today_by_tz({"UTC": d(2)}):
        spends = await FreezeService().burn_due_freezes()
    assert [(s.habit_id, s.covered_date, s.notify) for s in spends] == [(h.id, d(1), True)]
    assert await S(_spent)(h) == [(d(1), None)]
    count = await S(lambda: Habit.objects.get(pk=h.pk).freeze_count)()
    held = await S(lambda: HabitFreezeEvent.objects.get(habit=h, event_type="earned").state)()
    assert (count, held) == (0, "spent")


@pytest.mark.asyncio
async def test_nothing_before_local_midnight_and_per_user_timezones():
    def _prep():
        a = _user(tz="Asia/Almaty")
        b = _user(tz="America/New_York")
        ha, hb = _habit(a), _habit(b)
        _log(a, ha, d(0))
        _log(b, hb, d(0))
        return ha, hb

    ha, hb = await S(_prep)()
    # Almaty is already on Wednesday (Tue ended); New York is still on Tuesday.
    with today_by_tz({"Asia/Almaty": d(2), "America/New_York": d(1)}):
        spends = await FreezeService().burn_due_freezes()
    assert [s.habit_id for s in spends] == [ha.id]
    assert await S(_spent)(hb) == []


@pytest.mark.asyncio
async def test_idempotent_and_concurrent_runs_spend_once():
    def _prep():
        u = _user()
        h = _habit(u)
        _log(u, h, d(0))
        return h

    h = await S(_prep)()
    with today_by_tz({"UTC": d(2)}):
        svc = FreezeService()
        first, second = await asyncio.gather(svc.burn_due_freezes(), svc.burn_due_freezes())
        third = await svc.burn_due_freezes()
    assert len(first) + len(second) == 1 and third == []
    assert await S(_spent)(h) == [(d(1), None)]


@pytest.mark.asyncio
async def test_job_was_down_spends_for_guard_day_without_notice():
    def _prep():
        u = _user()
        h = _habit(u)
        _log(u, h, d(0))
        return h

    await S(_prep)()
    with today_by_tz({"UTC": d(4)}):  # Tue, Wed, Thu ended
        spends = await FreezeService().burn_due_freezes()
    assert [(s.covered_date, s.notify) for s in spends] == [(d(1), False)]


@pytest.mark.asyncio
async def test_no_spend_when_not_usable_no_freeze_or_no_logs():
    def _prep():
        u = _user()
        late = _habit(u, name="Late", earned_on=d(1))   # won on the guard day itself
        _log(u, late, d(0))
        none = _habit(u, name="None", freeze=False)
        _log(u, none, d(0))
        nologs = _habit(u, name="NoLogs")
        return late, none, nologs

    late, none, nologs = await S(_prep)()
    with today_by_tz({"UTC": d(2)}):
        spends = await FreezeService().burn_due_freezes()
    assert spends == []


@pytest.mark.asyncio
async def test_exempt_weekdays_skipped_and_notice_still_sent():
    # Fri log, Sat/Sun exempt, today Tue: only Monday ended unfilled -> guard day Monday.
    def _prep():
        u = _user()
        h = _habit(u, allowed_skip_days=0, exempt=[6, 7])
        _log(u, h, d(-3))   # Friday
        return h

    await S(_prep)()
    with today_by_tz({"UTC": d(1)}):  # Tuesday: Sat, Sun exempt, Mon ended
        spends = await FreezeService().burn_due_freezes()
    assert [(s.covered_date, s.notify) for s in spends] == [(d(0), True)]


@pytest.mark.asyncio
async def test_epoch_only_history_is_skipped():
    def _prep():
        u = _user()
        h = _habit(u)
        _log(u, h, d(0))
        Habit.objects.filter(pk=h.pk).update(streak_epoch=d(1))
        return h

    h = await S(_prep)()
    with today_by_tz({"UTC": d(3)}):
        spends = await FreezeService().burn_due_freezes()
    assert spends == [] and await S(_spent)(h) == []


@pytest.mark.asyncio
async def test_busy_habit_is_skipped_and_sweep_continues():
    from src.services import freeze_service as fs_module
    from src.services.transactions import ServiceBusyError

    def _prep():
        u = _user()
        h1, h2 = _habit(u, name="A"), _habit(u, name="B")
        _log(u, h1, d(0))
        _log(u, h2, d(0))
        return h1, h2

    h1, h2 = await S(_prep)()
    real = fs_module.run_in_transaction

    async def flaky(fn, habit_id, *a, **kw):
        if habit_id == h1.id:
            raise ServiceBusyError("busy")
        return await real(fn, habit_id, *a, **kw)

    with today_by_tz({"UTC": d(2)}), patch.object(fs_module, "run_in_transaction", side_effect=flaky):
        spends = await FreezeService().burn_due_freezes()
    assert [s.habit_id for s in spends] == [h2.id]


@pytest.mark.asyncio
async def test_spend_carries_notice_fields():
    def _prep():
        u = _user()
        h = _habit(u, name="Read")
        _log(u, h, d(0))
        return u, h

    u, h = await S(_prep)()
    with today_by_tz({"UTC": d(2)}):
        (s,) = await FreezeService().burn_due_freezes()
    assert (s.telegram_id, s.language, s.habit_name) == (u.telegram_id, "ru", "Read")
