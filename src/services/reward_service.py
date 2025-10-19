"""Reward selection and management service with weighted random selection."""

import random
import logging
from src.airtable.repositories import reward_repository, reward_progress_repository, habit_log_repository
from src.models.reward import Reward, RewardType
from src.models.reward_progress import RewardProgress, RewardStatus
from src.config import settings

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
        streak_multiplier = 1 + (streak_count * settings.streak_multiplier_rate)
        total_weight = habit_weight * streak_multiplier
        return total_weight

    def select_reward(
        self,
        total_weight: float,
        user_id: str | None = None,
        exclude_reward_ids: list[str] | None = None
    ) -> Reward:
        """
        Perform weighted random reward selection.

        Algorithm:
        1. Fetch all active rewards (including type="none" and cumulative)
        2. Filter out any rewards in exclude_reward_ids list
        3. Calculate adjusted weights for each reward using total_weight multiplier
        4. Perform weighted random selection using random.choices()
        5. Return selected reward

        Args:
            total_weight: Total weight multiplier from calculate_total_weight()
            user_id: Optional user ID for logging purposes
            exclude_reward_ids: Optional list of reward IDs to exclude from selection

        Returns:
            Selected reward (may be type="none")
        """
        logger.info(f"Selecting reward with total_weight={total_weight}, user_id={user_id}")
        if exclude_reward_ids:
            logger.info(f"Excluding {len(exclude_reward_ids)} rewards from selection")

        rewards = self.reward_repo.get_all_active()

        if not rewards:
            logger.warning("No active rewards found, returning default 'none' reward")
            # Create a default "none" reward if no rewards exist
            return Reward(
                name="No reward",
                weight=1.0,
                type=RewardType.NONE,
                pieces_required=1
            )

        logger.debug(f"Found {len(rewards)} active rewards")

        # Filter out excluded rewards
        if exclude_reward_ids:
            original_count = len(rewards)
            rewards = [r for r in rewards if r.id not in exclude_reward_ids]
            logger.info(f"After exclusion: {len(rewards)} rewards remaining (filtered out {original_count - len(rewards)})")

        # If all rewards are excluded, return "none" reward
        if not rewards:
            logger.warning("All rewards excluded, returning 'none' reward")
            return Reward(
                name="No reward",
                weight=1.0,
                type=RewardType.NONE,
                pieces_required=1
            )

        # Calculate adjusted weights
        adjusted_weights = [reward.weight * total_weight for reward in rewards]

        # Perform weighted random selection
        selected_reward = random.choices(rewards, weights=adjusted_weights, k=1)[0]
        logger.info(f"Selected reward: {selected_reward.name} (type: {selected_reward.type})")

        return selected_reward

    def get_todays_awarded_rewards(self, user_id: str) -> list[str]:
        """
        Get list of reward IDs that were already awarded today.

        This ensures no reward (cumulative or non-cumulative) can be awarded
        multiple times in the same day.

        Args:
            user_id: Airtable record ID of the user

        Returns:
            List of reward IDs that were awarded today
        """
        logger.info(f"Fetching today's awarded rewards for user={user_id}")

        # Get today's logs for this user
        todays_logs = self.habit_log_repo.get_todays_logs_by_user(user_id)

        # Filter for entries where a reward was actually awarded
        awarded_reward_ids = []
        for log in todays_logs:
            if log.got_reward and log.reward_id:
                awarded_reward_ids.append(log.reward_id)

        logger.info(f"Found {len(awarded_reward_ids)} rewards awarded today for user={user_id}")
        logger.debug(f"Today's awarded reward IDs: {awarded_reward_ids}")

        return awarded_reward_ids

    def update_reward_progress(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress:
        """
        Update progress for any reward (unified system).

        Algorithm:
        1. Get or create reward progress entry
        2. Increment pieces_earned by 1
        3. Airtable formula automatically calculates status:
           - If pieces_earned >= pieces_required: status = "⏳ Achieved"
           - Otherwise: status = "🕒 Pending"
        4. Save and return progress

        Args:
            user_id: Airtable record ID of the user
            reward_id: Airtable record ID of the reward

        Returns:
            Updated RewardProgress object
        """
        # Get or create progress
        logger.info(f"Updating reward progress for user={user_id}, reward={reward_id}")
        progress = self.progress_repo.get_by_user_and_reward(user_id, reward_id)
        reward = self.reward_repo.get_by_id(reward_id)

        if not reward:
            logger.error(f"Reward {reward_id} doesn't exist")
            raise ValueError("Reward doesn't exist")

        if progress is None:
            # Create new progress entry
            progress = RewardProgress(
                user_id=user_id,
                reward_id=reward_id,
                pieces_earned=0,
                status=RewardStatus.PENDING,
                pieces_required=reward.pieces_required,
                claimed=False
            )
            progress = self.progress_repo.create(progress)

        # Increment pieces earned
        new_pieces = progress.pieces_earned + 1

        # Update in database - Airtable will automatically calculate status field
        updated_progress = self.progress_repo.update(
            progress.id,
            {
                "pieces_earned": new_pieces
            }
        )

        return updated_progress

    def mark_reward_claimed(self, user_id: str, reward_id: str) -> RewardProgress:
        """
        Mark a reward as claimed by user.

        Args:
            user_id: Airtable record ID of the user
            reward_id: Airtable record ID of the reward

        Returns:
            Updated RewardProgress object

        Raises:
            ValueError: If progress not found or reward not in ACHIEVED status
        """
        progress = self.progress_repo.get_by_user_and_reward(user_id, reward_id)

        if not progress:
            raise ValueError("Reward progress not found")

        if progress.status != RewardStatus.ACHIEVED:
            raise ValueError("Reward must be in 'Achieved' status to be claimed")

        # Update claimed field - Airtable formula will update status to "✅ Claimed"
        updated_progress = self.progress_repo.update(
            progress.id,
            {"claimed": True}
        )

        return updated_progress


    def get_active_rewards(self) -> list[Reward]:
        """
        Get all active rewards.

        Returns:
            List of active rewards
        """
        return self.reward_repo.get_all_active()

    def get_user_reward_progress(self, user_id: str) -> list[RewardProgress]:
        """
        Get all reward progress for a user.

        Args:
            user_id: Airtable record ID of the user

        Returns:
            List of RewardProgress objects
        """
        return self.progress_repo.get_all_by_user(user_id)

    def get_actionable_rewards(self, user_id: str) -> list[RewardProgress]:
        """
        Get all achieved (actionable) rewards for a user.

        Args:
            user_id: Airtable record ID of the user

        Returns:
            List of RewardProgress objects with status "⏳ Achieved"
        """
        return self.progress_repo.get_achieved_by_user(user_id)


# Global service instance
reward_service = RewardService()
