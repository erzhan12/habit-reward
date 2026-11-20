"""Freeze reconciliation after backdate, undo and settings edits (feature 0048 §5, §6).

MON = 2026-11-16 (Monday). d(n) = MON + n days. Every scenario that could depend on
whether the burn job ran is checked under both schedules ("job" / "nojob").
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async

from src.core.models import Habit, HabitFreezeEvent, HabitLog, User
from src.services.freeze_service import FreezeService
from src.services.habit_service import HabitService
from src.services.transactions import run_in_transaction_sync

MON = date(2026, 11, 16)


def d(n):
    return MON + timedelta(days=n)


@contextmanager
def frozen(today, freeze_roll=False):
    with patch("src.services.habit_service.get_user_today", return_value=today), \
         patch("src.services.reward_service.random.choices", side_effect=lambda p, weights=None, k=1: [None]), \
         patch("src.services.freeze_service.random.random", return_value=0.0 if freeze_roll else 0.99):
        yield


_tg = iter(range(4840001, 4849999))


def _setup(allowed_skip_days=0, exempt=None):
    tg = str(next(_tg))
    user = User.objects.create_user(username=f"tg_{tg}", telegram_id=tg, name="R", language="en", timezone="UTC")
    habit = Habit.objects.create(
        user=user, name="Walk", weight=0, allowed_skip_days=allowed_skip_days, exempt_weekdays=exempt or []
    )
    Habit.objects.filter(pk=habit.pk).update(
        created_at=datetime.combine(d(-30), datetime.min.time(), tzinfo=dt_timezone.utc)
    )
    return user, habit


def _log(user, habit, day, streak=1):
    return HabitLog.objects.create(
        user=user, habit=habit, streak_count=streak, habit_weight=0,
        total_weight_applied=80.0, last_completed_date=day,
    )


def _win(user, habit, log):
    """Freeze won by ``log`` and now held."""
    Habit.objects.filter(pk=habit.pk).update(freeze_count=1)
    return HabitFreezeEvent.objects.create(
        user=user, habit=habit, habit_log=log, event_type="earned",
        earned_on=log.last_completed_date, state="held",
    )


def _job(habit, today):
    """What the burn job does for one habit (spend for the trailing guard day)."""
    def _fn():
        from src.core.repositories import habit_repository
        h = habit_repository.lock_for_update_sync(habit.id)
        return FreezeService().settle_due_spend_sync(h, today)
    return run_in_transaction_sync(_fn)


def snapshot(habit):
    habit.refresh_from_db()
    logs = dict(HabitLog.objects.filter(habit=habit).values_list("last_completed_date", "streak_count"))
    events = sorted(
        (e.event_type, e.state, e.earned_on, e.covered_date,
         e.earned_event.earned_on if e.earned_event_id else None)
        for e in HabitFreezeEvent.objects.filter(habit=habit).select_related("earned_event")
    )
    return {"count": habit.freeze_count, "logs": logs, "events": events}


async def complete(user, today, target=None, roll=False):
    with frozen(today, freeze_roll=roll):
        return await HabitService().process_habit_completion(
            user.telegram_id, "Walk", target_date=target, user_timezone="UTC")


async def undo_log(user, log_id, today):
    with frozen(today):
        return await HabitService().revert_habit_completion_by_log_id(user.id, log_id)


async def edit(habit, today, **updates):
    with frozen(today):
        return await HabitService().update_habit(habit.id, updates, user_timezone="UTC")


S = sync_to_async


# --- §5 backdate ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backdate_onto_covered_day_returns_freeze():
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 5)))()
    await complete(user, d(2))                      # Wed: catch-up spends for Tue, streak 6
    r = await complete(user, d(3), target=d(1))     # Thu: backdate Tue
    snap = await S(snapshot)(habit)
    assert r.freeze_returned is True
    assert snap["count"] == 1
    assert snap["events"] == [("earned", "held", d(0), None, None)]
    assert snap["logs"] == {d(0): 5, d(1): 6, d(2): 7}


@pytest.mark.asyncio
async def test_backdate_splitting_gap_moves_spend_to_new_guard_day():
    # A=1: Mon, miss Tue Wed Thu, Fri. Guard day Wed (spent). Backdate Tue -> gap Tue..Fri, guard Thu.
    user, habit = await S(_setup)(allowed_skip_days=1)

    def _prep():
        e = _win(user, habit, _log(user, habit, d(0), 5))
        HabitFreezeEvent.objects.filter(pk=e.pk).update(state="spent")
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(2), earned_event=e)
        _log(user, habit, d(4), 1)

    await S(_prep)()
    await complete(user, d(5), target=d(1))
    snap = await S(snapshot)(habit)
    spent = [e for e in snap["events"] if e[0] == "spent"]
    assert spent == [("spent", None, None, d(3), d(0))]
    assert snap["logs"] == {d(0): 5, d(1): 6, d(4): 7}
    assert snap["count"] == 0


@pytest.mark.asyncio
async def test_backdate_shrinking_gap_within_allowance_returns_freeze():
    # A=1: Mon, miss Tue Wed, Thu. Guard Wed spent. Backdate Tue -> gap Tue..Thu misses only Wed (<= A).
    user, habit = await S(_setup)(allowed_skip_days=1)

    def _prep():
        e = _win(user, habit, _log(user, habit, d(0), 5))
        HabitFreezeEvent.objects.filter(pk=e.pk).update(state="spent")
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(2), earned_event=e)
        _log(user, habit, d(3), 6)

    await S(_prep)()
    r = await complete(user, d(4), target=d(1))
    snap = await S(snapshot)(habit)
    assert r.freeze_returned is True and snap["count"] == 1
    assert snap["events"] == [("earned", "held", d(0), None, None)]
    assert snap["logs"] == {d(0): 5, d(1): 6, d(3): 7}


@pytest.mark.asyncio
async def test_return_while_holding_another_freeze_forfeits_it():
    user, habit = await S(_setup)()

    def _prep():
        e1 = _win(user, habit, _log(user, habit, d(0), 5))
        HabitFreezeEvent.objects.filter(pk=e1.pk).update(state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(1), earned_event=e1)
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        _win(user, habit, _log(user, habit, d(2), 6))   # F2 held

    await S(_prep)()
    r = await complete(user, d(3), target=d(1))
    snap = await S(snapshot)(habit)
    assert r.freeze_returned is False
    assert snap["count"] == 1
    assert snap["events"] == [("earned", "forfeited", d(0), None, None), ("earned", "held", d(2), None, None)]


@pytest.mark.parametrize("schedule", ["job", "nojob"])
@pytest.mark.asyncio
async def test_settle_first_backdate_independent_of_job(schedule):
    """Earn F1 Mon, spend Tue, win F2 Wed, miss Thu, backdate Tue on Fri:
    F2 is spent for Thu first, then Tue's backdate returns F1 into the empty inventory."""
    user, habit = await S(_setup)()

    def _prep():
        e1 = _win(user, habit, _log(user, habit, d(0), 5))
        HabitFreezeEvent.objects.filter(pk=e1.pk).update(state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(1), earned_event=e1)
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        _win(user, habit, _log(user, habit, d(2), 6))

    await S(_prep)()
    if schedule == "job":
        await S(_job)(habit, d(4))
    await complete(user, d(4), target=d(1))
    snap = await S(snapshot)(habit)
    assert snap["count"] == 1
    assert snap["events"] == [
        ("earned", "held", d(0), None, None),
        ("earned", "spent", d(2), None, None),
        ("spent", None, None, d(3), d(2)),
    ]


