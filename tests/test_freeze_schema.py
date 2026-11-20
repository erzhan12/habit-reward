"""Feature 0048 PR B, slice 1: freeze schema, constraints and repositories."""

from datetime import date

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction

from src.core.models import Habit, HabitFreezeEvent, HabitLog, User
from src.core.repositories import habit_freeze_event_repository, habit_repository

D = date(2026, 11, 20)


@pytest.fixture
def user():
    return User.objects.create_user(
        username="tg_4810001", telegram_id="4810001", name="F", language="en", timezone="UTC"
    )


@pytest.fixture
def habit(user):
    return Habit.objects.create(user=user, name="Walk", weight=0)


def _log(user, habit, d=D):
    return HabitLog.objects.create(
        user=user, habit=habit, streak_count=1, habit_weight=0,
        total_weight_applied=80.0, last_completed_date=d,
    )


def _violates(fn):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            fn()


# --- settings ---------------------------------------------------------------

def test_freeze_constants():
    assert settings.FREEZE_DROP_CHANCE == 10.0
    assert settings.MAX_FREEZES_PER_HABIT == 1
    assert settings.FREEZE_JOB_INTERVAL_SECONDS == 900


# --- Habit.freeze_count -----------------------------------------------------

def test_new_habit_has_no_freeze(habit):
    assert habit.freeze_count == 0


def test_freeze_count_range_constraint(habit):
    _violates(lambda: Habit.objects.filter(pk=habit.pk).update(freeze_count=2))


def test_try_grant_never_exceeds_cap(habit):
    assert habit_repository.try_grant_freeze_sync(habit.id, 1) is True
    assert habit_repository.try_grant_freeze_sync(habit.id, 1) is False
    habit.refresh_from_db()
    assert habit.freeze_count == 1


def test_try_consume_never_below_zero(habit):
    assert habit_repository.try_consume_freeze_sync(habit.id) is False
    habit_repository.try_grant_freeze_sync(habit.id, 1)
    assert habit_repository.try_consume_freeze_sync(habit.id) is True
    assert habit_repository.try_consume_freeze_sync(habit.id) is False
    habit.refresh_from_db()
    assert habit.freeze_count == 0


@pytest.mark.asyncio
async def test_async_cas_wrappers(habit):
    assert await habit_repository.try_grant_freeze(habit.id, 1) is True
    assert await habit_repository.try_consume_freeze(habit.id) is True


def test_lock_for_update_returns_habit(habit):
    with transaction.atomic():
        locked = habit_repository.lock_for_update_sync(habit.id)
    assert locked.pk == habit.pk


# --- HabitFreezeEvent constraints --------------------------------------------

def test_spent_requires_covered_date(user, habit):
    _violates(lambda: HabitFreezeEvent.objects.create(
        user=user, habit=habit, event_type="spent", covered_date=None))


def test_spent_never_references_a_log(user, habit):
    log = _log(user, habit)
    _violates(lambda: HabitFreezeEvent.objects.create(
        user=user, habit=habit, event_type="spent", covered_date=D, habit_log=log))


def test_earned_has_no_covered_date(user, habit):
    _violates(lambda: HabitFreezeEvent.objects.create(
        user=user, habit=habit, event_type="earned", covered_date=D, state="held"))


def test_one_spend_per_habit_day(user, habit):
    repo = habit_freeze_event_repository
    repo.create_spent_sync(habit, D, None)
    _violates(lambda: repo.create_spent_sync(habit, D, None))


def test_one_win_per_log(user, habit):
    log = _log(user, habit)
    repo = habit_freeze_event_repository
    e = repo.create_earned_sync(habit, log, D)
    repo.set_state_sync(e.id, "spent")
    _violates(lambda: repo.create_earned_sync(habit, log, D))


