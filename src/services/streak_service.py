"""Streak calculation service for per-habit streak tracking."""

import logging
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Awaitable
from django.core.cache import cache
from src.core.repositories import habit_freeze_event_repository, habit_log_repository, habit_repository
from src.utils.async_compat import run_sync_or_async, maybe_await
from src.bot.timezone_utils import get_user_today

logger = logging.getLogger(__name__)


# --- Gap engine (feature 0048 §2) -----------------------------------------------
# Pure functions, no DB. A "gap" is the run of days strictly between two
# completions (or, for the open trailing gap, between the last completion and the
# user's local today, counting only days that have ended).


class GapOutcome(str, Enum):
    """How a gap affects the streak of the completion that closes it."""

    CONTINUE = "continue"            # missed <= allowed_skip_days: s = prev + 1
    FREEZE_SAVED = "freeze_saved"    # exactly one day beyond the allowance, frozen: s = prev + 1
    FREEZE_BURNED = "freeze_burned"  # frozen, but more days were missed: s = 1
    RESET = "reset"                  # beyond the allowance, no freeze: s = 1

    @property
    def keeps_streak(self) -> bool:
        return self in (GapOutcome.CONTINUE, GapOutcome.FREEZE_SAVED)


@dataclass(frozen=True)
class GapResult:
    outcome: GapOutcome
    covered_date: date | None = None   # guard day c = missed[A] when a freeze covers it
    needs_catchup_spend: bool = False  # covered by inventory, no SPENT event yet


def missed_days(prev_date: date, end_date: date, exempt_weekdays: Iterable[int] | None) -> list[date]:
    """Non-exempt dates strictly between ``prev_date`` and ``end_date``."""
    exempt = set(exempt_weekdays or ())
    days = []
    current = prev_date + timedelta(days=1)
    while current < end_date:
        if current.isoweekday() not in exempt:
            days.append(current)
        current += timedelta(days=1)
    return days


def evaluate_gap(
    prev_date: date,
    cur_date: date,
    allowed_skip_days: int,
    exempt_weekdays: Iterable[int] | None,
    spent_dates: Collection[date],
    freeze_usable_for: Callable[[date], bool],
) -> GapResult:
    """Classify the gap between a completion on ``prev_date`` and ``cur_date``.

    ``cur_date`` is the next completion, or the user's local today for the trailing
    gap. The guard day ``c = missed[A]`` is covered by an existing SPENT event for
    ``c`` or, failing that, by a usable freeze in inventory (catch-up spend).
    """
    allowance = max(0, int(allowed_skip_days or 0))
    missed = missed_days(prev_date, cur_date, exempt_weekdays)
    if len(missed) <= allowance:
        return GapResult(GapOutcome.CONTINUE)

    guard = missed[allowance]
    covered_outcome = (
        GapOutcome.FREEZE_SAVED if len(missed) == allowance + 1 else GapOutcome.FREEZE_BURNED
    )
    if guard in spent_dates:
        return GapResult(covered_outcome, guard, False)
    if freeze_usable_for(guard):
        return GapResult(covered_outcome, guard, True)
    return GapResult(GapOutcome.RESET)


def freeze_usable_predicate(freeze_count: int, held_earned_on: date | None) -> Callable[[date], bool]:
    """The usable rule: a held freeze can cover day ``c`` unless it was won on or after ``c``.

    ``held_earned_on`` is the ``earned_on`` of the habit's held EARNED event, or None
    for an untracked (admin-granted) freeze or a grant with no earning date.
    """
    if freeze_count <= 0:
        return lambda _covered: False
    if held_earned_on is None:
        return lambda _covered: True
    return lambda covered: held_earned_on < covered


def find_due_spend(
    last_log_date: date | None,
    user_today: date,
    allowed_skip_days: int,
    exempt_weekdays: Iterable[int] | None,
    spent_dates: Collection[date],
    freeze_usable_for: Callable[[date], bool],
) -> date | None:
    """Guard day of the trailing gap if it has ended, is uncovered and a freeze can cover it.

    Shared by the burn job, the catch-up in mutating paths and the read-path prediction.
    A spend is due even when the streak is already broken (Duolingo-style).
    """
    if last_log_date is None:
        return None
    result = evaluate_gap(
        last_log_date, user_today, allowed_skip_days, exempt_weekdays, spent_dates, freeze_usable_for
    )
    return result.covered_date if result.needs_catchup_spend else None


