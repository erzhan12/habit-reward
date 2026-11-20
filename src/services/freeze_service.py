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
from datetime import date

from django.conf import settings
from django.db import IntegrityError, transaction

from src.core.models import Habit, HabitLog
from src.core.repositories import (
    habit_freeze_event_repository,
    habit_log_repository,
    habit_repository,
)
from src.services.streak_service import StreakService, find_due_spend, freeze_usable_predicate

logger = logging.getLogger(__name__)


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
                    self.event_repo.set_state_sync(held.id, "spent")
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


freeze_service = FreezeService()
