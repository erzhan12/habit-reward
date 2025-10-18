"""Unit tests for habit service."""

import pytest
from unittest.mock import patch

from src.services.habit_service import HabitService
from src.models.user import User
from src.models.habit import Habit
from src.models.reward import Reward, RewardType
from src.models.habit_completion_result import HabitCompletionResult


@pytest.fixture
def habit_service():
    """Create habit service instance."""
    return HabitService()


@pytest.fixture
def mock_user():
    """Create mock user."""
    return User(
        id="user123",
        telegram_id="123456789",
        name="Test User",
        weight=1.0,
        active=True
    )


@pytest.fixture
def mock_habit():
    """Create mock habit."""
    return Habit(
        id="habit123",
        name="Walking",
        weight=1.0,
        category="health",
        active=True
    )


@pytest.fixture
def mock_reward():
    """Create mock reward."""
    return Reward(
        id="reward123",
        name="Coffee",
        weight=1.0,
        type=RewardType.REAL,
        is_cumulative=False
    )


class TestHabitCompletion:
    """Test habit completion orchestration."""

    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_successful_habit_completion(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        habit_service,
        mock_user,
        mock_habit,
        mock_reward
    ):
        """Test successful habit completion flow."""
        # Setup mocks
        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 5
        mock_reward_service.calculate_total_weight.return_value = 1.5
        mock_reward_service.select_reward.return_value = mock_reward

        # Execute
        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo):

            result = habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking"
            )

        # Assertions
        assert isinstance(result, HabitCompletionResult)
        assert result.habit_confirmed is True
        assert result.habit_name == "Walking"
        assert result.streak_count == 5
        assert result.got_reward is True
        assert result.total_weight_applied == 1.5

        # Verify habit log was created
        mock_log_repo.create.assert_called_once()

    @patch('src.services.habit_service.user_repository')
    def test_user_not_found(self, mock_user_repo, habit_service):
        """Test error when user not found."""
        mock_user_repo.get_by_telegram_id.return_value = None

        with patch.object(habit_service, 'user_repo', mock_user_repo):
            with pytest.raises(ValueError, match="not found"):
                habit_service.process_habit_completion(
                    user_telegram_id="999999999",
                    habit_name="Walking"
                )

    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    def test_habit_not_found(
        self,
        mock_habit_repo,
        mock_user_repo,
        habit_service,
        mock_user
    ):
        """Test error when habit not found."""
        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = None

        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo):

            with pytest.raises(ValueError, match="not found"):
                habit_service.process_habit_completion(
                    user_telegram_id="123456789",
                    habit_name="NonExistentHabit"
                )

    @patch('src.services.habit_service.user_repository')
    @patch('src.services.habit_service.habit_repository')
    @patch('src.services.habit_service.streak_service')
    @patch('src.services.habit_service.reward_service')
    @patch('src.services.habit_service.habit_log_repository')
    def test_no_reward_completion(
        self,
        mock_log_repo,
        mock_reward_service,
        mock_streak_service,
        mock_habit_repo,
        mock_user_repo,
        habit_service,
        mock_user,
        mock_habit
    ):
        """Test habit completion with no reward."""
        # Setup mocks
        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 3
        mock_reward_service.calculate_total_weight.return_value = 1.3

        # Create none reward
        none_reward = Reward(
            id="reward_none",
            name="No reward",
            weight=1.0,
            type=RewardType.NONE,
            is_cumulative=False
        )
        mock_reward_service.select_reward.return_value = none_reward

        # Execute
        with patch.object(habit_service, 'user_repo', mock_user_repo), \
             patch.object(habit_service, 'habit_repo', mock_habit_repo), \
             patch.object(habit_service, 'streak_service', mock_streak_service), \
             patch.object(habit_service, 'reward_service', mock_reward_service), \
             patch.object(habit_service, 'habit_log_repo', mock_log_repo):

            result = habit_service.process_habit_completion(
                user_telegram_id="123456789",
                habit_name="Walking"
            )

        # Assertions
        assert result.got_reward is False
        assert result.reward is None

    def test_get_all_active_habits(self, habit_service):
        """Test getting all active habits."""
        mock_habits = [
            Habit(id="h1", name="Walking", weight=1.0, active=True),
            Habit(id="h2", name="Reading", weight=1.0, active=True)
        ]

        with patch.object(habit_service.habit_repo, 'get_all_active', return_value=mock_habits):
            habits = habit_service.get_all_active_habits()

        assert len(habits) == 2
        assert habits[0].name == "Walking"
