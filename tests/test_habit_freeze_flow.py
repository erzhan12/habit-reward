"""Completion with streak freezes, DB-backed (feature 0048 §4).

Dates: MON = 2026-11-16. Time is fixed by patching get_user_today in habit_service.
Random draws are forced by patching the module-level ``random`` of reward_service
(prize) and freeze_service (freeze roll).
"""

import asyncio
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import OperationalError

from src.core.models import Habit, HabitFreezeEvent, HabitLog, Reward, User
from src.services import transactions
from src.services.habit_service import HabitService
from src.services.reward_service import RewardService
from src.services.streak_service import StreakService

MON = date(2026, 11, 16)


def d(n):
    return MON + timedelta(days=n)


@contextmanager
def frozen(today, freeze_roll=False, prize=False):
    """Fix today; force the freeze roll (win/lose) and the prize draw (win/lose)."""
    def _choices(population, weights=None, k=1):
        winners = [x for x in population if x is not None]
        return [winners[0] if prize and winners else None]

    with patch("src.services.habit_service.get_user_today", return_value=today), \
         patch("src.services.reward_service.random.choices", side_effect=_choices), \
         patch("src.services.freeze_service.random.random", return_value=0.0 if freeze_roll else 0.99):
        yield


def _setup(tg="4820001", allowed_skip_days=0, with_reward=False, freeze_count=0):
    user = User.objects.create_user(
        username=f"tg_{tg}", telegram_id=tg, name="F", language="en", timezone="UTC"
    )
    habit = Habit.objects.create(
        user=user, name="Walk", weight=0, allowed_skip_days=allowed_skip_days, freeze_count=freeze_count
    )
    Habit.objects.filter(pk=habit.pk).update(
        created_at=datetime.combine(d(-30), datetime.min.time(), tzinfo=dt_timezone.utc)
    )
    if with_reward:
        Reward.objects.create(user=user, name="Coffee", weight=10, pieces_required=5)
    return user, habit


def _log(user, habit, day, streak):
    return HabitLog.objects.create(
        user=user, habit=habit, streak_count=streak, habit_weight=0,
        total_weight_applied=80.0, last_completed_date=day,
    )


def _earned(user, habit, log, earned_on, state="held"):
    return HabitFreezeEvent.objects.create(
        user=user, habit=habit, habit_log=log, event_type="earned", earned_on=earned_on, state=state
    )


async def _complete(user, today, target=None, **kw):
    with frozen(today, **kw):
        return await HabitService().process_habit_completion(
            user.telegram_id, "Walk", target_date=target, user_timezone="UTC"
        )


def _state(habit):
    habit.refresh_from_db()
    events = list(HabitFreezeEvent.objects.filter(habit=habit).order_by("id").values(
        "event_type", "state", "earned_on", "covered_date", "earned_event_id", "habit_log_id"))
    return habit.freeze_count, events


# --- winning ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_prize_and_roll_wins_freeze():
    user, habit = await sync_to_async(_setup)()
    r = await _complete(user, MON, freeze_roll=True)
    count, events = await sync_to_async(_state)(habit)
    assert r.freeze_won is True and r.freeze_count == 1
    assert count == 1
    assert len(events) == 1 and events[0]["event_type"] == "earned"
    assert events[0]["state"] == "held" and events[0]["earned_on"] == MON
    assert events[0]["habit_log_id"] is not None


@pytest.mark.asyncio
async def test_prize_means_no_freeze_roll():
    user, habit = await sync_to_async(_setup)(with_reward=True)
    r = await _complete(user, MON, freeze_roll=True, prize=True)
    assert r.got_reward is True and r.freeze_won is False
    assert (await sync_to_async(_state)(habit))[0] == 0


@pytest.mark.asyncio
async def test_lost_roll_wins_nothing():
    user, habit = await sync_to_async(_setup)()
    r = await _complete(user, MON, freeze_roll=False)
    assert r.freeze_won is False
    assert (await sync_to_async(_state)(habit)) == (0, [])


