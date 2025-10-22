"""Habit completion orchestration service."""

import logging
from datetime import datetime, date
from src.airtable.repositories import (
    user_repository,
    habit_repository,
    habit_log_repository
)
from src.services.streak_service import streak_service
from src.services.reward_service import reward_service
from src.models.habit import Habit
from src.models.habit_log import HabitLog
from src.models.habit_completion_result import HabitCompletionResult
from src.models.reward import RewardType

# Configure logging
logger = logging.getLogger(__name__)


class HabitService:
    """Service for orchestrating habit completion flow."""

    def __init__(self):
        """Initialize HabitService with repositories and services."""
        self.user_repo = user_repository
        self.habit_repo = habit_repository
        self.habit_log_repo = habit_log_repository
        self.streak_service = streak_service
        self.reward_service = reward_service

    def process_habit_completion(
        self,
        user_telegram_id: str,
        habit_name: str
    ) -> HabitCompletionResult:
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
        # 1. Verify user exists
        logger.info(f"Processing habit completion for user={user_telegram_id}, habit='{habit_name}'")
        user = self.user_repo.get_by_telegram_id(user_telegram_id)
        if not user:
            logger.error(f"User with telegram_id {user_telegram_id} not found")
            raise ValueError(f"User with telegram_id {user_telegram_id} not found")

        # 2. Get habit
        habit = self.habit_repo.get_by_name(habit_name)
        if not habit:
            logger.error(f"Habit '{habit_name}' not found")
            raise ValueError(f"Habit '{habit_name}' not found")

        # 3. Pull habit weight
        habit_weight = habit.weight

        # 4. Calculate current streak
        streak_count = self.streak_service.calculate_streak(user.id, habit.id)

        # 5. Calculate total_weight multiplier
        total_weight = self.reward_service.calculate_total_weight(
            habit_weight=habit_weight,
            streak_count=streak_count
        )

        # 6. Get today's awarded rewards to prevent duplicates
        todays_awarded_rewards = self.reward_service.get_todays_awarded_rewards(user.id)
        logger.info(f"Today's awarded rewards for user={user.id}: {len(todays_awarded_rewards)} rewards")

        # 7. Fetch active rewards and run weighted random draw (excluding today's awards)
        selected_reward = self.reward_service.select_reward(
            total_weight=total_weight,
            user_id=user.id,
            exclude_reward_ids=todays_awarded_rewards
        )

        # Determine if user got a meaningful reward (not "none" type)
        # This boolean flag is crucial for:
        # 1. Preventing duplicate rewards on the same day
        # 2. Progress tracking for cumulative rewards
        # 3. Analytics and reward rate calculations
        # 4. User feedback and experience
        got_reward = selected_reward.type != RewardType.NONE

        # 8. Update reward progress for ANY reward (unified system)
        reward_progress = None
        if got_reward:
            reward_progress = self.reward_service.update_reward_progress(
                user_id=user.id,
                reward_id=selected_reward.id
            )

        # 9. Log entry to Habit Log
        habit_log = HabitLog(
            user_id=user.id,
            habit_id=habit.id,
            timestamp=datetime.now(),
            reward_id=selected_reward.id if got_reward else None,
            got_reward=got_reward,
            streak_count=streak_count,
            habit_weight=habit_weight,
            total_weight_applied=total_weight,
            last_completed_date=date.today()
        )
        self.habit_log_repo.create(habit_log)

        # 10. Return response object
        return HabitCompletionResult(
            habit_confirmed=True,
            habit_name=habit.name,
            reward=selected_reward if got_reward else None,
            streak_count=streak_count,
            cumulative_progress=reward_progress,
            motivational_quote=None,  # Can be added later
            got_reward=got_reward,
            total_weight_applied=total_weight
        )

    def get_habit_by_name(self, habit_name: str) -> Habit | None:
        """
        Get habit by name.

        Args:
            habit_name: Name of the habit

        Returns:
            Habit object or None if not found
        """
        return self.habit_repo.get_by_name(habit_name)

    def get_all_active_habits(self) -> list[Habit]:
        """
        Get all active habits.

        Returns:
            List of active Habit objects
        """
        return self.habit_repo.get_all_active()

    def log_habit_completion(
        self,
        user_id: str,
        habit_id: str,
        reward_id: str | None,
        streak_count: int,
        habit_weight: float,
        total_weight: float
    ) -> HabitLog:
        """
        Log a habit completion entry.

        Args:
            user_id: Airtable record ID of the user
            habit_id: Airtable record ID of the habit
            reward_id: Airtable record ID of the reward (or None)
            streak_count: Current streak count
            habit_weight: Habit weight at time of completion
            total_weight: Total calculated weight

        Returns:
            Created HabitLog object
        """
        habit_log = HabitLog(
            user_id=user_id,
            habit_id=habit_id,
            timestamp=datetime.now(),
            reward_id=reward_id,
            got_reward=reward_id is not None,
            streak_count=streak_count,
            habit_weight=habit_weight,
            total_weight_applied=total_weight,
            last_completed_date=date.today()
        )
        return self.habit_log_repo.create(habit_log)

    def get_user_habit_logs(self, user_telegram_id: str, limit: int = 50) -> list[HabitLog]:
        """
        Get recent habit logs for a user.

        Args:
            user_telegram_id: Telegram ID of the user
            limit: Maximum number of logs to return

        Returns:
            List of HabitLog objects
        """
        user = self.user_repo.get_by_telegram_id(user_telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {user_telegram_id} not found")

        return self.habit_log_repo.get_logs_by_user(user.id, limit=limit)


# Global service instance
habit_service = HabitService()
