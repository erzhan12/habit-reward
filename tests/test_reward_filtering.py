"""Unit tests for reward filtering and ordering in get_user_reward_progress()."""

import pytest
from unittest.mock import AsyncMock

from src.services.reward_service import RewardService
from src.models.reward_progress import RewardProgress, RewardStatus


def _make_progress(
    *,
    pieces_earned: int,
    pieces_required: int,
    claimed: bool = False,
    reward_id: int = 1,
    user_id: int = 1,
) -> RewardProgress:
    """Build a Pydantic RewardProgress with the correct computed status."""
    if claimed:
        status = RewardStatus.CLAIMED
    elif pieces_earned >= pieces_required:
        status = RewardStatus.ACHIEVED
    else:
        status = RewardStatus.PENDING

    return RewardProgress(
        id=reward_id,
        user_id=user_id,
        reward_id=reward_id,
        pieces_earned=pieces_earned,
        pieces_required=pieces_required,
        claimed=claimed,
        status=status,
    )


class TestGetUserRewardProgress:
    """Tests for RewardService.get_user_reward_progress() filtering & ordering."""

    @pytest.fixture
    def service(self):
        svc = RewardService()
        svc.progress_repo = AsyncMock()
        return svc

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_claimed_rewards_hidden(self, service):
        """Claimed rewards must not appear in the result."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),
            _make_progress(pieces_earned=10, pieces_required=10, claimed=True, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 1
        assert result[0].reward_id == 1

    @pytest.mark.asyncio
    async def test_all_claimed_returns_empty(self, service):
        """If every reward is claimed the list should be empty."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=5, claimed=True, reward_id=1),
            _make_progress(pieces_earned=3, pieces_required=3, claimed=True, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert result == []

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sort_by_percentage_descending(self, service):
        """Pending rewards sorted by fill percentage high → low."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=3, pieces_required=10, reward_id=1),   # 30%
            _make_progress(pieces_earned=7, pieces_required=10, reward_id=2),   # 70%
            _make_progress(pieces_earned=1, pieces_required=2, reward_id=3),    # 50%
        ]

        result = await service.get_user_reward_progress("1")

        assert [r.reward_id for r in result] == [2, 3, 1]

    @pytest.mark.asyncio
    async def test_achieved_after_pending(self, service):
        """Achieved rewards come after all pending rewards."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=1),  # achieved
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=2),   # pending
        ]

        result = await service.get_user_reward_progress("1")

        assert result[0].reward_id == 2   # pending first
        assert result[1].reward_id == 1   # achieved second

    @pytest.mark.asyncio
    async def test_never_won_at_bottom(self, service):
        """Rewards with 0 pieces earned appear last."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=10, reward_id=1),   # never won
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=2),   # pending
        ]

        result = await service.get_user_reward_progress("1")

        assert result[0].reward_id == 2   # pending first
        assert result[1].reward_id == 1   # never-won last

    @pytest.mark.asyncio
    async def test_mixed_ordering_all_groups(self, service):
        """Full ordering: pending (by %) → achieved → never-won."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=5, reward_id=1),    # never won
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=2),  # achieved
            _make_progress(pieces_earned=3, pieces_required=10, reward_id=3),   # 30%
            _make_progress(pieces_earned=7, pieces_required=10, reward_id=4),   # 70%
            _make_progress(pieces_earned=5, pieces_required=5, claimed=True, reward_id=5),  # claimed
        ]

        result = await service.get_user_reward_progress("1")

        ids = [r.reward_id for r in result]
        # claimed (id=5) excluded; order: 70% → 30% → achieved → never-won
        assert ids == [4, 3, 2, 1]

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, service):
        """Empty input returns empty output."""
        service.progress_repo.get_all_by_user.return_value = []

        result = await service.get_user_reward_progress("1")

        assert result == []