@pytest.mark.asyncio
async def test_result_carries_reward_chance():
    user, habit = await sync_to_async(_setup)()
    await sync_to_async(_log)(user, habit, d(0), 3)
    r = await _complete(user, d(1))
    assert r.streak_count == 4
    assert r.reward_chance == pytest.approx(RewardService.calculate_reward_chance(4))
    assert r.total_weight_applied == pytest.approx(100 - r.reward_chance)


# --- spending ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_one_day_miss_job_already_ran():
    user, habit = await sync_to_async(_setup)()

    def _prep():
        log = _log(user, habit, d(0), 5)
        e = _earned(user, habit, log, d(0), state="spent")
        HabitFreezeEvent.objects.create(user=user, habit=habit, event_type="spent", covered_date=d(1), earned_event=e)

    await sync_to_async(_prep)()
    r = await _complete(user, d(2))
    assert (r.streak_count, r.freeze_used, r.freeze_burned, r.freeze_covered_date) == (6, True, False, d(1))
    count, events = await sync_to_async(_state)(habit)
    assert count == 0 and sum(e["event_type"] == "spent" for e in events) == 1


@pytest.mark.asyncio
async def test_one_day_miss_job_did_not_run_catch_up_spends():
    user, habit = await sync_to_async(_setup)(freeze_count=1)

    def _prep():
        log = _log(user, habit, d(0), 5)
        return _earned(user, habit, log, d(0)).id

    earned_id = await sync_to_async(_prep)()
    r = await _complete(user, d(2))
    assert (r.streak_count, r.freeze_used, r.freeze_covered_date) == (6, True, d(1))
    assert r.reward_chance == pytest.approx(RewardService.calculate_reward_chance(6))
    count, events = await sync_to_async(_state)(habit)
    assert count == 0
    spent = [e for e in events if e["event_type"] == "spent"]
    assert len(spent) == 1 and spent[0]["covered_date"] == d(1) and spent[0]["earned_event_id"] == earned_id
    assert [e["state"] for e in events if e["event_type"] == "earned"] == ["spent"]


@pytest.mark.asyncio
async def test_two_day_miss_burns_freeze_and_resets():
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(0), 5), d(0)))()
    r = await _complete(user, d(3))
    assert (r.streak_count, r.freeze_burned, r.freeze_used, r.freeze_covered_date) == (1, True, False, d(1))
    assert r.reward_chance == pytest.approx(20.0)
    assert (await sync_to_async(_state)(habit))[0] == 0


@pytest.mark.asyncio
async def test_allowance_absorbs_first_miss_freeze_covers_second():
    user, habit = await sync_to_async(_setup)(allowed_skip_days=1, freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(0), 5), d(0)))()
    r = await _complete(user, d(3))  # Tue (grace) + Wed (freeze) missed
    assert (r.streak_count, r.freeze_used, r.freeze_covered_date) == (6, True, d(2))


@pytest.mark.asyncio
async def test_catch_up_spend_and_rewin_in_same_completion():
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(0), 5), d(0)))()
    r = await _complete(user, d(2), freeze_roll=True)
    assert r.freeze_used is True and r.freeze_won is True and r.freeze_count == 1
    count, events = await sync_to_async(_state)(habit)
    assert count == 1
    assert sorted(e["state"] for e in events if e["event_type"] == "earned") == ["held", "spent"]


@pytest.mark.asyncio
async def test_admin_granted_freeze_is_spent_untracked():
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(_log)(user, habit, d(0), 5)
    r = await _complete(user, d(2))
    assert r.freeze_used is True
    count, events = await sync_to_async(_state)(habit)
    assert count == 0 and events == [{
        "event_type": "spent", "state": None, "earned_on": None, "covered_date": d(1),
        "earned_event_id": None, "habit_log_id": None}]


