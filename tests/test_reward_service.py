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
            selected = reward_service.select_reward(user_id=1, total_weight=10.0)

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
        assert updated.get_status() == RewardStatus.PENDING

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
        assert updated.get_status() == RewardStatus.ACHIEVED

    def test_mark_reward_claimed(self, reward_service, mock_progress_repo, mock_reward_repo):
        """Test marking reward as claimed (Feature 0014: also resets pieces_earned)."""
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
            # When claimed=True is set and pieces_earned=0, status becomes CLAIMED
            return RewardProgress(
                id=progress_id,
                user_id="user123",
                reward_id="r1",
                pieces_earned=0,  # Reset to 0 as per Feature 0014
                status=RewardStatus.CLAIMED,
                pieces_required=10,
                claimed=True
            )

        mock_progress_repo.update.side_effect = mock_update

        # Mock reward repository to return a reward
        mock_reward = Reward(
            id="r1",
            name="Test Reward",
            type=RewardType.VIRTUAL,
            weight=10.0,
            pieces_required=10,
            is_recurring=True
        )
        mock_reward_repo.get_by_id.return_value = mock_reward

        with patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'reward_repo', mock_reward_repo):
            updated = reward_service.mark_reward_claimed("user123", "r1")

        # Verify update was called with claimed=True AND pieces_earned=0
        mock_progress_repo.update.assert_called_once_with(
            "prog1",
            {"claimed": True, "pieces_earned": 0}
        )
        # Status should be CLAIMED after claiming
        assert updated.get_status() == RewardStatus.CLAIMED
        assert updated.claimed is True
        assert updated.pieces_earned == 0  # Verify pieces reset


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
                user_id=1,
                name="Morning Coffee",
                reward_type=RewardType.VIRTUAL,
                weight=5.0,
                pieces_required=3,
                piece_value=1.5
            )

        assert result is created_reward
        mock_repo.get_by_name.assert_awaited_once_with(1, "Morning Coffee")
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
                    user_id=1,
                    name="Morning Coffee",
                    reward_type=RewardType.VIRTUAL,
                    weight=5.0,
                    pieces_required=3,
                    piece_value=None
                )

        mock_repo.create.assert_not_called()


