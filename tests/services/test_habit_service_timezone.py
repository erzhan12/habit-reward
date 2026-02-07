"""Tests for timezone-aware behavior in habit_service."""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import patch

from src.services.habit_service import HabitService
from src.models.user import User
from src.models.habit import Habit
from src.models.reward import Reward
from src.models.reward_progress import RewardProgress, RewardStatus
from src.models.habit_completion_result import HabitCompletionResult


@pytest.fixture
def habit_service():
    return HabitService()


@pytest.fixture
def mock_user():
    return User(
        id=123,
        telegram_id="123456789",
        name="Test User",
        is_active=True
    )


@pytest.fixture
def mock_habit():
    return Habit(
        id=1,
        name="Walking",
        weight=10,
        category="health",
        active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_reward():
    return Reward(
        id=1,
        name="Coffee",
        weight=10,
        pieces_required=1
    )


class TestHabitCompletionTimezone:
    """Test that process_habit_completion uses user_timezone correctly."""

    @patch('src.services.habit_service.get_user_today')
    @patch('src.services.habit_service.audit_log_service')
    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_default_target_date_uses_user_timezone(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        mock_audit_service,
        mock_get_user_today,
        habit_service,
        mock_user,
        mock_habit,
        mock_reward,
    ):
        """When target_date is None, get_user_today(user_timezone) is called."""
        user_local_date = date(2026, 2, 8)
        mock_get_user_today.return_value = user_local_date

        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 1
        mock_reward_service.calculate_total_weight.return_value = 1.0
        mock_reward_service.select_reward.return_value = mock_reward
        mock_reward_service.get_todays_awarded_rewards.return_value = []
        mock_log_repo.get_log_for_habit_on_date.return_value = None

        mock_progress = RewardProgress(
            id=1, user_id=mock_user.id, reward_id=mock_reward.id,
            pieces_earned=1, status=RewardStatus.ACHIEVED,
            pieces_required=1, claimed=False
        )
        mock_reward_service.update_reward_progress.return_value = mock_progress

        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo), \
             patch.object(habit_service, 'audit_log_service', mock_audit_service):

            result = habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking",
                target_date=None,
                user_timezone="Asia/Almaty",
            )

        mock_get_user_today.assert_any_call("Asia/Almaty")
        assert isinstance(result, HabitCompletionResult)
        assert result.habit_confirmed is True

    @patch('src.services.habit_service.get_user_today')
    @patch('src.services.habit_service.audit_log_service')
    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_explicit_target_date_skips_timezone_default(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        mock_audit_service,
        mock_get_user_today,
        habit_service,
        mock_user,
        mock_habit,
        mock_reward,
    ):
        """When target_date is provided, it is used directly."""
        explicit_date = date(2026, 2, 6)
        mock_get_user_today.return_value = date(2026, 2, 8)

        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 1
        mock_reward_service.calculate_total_weight.return_value = 1.0
        mock_reward_service.select_reward.return_value = mock_reward
        mock_reward_service.get_todays_awarded_rewards.return_value = []
        mock_log_repo.get_log_for_habit_on_date.return_value = None

        mock_progress = RewardProgress(
            id=1, user_id=mock_user.id, reward_id=mock_reward.id,
            pieces_earned=1, status=RewardStatus.ACHIEVED,
            pieces_required=1, claimed=False
        )
        mock_reward_service.update_reward_progress.return_value = mock_progress

        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo), \
             patch.object(habit_service, 'audit_log_service', mock_audit_service):

            result = habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking",
                target_date=explicit_date,
                user_timezone="Asia/Almaty",
            )

        assert isinstance(result, HabitCompletionResult)
        assert result.habit_confirmed is True

    @patch('src.services.habit_service.get_user_today')
    @patch('src.services.habit_service.audit_log_service')
    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_utc_default_timezone(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        mock_audit_service,
        mock_get_user_today,
        habit_service,
        mock_user,
        mock_habit,
        mock_reward,
    ):
        """When user_timezone is not specified, defaults to UTC."""
        mock_get_user_today.return_value = date(2026, 2, 7)

        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 1
        mock_reward_service.calculate_total_weight.return_value = 1.0
        mock_reward_service.select_reward.return_value = mock_reward
        mock_reward_service.get_todays_awarded_rewards.return_value = []
        mock_log_repo.get_log_for_habit_on_date.return_value = None

        mock_progress = RewardProgress(
            id=1, user_id=mock_user.id, reward_id=mock_reward.id,
            pieces_earned=1, status=RewardStatus.ACHIEVED,
            pieces_required=1, claimed=False
        )
        mock_reward_service.update_reward_progress.return_value = mock_progress

        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo), \
             patch.object(habit_service, 'audit_log_service', mock_audit_service):

            result = habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking",
            )

        mock_get_user_today.assert_any_call("UTC")
        assert result.habit_confirmed is True

    @patch('src.services.habit_service.get_user_today')
    @patch('src.services.habit_service.audit_log_service')
    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_future_date_validation_uses_user_timezone(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        mock_audit_service,
        mock_get_user_today,
        habit_service,
        mock_user,
        mock_habit,
        mock_reward,
    ):
        """Future date check uses user's local 'today', not UTC."""
        mock_get_user_today.return_value = date(2026, 2, 8)

        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit

        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo), \
             patch.object(habit_service, 'audit_log_service', mock_audit_service):

            with pytest.raises(ValueError, match="future"):
                habit_service.process_habit_completion(
                    user_telegram_id="123456789",
                    habit_name="Walking",
                    target_date=date(2026, 2, 9),
                    user_timezone="Asia/Almaty",
                )