@pytest.mark.asyncio
async def test_backdate_cannot_spend_freeze_won_later():
    """Logs Sun, Wed (won the freeze). Backdate Tue on Thu: Mon is the guard day,
    the freeze was won on Wed >= Mon, so it is not usable and Tue resets."""
    user, habit = await sync_to_async(_setup)(freeze_count=1)

    def _prep():
        _log(user, habit, d(-1), 4)
        _earned(user, habit, _log(user, habit, d(2), 1), d(2))

    await sync_to_async(_prep)()
    r = await _complete(user, d(3), target=d(1))
    assert (r.streak_count, r.freeze_used, r.freeze_burned) == (1, False, False)
    assert (await sync_to_async(_state)(habit))[0] == 1


@pytest.mark.asyncio
async def test_backdate_spends_freeze_won_earlier():
    """Logs Sat (won freeze), then backdate Mon on Wed: Sun is the guard day -> covered."""
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(-2), 4), d(-2)))()
    r = await _complete(user, d(2), target=d(0))
    assert (r.streak_count, r.freeze_used, r.freeze_covered_date) == (5, True, d(-1))


@pytest.mark.asyncio
async def test_epoch_predecessor_rule_still_applies():
    user, habit = await sync_to_async(_setup)(freeze_count=1)

    def _prep():
        Habit.objects.filter(pk=habit.pk).update(streak_epoch=d(2))
        _log(user, habit, d(0), 9)

    await sync_to_async(_prep)()
    r = await _complete(user, d(3))
    # Pre-epoch log does not exist for the streak: no gap, no spend.
    assert (r.streak_count, r.freeze_used) == (1, False)
    assert (await sync_to_async(_state)(habit))[0] == 1


# --- transactions -------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overlapping_duplicate_completion_keeps_one_log():
    user, habit = await sync_to_async(_setup)(with_reward=True)
    with frozen(MON, prize=True):
        hs = HabitService()
        results = await asyncio.gather(
            hs.process_habit_completion(user.telegram_id, "Walk", user_timezone="UTC"),
            hs.process_habit_completion(user.telegram_id, "Walk", user_timezone="UTC"),
            return_exceptions=True,
        )
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 1 and "already completed" in str(errors[0])
    logs = await sync_to_async(lambda: list(HabitLog.objects.filter(habit=habit)))()
    assert len(logs) == 1
    pieces = await sync_to_async(
        lambda: list(user.reward_progress.values_list("pieces_earned", flat=True))
    )()
    assert pieces == [1]


@pytest.mark.asyncio
async def test_cache_invalidated_after_commit():
    user, habit = await sync_to_async(_setup)()
    key = StreakService.cache_key(user.id)
    await cache.aset(key, {"stale": True}, timeout=300)
    await _complete(user, MON)
    assert await cache.aget(key) is None


@pytest.mark.asyncio
async def test_retry_then_success_and_busy_after_exhaustion():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("database is locked")
        return "ok"

    with patch.object(transactions, "RETRY_DELAYS_SECONDS", (0, 0, 0)):
        assert await transactions.run_in_transaction(flaky) == "ok"
        assert calls["n"] == 3

        def always_locked():
            raise OperationalError("database table is locked")

        with pytest.raises(transactions.ServiceBusyError):
            await transactions.run_in_transaction(always_locked)


@pytest.mark.asyncio
async def test_non_lock_operational_error_is_not_retried():
    calls = {"n": 0}

    def broken():
        calls["n"] += 1
        raise OperationalError("no such table: x")

    with pytest.raises(OperationalError):
        await transactions.run_in_transaction(broken)
    assert calls["n"] == 1


def test_service_busy_is_not_a_value_error():
    assert not issubclass(transactions.ServiceBusyError, ValueError)