@dataclass(frozen=True)
class StreakState:
    """What the read paths show for one habit (feature 0048 §7).

    ``freeze_count`` is the effective inventory: the DB value minus a spend the job
    has not done yet. Read paths never write; they predict with the job's rule.
    """

    streak: int                     # 0 if broken
    next_streak: int                # streak of a completion today: streak + 1 if alive, else 1
    freeze_count: int
    freeze_used_for: date | None    # guard day, if the trailing gap is alive only thanks to a freeze
    freeze_at_risk: bool            # skipping today means the freeze is spent tonight

    def to_cache(self) -> dict:
        """Plain, JSON-safe form (the file cache outlives deploys)."""
        return {
            "streak": self.streak,
            "next_streak": self.next_streak,
            "freeze_count": self.freeze_count,
            "freeze_used_for": self.freeze_used_for.isoformat() if self.freeze_used_for else None,
            "freeze_at_risk": self.freeze_at_risk,
        }

    @classmethod
    def from_cache(cls, data: dict) -> "StreakState":
        used_for = data.get("freeze_used_for")
        return cls(
            streak=data["streak"],
            next_streak=data["next_streak"],
            freeze_count=data["freeze_count"],
            freeze_used_for=date.fromisoformat(used_for) if used_for else None,
            freeze_at_risk=data["freeze_at_risk"],
        )


def trailing_streak_state(
    last_date: date | None,
    last_streak: int,
    today: date,
    allowed_skip_days: int,
    exempt_weekdays: Iterable[int] | None,
    spent_dates: Collection[date],
    freeze_count: int,
    held_earned_on: date | None,
) -> StreakState:
    """Display state of a habit from its last counted completion and the trailing gap.

    ``last_date``/``last_streak`` are the last counted log (after the epoch rule) and
    its effective streak, or None/0 if there is none. Pure: no DB, no clock.
    """
    if last_date is None:
        return StreakState(0, 1, freeze_count, None, False)
    if last_date >= today:
        return StreakState(last_streak, last_streak + 1, freeze_count, None, False)

    usable = freeze_usable_predicate(freeze_count, held_earned_on)
    gap = evaluate_gap(last_date, today, allowed_skip_days, exempt_weekdays, spent_dates, usable)
    effective_count = freeze_count - 1 if gap.needs_catchup_spend else freeze_count
    if not gap.outcome.keeps_streak:
        # Broken; a due spend is still predicted (Duolingo-style), so the count drops.
        return StreakState(0, 1, effective_count, None, False)

    used_for = gap.covered_date if gap.outcome is GapOutcome.FREEZE_SAVED else None
    exempt = set(exempt_weekdays or ())
    allowance = max(0, int(allowed_skip_days or 0))
    at_risk = (
        gap.outcome is GapOutcome.CONTINUE
        and today.isoweekday() not in exempt
        and len(missed_days(last_date, today, exempt)) == allowance
        and usable(today)  # today would be the guard day
    )
    return StreakState(last_streak, last_streak + 1, effective_count, used_for, at_risk)