@pytest.mark.asyncio
async def test_backdate_onto_covered_day_from_job_spend():
    """The job spent the freeze for Tue; nobody completed since. Backdating Tue returns it."""
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 5)))()
    await S(_job)(habit, d(2))
    r = await complete(user, d(2), target=d(1))
    snap = await S(snapshot)(habit)
    assert r.freeze_returned is True and snap["count"] == 1
    assert snap["logs"] == {d(0): 5, d(1): 6}


# --- §6 undo ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_undo_of_win_revokes_held_freeze():
    user, habit = await S(_setup)()
    await complete(user, MON, roll=True)
    log_id = await S(lambda: HabitLog.objects.get(habit=habit).id)()
    r = await undo_log(user, log_id, MON)
    snap = await S(snapshot)(habit)
    assert r.freeze_revoked is True
    assert snap == {"count": 0, "logs": {}, "events": []}


@pytest.mark.asyncio
async def test_undo_of_win_already_spent_keeps_event_with_null_log():
    user, habit = await S(_setup)()

    def _prep():
        mon = _log(user, habit, d(0), 5)
        _win(user, habit, mon)
        return mon.id

    mon_id = await S(_prep)()
    await complete(user, d(2))                 # spends F for Tue, Wed streak 6
    r = await undo_log(user, mon_id, d(2))
    snap = await S(snapshot)(habit)
    assert r.freeze_revoked is False
    assert snap["count"] == 0
    assert ("earned", "spent", d(0), None, None) in snap["events"]
    left = await S(lambda: HabitFreezeEvent.objects.get(habit=habit, event_type="earned").habit_log_id)()
    assert left is None


