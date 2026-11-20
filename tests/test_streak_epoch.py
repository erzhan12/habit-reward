"""Launch streak reset via Habit.streak_epoch (feature 0048, PR A).

Logs dated before the epoch never count as a predecessor; a log dated exactly on
the epoch has effective streak 1 whatever its stored streak_count. No HabitLog row
is rewritten, so historical "longest streak" stats survive.
"""

import importlib
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.apps import apps as django_apps
from django.db.models import Max

from src.core.models import Habit, HabitLog, User
from src.services.habit_service import HabitService
from src.services.streak_service import StreakService

EPOCH = date(2026, 11, 20)  # a Friday

migration_0031 = importlib.import_module("src.core.migrations.0031_habit_streak_epoch")


def _make_user(tg="4800001", tz="UTC"):
    return User.objects.create_user(
        username=f"tg_{tg}", telegram_id=tg, name="Epoch", language="en", timezone=tz
    )


def _make_habit(user, epoch=EPOCH, name="Walk", **kw):
    return Habit.objects.create(user=user, name=name, weight=10, streak_epoch=epoch, **kw)


def _log(user, habit, d, streak):
    return HabitLog.objects.create(
        user=user, habit=habit, got_reward=False, streak_count=streak,
        habit_weight=habit.weight, total_weight_applied=50.0, last_completed_date=d,
    )


def _history(user, habit, end, days):
    """`days` consecutive logs ending on `end`, streak 1..days."""
    for i in range(days):
        _log(user, habit, end - timedelta(days=days - 1 - i), i + 1)


@pytest.fixture
def svc():
    return StreakService()


def _today(d):
    return patch("src.services.streak_service.get_user_today", return_value=d)


@pytest.mark.asyncio
async def test_history_before_epoch_does_not_count(svc):
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user)
    await sync_to_async(_history)(user, habit, EPOCH - timedelta(days=1), 12)

    with _today(EPOCH):
        assert await svc.calculate_streak(user.id, habit.id) == 1
        assert await svc.get_current_streak(user.id, habit.id) == 0
        assert await svc.calculate_streak_for_date(user.id, habit.id, EPOCH) == 1
        streak_map = await svc.get_validated_streak_map(user.id, [habit])
    assert streak_map[habit.id] == 0


@pytest.mark.asyncio
async def test_epoch_day_log_is_day_one_and_keeps_stored_value(svc):
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user)
    await sync_to_async(_history)(user, habit, EPOCH, 30)  # record 30 reached on deploy day

    with _today(EPOCH):
        assert await svc.get_current_streak(user.id, habit.id) == 1
        streak_map = await svc.get_validated_streak_map(user.id, [habit])
        assert streak_map[habit.id] == 1
    with _today(EPOCH + timedelta(days=1)):
        assert await svc.calculate_streak(user.id, habit.id) == 2
        assert await svc.get_current_streak(user.id, habit.id) == 1
    assert await svc.calculate_streak_for_date(user.id, habit.id, EPOCH + timedelta(days=1)) == 2

    stored = await sync_to_async(
        lambda: HabitLog.objects.get(habit=habit, last_completed_date=EPOCH).streak_count
    )()
    assert stored == 30
    longest = await sync_to_async(
        lambda: HabitLog.objects.filter(habit=habit).aggregate(m=Max("streak_count"))["m"]
    )()
    assert longest == 30


@pytest.mark.asyncio
async def test_no_epoch_counts_full_history(svc):
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user, epoch=None)
    await sync_to_async(_history)(user, habit, EPOCH - timedelta(days=1), 12)

    with _today(EPOCH):
        assert await svc.calculate_streak(user.id, habit.id) == 13
        assert await svc.get_current_streak(user.id, habit.id) == 12


