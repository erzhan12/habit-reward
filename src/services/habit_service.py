"""Habit completion orchestration service."""

import asyncio
import logging
import inspect
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from functools import partial
from typing import Awaitable
from contextlib import asynccontextmanager
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.db import IntegrityError, transaction
from src.core.repositories import (
    user_repository,
    habit_repository,
    habit_log_repository,
    reward_progress_repository
)
from src.bot.timezone_utils import get_user_today
from src.core.models import Habit, HabitLog, RewardProgress
from src.services.streak_service import GapOutcome, StreakService, evaluate_gap, streak_service
from src.services.reward_service import reward_service
from src.services.freeze_service import freeze_service
from src.services.transactions import run_in_transaction
from src.services.audit_log_service import audit_log_service
from src.models.habit_completion_result import HabitCompletionResult
from src.models.habit_revert_result import HabitRevertResult
from src.models.reward_progress import RewardProgress as RewardProgressModel
from src.utils.async_compat import run_sync_or_async, maybe_await
from src.realtime.manager import connection_manager

# Configure logging
logger = logging.getLogger(__name__)


async def _safe_notify_user(user_id: int) -> None:
    """Send WebSocket notification, swallowing any errors."""
    try:
        await connection_manager.notify_user(user_id)
    except Exception:
        logger.warning("WebSocket notification failed for user %s", user_id, exc_info=True)