@pytest.mark.asyncio
async def test_undo_of_completion_after_frozen_day_keeps_spend():
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 5)))()
    await complete(user, d(2))
    wed = await S(lambda: HabitLog.objects.get(habit=habit, last_completed_date=d(2)).id)()
    await undo_log(user, wed, d(2))
    snap = await S(snapshot)(habit)
    assert snap["count"] == 0
    assert ("spent", None, None, d(1), d(0)) in snap["events"]


@pytest.mark.asyncio
async def test_undo_merging_gaps_returns_ineligible_spend():
    """Mon, miss Tue, win F on Wed, F spent for Thu, Fri; undo Wed -> merged gap Mon..Fri has
    guard Tue, F (won Wed) cannot cover Tue: returned, Fri resets."""
    user, habit = await S(_setup)()

    def _prep():
        _log(user, habit, d(0), 5)
        wed = _log(user, habit, d(2), 1)
        e = _win(user, habit, wed)
        HabitFreezeEvent.objects.filter(pk=e.pk).update(state="spent")
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(3), earned_event=e)
        _log(user, habit, d(4), 2)
        return wed.id

    wed_id = await S(_prep)()
    await undo_log(user, wed_id, d(4))
    snap = await S(snapshot)(habit)
    assert snap["logs"] == {d(0): 5, d(4): 1}
    assert not any(e[0] == "spent" for e in snap["events"])
    assert snap["events"] == [("earned", "held", d(2), None, None)]
    assert snap["count"] == 1


@pytest.mark.asyncio
async def test_undo_merging_two_spends_keeps_one_on_guard_day():
    """Earn Mon, spend Tue, re-win Wed, spend Thu, Fri; undo Wed, then backdate the Sunday before:
    exactly one SPENT (Tue), Thu's returned, no IntegrityError."""
    user, habit = await S(_setup)()

    def _prep():
        mon = _log(user, habit, d(0), 5)
        e1 = _win(user, habit, mon)
        HabitFreezeEvent.objects.filter(pk=e1.pk).update(state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(1), earned_event=e1)
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        wed = _log(user, habit, d(2), 6)
        e2 = _win(user, habit, wed)
        HabitFreezeEvent.objects.filter(pk=e2.pk).update(state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(3), earned_event=e2)
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        _log(user, habit, d(4), 7)
        return wed.id

    wed_id = await S(_prep)()
    await undo_log(user, wed_id, d(4))
    await complete(user, d(4), target=d(-1))
    snap = await S(snapshot)(habit)
    spent = [e for e in snap["events"] if e[0] == "spent"]
    assert spent == [("spent", None, None, d(1), d(0))]
    assert snap["count"] == 1


@pytest.mark.parametrize("schedule", ["job", "nojob"])
@pytest.mark.asyncio
async def test_undo_settles_first(schedule):
    """Earn Mon, miss Tue, undo Mon on Wed: the Tue spend happens first either way,
    so the Monday freeze is spent (not revoked)."""
    user, habit = await S(_setup)()

    def _prep():
        mon = _log(user, habit, d(0), 5)
        _win(user, habit, mon)
        return mon.id

    mon_id = await S(_prep)()
    if schedule == "job":
        await S(_job)(habit, d(2))
    r = await undo_log(user, mon_id, d(2))
    snap = await S(snapshot)(habit)
    assert r.freeze_revoked is False
    assert snap == {
        "count": 0,
        "logs": {},
        "events": [("earned", "spent", d(0), None, None), ("spent", None, None, d(1), d(0))],
    }


@pytest.mark.asyncio
async def test_undo_never_revokes_a_freeze_from_another_win():
    """F1 returned by a backdate is held; undoing F2's earning log (F2 spent) leaves F1 alone."""
    user, habit = await S(_setup)()

    def _prep():
        mon = _log(user, habit, d(0), 5)
        e1 = _win(user, habit, mon)
        HabitFreezeEvent.objects.filter(pk=e1.pk).update(state="held")
        wed = _log(user, habit, d(2), 1)
        e2 = HabitFreezeEvent.objects.create(user=user, habit=habit, habit_log=wed, event_type="earned",
                                             earned_on=d(2), state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(3), earned_event=e2)
        _log(user, habit, d(4), 2)
        return wed.id

    wed_id = await S(_prep)()
    r = await undo_log(user, wed_id, d(4))
    snap = await S(snapshot)(habit)
    assert r.freeze_revoked is False
    assert snap["count"] == 1
    assert ("earned", "held", d(0), None, None) in snap["events"]


