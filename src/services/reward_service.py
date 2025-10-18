"""Reward selection and management service with weighted random selection."""

import random
import logging
from src.airtable.repositories import reward_repository, reward_progress_repository
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

    def calculate_total_weight(
        self,
        habit_weight: float,
        user_weight: float,
        streak_count: int
    ) -> float:
        """
        Calculate total weight multiplier for reward selection.

        Formula: total_weight = habit_weight × user_weight × streak_multiplier
        Where: streak_multiplier = 1 + (streak_count × 0.1)

        Args:
            habit_weight: Weight of the habit
            user_weight: Weight/multiplier of the user
            streak_count: Current streak count for this habit

        Returns:
            Total weight multiplier
        """
        streak_multiplier = 1 + (streak_count * settings.streak_multiplier_rate)
        total_weight = habit_weight * user_weight * streak_multiplier
        return total_weight

    def select_reward(self, total_weight: float) -> Reward:
        """
        Perform weighted random reward selection.

        Algorithm:
        1. Fetch all active rewards (including type="none" and cumulative)
        2. Calculate adjusted weights for each reward using total_weight multiplier
        3. Perform weighted random selection using random.choices()
        4. Return selected reward

        Args:
            total_weight: Total weight multiplier from calculate_total_weight()

        Returns:
            Selected reward (may be type="none")
        """
        logger.info(f"Selecting reward with total_weight={total_weight}")
        rewards = self.reward_repo.get_all_active()

        if not rewards:
            logger.warning("No active rewards found, returning default 'none' reward")
            # Create a default "none" reward if no rewards exist
            return Reward(
                name="No reward",
                weight=1.0,
                type=RewardType.NONE,
                is_cumulative=False
            )

        logger.debug(f"Found {len(rewards)} active rewards")
        # Calculate adjusted weights
        adjusted_weights = [reward.weight * total_weight for reward in rewards]

        # Perform weighted random selection
        selected_reward = random.choices(rewards, weights=adjusted_weights, k=1)[0]
        logger.info(f"Selected reward: {selected_reward.name} (type: {selected_reward.type})")

        return selected_reward

    def update_cumulative_progress(
        self,
        user_id: str,
        reward_id: str
    ) -> RewardProgress:
        """
        Update progress for a cumulative reward.

        Algorithm:
        1. Get or create reward progress entry
        2. Increment pieces_earned by 1
        3. Check if pieces_earned >= pieces_required
        4. If met: update status to "⏳ Achieved" and set actionable_now = True
        5. Otherwise: keep status as "🕒 Pending"
        6. Update progress_percent
        7. Save and return progress

        Args:
            user_id: Airtable record ID of the user
            reward_id: Airtable record ID of the reward

        Returns:
            Updated RewardProgress object
        """
        # Get or create progress
        logger.info(f"Updating cumulative progress for user={user_id}, reward={reward_id}")
        progress = self.progress_repo.get_by_user_and_reward(user_id, reward_id)
        reward = self.reward_repo.get_by_id(reward_id)

        if not reward or not reward.is_cumulative:
            logger.error(f"Reward {reward_id} is not cumulative or doesn't exist")
            raise ValueError("Reward is not cumulative or doesn't exist")

        if progress is None:
            # Create new progress entry
            progress = RewardProgress(
                user_id=user_id,
                reward_id=reward_id,
                pieces_earned=0,
                status=RewardStatus.PENDING,
                actionable_now=False,
                pieces_required=reward.pieces_required
            )
            progress = self.progress_repo.create(progress)

        # Increment pieces earned
        new_pieces = progress.pieces_earned + 1

        # Check if reward is achieved
        if reward.pieces_required and new_pieces >= reward.pieces_required:
            new_status = RewardStatus.ACHIEVED
            actionable = True
        else:
            new_status = progress.status  # Keep current status
            actionable = False

        # Update in database
        updated_progress = self.progress_repo.update(
            progress.id,
            {
                "pieces_earned": new_pieces,
                "status": new_status.value,
                "actionable_now": actionable
            }
        )

        return updated_progress

    def mark_reward_completed(self, user_id: str, reward_id: str) -> RewardProgress:
        """
        Mark a reward as completed (claimed by user).

        Args:
            user_id: Airtable record ID of the user
            reward_id: Airtable record ID of the reward

        Returns:
            Updated RewardProgress object
        """
        progress = self.progress_repo.get_by_user_and_reward(user_id, reward_id)

        if not progress:
            raise ValueError("Reward progress not found")

        if progress.status != RewardStatus.ACHIEVED:
            raise ValueError("Reward must be in 'Achieved' status to be marked completed")

        updated_progress = self.progress_repo.update(
            progress.id,
            {
                "status": RewardStatus.COMPLETED.value,
                "actionable_now": False
            }
        )

        return updated_progress

    def set_reward_status(
        self,
        user_id: str,
        reward_id: str,
        status: RewardStatus
    ) -> RewardProgress:
        """
        Manually set reward status (admin function).

        Args:
            user_id: Airtable record ID of the user
            reward_id: Airtable record ID of the reward
            status: New status to set

        Returns:
            Updated RewardProgress object
        """
        progress = self.progress_repo.get_by_user_and_reward(user_id, reward_id)

        if not progress:
            raise ValueError("Reward progress not found")

        actionable = status == RewardStatus.ACHIEVED

        updated_progress = self.progress_repo.update(
            progress.id,
            {
                "status": status.value,
                "actionable_now": actionable
            }
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