class StreakService:
    """Service for calculating and managing habit streaks."""

    def __init__(self):
        """Initialize StreakService with repositories."""
        self._refresh_dependencies()

    def _refresh_dependencies(self) -> None:
        """Rebind repositories to allow test patching."""
        self.habit_log_repo = habit_log_repository
        self.habit_repo = habit_repository
        self.freeze_event_repo = habit_freeze_event_repository

    @staticmethod
    def streak_epoch(habit) -> date | None:
        """Return the habit's streak epoch (feature 0048 launch reset), or None."""
        return getattr(habit, "streak_epoch", None) if habit is not None else None

    @classmethod
    def counted_log(cls, log, habit):
        """Return ``log`` if it counts as a streak predecessor, else None.

        Logs dated before the habit's ``streak_epoch`` do not exist for streak purposes.
        """
        if log is None:
            return None
        epoch = cls.streak_epoch(habit)
        if epoch is not None and log.last_completed_date < epoch:
            return None
        return log

    @classmethod
    def effective_streak(cls, log, habit) -> int:
        """Streak of ``log`` as the engine sees it.

        A log dated exactly on ``streak_epoch`` has no counted predecessor, so it is
        streak day 1 whatever its stored ``streak_count`` (which may be a pre-reset
        value). The stored value is kept for historical stats.
        """
        return cls._effective_streak_of(log.last_completed_date, log.streak_count, habit)

    @classmethod
    def _effective_streak_of(cls, last_completed_date: date, streak_count: int, habit) -> int:
        epoch = cls.streak_epoch(habit)
        if epoch is not None and last_completed_date == epoch:
            return 1
        return streak_count

    @staticmethod
    def _is_streak_alive(
        last_completed_date: date,
        today: date,
        allowed_skip_days: int = 0,
        exempt_weekdays: list[int] | None = None,
    ) -> bool:
        """True if the gap since ``last_completed_date`` is within the allowance (no freezes)."""
        if last_completed_date >= today:
            return True
        return len(missed_days(last_completed_date, today, exempt_weekdays)) <= max(0, int(allowed_skip_days or 0))

    # --- Freeze-aware single-habit helpers --------------------------------------------

    async def _freeze_inputs(self, habit) -> tuple[set[date], date | None]:
        """SPENT covered dates and the held freeze's ``earned_on`` for one habit."""
        if habit is None:
            return set(), None
        spent = await maybe_await(self.freeze_event_repo.get_spent_dates_for_habit(habit.id))
        held_on = None
        if habit.freeze_count > 0:
            held = await maybe_await(self.freeze_event_repo.get_held_earned(habit.id))
            held_on = held.earned_on if held else None
        return set(spent), held_on

    async def _state_for_habit(self, user_id, habit_id, user_timezone: str) -> tuple[StreakState, bool]:
        """Trailing state of one habit and whether it is completed today.

        A missing habit means strict rules and no freeze.
        """
        last_log = await maybe_await(self.habit_log_repo.get_last_log_for_habit(user_id, habit_id))
        if last_log is None:
            return StreakState(0, 1, 0, None, False), False
        habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
        freeze_count = habit.freeze_count if habit is not None else 0
        last = self.counted_log(last_log, habit)
        if last is None:
            return StreakState(0, 1, freeze_count, None, False), False
        today = get_user_today(user_timezone)
        completed_today = last.last_completed_date >= today
        spent, held_on = (set(), None)
        if not completed_today:
            spent, held_on = await self._freeze_inputs(habit)
        return trailing_streak_state(
            last.last_completed_date,
            self.effective_streak(last, habit),
            today,
            habit.allowed_skip_days if habit is not None else 0,
            habit.exempt_weekdays if habit is not None else [],
            spent,
            freeze_count,
            held_on,
        ), completed_today

    def calculate_streak(
        self,
        user_id: str,
        habit_id: str,
        user_timezone: str = 'UTC',
    ) -> int | Awaitable[int]:
        """Streak a completion today would get (prediction, same rule as the completion).

        Already completed today: the current streak. Otherwise ``prev + 1`` if the
        trailing gap keeps the streak (allowance, exempt days, a spent or usable
        freeze), else 1.
        """

        async def _impl() -> int:
            self._refresh_dependencies()
            state, completed_today = await self._state_for_habit(user_id, habit_id, user_timezone)
            return state.streak if completed_today else state.next_streak

        return run_sync_or_async(_impl())

    def calculate_streak_for_date(
        self,
        user_id: str,
        habit_id: str,
        target_date: date
    ) -> int | Awaitable[int]:
        """Streak a completion on ``target_date`` (a backdate) would get.

        Uses the gap between the last counted completion before ``target_date`` and
        ``target_date``, honouring SPENT events and a usable freeze like the completion.
        """

        async def _impl() -> int:
            self._refresh_dependencies()
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_before_date(user_id, habit_id, target_date)
            )
            if last_log is None:
                return 1

            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            last = self.counted_log(last_log, habit)
            if last is None:
                return 1
            if last.last_completed_date >= target_date:
                logger.warning(
                    "Unexpected state in calculate_streak_for_date: last_date=%s >= target_date=%s",
                    last.last_completed_date,
                    target_date,
                )
                return 1

            spent, held_on = await self._freeze_inputs(habit)
            gap = evaluate_gap(
                last.last_completed_date,
                target_date,
                habit.allowed_skip_days if habit is not None else 0,
                habit.exempt_weekdays if habit is not None else [],
                spent,
                freeze_usable_predicate(habit.freeze_count if habit is not None else 0, held_on),
            )
            return self.effective_streak(last, habit) + 1 if gap.outcome.keeps_streak else 1

        return run_sync_or_async(_impl())

    def get_last_completed_date(
        self,
        user_id: str,
        habit_id: str
    ) -> date | None | Awaitable[date | None]:
        """Get the last completed date for a specific habit and user."""

        async def _impl() -> date | None:
            last_log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user_id, habit_id)
            )
            return last_log.last_completed_date if last_log else None

        return run_sync_or_async(_impl())

    def get_current_streak(
        self,
        user_id: str,
        habit_id: str,
        user_timezone: str = 'UTC',
    ) -> int | Awaitable[int]:
        """Current streak for display: 0 if broken, freezes (spent or predicted) included."""

        async def _impl() -> int:
            self._refresh_dependencies()
            state, _completed_today = await self._state_for_habit(user_id, habit_id, user_timezone)
            return state.streak

        return run_sync_or_async(_impl())

    def get_all_streaks_for_user(
        self,
        user_id: str,
        user_timezone: str = 'UTC',
    ) -> dict[str, int] | Awaitable[dict[str, int]]:
        """Get current streaks for all habits for a user.

        Returns 0 for any habit whose streak has been broken.
        """

        async def _impl() -> dict[str, int]:
            self._refresh_dependencies()
            logs = await maybe_await(self.habit_log_repo.get_logs_by_user(user_id))

            habit_streaks: dict[str, int] = {}
            processed_habits: set[str] = set()

            for log in logs:
                if log.habit_id not in processed_habits:
                    processed_habits.add(log.habit_id)
                    streak = await maybe_await(
                        self.get_current_streak(user_id, log.habit_id, user_timezone)
                    )
                    habit_streaks[log.habit_id] = streak

            return habit_streaks

        return run_sync_or_async(_impl())

    @staticmethod
    def cache_key(user_id: int | str) -> str:
        """Return the cache key for a user's streak states (v3: StreakState dicts)."""
        return f'streaks:v3:{user_id}'

    def get_streak_states(
        self,
        user_id: int | str,
        habits: list,
        user_timezone: str = 'UTC',
    ) -> dict[int, StreakState] | Awaitable[dict[int, StreakState]]:
        """Batch display state for ``habits`` (feature 0048 §7), cached for 5 minutes.

        Three queries per user: latest log per habit, SPENT dates, held EARNED dates.
        A cache hit that lacks a requested habit is treated as a miss. The cache is
        invalidated on commit by every path that writes logs or freeze events.
        """

        async def _impl() -> dict[int, StreakState]:
            self._refresh_dependencies()

            key = self.cache_key(user_id)
            cached = await cache.aget(key)
            if cached is not None and all(h.id in cached for h in habits):
                return {h.id: StreakState.from_cache(cached[h.id]) for h in habits}

            today = get_user_today(user_timezone)
            raw = await self.habit_log_repo.get_latest_streak_counts(user_id)
            spent_by_habit = await maybe_await(self.freeze_event_repo.get_spent_dates_by_habit(user_id))
            held_by_habit = await maybe_await(self.freeze_event_repo.get_held_earned_on_by_habit(user_id))

            result: dict[int, StreakState] = {}
            for habit in habits:
                last_date, last_streak = None, 0
                entry = raw.get(habit.id)
                if entry is not None:
                    streak_count, completed = entry
                    epoch = self.streak_epoch(habit)
                    if epoch is None or completed >= epoch:
                        last_date = completed
                        last_streak = self._effective_streak_of(completed, streak_count, habit)
                result[habit.id] = trailing_streak_state(
                    last_date,
                    last_streak,
                    today,
                    habit.allowed_skip_days,
                    habit.exempt_weekdays,
                    spent_by_habit.get(habit.id, set()),
                    habit.freeze_count,
                    held_by_habit.get(habit.id),
                )

            await cache.aset(key, {hid: s.to_cache() for hid, s in result.items()}, timeout=300)
            return result

        return run_sync_or_async(_impl())

    def get_validated_streak_map(
        self,
        user_id: int | str,
        habits: list,
        user_timezone: str = 'UTC',
    ) -> dict[int, int] | Awaitable[dict[int, int]]:
        """``{habit_id: current streak}`` (0 if broken), from ``get_streak_states``."""

        async def _impl() -> dict[int, int]:
            states = await maybe_await(self.get_streak_states(user_id, habits, user_timezone))
            return {habit_id: state.streak for habit_id, state in states.items()}

        return run_sync_or_async(_impl())


# Global service instance
streak_service = StreakService()