class TestDailyLimitEnforcement:
    """Test daily limit enforcement for rewards (Feature 0014)."""

    @pytest.mark.asyncio
    async def test_get_todays_pieces_by_reward_no_logs(self, reward_service):
        """Test counting when no logs exist for today."""
        mock_habit_log_repo = Mock()
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=[])

        with patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            count = await reward_service.get_todays_pieces_by_reward("user123", "r1")

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_todays_pieces_by_reward_counts_all(self, reward_service):
        """Test that all pieces awarded today are counted (claimed and unclaimed)."""
        # Create mock logs - 2 pieces awarded today for reward r1
        mock_log1 = Mock(got_reward=True, reward_id="r1")
        mock_log2 = Mock(got_reward=True, reward_id="r1")
        mock_log3 = Mock(got_reward=True, reward_id="r2")  # Different reward
        mock_log4 = Mock(got_reward=False, reward_id="r1")  # No reward

        mock_habit_log_repo = Mock()
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(
            return_value=[mock_log1, mock_log2, mock_log3, mock_log4]
        )

        with patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            count = await reward_service.get_todays_pieces_by_reward("user123", "r1")

        assert count == 2

    @pytest.mark.asyncio
    async def test_get_todays_pieces_includes_claimed(self, reward_service):
        """Test that claimed pieces are still counted toward daily limit (blocking bug fix)."""
        # Create mock logs - 1 piece awarded today
        mock_log = Mock(got_reward=True, reward_id="r1")

        mock_habit_log_repo = Mock()
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(
            return_value=[mock_log]
        )

        with patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            count = await reward_service.get_todays_pieces_by_reward("user123", "r1")

        # Should count the piece even if it was claimed
        assert count == 1

    @pytest.mark.asyncio
    async def test_select_reward_excludes_at_daily_limit(self, reward_service):
        """Test that rewards at their daily limit are excluded from selection."""
        # Setup: reward with max_daily_claims=1
        mock_reward = Mock(
            id="r1",
            name="Limited Reward",
            weight=10.0,
            type=RewardType.REAL,
            pieces_required=5,
            max_daily_claims=1
        )

        mock_reward_repo = Mock()
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])

        mock_progress_repo = Mock()
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[])

        # Mock: 1 piece already awarded today
        mock_habit_log_repo = Mock()
        mock_log = Mock(got_reward=True, reward_id="r1")
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=[mock_log])

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            selected = await reward_service.select_reward(
                total_weight=10.0,
                user_id="user123"
            )

        # Should return "No reward" since the only reward is at its daily limit
        assert selected.type == RewardType.NONE
        assert selected.name == "No reward"

    @pytest.mark.asyncio
    async def test_select_reward_allows_unlimited(self, reward_service):
        """Test that rewards with max_daily_claims=NULL/0 are not limited."""
        # Setup: reward with max_daily_claims=None (unlimited)
        mock_reward = Mock(
            id="r1",
            name="Unlimited Reward",
            weight=10.0,
            type=RewardType.REAL,
            pieces_required=5,
            max_daily_claims=None
        )

        mock_reward_repo = Mock()
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])

        mock_progress_repo = Mock()
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[])

        # Mock: 5 pieces already awarded today (but unlimited is set)
        mock_habit_log_repo = Mock()
        mock_logs = [Mock(got_reward=True, reward_id="r1") for _ in range(5)]
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=mock_logs)

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            selected = await reward_service.select_reward(
                total_weight=10.0,
                user_id="user123"
            )

        # Should still select the reward since it's unlimited
        assert selected == mock_reward

    @pytest.mark.asyncio
    async def test_select_reward_excludes_completed(self, reward_service):
        """Test that completed rewards are excluded from selection."""
        # Setup: reward that is completed
        mock_reward = Mock(spec=['id', 'name', 'weight', 'type', 'pieces_required', 'max_daily_claims'])
        mock_reward.id = "r1"
        mock_reward.name = "Completed Reward"
        mock_reward.weight = 10.0
        mock_reward.type = RewardType.REAL
        mock_reward.pieces_required = 5
        mock_reward.max_daily_claims = None

        mock_progress = Mock(
            reward_id="r1",
            pieces_earned=5,
            claimed=False
        )
        mock_progress.get_status = Mock(return_value=RewardStatus.ACHIEVED)

        mock_reward_repo = Mock()
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])

        mock_progress_repo = Mock()
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[mock_progress])

        mock_habit_log_repo = Mock()
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=[])

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            selected = await reward_service.select_reward(
                total_weight=10.0,
                user_id="user123"
            )

        # Should return "No reward" since the only reward is completed
        assert selected.type == RewardType.NONE
        assert selected.name == "No reward"

    @pytest.mark.asyncio
    async def test_claim_reset_scenario_prevents_bypass(self, reward_service):
        """
        Test the blocking bug scenario from code review:
        1. Reward with max_daily_claims=1
        2. User earns 1 piece (limit reached)
        3. User claims the reward
        4. User tries to earn again same day
        5. Should be BLOCKED (daily limit already reached)
        """
        # Setup: reward with max_daily_claims=1
        mock_reward = Mock(
            id="r1",
            name="Once Daily",
            weight=10.0,
            type=RewardType.REAL,
            pieces_required=1,
            max_daily_claims=1
        )

        mock_reward_repo = Mock()
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])

        # Progress shows CLAIMED status (user already claimed)
        mock_progress = Mock(
            reward_id="r1",
            pieces_earned=0,  # Reset after claim
            claimed=True
        )
        mock_progress.get_status = Mock(return_value=RewardStatus.CLAIMED)

        mock_progress_repo = Mock()
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[mock_progress])

        # Log shows 1 piece was awarded today (even though claimed)
        mock_habit_log_repo = Mock()
        mock_log = Mock(got_reward=True, reward_id="r1")
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=[mock_log])

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            selected = await reward_service.select_reward(
                total_weight=10.0,
                user_id="user123"
            )

        # Should return "No reward" - daily limit prevents earning again
        # This is the fix for the blocking bug!
        assert selected.type == RewardType.NONE
        assert selected.name == "No reward"

    @pytest.mark.asyncio
    async def test_select_reward_multiple_limits(self, reward_service):
        """Test reward with max_daily_claims=2 allows 2 pieces per day."""
        # Setup: reward with max_daily_claims=2
        mock_reward = Mock(
            id="r1",
            name="Twice Daily",
            weight=10.0,
            type=RewardType.REAL,
            pieces_required=10,
            max_daily_claims=2
        )

        mock_reward_repo = Mock()
        mock_reward_repo.get_all_active = AsyncMock(return_value=[mock_reward])

        mock_progress_repo = Mock()
        mock_progress_repo.get_all_by_user = AsyncMock(return_value=[])

        # Mock: 1 piece already awarded today (under limit of 2)
        mock_habit_log_repo = Mock()
        mock_log = Mock(got_reward=True, reward_id="r1")
        mock_habit_log_repo.get_todays_logs_by_user = AsyncMock(return_value=[mock_log])

        with patch.object(reward_service, 'reward_repo', mock_reward_repo), \
             patch.object(reward_service, 'progress_repo', mock_progress_repo), \
             patch.object(reward_service, 'habit_log_repo', mock_habit_log_repo):
            selected = await reward_service.select_reward(
                total_weight=10.0,
                user_id="user123"
            )

        # Should select the reward (1 < 2)
        assert selected == mock_reward
