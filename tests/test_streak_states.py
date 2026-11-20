"""Read-path streak states with freezes (feature 0048 §3 prediction, §7 display).

Pure ``trailing_streak_state`` cases, then a DB-backed matrix that checks the
read path agrees with the writers: the state is the same before and after the
burn job, and a completion today writes exactly the predicted ``next_streak`` at
the displayed chance. Dates: MON = 2026-11-16.
"""

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.core.cache import cache

from src.core.models import Habit, HabitFreezeEvent, HabitLog, User
from src.services.freeze_service import FreezeService
from src.services.habit_service import HabitService
from src.services.reward_service import RewardService
from src.services.streak_service import StreakService, StreakState, trailing_streak_state

MON = date(2026, 11, 16)


def d(n):
    return MON + timedelta(days=n)


def state(last, streak, today, A=0, exempt=(), spent=(), count=0, held_on=None):
    return trailing_streak_state(last, streak, today, A, list(exempt), set(spent), count, held_on)


# --- Pure ------------------------------------------------------------------------


class TestTrailingStreakState:
    def test_no_counted_log(self):
        assert state(None, 0, d(2), count=1) == StreakState(0, 1, 1, None, False)

    def test_completed_today(self):
        assert state(d(2), 4, d(2), count=1) == StreakState(4, 5, 1, None, False)

    def test_continue_yesterday_at_risk_with_freeze(self):
        assert state(d(1), 4, d(2), count=1) == StreakState(4, 5, 1, None, True)

    def test_not_at_risk_without_freeze(self):
        assert state(d(1), 4, d(2)).freeze_at_risk is False

    def test_not_at_risk_when_today_exempt(self):
        # Fri log, today Sat exempt: skipping Saturday is free.
        assert state(d(-3), 4, d(-2), exempt=[6, 7], count=1).freeze_at_risk is False

    def test_not_at_risk_when_allowance_left(self):
        # A=1, log yesterday: 0 missed < A, skipping today is still free.
        assert state(d(1), 4, d(2), A=1, count=1).freeze_at_risk is False

    def test_at_risk_with_allowance_used(self):
        # A=1, Mon log, Tue missed, today Wed: skipping Wed would need the freeze.
        assert state(d(0), 4, d(2), A=1, count=1).freeze_at_risk is True

    def test_not_at_risk_when_freeze_won_today(self):
        # A freeze won on the would-be guard day cannot cover it.
        assert state(d(1), 4, d(2), count=1, held_on=d(2)).freeze_at_risk is False

    def test_saved_predicted_spend(self):
        assert state(d(0), 4, d(2), count=1, held_on=d(0)) == StreakState(4, 5, 0, d(1), False)

    def test_saved_already_spent(self):
        assert state(d(0), 4, d(2), spent=[d(1)]) == StreakState(4, 5, 0, d(1), False)

    def test_burned_predicted_spend_drops_count(self):
        assert state(d(0), 4, d(3), count=1) == StreakState(0, 1, 0, None, False)

    def test_burned_already_spent(self):
        assert state(d(0), 4, d(3), spent=[d(1)]) == StreakState(0, 1, 0, None, False)

    def test_reset_without_freeze(self):
        assert state(d(0), 4, d(2)) == StreakState(0, 1, 0, None, False)

    def test_freeze_won_on_guard_day_not_usable(self):
        assert state(d(0), 4, d(2), count=1, held_on=d(1)) == StreakState(0, 1, 1, None, False)

    def test_cache_round_trip(self):
        s = StreakState(4, 5, 0, d(1), False)
        assert StreakState.from_cache(s.to_cache()) == s
        assert s.to_cache()["freeze_used_for"] == "2026-11-17"


# --- DB-backed -------------------------------------------------------------------

_tg = iter(range(4870001, 4879999))


def _setup(A=0, exempt=None, freeze_count=0, epoch=None):
    tg = str(next(_tg))
    user = User.objects.create_user(username=f"tg_{tg}", telegram_id=tg, name="S", language="en", timezone="UTC")
    habit = Habit.objects.create(
        user=user, name="Walk", weight=0, allowed_skip_days=A, exempt_weekdays=exempt or [],
        freeze_count=freeze_count, streak_epoch=epoch,
    )
    Habit.objects.filter(pk=habit.pk).update(
        created_at=datetime.combine(d(-30), datetime.min.time(), tzinfo=dt_timezone.utc)
    )
    return user, habit


def _log(user, habit, day, streak):
    return HabitLog.objects.create(user=user, habit=habit, streak_count=streak, habit_weight=0,
                                   total_weight_applied=80.0, last_completed_date=day)


def _earned(user, habit, log, earned_on):
    HabitFreezeEvent.objects.create(user=user, habit=habit, habit_log=log, event_type="earned",
                                    earned_on=earned_on, state="held")


@contextmanager
def _today(today):
    with patch("src.services.streak_service.get_user_today", return_value=today), \
         patch("src.services.freeze_service.get_user_today", return_value=today), \
         patch("src.services.habit_service.get_user_today", return_value=today), \
         patch("src.services.reward_service.random.choices", return_value=[None]), \
         patch("src.services.freeze_service.random.random", return_value=0.99):
        yield


async def _states(user, habit):
    await cache.adelete(StreakService.cache_key(user.id))
    fresh = await sync_to_async(Habit.objects.get)(pk=habit.pk)
    return (await StreakService().get_streak_states(user.id, [fresh], "UTC"))[habit.id]