@pytest.mark.asyncio
async def test_double_undo_raises_without_double_effects():
    user, habit = await S(_setup)()
    await complete(user, MON, roll=True)
    log_id = await S(lambda: HabitLog.objects.get(habit=habit).id)()
    await undo_log(user, log_id, MON)
    with pytest.raises(ValueError):
        await undo_log(user, log_id, MON)
    assert (await S(snapshot)(habit))["count"] == 0


# --- settings edits --------------------------------------------------------------------------

@pytest.mark.parametrize("schedule", ["job", "nojob"])
@pytest.mark.asyncio
async def test_raising_allowance_returns_spend(schedule):
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 1)))()
    if schedule == "job":
        await S(_job)(habit, d(2))
    await edit(habit, d(2), allowed_skip_days=1)
    snap = await S(snapshot)(habit)
    assert snap["count"] == 1 and snap["events"] == [("earned", "held", d(0), None, None)]
    r = await complete(user, d(2))
    assert (r.streak_count, r.freeze_used) == (2, False)


@pytest.mark.parametrize("schedule", ["job", "nojob"])
@pytest.mark.asyncio
async def test_exempting_covered_weekday_moves_spend(schedule):
    """A=0, Mon earn, miss Tue+Wed, Tue spent; on Thu exempt Tuesdays -> spend moves to Wed."""
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 1)))()
    if schedule == "job":
        await S(_job)(habit, d(3))
    await edit(habit, d(3), exempt_weekdays=[2])
    r = await complete(user, d(3))
    snap = await S(snapshot)(habit)
    assert [e for e in snap["events"] if e[0] == "spent"] == [("spent", None, None, d(2), d(0))]
    assert r.streak_count == 2


@pytest.mark.parametrize("schedule", ["job", "nojob"])
@pytest.mark.asyncio
async def test_settings_edit_settles_under_old_settings(schedule):
    """A=0: earn F1 Mon, spend Tue, earn F2 Wed, miss Thu, raise A to 1 on Fri -> same result
    either way: F1 held, F2 forfeited."""
    user, habit = await S(_setup)()

    def _prep():
        e1 = _win(user, habit, _log(user, habit, d(0), 5))
        HabitFreezeEvent.objects.filter(pk=e1.pk).update(state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(1), earned_event=e1)
        Habit.objects.filter(pk=habit.pk).update(freeze_count=0)
        _win(user, habit, _log(user, habit, d(2), 6))

    await S(_prep)()
    if schedule == "job":
        await S(_job)(habit, d(4))
    await edit(habit, d(4), allowed_skip_days=1)
    snap = await S(snapshot)(habit)
    assert snap["count"] == 1
    assert snap["events"] == [("earned", "forfeited", d(2), None, None), ("earned", "held", d(0), None, None)]


@pytest.mark.asyncio
async def test_non_streak_edit_does_not_touch_freezes():
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 5)))()
    await edit(habit, d(2), name="Walk")
    snap = await S(snapshot)(habit)
    assert snap["count"] == 1 and not any(e[0] == "spent" for e in snap["events"])


# --- admin revert uses the shared undo transaction ---------------------------------------------

def test_admin_revert_revokes_held_freeze():
    from django.contrib.admin.sites import AdminSite
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.test import RequestFactory

    from src.core.admin import HabitLogAdmin

    user, habit = _setup()
    log = _log(user, habit, d(0), 1)
    _win(user, habit, log)

    request = RequestFactory().get("/admin/core/habitlog/")
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)

    with patch("src.core.admin.get_user_today", return_value=d(0)):
        HabitLogAdmin(HabitLog, AdminSite()).revert_selected_logs(request, HabitLog.objects.filter(pk=log.pk))

    assert snapshot(habit) == {"count": 0, "logs": {}, "events": []}


@pytest.mark.asyncio
async def test_bot_shaped_edit_with_unchanged_settings_touches_nothing():
    """The bot always sends allowed_skip_days and exempt_weekdays; unchanged values must not
    settle or reconcile (a due spend stays for the job, streaks stay as stored)."""
    user, habit = await S(_setup)()
    await S(lambda: _win(user, habit, _log(user, habit, d(0), 5)))()
    await edit(habit, d(2), name="Walk", weight=3, allowed_skip_days=0, exempt_weekdays=[])
    snap = await S(snapshot)(habit)
    assert snap["count"] == 1 and not any(e[0] == "spent" for e in snap["events"])
    assert snap["logs"] == {d(0): 5}
    habit_weight = await S(lambda: Habit.objects.get(pk=habit.pk).weight)()
    assert habit_weight == 3
