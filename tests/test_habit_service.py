"""Unit tests for habit service."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
        is_active=True
    )


@pytest.fixture
def mock_habit():
    """Create mock habit."""
    return Habit(
        id="habit123",
        name="Walking",
        weight=10,
        category="health",
        active=True
    )


@pytest.fixture
def mock_reward():
    """Create mock reward."""
    return Reward(
        id="reward123",
        name="Coffee",
        weight=10,
        type=RewardType.REAL,
        pieces_required=1
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
        from src.models.reward_progress import RewardProgress, RewardStatus
        
        # Setup mocks
        mock_user_repo.get_by_telegram_id.return_value = mock_user
        mock_habit_repo.get_by_name.return_value = mock_habit
        mock_streak_service.calculate_streak.return_value = 5
        mock_reward_service.calculate_total_weight.return_value = 1.5
        mock_reward_service.select_reward.return_value = mock_reward
        mock_reward_service.get_todays_awarded_rewards.return_value = []
        
        # Mock reward progress return
        mock_progress = RewardProgress(
            id="prog1",
            user_id=mock_user.id,
            reward_id=mock_reward.id,
            pieces_earned=1,
            status=RewardStatus.ACHIEVED,
            pieces_required=1,
            claimed=False
        )
        mock_reward_service.update_reward_progress.return_value = mock_progress

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
        mock_reward_service.get_todays_awarded_rewards.return_value = []

        # Create none reward
        none_reward = Reward(
            id="reward_none",
            name="No reward",
            weight=10,
            type=RewardType.NONE,
            pieces_required=1
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
            Habit(id="h1", name="Walking", weight=10, active=True),
            Habit(id="h2", name="Reading", weight=10, active=True)
        ]

        with patch.object(habit_service.habit_repo, 'get_all_active', return_value=mock_habits):
            habits = habit_service.get_all_active_habits()

        assert len(habits) == 2
        assert habits[0].name == "Walking"

    @pytest.mark.asyncio
    async def test_get_active_habits_pending_for_today_filters_completed(self, habit_service):
        """Habits completed today should be excluded from the selection list."""
        all_habits = [
            Habit(id="1", name="Walking", weight=10, active=True),
            Habit(id="2", name="Reading", weight=5, active=True),
        ]
        todays_logs = [SimpleNamespace(habit_id="1")]

        habit_service.habit_repo = SimpleNamespace(
            get_all_active=AsyncMock(return_value=all_habits)
        )
        habit_service.habit_log_repo = SimpleNamespace(
            get_todays_logs_by_user=AsyncMock(return_value=todays_logs)
        )

        available = await habit_service.get_active_habits_pending_for_today(user_id=42)

        assert [habit.id for habit in available] == ["2"]
        habit_service.habit_repo.get_all_active.assert_awaited_once()
        habit_service.habit_log_repo.get_todays_logs_by_user.assert_awaited_once_with(
            user_id=42,
            target_date=None,
        )


class TestHabitRevert:
    """Tests for reverting habit completions."""

    @pytest.mark.asyncio
    async def test_revert_habit_completion_success_with_reward(self, habit_service):
        """Reverting a habit removes the log and rolls back reward progress."""
        user = SimpleNamespace(id=1, is_active=True)
        habit = SimpleNamespace(id=2, name="Walking", active=True)
        reward = SimpleNamespace(name="Coffee")
        log = SimpleNamespace(id=5, reward=reward, reward_id=7, got_reward=True)
        progress = SimpleNamespace(
            id=9,
            user_id=user.id,
            reward_id=log.reward_id,
            pieces_earned=2,
            pieces_required=5,
            claimed=False,
            reward=SimpleNamespace(name="Coffee", pieces_required=5)
        )

        user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        habit_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=habit))
        habit_log_repo = SimpleNamespace(
            get_last_log_for_habit=AsyncMock(return_value=log),
            delete=AsyncMock(return_value=1)
        )
        reward_progress_repo = SimpleNamespace(
            decrement_pieces_earned=AsyncMock(return_value=progress)
        )

        habit_service.user_repo = user_repo
        habit_service.habit_repo = habit_repo
        habit_service.habit_log_repo = habit_log_repo
        habit_service.reward_progress_repo = reward_progress_repo

        atomic_context = AsyncMock()
        atomic_context.__aenter__.return_value = None
        atomic_context.__aexit__.return_value = None
        with patch('src.services.habit_service.transaction.atomic', return_value=atomic_context):
            result = await habit_service.revert_habit_completion('123', habit.id)

        habit_service.habit_log_repo.delete.assert_awaited_once_with(log.id)
        habit_service.reward_progress_repo.decrement_pieces_earned.assert_awaited_once_with(
            user.id, log.reward_id
        )
        assert result.habit_name == habit.name
        assert result.reward_reverted is True
        assert result.reward_name == 'Coffee'
        assert result.reward_progress.pieces_earned == 2

    @pytest.mark.asyncio
    async def test_revert_habit_completion_no_log(self, habit_service):
        """Reverting without an existing log raises a ValueError."""
        user = SimpleNamespace(id=1, is_active=True)
        habit = SimpleNamespace(id=2, name="Walking", active=True)

        habit_service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        habit_service.habit_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=habit))
        habit_service.habit_log_repo = SimpleNamespace(get_last_log_for_habit=AsyncMock(return_value=None))
        habit_service.reward_progress_repo = SimpleNamespace(decrement_pieces_earned=AsyncMock())

        with pytest.raises(ValueError, match="No habit completion found to revert"):
            await habit_service.revert_habit_completion('123', habit.id)

    @pytest.mark.asyncio
    async def test_revert_habit_completion_inactive_user(self, habit_service):
        """Reverting with an inactive user raises a ValueError."""
        user = SimpleNamespace(id=1, is_active=False)

        habit_service.user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        habit_service.habit_repo = SimpleNamespace(get_by_id=AsyncMock())
        habit_service.habit_log_repo = SimpleNamespace(get_last_log_for_habit=AsyncMock())
        habit_service.reward_progress_repo = SimpleNamespace(decrement_pieces_earned=AsyncMock())

        with pytest.raises(ValueError, match="User is inactive"):
            await habit_service.revert_habit_completion('123', 2)

    @pytest.mark.asyncio
    async def test_revert_habit_completion_success_no_reward(self, habit_service):
        """Reverting a habit without a reward only deletes the log."""
        user = SimpleNamespace(id=1, is_active=True)
        habit = SimpleNamespace(id=2, name="Reading", active=True)
        log = SimpleNamespace(id=5, reward=None, reward_id=None, got_reward=False)

        user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        habit_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=habit))
        habit_log_repo = SimpleNamespace(
            get_last_log_for_habit=AsyncMock(return_value=log),
            delete=AsyncMock(return_value=1)
        )
        reward_progress_repo = SimpleNamespace(
            decrement_pieces_earned=AsyncMock()
        )

        habit_service.user_repo = user_repo
        habit_service.habit_repo = habit_repo
        habit_service.habit_log_repo = habit_log_repo
        habit_service.reward_progress_repo = reward_progress_repo

        atomic_context = AsyncMock()
        atomic_context.__aenter__.return_value = None
        atomic_context.__aexit__.return_value = None
        with patch('src.services.habit_service.transaction.atomic', return_value=atomic_context):
            result = await habit_service.revert_habit_completion('123', habit.id)

        habit_service.habit_log_repo.delete.assert_awaited_once_with(log.id)
        # Should NOT call decrement_pieces_earned when no reward
        habit_service.reward_progress_repo.decrement_pieces_earned.assert_not_awaited()
        assert result.habit_name == habit.name
        assert result.reward_reverted is False
        assert result.reward_name is None

    @pytest.mark.asyncio
    async def test_revert_habit_completion_reward_progress_at_zero(self, habit_service):
        """Reverting when reward progress is already at zero returns progress at zero."""
        user = SimpleNamespace(id=1, is_active=True)
        habit = SimpleNamespace(id=2, name="Walking", active=True)
        reward = SimpleNamespace(name="Coffee")
        log = SimpleNamespace(id=5, reward=reward, reward_id=7, got_reward=True)
        # Progress already at zero after decrement
        progress = SimpleNamespace(
            id=9,
            user_id=user.id,
            reward_id=log.reward_id,
            pieces_earned=0,  # Already at zero
            pieces_required=5,
            claimed=False,
            reward=SimpleNamespace(name="Coffee", pieces_required=5)
        )

        user_repo = SimpleNamespace(get_by_telegram_id=AsyncMock(return_value=user))
        habit_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=habit))
        habit_log_repo = SimpleNamespace(
            get_last_log_for_habit=AsyncMock(return_value=log),
            delete=AsyncMock(return_value=1)
        )
        reward_progress_repo = SimpleNamespace(
            decrement_pieces_earned=AsyncMock(return_value=progress)
        )

        habit_service.user_repo = user_repo
        habit_service.habit_repo = habit_repo
        habit_service.habit_log_repo = habit_log_repo
        habit_service.reward_progress_repo = reward_progress_repo

        atomic_context = AsyncMock()
        atomic_context.__aenter__.return_value = None
        atomic_context.__aexit__.return_value = None
        with patch('src.services.habit_service.transaction.atomic', return_value=atomic_context):
            result = await habit_service.revert_habit_completion('123', habit.id)

        habit_service.habit_log_repo.delete.assert_awaited_once_with(log.id)
        habit_service.reward_progress_repo.decrement_pieces_earned.assert_awaited_once_with(
            user.id, log.reward_id
        )
        assert result.habit_name == habit.name
        assert result.reward_reverted is True
        assert result.reward_progress.pieces_earned == 0  # Verify it's at zero
        assert result.reward_name == 'Coffee'