# Each case: (setup kwargs, logs [(day, streak)], earned_on for a held freeze or None, today,
#             expected state before the job)
CASES = {
    "continue": (dict(), [(d(0), 3)], None, d(1), StreakState(3, 4, 0, None, False)),
    "at_risk": (dict(freeze_count=1), [(d(0), 3)], d(0), d(1), StreakState(3, 4, 1, None, True)),
    "saved": (dict(freeze_count=1), [(d(0), 3)], d(0), d(2), StreakState(3, 4, 0, d(1), False)),
    "burned": (dict(freeze_count=1), [(d(0), 3)], d(0), d(3), StreakState(0, 1, 0, None, False)),
    "reset": (dict(), [(d(0), 3)], None, d(2), StreakState(0, 1, 0, None, False)),
    "allowance": (dict(A=1, freeze_count=1), [(d(0), 3)], d(0), d(3), StreakState(3, 4, 0, d(2), False)),
    # Fri log, Sat/Sun exempt, Mon missed, today Tue.
    "exempt": (dict(exempt=[6, 7], freeze_count=1), [(d(-3), 3)], d(-3), d(1), StreakState(3, 4, 0, d(0), False)),
    # Freeze won on the guard day (backdated win) cannot cover it.
    "won_on_guard": (dict(freeze_count=1), [(d(0), 3)], d(1), d(2), StreakState(0, 1, 1, None, False)),
    # Epoch day log counts as streak 1 whatever was stored.
    "epoch_day": (dict(epoch=d(0), freeze_count=1), [(d(0), 9)], d(0), d(2), StreakState(1, 2, 0, d(1), False)),
    # Only pre-epoch history: nothing to show, freeze untouched.
    "pre_epoch": (dict(epoch=d(1), freeze_count=1), [(d(0), 9)], None, d(3), StreakState(0, 1, 1, None, False)),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("job_first", [True, False], ids=["job_then_complete", "catch_up"])
@pytest.mark.parametrize("name", list(CASES))
async def test_prediction_matches_job_and_completion(name, job_first):
    kwargs, logs, earned_on, today, expected = CASES[name]

    def _prep():
        user, habit = _setup(**kwargs)
        made = [_log(user, habit, day, streak) for day, streak in logs]
        if earned_on is not None:
            _earned(user, habit, made[-1], earned_on)
        return user, habit

    user, habit = await sync_to_async(_prep)()

    with _today(today):
        before = await _states(user, habit)
        assert before == expected

        if job_first:
            await FreezeService().burn_due_freezes()
            after = await _states(user, habit)
            assert after == before, "read path must predict exactly what the job does"

        result = await HabitService().process_habit_completion(
            user.telegram_id, "Walk", user_timezone="UTC"
        )

    assert result.streak_count == before.next_streak
    # The completion (with or without the job) leaves the predicted inventory, unless it won one.
    count = await sync_to_async(lambda: Habit.objects.get(pk=habit.pk).freeze_count)()
    assert count == before.freeze_count
    log = await sync_to_async(HabitLog.objects.get)(habit=habit, last_completed_date=today)
    displayed = round(RewardService.calculate_reward_chance(before.next_streak))
    assert round(100 - log.total_weight_applied) == displayed


@pytest.mark.asyncio
async def test_batch_cache_miss_when_habit_missing():
    def _prep():
        user, h1 = _setup()
        h2 = Habit.objects.create(user=user, name="Read", weight=0)
        _log(user, h1, d(0), 2)
        _log(user, h2, d(0), 5)
        return user, h1, h2

    user, h1, h2 = await sync_to_async(_prep)()
    svc = StreakService()
    with _today(d(1)):
        await cache.adelete(StreakService.cache_key(user.id))
        first = await svc.get_streak_states(user.id, [h1], "UTC")
        both = await svc.get_streak_states(user.id, [h1, h2], "UTC")
        cached = await svc.get_streak_states(user.id, [h2], "UTC")
    assert set(first) == {h1.id}
    assert (both[h1.id].streak, both[h2.id].streak) == (2, 5)
    assert cached[h2.id].streak == 5


@pytest.mark.asyncio
async def test_single_habit_paths_honour_spent_freeze():
    """get_current_streak / calculate_streak / calculate_streak_for_date read SPENT events."""

    def _prep():
        user, habit = _setup(freeze_count=1)
        log = _log(user, habit, d(0), 3)
        _earned(user, habit, log, d(0))
        return user, habit

    user, habit = await sync_to_async(_prep)()
    svc = StreakService()
    with _today(d(2)):
        await FreezeService().burn_due_freezes()  # spends for Tue
        current = await svc.get_current_streak(user.id, habit.id, "UTC")
        next_today = await svc.calculate_streak(user.id, habit.id, "UTC")
        on_wed = await svc.calculate_streak_for_date(user.id, habit.id, d(2))
        on_thu = await svc.calculate_streak_for_date(user.id, habit.id, d(3))
    assert (current, next_today, on_wed, on_thu) == (3, 4, 4, 1)


@pytest.mark.asyncio
async def test_get_validated_streak_map_is_streak_projection():
    def _prep():
        user, habit = _setup(freeze_count=1)
        log = _log(user, habit, d(0), 3)
        _earned(user, habit, log, d(0))
        return user, habit

    user, habit = await sync_to_async(_prep)()
    with _today(d(2)):
        await cache.adelete(StreakService.cache_key(user.id))
        streaks = await StreakService().get_validated_streak_map(user.id, [habit], "UTC")
    assert streaks == {habit.id: 3}  # alive thanks to the predicted freeze