# --- review follow-ups ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_completion_audit_row_survives_undo():
    from src.core.models import BotAuditLog

    user, habit = await sync_to_async(_setup)()
    await _complete(user, MON)
    with patch("src.services.habit_service.get_user_today", return_value=MON):
        await HabitService().revert_habit_completion(user.telegram_id, habit.id)
    rows = await sync_to_async(lambda: list(
        BotAuditLog.objects.filter(user=user, event_type="habit_completed").values("habit_log_id")
    ))()
    assert len(rows) == 1 and rows[0]["habit_log_id"] is None


@pytest.mark.asyncio
async def test_failed_catch_up_spend_falls_back_to_reset():
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(0), 5), d(0)))()
    with patch("src.services.freeze_service.FreezeService.spend_sync", return_value=False):
        r = await _complete(user, d(2))
    assert (r.streak_count, r.freeze_used, r.freeze_covered_date) == (1, False, None)


@pytest.mark.asyncio
async def test_failed_catch_up_with_existing_log_is_already_completed():
    hs = HabitService()
    user, habit = await sync_to_async(_setup)(freeze_count=1)
    await sync_to_async(lambda: _earned(user, habit, _log(user, habit, d(0), 5), d(0)))()

    def _commit_after_concurrent_insert():
        # Another submit of the same completion committed its log first.
        _log(user, habit, d(2), 6)
        return hs._commit_completion_sync(user, habit.id, d(2), d(2))

    with frozen(d(2)), \
         patch("src.services.freeze_service.FreezeService.spend_sync", return_value=False):
        with pytest.raises(ValueError, match="already completed"):
            await transactions.run_in_transaction(_commit_after_concurrent_insert)


@pytest.mark.asyncio
async def test_unrelated_integrity_error_is_not_relabelled():
    from django.db import IntegrityError

    user, habit = await sync_to_async(_setup)()
    with patch("src.services.habit_service.run_in_transaction",
               side_effect=IntegrityError("FOREIGN KEY constraint failed")):
        with pytest.raises(IntegrityError):
            await _complete(user, MON)


@pytest.mark.django_db(transaction=True)
def test_two_threads_same_completion_separate_connections():
    """Two completions of one habit/day on separate DB connections overlap inside
    their transactions: exactly one log survives, the other attempt fails cleanly
    (duplicate) after lock retries, and no partial progress is left behind."""
    import threading

    from django.db import IntegrityError, connection

    user, habit = _setup(tg="4820099", with_reward=True)
    hs = HabitService()
    barrier = threading.Barrier(2, timeout=5)
    first_call = threading.local()
    real_select = RewardService.select_reward_sync
    outcomes, lock_messages = [], []

    def select_then_wait(self, *args, **kwargs):
        selected = real_select(self, *args, **kwargs)
        if not getattr(first_call, "done", False):
            first_call.done = True
            barrier.wait()  # both transactions have read, neither has written
        return selected

    def worker():
        try:
            transactions.run_in_transaction_sync(hs._commit_completion_sync, user, habit.id, MON, MON)
            outcomes.append("ok")
        except (IntegrityError, ValueError) as exc:
            outcomes.append(f"dup:{type(exc).__name__}")
        except transactions.ServiceBusyError as exc:
            lock_messages.append(str(exc.__cause__))
            outcomes.append("busy")
        finally:
            connection.close()

    real_is_lock = transactions.is_lock_error

    def record_lock(exc):
        if real_is_lock(exc):
            lock_messages.append(str(exc))
        return real_is_lock(exc)

    with frozen(MON, prize=True), \
         patch.object(RewardService, "select_reward_sync", select_then_wait), \
         patch.object(transactions, "is_lock_error", side_effect=record_lock), \
         patch.object(transactions, "RETRY_DELAYS_SECONDS", (0.05, 0.1, 0.2)):
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)

    assert sorted(outcomes)[-1] == "ok" and outcomes.count("ok") == 1, (outcomes, lock_messages)
    assert HabitLog.objects.filter(habit=habit).count() == 1
    assert list(user.reward_progress.values_list("pieces_earned", flat=True)) == [1]
    print("lock messages observed:", sorted(set(lock_messages)))