@pytest.mark.asyncio
async def test_backdate_before_epoch_gets_one_and_leaves_later_streaks(svc):
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user)
    # Pre-epoch history with a hole on EPOCH-3, then epoch-day (stored 9) and two days after.
    await sync_to_async(_history)(user, habit, EPOCH - timedelta(days=4), 5)
    await sync_to_async(_log)(user, habit, EPOCH - timedelta(days=2), 1)
    await sync_to_async(_log)(user, habit, EPOCH - timedelta(days=1), 2)
    await sync_to_async(_log)(user, habit, EPOCH, 9)
    await sync_to_async(_log)(user, habit, EPOCH + timedelta(days=1), 2)
    await sync_to_async(_log)(user, habit, EPOCH + timedelta(days=2), 3)

    hole = EPOCH - timedelta(days=3)
    assert await svc.calculate_streak_for_date(user.id, habit.id, hole) == 1

    await sync_to_async(_log)(user, habit, hole, 1)
    hs = HabitService()
    with patch("src.services.habit_service.get_user_today", return_value=EPOCH + timedelta(days=2)):
        await hs.recalculate_streaks_after_backdate(user.id, habit.id, hole)

    rows = await sync_to_async(
        lambda: dict(HabitLog.objects.filter(habit=habit).values_list("last_completed_date", "streak_count"))
    )()
    # Pre-epoch rows are never rewritten (historical stats), nor is the epoch-day row.
    assert rows[EPOCH - timedelta(days=2)] == 1
    assert rows[EPOCH - timedelta(days=1)] == 2
    assert rows[EPOCH] == 9
    assert rows[EPOCH + timedelta(days=1)] == 2
    assert rows[EPOCH + timedelta(days=2)] == 3


@pytest.mark.asyncio
async def test_recalc_from_epoch_day_uses_effective_streak(svc):
    """Backdating onto the day after the epoch recomputes successors from effective 1."""
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user)
    await sync_to_async(_log)(user, habit, EPOCH, 9)
    await sync_to_async(_log)(user, habit, EPOCH + timedelta(days=2), 1)

    d1 = EPOCH + timedelta(days=1)
    assert await svc.calculate_streak_for_date(user.id, habit.id, d1) == 2
    await sync_to_async(_log)(user, habit, d1, 2)
    hs = HabitService()
    with patch("src.services.habit_service.get_user_today", return_value=EPOCH + timedelta(days=2)):
        await hs.recalculate_streaks_after_backdate(user.id, habit.id, d1)

    rows = await sync_to_async(
        lambda: dict(HabitLog.objects.filter(habit=habit).values_list("last_completed_date", "streak_count"))
    )()
    assert rows[EPOCH] == 9
    assert rows[d1] == 2
    assert rows[EPOCH + timedelta(days=2)] == 3


def test_migration_sets_epoch_per_user_local_date():
    """At 20:00 UTC on 20 Nov it is already 21 Nov in Asia/Almaty (UTC+5)."""
    almaty = _make_user(tg="4800002", tz="Asia/Almaty")
    utc = _make_user(tg="4800003", tz="UTC")
    blank = _make_user(tg="4800004", tz="")
    h_almaty = _make_habit(almaty, epoch=None)
    h_utc = _make_habit(utc, epoch=None)
    h_blank = _make_habit(blank, epoch=None)
    _log(almaty, h_almaty, date(2026, 11, 20), 7)

    now = datetime(2026, 11, 20, 20, 0, tzinfo=dt_timezone.utc)
    with patch.object(migration_0031.timezone, "now", return_value=now):
        migration_0031.set_streak_epoch(django_apps, None)

    for h in (h_almaty, h_utc, h_blank):
        h.refresh_from_db()
    assert h_almaty.streak_epoch == date(2026, 11, 21)
    assert h_utc.streak_epoch == date(2026, 11, 20)
    assert h_blank.streak_epoch == date(2026, 11, 20)
    assert HabitLog.objects.get(habit=h_almaty).streak_count == 7

    migration_0031.clear_streak_epoch(django_apps, None)
    h_utc.refresh_from_db()
    assert h_utc.streak_epoch is None


@pytest.mark.asyncio
async def test_grace_gap_after_epoch_day_uses_effective_streak(svc):
    """Grace-day branch: epoch-day log (stored 30), one skipped day allowed → next is 2."""
    user = await sync_to_async(_make_user)()
    habit = await sync_to_async(_make_habit)(user, allowed_skip_days=1)
    await sync_to_async(_log)(user, habit, EPOCH, 30)

    d = EPOCH + timedelta(days=2)
    with _today(d):
        assert await svc.calculate_streak(user.id, habit.id) == 2
    assert await svc.calculate_streak_for_date(user.id, habit.id, d) == 2

    await sync_to_async(_log)(user, habit, d, 99)
    hs = HabitService()
    with patch("src.services.habit_service.get_user_today", return_value=d):
        await hs.recalculate_streaks_after_backdate(user.id, habit.id, EPOCH)
    stored = await sync_to_async(
        lambda: HabitLog.objects.get(habit=habit, last_completed_date=d).streak_count
    )()
    assert stored == 2