def test_at_most_one_held_per_habit(user, habit):
    repo = habit_freeze_event_repository
    repo.create_earned_sync(habit, _log(user, habit, date(2026, 11, 1)), date(2026, 11, 1))
    _violates(lambda: repo.create_earned_sync(habit, _log(user, habit, date(2026, 11, 2)), date(2026, 11, 2)))


# --- repository behaviour -------------------------------------------------------

def test_create_earned_is_held_with_provenance(user, habit):
    log = _log(user, habit)
    e = habit_freeze_event_repository.create_earned_sync(habit, log, D)
    assert (e.event_type, e.state, e.earned_on, e.habit_log_id, e.user_id) == (
        "earned", "held", D, log.id, user.id)
    assert habit_freeze_event_repository.get_held_earned_sync(habit.id).id == e.id
    assert habit_freeze_event_repository.get_earned_for_log_sync(log.id).id == e.id


def test_create_spent_links_earned_event(user, habit):
    e = habit_freeze_event_repository.create_earned_sync(habit, _log(user, habit), D)
    habit_freeze_event_repository.set_state_sync(e.id, "spent")
    s = habit_freeze_event_repository.create_spent_sync(habit, date(2026, 11, 22), e)
    assert (s.event_type, s.covered_date, s.earned_event_id, s.state, s.habit_log_id) == (
        "spent", date(2026, 11, 22), e.id, None, None)
    assert [x.id for x in habit_freeze_event_repository.get_spent_for_habit_sync(habit.id)] == [s.id]
    assert habit_freeze_event_repository.get_held_earned_sync(habit.id) is None


def test_update_covered_date_and_delete(user, habit):
    s = habit_freeze_event_repository.create_spent_sync(habit, D, None)
    habit_freeze_event_repository.update_covered_date_sync(s.id, date(2026, 11, 21))
    s.refresh_from_db()
    assert s.covered_date == date(2026, 11, 21)
    habit_freeze_event_repository.delete_sync(s.id)
    assert not HabitFreezeEvent.objects.filter(pk=s.id).exists()


@pytest.mark.asyncio
async def test_spent_dates_by_habit():
    from asgiref.sync import sync_to_async

    def _setup():
        u = User.objects.create_user(username="tg_4810009", telegram_id="4810009", name="Q",
                                     language="en", timezone="UTC")
        h1 = Habit.objects.create(user=u, name="A", weight=0)
        h2 = Habit.objects.create(user=u, name="B", weight=0)
        habit_freeze_event_repository.create_spent_sync(h1, date(2026, 11, 3), None)
        habit_freeze_event_repository.create_spent_sync(h1, date(2026, 11, 5), None)
        habit_freeze_event_repository.create_spent_sync(h2, date(2026, 11, 4), None)
        return u, h1, h2

    u, h1, h2 = await sync_to_async(_setup)()
    result = await habit_freeze_event_repository.get_spent_dates_by_habit(u.id)
    assert result == {h1.id: {date(2026, 11, 3), date(2026, 11, 5)}, h2.id: {date(2026, 11, 4)}}


# --- deletion semantics ------------------------------------------------------------

def test_log_delete_keeps_earned_event_with_null_log(user, habit):
    log = _log(user, habit)
    e = habit_freeze_event_repository.create_earned_sync(habit, log, D)
    habit_freeze_event_repository.set_state_sync(e.id, "spent")
    log.delete()
    e.refresh_from_db()
    assert e.habit_log_id is None and e.earned_on == D


def test_earned_delete_nulls_spend_link(user, habit):
    e = habit_freeze_event_repository.create_earned_sync(habit, _log(user, habit), D)
    habit_freeze_event_repository.set_state_sync(e.id, "spent")
    s = habit_freeze_event_repository.create_spent_sync(habit, date(2026, 11, 22), e)
    e.delete()
    s.refresh_from_db()
    assert s.earned_event_id is None


# --- 0033: one log per habit and day ------------------------------------------------

def test_one_log_per_habit_day(user, habit):
    _log(user, habit)
    _violates(lambda: _log(user, habit))
