"""Habit completion orchestration service."""

import logging
import inspect
from datetime import datetime, date
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
from src.core.models import Reward, Habit, HabitLog, RewardProgress
from src.services.streak_service import streak_service
from src.services.reward_service import reward_service
from src.services.audit_log_service import audit_log_service
from src.models.habit_completion_result import HabitCompletionResult
from src.models.habit_revert_result import HabitRevertResult
from src.models.reward_progress import RewardProgress as RewardProgressModel
from src.utils.async_compat import run_sync_or_async, maybe_await

# Import RewardType from Django models
RewardType = Reward.RewardType

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
        habit_name: str
    ) -> HabitCompletionResult | Awaitable[HabitCompletionResult]:
        """
        Main orchestration for habit completion.

        Flow:
        1. Verify user exists in Users table by telegram_id
        2. Get habit (from selection or NLP classification)
        3. Pull habit weight from Habits table
        4. Calculate current streak for this specific habit
        5. Calculate total_weight multiplier
        6. Get today's awarded rewards (to prevent duplicate awards)
        7. Fetch all active rewards and run weighted random draw (excluding today's awards)
        8. If cumulative reward: update Reward Progress, check if achieved
        9. Log entry to Habit Log with all calculated values
        10. Return response object with habit confirmation, reward result, streak status

        Note: No reward (cumulative or non-cumulative) can be awarded twice in the same day.

        Args:
            user_telegram_id: Telegram ID of the user
            habit_name: Name of the habit to log

        Returns:
            HabitCompletionResult with all completion details

        Raises:
            ValueError: If user or habit not found
        """

        async def _impl() -> HabitCompletionResult:
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

            habit = await maybe_await(self.habit_repo.get_by_name(habit_name))
            if not habit:
                logger.error("Habit '%s' not found", habit_name)
                raise ValueError(f"Habit '{habit_name}' not found")

            habit_weight = habit.weight
            streak_count = await maybe_await(
                self.streak_service.calculate_streak(user.id, habit.id)
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

            got_reward = selected_reward.type != RewardType.NONE

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
                    last_completed_date=date.today(),
                )
                await maybe_await(self.habit_log_repo.create(habit_log))

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

            # Log reward revert to audit trail (if reward was reverted)
            if reward_reverted and log.reward:
                revert_snapshot = {
                    "habit_name": habit.name,
                    "reward_name": reward_name,
                }
                if progress:
                    revert_snapshot["reward_progress"] = {
                        "pieces_earned": progress.pieces_earned,
                        "pieces_required": progress.get_pieces_required(),
                        "claimed": progress.claimed,
                    }

                await maybe_await(
                    self.audit_log_service.log_reward_revert(
                        user_id=user.id,
                        reward=log.reward,
                        habit_log=log,
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
        habit_name: str,
    ) -> Habit | None | Awaitable[Habit | None]:
        """Get habit by name."""

        async def _impl() -> Habit | None:
            return await maybe_await(self.habit_repo.get_by_name(habit_name))

        return run_sync_or_async(_impl())

    def get_all_active_habits(self) -> list[Habit] | Awaitable[list[Habit]]:
        """Get all active habits supporting sync tests and async handlers."""

        result = self.habit_repo.get_all_active()
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
            habits = await maybe_await(self.habit_repo.get_all_active())
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


# Global service instance
habit_service = HabitService()