def _try_schedule_notify(user_id: int) -> None:
    """Schedule a WebSocket notification if an event loop is running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # No event loop running — nothing to schedule
    loop.create_task(_safe_notify_user(user_id))


@dataclass
class CompletionCommit:
    """What the completion transaction decided (feature 0048 §4)."""

    habit_log: HabitLog
    streak_count: int
    reward_chance: float
    effective_no_reward: float
    selected_reward: object | None
    reward_progress: RewardProgress | None
    outcome: GapOutcome | None
    covered_date: date | None
    freeze_won: bool
    freeze_count: int


class HabitService:
    """Service for orchestrating habit completion flow."""

    def __init__(self):
        """Initialize HabitService with repositories and services."""
        self.user_repo = user_repository
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.reward_progress_repo = reward_progress_repository
        self.streak_service = streak_service
        self.reward_service = reward_service
        self.freeze_service = freeze_service
        self.audit_log_service = audit_log_service

    def _refresh_dependencies(self) -> None:
        """Rebind dependencies to allow patching in tests."""
        self.user_repo = user_repository
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.reward_progress_repo = reward_progress_repository
        self.streak_service = streak_service
        self.reward_service = reward_service
        self.freeze_service = freeze_service
        self.audit_log_service = audit_log_service

    @asynccontextmanager
    async def _atomic(self):
        """Async-friendly transaction context manager."""

        ctx = transaction.atomic()

        if hasattr(ctx, "__aenter__"):
            await ctx.__aenter__()
            try:
                yield
            except Exception as exc:  # pragma: no cover - safety net
                await ctx.__aexit__(type(exc), exc, exc.__traceback__)
                raise
            else:
                await ctx.__aexit__(None, None, None)
            return

        # Fallback for standard sync context manager
        enter = await sync_to_async(ctx.__enter__, thread_sensitive=True)()
        try:
            yield enter
        except Exception as exc:  # pragma: no cover
            await sync_to_async(ctx.__exit__, thread_sensitive=True)(
                type(exc), exc, exc.__traceback__
            )
            raise
        else:
            await sync_to_async(ctx.__exit__, thread_sensitive=True)(None, None, None)

    async def _revert_log_transaction(
        self,
        log: HabitLog,
        user_id: int,
        reward_reverted: bool,
        reward_name: str | None,
    ) -> tuple[RewardProgress | None, str | None]:
        """Run log deletion and reward rollback inside a DB transaction."""

        async with self._atomic():
            deleted = await maybe_await(self.habit_log_repo.delete(log.id))
            if deleted == 0:
                raise ValueError("No habit completion found to revert")

            progress_obj: RewardProgress | None = None
            updated_reward_name = reward_name

            if reward_reverted and log.reward_id:
                progress_obj = await maybe_await(
                    self.reward_progress_repo.decrement_pieces_earned(
                        user_id,
                        log.reward_id,
                    )
                )
                if progress_obj:
                    updated_reward_name = (
                        reward_name or getattr(progress_obj.reward, "name", None)
                    )

            return progress_obj, updated_reward_name

    def process_habit_completion(
        self,
        user_telegram_id: str,
        habit_name: str,
        target_date: date | None = None,
        user_timezone: str = 'UTC',
    ) -> HabitCompletionResult | Awaitable[HabitCompletionResult]:
        """
        Main orchestration for habit completion.

        Flow:
        1. Verify user exists in Users table by telegram_id
        2. Get habit (from selection or NLP classification)
        3. Validate target_date (if backdating)
        4. Check for duplicate entries on target_date
        5. Snapshot habit weight (stored on the log; no longer affects the chance)
        6. Calculate streak for target_date (or today if not backdating)
        7. Reward chance from the streak only (calculate_reward_chance)
        8. Get today's awarded rewards (to prevent duplicate awards)
        9. Fetch all active rewards and run weighted random draw (excluding today's awards)
        10. If cumulative reward: update Reward Progress, check if achieved
        11. Log entry to Habit Log with all calculated values
        12. Return response object with habit confirmation, reward result, streak status

        Note: No reward (cumulative or non-cumulative) can be awarded twice in the same day.

        Args:
            user_telegram_id: Telegram ID of the user
            habit_name: Name of the habit to log
            target_date: Optional date for backdating (defaults to today)
                        Must be within 7 days and not before habit creation

        Returns:
            HabitCompletionResult with all completion details

        Raises:
            ValueError: If user or habit not found, or validation fails
        """

        async def _impl() -> HabitCompletionResult:
            self._refresh_dependencies()
            nonlocal target_date  # Allow modification of outer scope variable
            logger.info(
                "Processing habit completion for user=%s, habit='%s'",
                user_telegram_id,
                habit_name,
            )
            user = await maybe_await(
                self.user_repo.get_by_telegram_id(user_telegram_id)
            )
            if not user:
                logger.error(
                    "User with telegram_id %s not found",
                    user_telegram_id,
                )
                raise ValueError(
                    f"User with telegram_id {user_telegram_id} not found"
                )

            habit = await maybe_await(self.habit_repo.get_by_name(user.id, habit_name))
            if not habit:
                logger.error("Habit '%s' not found for user %s", habit_name, user.id)
                raise ValueError(f"Habit '{habit_name}' not found")

            # Validate target_date for backdating
            today = get_user_today(user_timezone)

            # Default target_date to today if not specified
            if target_date is None:
                target_date = today
            max_backdate_days = 7
            earliest_allowed = today - timedelta(days=max_backdate_days)

            if target_date > today:
                logger.error(
                    "Cannot log habit for future date: %s (today: %s)",
                    target_date,
                    today
                )
                raise ValueError("Cannot log habits for future dates")

            if target_date < earliest_allowed:
                logger.error(
                    "Cannot backdate more than %d days: %s (earliest: %s)",
                    max_backdate_days,
                    target_date,
                    earliest_allowed
                )
                raise ValueError(f"Cannot backdate more than {max_backdate_days} days")

            if target_date < habit.created_at.date():
                logger.error(
                    "Cannot backdate before habit was created: %s (habit created: %s)",
                    target_date,
                    habit.created_at.date()
                )
                raise ValueError(
                    f"Cannot backdate before habit was created on {habit.created_at.date()}"
                )

            # Check for duplicate entries on target_date
            existing_log = await maybe_await(
                self.habit_log_repo.get_log_for_habit_on_date(
                    user.id, habit.id, target_date
                )
            )
            if existing_log:
                logger.warning(
                    "Habit '%s' already completed on %s for user %s",
                    habit_name,
                    target_date,
                    user.id
                )
                raise ValueError(
                    f"Habit '{habit_name}' already completed on {target_date}"
                )

            # Feature 0048 §4: everything that reads or changes streaks, freezes,
            # rewards and the log runs as ONE sync function in ONE transaction.
            try:
                commit = await run_in_transaction(
                    self._commit_completion_sync, user, habit.id, target_date, today
                )
            except IntegrityError:
                # uniq_habitlog_habit_day: a concurrent submit of the same completion won.
                if await maybe_await(
                    self.habit_log_repo.get_log_for_habit_on_date(user.id, habit.id, target_date)
                ):
                    raise ValueError(
                        f"Habit '{habit_name}' already completed on {target_date}"
                    )
                raise

            streak_count = commit.streak_count
            effective_no_reward = commit.effective_no_reward
            selected_reward = commit.selected_reward
            got_reward = selected_reward is not None
            reward_progress = commit.reward_progress
            habit_log = commit.habit_log
            freeze_used = commit.outcome == GapOutcome.FREEZE_SAVED
            freeze_burned = commit.outcome == GapOutcome.FREEZE_BURNED

            # Log habit completion to audit trail (after transaction commits)
            snapshot = {
                "habit_name": habit.name,
                "streak_count": streak_count,
                "effective_no_reward": effective_no_reward,
                "selected_reward_name": selected_reward.name if got_reward else None,
                "reward_chance": commit.reward_chance,
                "freeze_used": freeze_used,
                "freeze_burned": freeze_burned,
                "freeze_covered_date": commit.covered_date.isoformat() if commit.covered_date else None,
                "freeze_won": commit.freeze_won,
            }

            if reward_progress:
                snapshot["reward_progress"] = {
                    "pieces_earned": reward_progress.pieces_earned,
                    "pieces_required": reward_progress.get_pieces_required(),
                    "claimed": reward_progress.claimed,
                }

            await maybe_await(
                self.audit_log_service.log_habit_completion(
                    user_id=user.id,
                    habit=habit,
                    reward=selected_reward if got_reward else None,
                    habit_log=habit_log,
                    snapshot=snapshot,
                )
            )

            # Notify connected WebSocket clients (non-blocking)
            _try_schedule_notify(user.id)

            return HabitCompletionResult(
                habit_confirmed=True,
                habit_name=habit.name,
                reward=selected_reward if got_reward else None,
                streak_count=streak_count,
                cumulative_progress=reward_progress,
                motivational_quote=None,
                got_reward=got_reward,
                total_weight_applied=effective_no_reward,
                reward_chance=commit.reward_chance,
                freeze_won=commit.freeze_won,
                freeze_used=freeze_used,
                freeze_burned=freeze_burned,
                freeze_covered_date=commit.covered_date,
                freeze_count=commit.freeze_count,
            )

        return run_sync_or_async(_impl())

    def _commit_completion_sync(
        self, user, habit_id: int, target_date: date, today: date
    ) -> CompletionCommit:
        """Steps 1-8 of plan §4. Runs inside ``transaction.atomic()`` (see run_in_transaction)."""
        habit = self.habit_repo.lock_for_update_sync(habit_id)
        fs = self.freeze_service

        # Settle first: do what the burn job would have done for the trailing gap,
        # so the result never depends on whether the job already ran.
        fs.settle_due_spend_sync(habit, today)

        # 1-2. Resolve the gap this completion closes; catch-up spend if needed.
        prev = StreakService.counted_log(
            self.habit_log_repo.get_last_log_before_date_sync(habit.id, target_date), habit
        )
        outcome: GapOutcome | None = None
        covered: date | None = None
        if prev is None:
            streak_count = 1
        else:
            gap = evaluate_gap(
                prev.last_completed_date, target_date, habit.allowed_skip_days,
                habit.exempt_weekdays, fs.spent_dates_sync(habit.id), fs.usable_predicate_sync(habit),
            )
            outcome, covered = gap.outcome, gap.covered_date
            if gap.needs_catchup_spend and not fs.spend_sync(habit, covered):
                if covered not in fs.spent_dates_sync(habit.id):
                    if self.habit_log_repo.get_log_for_habit_on_date_sync(habit.id, target_date):
                        raise ValueError(f"Habit '{habit.name}' already completed on {target_date}")
                    outcome, covered = GapOutcome.RESET, None
            streak_count = (
                StreakService.effective_streak(prev, habit) + 1 if outcome.keeps_streak else 1
            )

        # 3. Roll the prize at the chance of this streak day.
        reward_chance = self.reward_service.calculate_reward_chance(streak_count)
        effective_no_reward = 100.0 - reward_chance
        selected_reward = self.reward_service.select_reward_sync(
            effective_no_reward, user.id, target_date=today
        )
        reward_progress = (
            self.reward_service.update_reward_progress_sync(user.id, selected_reward.id)
            if selected_reward is not None else None
        )

        # 4. The log; uniq_habitlog_habit_day rolls the whole block back on a duplicate.
        habit_log = self.habit_log_repo.create_sync(
            user_id=user.id,
            habit_id=habit.id,
            reward_id=selected_reward.id if selected_reward is not None else None,
            got_reward=selected_reward is not None,
            streak_count=streak_count,
            habit_weight=habit.weight,
            total_weight_applied=effective_no_reward,
            last_completed_date=target_date,
        )

        # 6. Backdate: recompute later streaks inside the same transaction.
        if target_date < today:
            self._recalculate_streaks_sync(habit, target_date, today)

        # 7. Freeze roll, last, against the final inventory.
        freeze_count = self.habit_repo.lock_for_update_sync(habit.id).freeze_count
        habit.freeze_count = freeze_count
        freeze_won = False
        if fs.should_roll(selected_reward is not None, freeze_count) and fs.roll():
            freeze_won = fs.grant_won_sync(habit, habit_log, target_date)

        # 8. Invalidate the streak cache only after COMMIT.
        transaction.on_commit(partial(cache.delete, StreakService.cache_key(user.id)), robust=True)

        return CompletionCommit(
            habit_log=habit_log,
            streak_count=streak_count,
            reward_chance=reward_chance,
            effective_no_reward=effective_no_reward,
            selected_reward=selected_reward,
            reward_progress=reward_progress,
            outcome=outcome,
            covered_date=covered,
            freeze_won=freeze_won,
            freeze_count=habit.freeze_count,
        )

    def _recalculate_streaks_sync(self, habit, backdate_date: date, today: date) -> None:
        """Recompute stored streaks of logs on/after ``backdate_date`` (inside a transaction).

        Never walks below the streak epoch; the epoch-day log keeps its stored value.
        Freeze-aware reconciliation (returns, relocation) is added in slice 4.
        """
        epoch = StreakService.streak_epoch(habit)
        start_date = max(backdate_date, epoch) if epoch is not None else backdate_date
        logs = self.habit_log_repo.get_logs_for_habit_in_daterange_sync(habit.id, start_date, today)
        if not logs:
            return
        spent = self.freeze_service.spent_dates_sync(habit.id)
        prev = StreakService.counted_log(
            self.habit_log_repo.get_last_log_before_date_sync(habit.id, logs[0].last_completed_date), habit
        )
        for log in logs:
            if epoch is not None and log.last_completed_date == epoch:
                prev = log
                continue
            if prev is None:
                new_streak = 1
            else:
                gap = evaluate_gap(
                    prev.last_completed_date, log.last_completed_date, habit.allowed_skip_days,
                    habit.exempt_weekdays, spent, lambda _c: False,
                )
                new_streak = (
                    StreakService.effective_streak(prev, habit) + 1 if gap.outcome.keeps_streak else 1
                )
            if log.streak_count != new_streak:
                logger.info(
                    "Updating log %s: date=%s, old_streak=%s, new_streak=%s",
                    log.id, log.last_completed_date, log.streak_count, new_streak,
                )
                self.habit_log_repo.set_streak_count_sync(log.id, new_streak)
                log.streak_count = new_streak
            prev = log

    def _recalculate_by_id_sync(self, habit_id, backdate_date: date, today: date) -> None:
        habit = self.habit_repo.lock_for_update_sync(habit_id)
        self._recalculate_streaks_sync(habit, backdate_date, today)
        transaction.on_commit(partial(cache.delete, StreakService.cache_key(habit.user_id)), robust=True)

    def recalculate_streaks_after_backdate(
        self,
        user_id: int | str,
        habit_id: int | str,
        backdate_date: date,
        user_timezone: str = 'UTC',
    ) -> None | Awaitable[None]:
        """Recalculate streak counts for all logs on or after a backdated entry.

        When a habit is logged for a past date, all subsequent logs for that habit
        need their streak_count recalculated to maintain consistency.

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            backdate_date: The date that was backdated (inclusive start for recalculation)
        """

        async def _impl() -> None:
            logger.info(
                "Recalculating streaks after backdate for user=%s, habit_id=%s, from_date=%s",
                user_id, habit_id, backdate_date,
            )
            today = get_user_today(user_timezone)
            await run_in_transaction(self._recalculate_by_id_sync, habit_id, backdate_date, today)
            logger.info("Streak recalculation completed")

        return run_sync_or_async(_impl())

    def revert_habit_completion(
        self,
        user_telegram_id: str,
        habit_id: int | str
    ) -> HabitRevertResult | Awaitable[HabitRevertResult]:
        """Revert the most recent habit completion for a given habit."""

        async def _impl() -> HabitRevertResult:
            logger.info(
                "Reverting habit completion for user=%s, habit_id=%s",
                user_telegram_id,
                habit_id,
            )

            user = await maybe_await(
                self.user_repo.get_by_telegram_id(user_telegram_id)
            )
            if not user:
                logger.error(
                    "User with telegram_id %s not found for revert",
                    user_telegram_id,
                )
                raise ValueError(
                    f"User with telegram_id {user_telegram_id} not found"
                )

            if not user.is_active:
                logger.error("User %s is inactive, cannot revert", user_telegram_id)
                raise ValueError("User is inactive")

            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            if not habit or not getattr(habit, "active", True):
                logger.error(
                    "Habit '%s' not found or inactive for revert",
                    habit_id,
                )
                raise ValueError(f"Habit '{habit_id}' not found")

            log = await maybe_await(
                self.habit_log_repo.get_last_log_for_habit(user.id, habit.id)
            )
            if not log:
                logger.warning(
                    "No habit completion found to revert for user=%s, habit=%s",
                    user.id,
                    habit.id,
                )
                raise ValueError("No habit completion found to revert")

            # Store log info before deletion (for audit log)
            log_id_before_deletion = log.id
            reward_before_deletion = log.reward
            reward_name = log.reward.name if log.reward else None
            reward_reverted = bool(log.got_reward and log.reward_id)
            reward_progress_model: RewardProgressModel | None = None

            try:
                progress, reward_name = await self._revert_log_transaction(
                    log=log,
                    user_id=user.id,
                    reward_reverted=reward_reverted,
                    reward_name=reward_name,
                )
            except ValueError as error:
                logger.error(
                    "Failed to delete habit log %s for user %s: %s",
                    log.id,
                    user.id,
                    error,
                )
                raise

            await cache.adelete(streak_service.cache_key(user.id))

            if progress:
                reward_progress_model = RewardProgressModel.model_validate(
                    progress,
                    from_attributes=True,
                )
                reward_name = reward_name or getattr(progress.reward, "name", None)
            elif reward_reverted:
                logger.warning(
                    "Reward progress missing during revert; rolling back without progress snapshot"
                )

            logger.info(
                "Habit completion revert successful for user=%s, habit=%s",
                user.id,
                habit.id,
            )

            # Log habit revert to audit trail (always, not just when reward exists)
            revert_snapshot = {
                "habit_name": habit.name,
                "log_id": log_id_before_deletion,  # Store deleted log ID in snapshot
            }

            # Add reward info to snapshot if reward was reverted
            if reward_reverted and reward_name:
                revert_snapshot["reward_name"] = reward_name

            if progress:
                revert_snapshot["reward_progress"] = {
                    "pieces_earned": progress.pieces_earned,
                    "pieces_required": progress.get_pieces_required(),
                    "claimed": progress.claimed,
                }

            await maybe_await(
                self.audit_log_service.log_habit_revert(
                    user_id=user.id,
                    habit=habit,
                    reward=reward_before_deletion if reward_reverted else None,
                    habit_log=None,  # Don't pass deleted log (FK constraint)
                    progress_snapshot=revert_snapshot,
                )
            )

            # Notify connected WebSocket clients (non-blocking)
            _try_schedule_notify(user.id)

            return HabitRevertResult(
                habit_name=habit.name,
                reward_reverted=reward_reverted,
                reward_name=reward_name,
                reward_progress=reward_progress_model,
                success=True,
            )

        return run_sync_or_async(_impl())

    def revert_habit_completion_by_log_id(
        self,
        user_id: int | str,
        log_id: int | str
    ) -> HabitRevertResult | Awaitable[HabitRevertResult]:
        """Revert a specific habit completion by log ID.

        This method is used by the REST API to revert a specific log entry,
        unlike revert_habit_completion which reverts the most recent log.

        Args:
            user_id: User primary key (for ownership verification)
            log_id: HabitLog primary key to revert

        Returns:
            HabitRevertResult with revert details

        Raises:
            ValueError: If log not found or doesn't belong to user
        """

        async def _impl() -> HabitRevertResult:
            logger.info(
                "Reverting habit completion by log_id=%s for user=%s",
                log_id,
                user_id,
            )

            # Get the specific log by ID
            log = await maybe_await(self.habit_log_repo.get_by_id(log_id))
            if not log:
                logger.warning("Habit log %s not found for revert", log_id)
                raise ValueError(f"Habit log {log_id} not found")

            # Verify ownership
            if log.user_id != int(user_id):
                logger.warning(
                    "User %s attempted to revert log %s belonging to user %s",
                    user_id,
                    log_id,
                    log.user_id,
                )
                raise ValueError("Access denied")

            # Get habit for the response
            habit = await maybe_await(self.habit_repo.get_by_id(log.habit_id))
            if not habit:
                logger.error("Habit %s not found for log %s", log.habit_id, log_id)
                raise ValueError("Associated habit not found")

            # Store log info before deletion (for audit log)
            log_id_before_deletion = log.id
            reward_before_deletion = log.reward
            reward_name = log.reward.name if log.reward else None
            reward_reverted = bool(log.got_reward and log.reward_id)
            reward_progress_model: RewardProgressModel | None = None

            try:
                progress, reward_name = await self._revert_log_transaction(
                    log=log,
                    user_id=log.user_id,
                    reward_reverted=reward_reverted,
                    reward_name=reward_name,
                )
            except ValueError as error:
                logger.error(
                    "Failed to delete habit log %s for user %s: %s",
                    log.id,
                    log.user_id,
                    error,
                )
                raise

            await cache.adelete(streak_service.cache_key(log.user_id))

            if progress:
                reward_progress_model = RewardProgressModel.model_validate(
                    progress,
                    from_attributes=True,
                )
                reward_name = reward_name or getattr(progress.reward, "name", None)
            elif reward_reverted:
                logger.warning(
                    "Reward progress missing during revert; rolling back without progress snapshot"
                )

            logger.info(
                "Habit completion revert successful for log_id=%s, user=%s",
                log_id,
                log.user_id,
            )

            # Log habit revert to audit trail
            revert_snapshot = {
                "habit_name": habit.name,
                "log_id": log_id_before_deletion,
            }

            if reward_reverted and reward_name:
                revert_snapshot["reward_name"] = reward_name

            if progress:
                revert_snapshot["reward_progress"] = {
                    "pieces_earned": progress.pieces_earned,
                    "pieces_required": progress.get_pieces_required(),
                    "claimed": progress.claimed,
                }

            await maybe_await(
                self.audit_log_service.log_habit_revert(
                    user_id=log.user_id,
                    habit=habit,
                    reward=reward_before_deletion if reward_reverted else None,
                    habit_log=None,  # Don't pass deleted log (FK constraint)
                    progress_snapshot=revert_snapshot,
                )
            )

            # Notify connected WebSocket clients (non-blocking)
            _try_schedule_notify(log.user_id)

            return HabitRevertResult(
                habit_name=habit.name,
                reward_reverted=reward_reverted,
                reward_name=reward_name,
                reward_progress=reward_progress_model,
                success=True,
            )

        return run_sync_or_async(_impl())

    def get_habit_by_name(
        self,
        user_id: int | str,
        habit_name: str,
    ) -> Habit | None | Awaitable[Habit | None]:
        """Get habit by name for a specific user."""

        async def _impl() -> Habit | None:
            return await maybe_await(self.habit_repo.get_by_name(user_id, habit_name))

        return run_sync_or_async(_impl())

    def get_habit_by_id(
        self,
        user_id: int | str,
        habit_id: int | str,
    ) -> Habit | None | Awaitable[Habit | None]:
        """Get a single active habit by ID, verifying it belongs to the user."""

        async def _impl() -> Habit | None:
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            if not habit or not getattr(habit, "active", True):
                return None
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            if habit.user_id != user_pk:
                return None
            return habit

        return run_sync_or_async(_impl())

    def get_all_active_habits(self, user_id: int | str) -> list[Habit] | Awaitable[list[Habit]]:
        """Get all active habits for a specific user supporting sync tests and async handlers."""

        result = self.habit_repo.get_all_active(user_id)
        if inspect.isawaitable(result):
            return run_sync_or_async(result)
        return result

    def get_active_habits_pending_for_today(
        self,
        user_id: int | str,
        target_date: date | None = None,
    ) -> list[Habit] | Awaitable[list[Habit]]:
        """Return active habits that have not been completed today."""

        async def _impl() -> list[Habit]:
            habits = await maybe_await(self.habit_repo.get_all_active(user_id))
            if not habits:
                return []

            logs_today = await maybe_await(
                self.habit_log_repo.get_todays_logs_by_user(
                    user_id=user_id,
                    target_date=target_date,
                )
            )
            if not logs_today:
                return habits

            completed_habit_ids = {log.habit_id for log in logs_today}
            return [habit for habit in habits if habit.id not in completed_habit_ids]

        return run_sync_or_async(_impl())

    def log_habit_completion(
        self,
        user_id: str,
        habit_id: str,
        reward_id: str | None,
        streak_count: int,
        habit_weight: float,
        total_weight: float,
        user_timezone: str = 'UTC',
    ) -> HabitLog | Awaitable[HabitLog]:
        """Log a habit completion entry."""

        async def _impl() -> HabitLog:
            habit_log = HabitLog(
                user_id=user_id,
                habit_id=habit_id,
                timestamp=datetime.now(),
                reward_id=reward_id,
                got_reward=reward_id is not None,
                streak_count=streak_count,
                habit_weight=habit_weight,
                total_weight_applied=total_weight,
                last_completed_date=get_user_today(user_timezone),
            )
            return await maybe_await(self.habit_log_repo.create(habit_log))

        return run_sync_or_async(_impl())

    def get_user_habit_logs(
        self,
        user_telegram_id: str,
        limit: int = 50
    ) -> list[HabitLog] | Awaitable[list[HabitLog]]:
        """Get recent habit logs for a user."""

        async def _impl() -> list[HabitLog]:
            user = await maybe_await(
                self.user_repo.get_by_telegram_id(user_telegram_id)
            )
            if not user:
                raise ValueError(
                    f"User with telegram_id {user_telegram_id} not found"
                )

            return await maybe_await(
                self.habit_log_repo.get_logs_by_user(user.id, limit=limit)
            )

        return run_sync_or_async(_impl())

    def get_habit_completions_for_daterange(
        self,
        user_id: int | str,
        habit_id: int | str,
        start_date: date,
        end_date: date
    ) -> list[date] | Awaitable[list[date]]:
        """Get all dates with completions for a habit within a date range.

        Used to show which dates already have completions when presenting
        the date picker in the backdate flow.

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of dates that have completions for this habit
        """

        async def _impl() -> list[date]:
            logs = await maybe_await(
                self.habit_log_repo.get_logs_for_habit_in_daterange(
                    user_id, habit_id, start_date, end_date
                )
            )
            # Extract unique dates from logs
            return [log.last_completed_date for log in logs]

        return run_sync_or_async(_impl())


# Global service instance
habit_service = HabitService()
