"""Reward selection and management service with weighted random selection."""

import random
import logging
from enum import Enum
from typing import Awaitable
from types import SimpleNamespace, MethodType

from src.core.repositories import reward_repository, reward_progress_repository, habit_log_repository
from src.core.models import Reward, RewardProgress
from src.models.reward_progress import RewardProgress as RewardProgressModel
from django.conf import settings
from src.utils.async_compat import run_sync_or_async, maybe_await

# Import enums from Django models
RewardType = Reward.RewardType
RewardStatus = RewardProgress.RewardStatus

# Configure logging
logger = logging.getLogger(__name__)


class RewardService:
    """Service for reward selection and cumulative reward progress tracking."""

    def __init__(self):
        """Initialize RewardService with repositories."""
        self.reward_repo = reward_repository
        self.progress_repo = reward_progress_repository
        self.habit_log_repo = habit_log_repository

    def calculate_total_weight(
        self,
        habit_weight: int,
        streak_count: int
    ) -> float:
        """
        Calculate total weight multiplier for reward selection.

        Formula: total_weight = habit_weight × streak_multiplier
        Where: streak_multiplier = 1 + (streak_count × 0.1)

        Args:
            habit_weight: Weight of the habit (integer 1-100)
            streak_count: Current streak count for this habit

        Returns:
            Total weight multiplier
        """
        streak_multiplier = 1 + (streak_count * settings.STREAK_MULTIPLIER_RATE)
        total_weight = habit_weight * streak_multiplier
        return total_weight

    def select_reward(
        self,
        total_weight: float,
        user_id: str | None = None,
        exclude_reward_ids: list[str] | None = None
    ) -> Reward | None | Awaitable[Reward | None]:
        """Perform weighted random reward selection with implicit 50% 'no reward' probability.

        Returns:
            Reward | None: Selected reward, or None for "no reward" outcome
        """

        async def _impl() -> Reward | None:
            logger.info(
                "Selecting reward with total_weight=%s, user_id=%s",
                total_weight,
                user_id,
            )
            if exclude_reward_ids:
                logger.info(
                    "Excluding %s rewards from selection",
                    len(exclude_reward_ids),
                )

            # user_id is required now since rewards are user-specific
            if not user_id:
                logger.error("user_id is required for select_reward")
                return None

            rewards = await maybe_await(self.reward_repo.get_all_active(user_id))

            if not rewards:
                logger.warning("No active rewards found for user %s, returning None (no reward)", user_id)
                return None

            logger.debug("Found %s active rewards", len(rewards))

            if exclude_reward_ids:
                original_count = len(rewards)
                rewards = [r for r in rewards if r.id not in exclude_reward_ids]
                logger.info(
                    "After exclusion: %s rewards remaining (filtered out %s)",
                    len(rewards),
                    original_count - len(rewards),
                )

            if not rewards:
                logger.warning("All rewards excluded, returning None (no reward)")
                return None

            # Apply user-specific filters if user_id is provided
            if user_id:
                logger.info("Applying user-specific filters for user=%s", user_id)

                # Fetch user's reward progress
                progress_list = await maybe_await(
                    self.progress_repo.get_all_by_user(user_id)
                )
                progress_by_reward_id = {p.reward_id: p for p in progress_list}
                logger.debug("Found %s progress records for user", len(progress_list))

                eligible_rewards = []
                excluded_completed = []
                excluded_daily_limit = []
                excluded_legacy_none = []

                for reward in rewards:
                    # Filter 0: Exclude legacy 'none' type rewards (transition safety)
                    if reward.type == "none":
                        excluded_legacy_none.append(reward.name)
                        logger.debug(
                            "Excluding %s - legacy 'none' type reward",
                            reward.name,
                        )
                        if getattr(reward, "active", False) and hasattr(self.reward_repo, "update"):
                            try:
                                await maybe_await(
                                    self.reward_repo.update(reward.id, {"active": False})
                                )
                            except Exception:
                                logger.warning(
                                    "Failed to deactivate legacy 'none' reward %s",
                                    getattr(reward, "id", None),
                                )
                        continue

                    progress = progress_by_reward_id.get(reward.id)

                    # Filter 1: Check if reward is already completed
                    if progress and progress.pieces_earned >= reward.pieces_required:
                        excluded_completed.append(reward.name)
                        logger.debug(
                            "Excluding %s - already completed (%s/%s pieces)",
                            reward.name,
                            progress.pieces_earned,
                            reward.pieces_required,
                        )
                        continue

                    # Filter 2: Check daily limit
                    if reward.max_daily_claims is not None and reward.max_daily_claims > 0:
                        today_count = await maybe_await(
                            self.get_todays_pieces_by_reward(user_id, reward.id)
                        )
                        if today_count >= reward.max_daily_claims:
                            excluded_daily_limit.append(
                                f"{reward.name} ({today_count}/{reward.max_daily_claims})"
                            )
                            logger.debug(
                                "Excluding %s - daily limit reached (%s/%s pieces today)",
                                reward.name,
                                today_count,
                                reward.max_daily_claims,
                            )
                            continue

                    # Reward passed all filters
                    eligible_rewards.append(reward)

                if excluded_legacy_none:
                    logger.info(
                        "Excluded %s legacy 'none' type rewards: %s",
                        len(excluded_legacy_none),
                        ", ".join(excluded_legacy_none),
                    )

                if excluded_completed:
                    logger.info(
                        "Excluded %s completed rewards: %s",
                        len(excluded_completed),
                        ", ".join(excluded_completed),
                    )

                if excluded_daily_limit:
                    logger.info(
                        "Excluded %s rewards due to daily limit: %s",
                        len(excluded_daily_limit),
                        ", ".join(excluded_daily_limit),
                    )

                rewards = eligible_rewards

                if not rewards:
                    logger.warning(
                        "No eligible rewards remain after filtering (legacy none: %s, completed: %s, daily limit: %s)",
                        len(excluded_legacy_none),
                        len(excluded_completed),
                        len(excluded_daily_limit),
                    )
                    return None

            # Calculate reward weights
            reward_weights = [reward.weight * total_weight for reward in rewards]

            # Calculate implicit "no reward" weight for 50% probability
            # no_reward_weight = 1.0 * sum(reward_weights) ensures:
            # P(no_reward) = sum(weights) / (sum(weights) + sum(weights)) = 0.5
            # This 50% split doesn't depend on streak multiplier (both sides scale equally)
            no_reward_weight = 1.0 * sum(reward_weights)

            # Perform weighted selection including implicit "no reward" option
            population = rewards + [None]
            weights = reward_weights + [no_reward_weight]

            selected = random.choices(population, weights=weights, k=1)[0]

            if selected is None:
                logger.info("Selected: None (no reward)")
            else:
                logger.info(
                    "Selected reward: %s (type: %s)",
                    selected.name,
                    selected.type,
                )

            return selected

        return run_sync_or_async(_impl())

    def get_todays_awarded_rewards(self, user_id: str) -> list[str] | Awaitable[list[str]]:
        """Get list of reward IDs that were already awarded today."""

        async def _impl() -> list[str]:
            logger.info("Fetching today's awarded rewards for user=%s", user_id)

            todays_logs = await maybe_await(
                self.habit_log_repo.get_todays_logs_by_user(user_id)
            )

            awarded_reward_ids = [
                log.reward_id
                for log in todays_logs
                if log.got_reward and log.reward_id
            ]

            logger.info(
                "Found %s rewards awarded today for user=%s",
                len(awarded_reward_ids),
                user_id,
            )
            logger.debug("Today's awarded reward IDs: %s", awarded_reward_ids)
            return awarded_reward_ids

        return run_sync_or_async(_impl())

    def get_todays_pieces_by_reward(
        self,
        user_id: str,
        reward_id: str
    ) -> int | Awaitable[int]:
        """
        Count how many pieces of a specific reward were awarded today.

        This counts ALL pieces awarded today from habit logs, regardless of
        whether they have been claimed or not. This prevents users from
        bypassing daily limits by claiming between completions.

        Args:
            user_id: User ID
            reward_id: Reward ID

        Returns:
            Number of pieces awarded today for this reward (claimed or unclaimed)
        """

        async def _impl() -> int:
            logger.debug(
                "Counting today's pieces (all) for user=%s, reward=%s",
                user_id,
                reward_id,
            )

            # Get today's logs for this user
            todays_logs = await maybe_await(
                self.habit_log_repo.get_todays_logs_by_user(user_id)
            )

            # Count logs where this specific reward was awarded
            # This includes both claimed and unclaimed pieces to prevent bypass
            count = sum(
                1 for log in todays_logs
                if log.got_reward and log.reward_id == reward_id
            )

            logger.debug(
                "Found %s pieces awarded today for user=%s, reward=%s (including claimed)",
                count,
                user_id,
                reward_id,
            )
            return count

        return run_sync_or_async(_impl())

    def update_reward_progress(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress | Awaitable[RewardProgress]:
        """Update progress for any reward (unified system)."""

        async def _impl() -> RewardProgress:
            logger.info(
                "Updating reward progress for user=%s, reward=%s",
                user_id,
                reward_id,
            )
            progress = await maybe_await(
                self.progress_repo.get_by_user_and_reward(user_id, reward_id)
            )
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))

            if not reward:
                logger.error("Reward %s doesn't exist", reward_id)
                raise ValueError("Reward doesn't exist")

            if progress is None:
                progress = await maybe_await(
                    self.progress_repo.create(
                        SimpleNamespace(
                            user_id=user_id,
                            reward_id=reward_id,
                            pieces_earned=0,
                            claimed=False,
                        )
                    )
                )

            progress = self._coerce_progress(progress)
            current_status = progress.get_status()

            if current_status == RewardStatus.ACHIEVED:
                logger.info(
                    "Reward %s already achieved for user %s, skipping increment",
                    reward_id,
                    user_id,
                )
                return progress

            updates: dict[str, object] = {}
            if current_status == RewardStatus.CLAIMED:
                logger.info(
                    "Reward %s was claimed for user %s, resetting claimed flag",
                    reward_id,
                    user_id,
                )
                updates["claimed"] = False

            new_pieces = progress.pieces_earned + 1
            updates["pieces_earned"] = new_pieces

            updated_progress = await maybe_await(
                self.progress_repo.update(progress.id, updates)
            )

            return self._coerce_progress(updated_progress)

        return run_sync_or_async(_impl())

    def mark_reward_claimed(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress | Awaitable[RewardProgress]:
        """Mark a reward as claimed by user and reset the counter.

        For non-recurring rewards (is_recurring=False), also deactivates the reward
        after claiming.
        """

        async def _impl() -> RewardProgress:
            progress = await maybe_await(
                self.progress_repo.get_by_user_and_reward(user_id, reward_id)
            )

            if not progress:
                raise ValueError("Reward progress not found")

            current_status = progress.get_status()

            if current_status != RewardStatus.ACHIEVED:
                raise ValueError("Reward must be in 'Achieved' status to be claimed")

            # Get reward to check is_recurring
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))
            if not reward:
                raise ValueError("Reward not found")

            # Update progress (reset pieces and mark claimed)
            updated_progress = await maybe_await(
                self.progress_repo.update(
                    progress.id,
                    {
                        "claimed": True,
                        "pieces_earned": 0,  # Reset counter for fresh start
                    },
                )
            )

            # Auto-deactivate non-recurring rewards
            if not reward.is_recurring:
                await maybe_await(
                    self.reward_repo.update(reward_id, {"active": False})
                )
                logger.info(
                    "Auto-deactivated non-recurring reward %s for user %s",
                    reward_id,
                    user_id,
                )

            logger.info(
                "Marked reward %s as claimed for user %s and reset pieces_earned to 0",
                reward_id,
                user_id,
            )

            return self._coerce_progress(updated_progress)

        return run_sync_or_async(_impl())


    def get_active_rewards(self, user_id: int | str) -> list[Reward] | Awaitable[list[Reward]]:
        """Get all active rewards for a specific user."""

        async def _impl() -> list[Reward]:
            return await maybe_await(self.reward_repo.get_all_active(user_id))

        return run_sync_or_async(_impl())

    def create_reward(
        self,
        *,
        user_id: int | str,
        name: str,
        reward_type: RewardType | str,
        weight: float,
        pieces_required: int,
        piece_value: float | None = None,
        is_recurring: bool = True
    ) -> Reward | Awaitable[Reward]:
        """Create a new reward after performing validation checks."""

        async def _impl() -> Reward:
            logger.info(
                "Creating reward for user=%s name=%s type=%s weight=%s pieces_required=%s piece_value=%s is_recurring=%s",
                user_id,
                name,
                reward_type,
                weight,
                pieces_required,
                piece_value,
                is_recurring,
            )

            existing = await maybe_await(self.reward_repo.get_by_name(user_id, name))
            if existing:
                logger.warning(
                    "Reward creation blocked: duplicate name '%s' for user %s",
                    name,
                    user_id,
                )
                raise ValueError("Reward name already exists")

            reward_type_value = (
                reward_type.value
                if isinstance(reward_type, Enum)
                else reward_type
            )

            data: dict[str, object] = {
                "user_id": user_id,
                "name": name,
                "type": reward_type_value,
                "weight": weight,
                "pieces_required": pieces_required,
                "is_recurring": is_recurring,
            }

            if piece_value is not None:
                data["piece_value"] = piece_value

            reward = await maybe_await(self.reward_repo.create(data))
            logger.info(
                "Reward '%s' created with id=%s for user %s",
                reward.name,
                getattr(reward, "id", None),
                user_id,
            )
            return reward

        return run_sync_or_async(_impl())

    def get_user_reward_progress(
        self,
        user_id: str
    ) -> list[RewardProgress] | Awaitable[list[RewardProgress]]:
        """Get all reward progress for a user."""

        async def _impl() -> list[RewardProgress]:
            results = await maybe_await(self.progress_repo.get_all_by_user(user_id))
            return [self._coerce_progress(r) for r in results]

        return run_sync_or_async(_impl())

    def get_actionable_rewards(
        self,
        user_id: str
    ) -> list[RewardProgress] | Awaitable[list[RewardProgress]]:
        """Get all achieved (actionable) rewards for a user."""

        async def _impl() -> list[RewardProgress]:
            results = await maybe_await(
                self.progress_repo.get_achieved_by_user(user_id)
            )
            return [self._coerce_progress(r) for r in results]

        return run_sync_or_async(_impl())

    def toggle_reward_active(
        self,
        user_id: str,
        reward_id: str,
        active: bool
    ) -> Reward | Awaitable[Reward]:
        """Toggle reward active status.

        Args:
            user_id: User ID (for ownership validation)
            reward_id: Reward ID
            active: New active status (True=activate, False=deactivate)

        Returns:
            Updated Reward instance

        Raises:
            ValueError: If reward not found or user doesn't own it
        """

        async def _impl() -> Reward:
            # Validate reward exists
            reward = await maybe_await(self.reward_repo.get_by_id(reward_id))
            if not reward:
                logger.error("Reward %s not found", reward_id)
                raise ValueError("Reward not found")

            # Validate ownership
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            reward_user_id = int(reward.user_id) if isinstance(reward.user_id, str) else reward.user_id
            if reward_user_id != user_id_int:
                logger.error(
                    "User %s attempted to toggle reward %s owned by user %s",
                    user_id,
                    reward_id,
                    reward.user_id
                )
                raise ValueError("You don't have permission to modify this reward")

            # Update active status
            updated_reward = await maybe_await(
                self.reward_repo.update(reward_id, {"active": active})
            )

            logger.info(
                "User %s toggled reward %s active status to %s",
                user_id,
                reward_id,
                active
            )

            return updated_reward

        return run_sync_or_async(_impl())


    @staticmethod
    def _coerce_progress(progress: RewardProgress) -> RewardProgress:
        """Ensure progress object exposes `get_status` and typed fields."""

        if hasattr(progress, "get_status"):
            return progress

        if hasattr(progress, "status"):
            progress.get_status = MethodType(
                lambda self: getattr(self, "status"),
                progress,
            )
            return progress

        required_attrs = ("user_id", "reward_id")
        if not all(hasattr(progress, attr) for attr in required_attrs):
            return progress

        return RewardProgressModel.model_validate(
            progress,
            from_attributes=True,
        )


# Global service instance
reward_service = RewardService()
