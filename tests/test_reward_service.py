"""Unit tests for reward service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.services.reward_service import RewardService
from src.models.reward import Reward, RewardType
from src.models.reward_progress import RewardProgress, RewardStatus


@pytest.fixture
def reward_service():
    """Create reward service instance."""
    return RewardService()


@pytest.fixture
def mock_reward_repo():
    """Create mock reward repository."""
    return Mock()


@pytest.fixture
def mock_progress_repo():
    """Create mock reward progress repository."""
    return Mock()


class TestWeightCalculation:
    """Test weight calculation logic."""

    def test_basic_weight_calculation(self, reward_service):
        """Test basic weight calculation without streak."""
        total_weight = reward_service.calculate_total_weight(
            habit_weight=10,
            streak_count=1
        )

        # 10 * (1 + 1*0.1) = 10 * 1.1 = 11.0
        assert total_weight == pytest.approx(11.0)

    def test_weight_with_high_streak(self, reward_service):
        """Test weight calculation with high streak."""
        total_weight = reward_service.calculate_total_weight(
            habit_weight=10,
            streak_count=10
        )

        # 10 * (1 + 10*0.1) = 10 * 2.0 = 20.0
        assert total_weight == pytest.approx(20.0)

    def test_weight_with_habit_multiplier(self, reward_service):
        """Test weight calculation with habit multiplier."""
        total_weight = reward_service.calculate_total_weight(
            habit_weight=20,
            streak_count=5
        )

        # 20 * (1 + 5*0.1) = 20 * 1.5 = 30.0
        assert total_weight == pytest.approx(30.0)


class TestRewardSelection:
    """Test reward selection logic."""

    def test_select_reward_from_multiple(self, reward_service, mock_reward_repo):
        """Test weighted random selection."""
        mock_rewards = [
            Reward(id="r1", name="Reward 1", weight=10, type=RewardType.VIRTUAL),
            Reward(id="r2", name="Reward 2", weight=20, type=RewardType.REAL),
            Reward(id="r3", name="No Reward", weight=50, type=RewardType.NONE)
        ]
        mock_reward_repo.get_all_active.return_value = mock_rewards

        with patch.object(reward_service, 'reward_repo', mock_reward_repo):
            selected = reward_service.select_reward(total_weight=10.0)

        assert selected in mock_rewards

    def test_select_reward_empty_list(self, reward_service, mock_reward_repo):
        """Test reward selection when no rewards exist."""
        mock_reward_repo.get_all_active.return_value = []

        with patch.object(reward_service, 'reward_repo', mock_reward_repo):
            selected = reward_service.select_reward(total_weight=10.0)

        assert selected.type == RewardType.NONE
        assert selected.name == "No reward"


class TestCumulativeProgress:
    """Test cumulative reward progress logic."""

    def test_create_new_progress(self, reward_service, mock_reward_repo, mock_progress_repo):
        """Test creating new progress entry."""
        mock_reward = Reward(
            id="r1",
            name="Multi-piece Reward",
            weight=10,
            type=RewardType.REAL,
            pieces_required=10,
            piece_value=1.0
        )
        mock_reward_repo.get_by_id.return_value = mock_reward
        mock_progress_repo.get_by_user_and_reward.return_value = None

        # Mock create to return a progress with id
        def mock_create(progress):
            progress.id = "prog1"
            return progress

        mock_progress_repo.create.side_effect = mock_create

        # Mock update to return updated progress
        def mock_update(progress_id, updates):
            # Status is calculated by Airtable, so we simulate it based on pieces_earned
            pieces_earned = updates["pieces_earned"]
            status = RewardStatus.ACHIEVED if pieces_earned >= 10 else RewardStatus.PENDING
            return RewardProgress(
                id=progress_id,
                user_id="user123",
                reward_id="r1",
                pieces_earned=pieces_earned,
                status=status,
                pieces_required=10
            )

        mock_progress_repo.update.side_effect = mock_update

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo):
            updated = reward_service.update_reward_progress("user123", "r1")

        assert updated.pieces_earned == 1
        assert updated.status == RewardStatus.PENDING

    def test_achieve_cumulative_reward(self, reward_service, mock_reward_repo, mock_progress_repo):
        """Test achieving reward when pieces requirement met."""
        mock_reward = Reward(
            id="r1",
            name="Multi-piece Reward",
            weight=10,
            type=RewardType.REAL,
            pieces_required=10,
            piece_value=1.0
        )
        mock_reward_repo.get_by_id.return_value = mock_reward

        existing_progress = RewardProgress(
            id="prog1",
            user_id="user123",
            reward_id="r1",
            pieces_earned=9,
            status=RewardStatus.PENDING,
            pieces_required=10
        )
        mock_progress_repo.get_by_user_and_reward.return_value = existing_progress

        # Mock update to return achieved progress
        def mock_update(progress_id, updates):
            # Status is calculated by Airtable, so we simulate it based on pieces_earned
            pieces_earned = updates["pieces_earned"]
            status = RewardStatus.ACHIEVED if pieces_earned >= 10 else RewardStatus.PENDING
            return RewardProgress(
                id=progress_id,
                user_id="user123",
                reward_id="r1",
                pieces_earned=pieces_earned,
                status=status,
                pieces_required=10
            )

        mock_progress_repo.update.side_effect = mock_update

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo):
            updated = reward_service.update_reward_progress("user123", "r1")

        assert updated.pieces_earned == 10
        assert updated.status == RewardStatus.ACHIEVED

    def test_mark_reward_claimed(self, reward_service, mock_progress_repo):
        """Test marking reward as claimed."""
        achieved_progress = RewardProgress(
            id="prog1",
            user_id="user123",
            reward_id="r1",
            pieces_earned=10,
            status=RewardStatus.ACHIEVED,
            pieces_required=10,
            claimed=False
        )
        mock_progress_repo.get_by_user_and_reward.return_value = achieved_progress

        def mock_update(progress_id, updates):
            # When claimed=True is set, Airtable formula updates status to CLAIMED
            return RewardProgress(
                id=progress_id,
                user_id="user123",
                reward_id="r1",
                pieces_earned=10,
                status=RewardStatus.CLAIMED,
                pieces_required=10,
                claimed=True
            )

        mock_progress_repo.update.side_effect = mock_update

        with patch.object(reward_service, 'progress_repo', mock_progress_repo):
            updated = reward_service.mark_reward_claimed("user123", "r1")

        # Verify update was called with claimed=True
        mock_progress_repo.update.assert_called_once_with("prog1", {"claimed": True})
        # Status should be CLAIMED after claiming
        assert updated.status == RewardStatus.CLAIMED
        assert updated.claimed is True


class TestCreateReward:
    """Test reward creation helper."""

    @pytest.mark.asyncio
    async def test_create_reward_with_pydantic_enum(self, reward_service):
        """Should normalize enum value and persist reward."""
        created_reward = Mock(name="Morning Coffee", id="r123")
        mock_repo = Mock()
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=created_reward)

        with patch.object(reward_service, 'reward_repo', mock_repo):
            result = await reward_service.create_reward(
                name="Morning Coffee",
                reward_type=RewardType.VIRTUAL,
                weight=5.0,
                pieces_required=3,
                piece_value=1.5
            )

        assert result is created_reward
        mock_repo.get_by_name.assert_awaited_once_with("Morning Coffee")
        await_call = mock_repo.create.await_args
        payload = await_call.args[0]
        assert payload["type"] == RewardType.VIRTUAL.value
        assert payload["piece_value"] == 1.5

    @pytest.mark.asyncio
    async def test_create_reward_duplicate_name(self, reward_service):
        """Should raise error when reward name already exists."""
        existing_reward = Mock()
        mock_repo = Mock()
        mock_repo.get_by_name = AsyncMock(return_value=existing_reward)
        mock_repo.create = AsyncMock()

        with patch.object(reward_service, 'reward_repo', mock_repo):
            with pytest.raises(ValueError):
                await reward_service.create_reward(
                    name="Morning Coffee",
                    reward_type=RewardType.VIRTUAL,
                    weight=5.0,
                    pieces_required=3,
                    piece_value=None
                )

        mock_repo.create.assert_not_called()
