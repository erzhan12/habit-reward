"""Habit completion orchestration service."""

import logging
import inspect
from datetime import datetime, date, timedelta
from typing import Awaitable
from contextlib import asynccontextmanager
from asgiref.sync import sync_to_async
from django.db import transaction
from src.core.repositories import (
    user_repository,
    habit_repository,
    habit_log_repository,
    reward_progress_repository
)
from src.core.models import Habit, HabitLog, RewardProgress
from src.services.streak_service import streak_service
from src.services.reward_service import reward_service
from src.services.audit_log_service import audit_log_service
from src.models.habit_completion_result import HabitCompletionResult
from src.models.habit_revert_result import HabitRevertResult
from src.models.reward_progress import RewardProgress as RewardProgressModel
from src.utils.async_compat import run_sync_or_async, maybe_await

# Configure logging
logger = logging.getLogger(__name__)


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
        self.audit_log_service = audit_log_service

    def _refresh_dependencies(self) -> None:
        """Rebind dependencies to allow patching in tests."""
        self.user_repo = user_repository
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.reward_progress_repo = reward_progress_repository
        self.streak_service = streak_service
        self.reward_service = reward_service
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
        target_date: date | None = None
    ) -> HabitCompletionResult | Awaitable[HabitCompletionResult]:
        """
        Main orchestration for habit completion.

        Flow:
        1. Verify user exists in Users table by telegram_id
        2. Get habit (from selection or NLP classification)
        3. Validate target_date (if backdating)
        4. Check for duplicate entries on target_date
        5. Pull habit weight from Habits table
        6. Calculate streak for target_date (or today if not backdating)
        7. Calculate total_weight multiplier
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

            # Default target_date to today if not specified
            if target_date is None:
                target_date = date.today()

            # Validate target_date for backdating
            today = date.today()
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

            habit_weight = habit.weight

            # Calculate streak for target_date
            if target_date == today:
                # Use normal streak calculation for today
                streak_count = await maybe_await(
                    self.streak_service.calculate_streak(user.id, habit.id)
                )
            else:
                # Use backdate-aware streak calculation
                streak_count = await maybe_await(
                    self.streak_service.calculate_streak_for_date(
                        user.id, habit.id, target_date
                    )
                )

            total_weight = self.reward_service.calculate_total_weight(
                habit_weight=habit_weight,
                streak_count=streak_count,
            )

            # Daily limit logic is now handled internally in select_reward()
            # based on each reward's max_daily_claims configuration
            selected_reward = await maybe_await(
                self.reward_service.select_reward(
                    total_weight=total_weight,
                    user_id=user.id,
                    exclude_reward_ids=[],  # No manual exclusion needed
                )
            )

            got_reward = selected_reward is not None

            # Wrap reward progress update and habit log creation in atomic transaction
            # This ensures both operations succeed or both are rolled back,
            # preventing orphaned progress entries with 0 pieces
            async with self._atomic():
                reward_progress = None
                if got_reward:
                    reward_progress = await maybe_await(
                        self.reward_service.update_reward_progress(
                            user_id=user.id,
                            reward_id=selected_reward.id,
                        )
                    )

                habit_log = HabitLog(
                    user_id=user.id,
                    habit_id=habit.id,
                    timestamp=datetime.now(),
                    reward_id=selected_reward.id if got_reward else None,
                    got_reward=got_reward,
                    streak_count=streak_count,
                    habit_weight=habit_weight,
                    total_weight_applied=total_weight,
                    last_completed_date=target_date,  # Use target_date for backdating
                )
                await maybe_await(self.habit_log_repo.create(habit_log))

            # If backdating, recalculate streaks for all subsequent logs
            if target_date < today:
                logger.info(
                    "Backdating detected (target_date=%s < today=%s). Recalculating subsequent streaks.",
                    target_date,
                    today
                )
                await maybe_await(
                    self.recalculate_streaks_after_backdate(
                        user.id, habit.id, target_date
                    )
                )

            # Log habit completion to audit trail (after transaction commits)
            snapshot = {
                "habit_name": habit.name,
                "streak_count": streak_count,
                "total_weight": total_weight,
                "selected_reward_name": selected_reward.name if got_reward else None,
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

            return HabitCompletionResult(
                habit_confirmed=True,
                habit_name=habit.name,
                reward=selected_reward if got_reward else None,
                streak_count=streak_count,
                cumulative_progress=reward_progress,
                motivational_quote=None,
                got_reward=got_reward,
                total_weight_applied=total_weight,
            )

        return run_sync_or_async(_impl())

    def recalculate_streaks_after_backdate(
        self,
        user_id: int | str,
        habit_id: int | str,
        backdate_date: date
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
                user_id,
                habit_id,
                backdate_date
            )

            # Get habit for grace days and exempt weekdays
            habit = await maybe_await(self.habit_repo.get_by_id(habit_id))
            if not habit:
                logger.error("Habit %s not found for streak recalculation", habit_id)
                return

            # Get all logs from backdate_date onwards, sorted by completion date
            today = date.today()
            logs = await maybe_await(
                self.habit_log_repo.get_logs_for_habit_in_daterange(
                    user_id, habit_id, backdate_date, today
                )
            )

            if not logs:
                logger.info("No logs found for recalculation")
                return

            logger.info(f"Recalculating {len(logs)} logs from {backdate_date} to {today}")

            # Recalculate each log's streak in chronological order
            for i, log in enumerate(logs):
                if i == 0:
                    # First log in the sequence - calculate streak based on previous logs
                    new_streak = await maybe_await(
                        self.streak_service.calculate_streak_for_date(
                            user_id, habit_id, log.last_completed_date
                        )
                    )
                else:
                    # Calculate based on previous log in this sequence
                    prev_log = logs[i - 1]
                    prev_date = prev_log.last_completed_date
                    current_date = log.last_completed_date
                    day_before_current = current_date - timedelta(days=1)

                    # Check if consecutive
                    if prev_date == day_before_current:
                        new_streak = prev_log.streak_count + 1
                    elif prev_date < day_before_current:
                        # Gap exists - check grace days and exempt weekdays
                        current_check_date = prev_date + timedelta(days=1)
                        missed_days = 0

                        while current_check_date < current_date:
                            weekday = current_check_date.isoweekday()
                            if weekday not in habit.exempt_weekdays:
                                missed_days += 1
                            current_check_date += timedelta(days=1)

                        if missed_days <= habit.allowed_skip_days:
                            new_streak = prev_log.streak_count + 1
                        else:
                            new_streak = 1
                    else:
                        # This shouldn't happen (logs are sorted by date)
                        logger.warning(
                            "Unexpected log order: prev_date=%s >= current_date=%s",
                            prev_date,
                            current_date
                        )
                        new_streak = 1

                # Update log if streak changed
                if log.streak_count != new_streak:
                    logger.info(
                        "Updating log %s: date=%s, old_streak=%s, new_streak=%s",
                        log.id,
                        log.last_completed_date,
                        log.streak_count,
                        new_streak
                    )
                    await maybe_await(
                        self.habit_log_repo.update(log.id, {"streak_count": new_streak})
                    )
                else:
                    logger.debug(
                        "Log %s streak unchanged: date=%s, streak=%s",
                        log.id,
                        log.last_completed_date,
                        log.streak_count
                    )

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
        total_weight: float
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
                last_completed_date=date.today(),
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
