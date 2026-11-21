"""Streak freeze service (feature 0048).

A completion that wins no prize rolls a FREEZE_DROP_CHANCE chance of a freeze; a
habit holds at most MAX_FREEZES_PER_HABIT. A freeze covers the guard day of a gap
(see ``streak_service.evaluate_gap``) and is spent when that day ends.

Methods ending in ``_sync`` must run inside the caller's ``transaction.atomic()``
after the habit row was locked (``habit_repository.lock_for_update_sync``).
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import partial

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction

from src.core.models import Habit, HabitFreezeEvent, HabitLog
from src.core.repositories import (
    habit_freeze_event_repository,
    habit_log_repository,
    habit_repository,
)
from src.bot.timezone_utils import get_user_today
from src.services.streak_service import StreakService, find_due_spend, freeze_usable_predicate, missed_days
from src.services.transactions import ServiceBusyError, run_in_transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FreezeSpend:
    """A spend created by one burn-job run (the only run allowed to notify about it)."""

    habit_id: int
    user_id: int
    telegram_id: str | None
    language: str
    habit_name: str
    covered_date: date
    notify: bool  # False when the streak is already broken despite the freeze


class FreezeService:
    def __init__(self):
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.event_repo = habit_freeze_event_repository

    # --- Rolling -----------------------------------------------------------------

    @staticmethod
    def should_roll(got_reward: bool, freeze_count: int) -> bool:
        """Roll only after a completion without a prize, and only with room in inventory."""
        return not got_reward and freeze_count < settings.MAX_FREEZES_PER_HABIT

    @staticmethod
    def roll() -> bool:
        return random.random() * 100 < settings.FREEZE_DROP_CHANCE

    # --- Reads (inside the transaction) ----------------------------------------------

    def spent_dates_sync(self, habit_id) -> set[date]:
        return {e.covered_date for e in self.event_repo.get_spent_for_habit_sync(habit_id)}

    def usable_predicate_sync(self, habit: Habit) -> Callable[[date], bool]:
        held = self.event_repo.get_held_earned_sync(habit.id)
        return freeze_usable_predicate(habit.freeze_count, held.earned_on if held else None)

    # --- Writes (inside the transaction, habit row locked) --------------------------------

    def spend_sync(self, habit: Habit, covered_date: date) -> bool:
        """Spend the held freeze for ``covered_date``. False if someone else got there first.

        Runs in a savepoint: a lost compare-and-set or an IntegrityError on
        ``uniq_freeze_spent_habit_day`` rolls back only this spend, and the outer
        transaction stays usable.
        """
        try:
            with transaction.atomic():
                held = self.event_repo.get_held_earned_sync(habit.id)
                if not self.habit_repo.try_consume_freeze_sync(habit.id):
                    return False
                if held is not None:
                    self.event_repo.set_state_sync(held.id, HabitFreezeEvent.State.SPENT)
                self.event_repo.create_spent_sync(habit, covered_date, held)
        except IntegrityError:
            logger.info("Freeze spend for habit %s on %s already exists", habit.id, covered_date)
            return False
        habit.freeze_count = max(0, habit.freeze_count - 1)
        logger.info("Freeze spent: habit=%s covered_date=%s", habit.id, covered_date)
        return True

    def settle_due_spend_sync(self, habit: Habit, user_today: date) -> date | None:
        """Do exactly what the burn job would have done by now for the trailing gap.

        Returns the covered date if this call spent a freeze, else None.
        """
        if habit.freeze_count <= 0:
            return None
        last_log = StreakService.counted_log(
            self.habit_log_repo.get_last_log_on_or_before_sync(habit.id, user_today), habit
        )
        if last_log is None:
            return None
        covered = find_due_spend(
            last_log.last_completed_date,
            user_today,
            habit.allowed_skip_days,
            habit.exempt_weekdays,
            self.spent_dates_sync(habit.id),
            self.usable_predicate_sync(habit),
        )
        if covered is not None and self.spend_sync(habit, covered):
            return covered
        return None

    def return_spend_sync(self, habit: Habit, spend: HabitFreezeEvent) -> bool:
        """Undo a spend (plan §5 "returning a freeze"). True if the freeze is back in inventory.

        If the habit already holds a freeze the return is dropped and the spend's own
        freeze becomes ``forfeited``; either way exactly the freeze in inventory is held.
        """
        granted = self.habit_repo.try_grant_freeze_sync(habit.id, settings.MAX_FREEZES_PER_HABIT)
        if spend.earned_event_id:
            self.event_repo.set_state_sync(
                spend.earned_event_id,
                HabitFreezeEvent.State.HELD if granted else HabitFreezeEvent.State.FORFEITED,
            )
        self.event_repo.delete_sync(spend.id)
        if granted:
            habit.freeze_count = min(settings.MAX_FREEZES_PER_HABIT, habit.freeze_count + 1)
        logger.info(
            "Freeze spend for habit %s on %s %s", habit.id, spend.covered_date,
            "returned" if granted else "dropped (inventory full; forfeited)",
        )
        return granted

    def move_spend_sync(self, spend: HabitFreezeEvent, covered_date: date) -> None:
        self.event_repo.update_covered_date_sync(spend.id, covered_date)
        spend.covered_date = covered_date

    def revoke_won_sync(self, habit: Habit, habit_log_id: int) -> bool:
        """Undo of a winning completion: revoke its freeze only if that freeze is still held."""
        earned = self.event_repo.get_earned_for_log_sync(habit_log_id)
        if earned is None or earned.state != HabitFreezeEvent.State.HELD:
            return False
        if not self.habit_repo.try_consume_freeze_sync(habit.id):
            logger.error("Held freeze event %s but habit %s has no freeze", earned.id, habit.id)
            return False
        self.event_repo.delete_sync(earned.id)
        habit.freeze_count = max(0, habit.freeze_count - 1)
        return True

    def grant_won_sync(self, habit: Habit, habit_log: HabitLog, earned_on: date) -> bool:
        """Put a freeze won by ``habit_log`` into inventory (EARNED, state held)."""
        try:
            with transaction.atomic():
                if not self.habit_repo.try_grant_freeze_sync(habit.id, settings.MAX_FREEZES_PER_HABIT):
                    return False
                self.event_repo.create_earned_sync(habit, habit_log, earned_on)
        except IntegrityError:
            logger.warning("Freeze grant for habit %s conflicted; skipped", habit.id)
            return False
        habit.freeze_count = min(settings.MAX_FREEZES_PER_HABIT, habit.freeze_count + 1)
        logger.info("Freeze won: habit=%s earned_on=%s", habit.id, earned_on)
        return True

    # --- Admin actions (plan "Repositories and admin"; run inside run_in_transaction_sync) --

    def admin_grant_sync(self, habit_id) -> bool:
        """Grant an untracked freeze (no EARNED event). False if the inventory is full."""
        habit = self.habit_repo.lock_for_update_sync(habit_id)
        if not self.habit_repo.try_grant_freeze_sync(habit.id, settings.MAX_FREEZES_PER_HABIT):
            return False
        self._invalidate_streak_cache(habit.user_id)
        logger.info("Admin granted a freeze: habit=%s", habit.id)
        return True

    def admin_remove_sync(self, habit_id) -> bool:
        """Remove the held freeze; a tracked one is marked forfeited. False if none is held."""
        habit = self.habit_repo.lock_for_update_sync(habit_id)
        held = self.event_repo.get_held_earned_sync(habit.id)
        if not self.habit_repo.try_consume_freeze_sync(habit.id):
            return False
        if held is not None:
            self.event_repo.set_state_sync(held.id, HabitFreezeEvent.State.FORFEITED)
        self._invalidate_streak_cache(habit.user_id)
        logger.info("Admin removed a freeze: habit=%s tracked=%s", habit.id, held is not None)
        return True

    @staticmethod
    def _invalidate_streak_cache(user_id) -> None:
        transaction.on_commit(partial(cache.delete, StreakService.cache_key(user_id)), robust=True)

    # --- Periodic burn job (plan §3) ----------------------------------------------------

    def _burn_one_sync(self, habit_id) -> FreezeSpend | None:
        """One habit, one transaction: lock, compute the trailing gap inside, spend if due."""
        habit = self.habit_repo.lock_for_update_sync(habit_id)
        if habit.freeze_count <= 0 or not habit.active:
            return None
        user = habit.user
        today = get_user_today(user.timezone or "UTC")
        covered = self.settle_due_spend_sync(habit, today)
        if covered is None:
            return None
        transaction.on_commit(partial(cache.delete, StreakService.cache_key(user.id)), robust=True)
        last_log = StreakService.counted_log(
            self.habit_log_repo.get_last_log_on_or_before_sync(habit.id, today), habit
        )
        gap = missed_days(last_log.last_completed_date, today, habit.exempt_weekdays)
        # "Complete today to keep your streak" is only true while exactly A + 1 days are missed.
        notify = len(gap) == max(0, int(habit.allowed_skip_days or 0)) + 1
        return FreezeSpend(
            habit_id=habit.id,
            user_id=user.id,
            telegram_id=user.telegram_id,
            language=user.language or "en",
            habit_name=habit.name,
            covered_date=covered,
            notify=notify,
        )

    async def burn_due_freezes(self) -> list[FreezeSpend]:
        """Spend every freeze whose guard day has ended. Idempotent; safe to run concurrently.

        Candidates are read outside any transaction; each habit is then re-checked under
        its lock. A habit whose transaction stays busy is skipped until the next tick.
        """
        habit_ids = await sync_to_async(self.habit_repo.get_ids_with_freeze_sync)()
        spends: list[FreezeSpend] = []
        for habit_id in habit_ids:
            try:
                spend = await run_in_transaction(self._burn_one_sync, habit_id)
            except ServiceBusyError:
                logger.warning("Freeze burn skipped for busy habit %s", habit_id)
                continue
            except Habit.DoesNotExist:  # deleted after the candidate read
                continue
            except Exception:  # one bad habit must not drop the notices for earlier spends
                logger.exception("Freeze burn failed for habit %s", habit_id)
                continue
            if spend is not None:
                spends.append(spend)
        logger.info("Freeze burn: %s candidate(s), %s spent", len(habit_ids), len(spends))
        return spends


freeze_service = FreezeService()
