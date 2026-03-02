"""Unit tests for reward filtering and ordering in get_user_reward_progress()."""

import pytest
from unittest.mock import AsyncMock

from src.services.reward_service import RewardService
from src.models.reward_progress import RewardProgress


def _make_progress(
    *,
    pieces_earned: int,
    pieces_required: int | None,
    claimed: bool = False,
    times_claimed: int = 0,
    progress_id: int | None = None,
    reward_id: int = 99,
    user_id: int = 42,
) -> RewardProgress:
    """Build a Pydantic RewardProgress, letting the model derive status itself."""
    return RewardProgress(
        id=progress_id if progress_id is not None else reward_id,
        user_id=user_id,
        reward_id=reward_id,
        pieces_earned=pieces_earned,
        pieces_required=pieces_required,
        claimed=claimed,
        times_claimed=times_claimed,
    )


class TestGetUserRewardProgress:
    """Tests for RewardService.get_user_reward_progress() filtering & ordering."""

    @pytest.fixture
    def service(self):
        svc = RewardService()
        svc.progress_repo = AsyncMock()
        svc.reward_repo = AsyncMock()
        # Default: no extra active rewards beyond those with progress
        svc.reward_repo.get_all_active.return_value = []
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

    @pytest.mark.asyncio
    async def test_partially_earned_claimed_reward_hidden(self, service):
        """Claimed reward with pieces_earned < pieces_required is still filtered out."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=3, pieces_required=10, claimed=True, reward_id=1),
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 1
        assert result[0].reward_id == 2

    @pytest.mark.asyncio
    async def test_claimed_with_pieces_required_none_hidden(self, service):
        """claimed=True takes priority even when pieces_required is None."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=2, pieces_required=None, claimed=True, reward_id=1),
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 1
        assert result[0].reward_id == 2

    @pytest.mark.asyncio
    async def test_recurring_reward_with_zero_pieces_visible(self, service):
        """Recurring reward with claimed=False and pieces_earned=0 must appear (fresh cycle after claim)."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=5, claimed=False, times_claimed=3, reward_id=1),
            _make_progress(pieces_earned=4, pieces_required=10, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 2
        # Pending (40%) first, then never-won (0/5) last
        assert [r.reward_id for r in result] == [2, 1]

    @pytest.mark.asyncio
    async def test_claimed_recurring_reward_visible_as_never_won(self, service):
        """Recurring reward with claimed=True (legacy data) must appear in never-won group."""
        from unittest.mock import Mock

        recurring_reward = Mock()
        recurring_reward.is_recurring = True

        claimed_progress = _make_progress(
            pieces_earned=0, pieces_required=5, claimed=True, times_claimed=2, reward_id=1,
        )
        claimed_progress.reward = recurring_reward

        service.progress_repo.get_all_by_user.return_value = [
            claimed_progress,
            _make_progress(pieces_earned=3, pieces_required=10, reward_id=2),
        ]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 2
        # Pending (30%) first, then recurring claimed as never-won last
        assert [r.reward_id for r in result] == [2, 1]

    @pytest.mark.asyncio
    async def test_active_reward_without_progress_visible(self, service):
        """Active reward with no RewardProgress entry must appear as never-won."""
        from unittest.mock import Mock

        reward_no_progress = Mock()
        reward_no_progress.id = 99
        reward_no_progress.pieces_required = 3
        reward_no_progress.is_recurring = True

        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),
        ]
        service.reward_repo.get_all_active.return_value = [reward_no_progress]

        result = await service.get_user_reward_progress("1")

        assert len(result) == 2
        # Pending (50%) first, then never-won (no progress) last
        assert result[0].reward_id == 1
        assert result[1].reward_id == 99
        assert result[1].pieces_earned == 0
        assert result[1].pieces_required == 3

    @pytest.mark.asyncio
    async def test_repo_filters_inactive_rewards_at_db_level(self):
        """Integration test: get_all_by_user only returns progress for active rewards.

        Creates both an active and inactive reward with progress, then verifies
        the repository's reward__active=True filter excludes the inactive one.
        """
        from src.core.models import User, Reward
        from src.core.models import RewardProgress as DjangoRewardProgress
        from src.core.repositories import RewardProgressRepository

        user = await User.objects.acreate(
            telegram_id="999888777",
            name="Filter Test User",
            username="filter_test",
        )

        try:
            active_reward = await Reward.objects.acreate(
                user=user,
                name="Active Reward",
                weight=10.0,
                pieces_required=5,
                active=True,
            )
            inactive_reward = await Reward.objects.acreate(
                user=user,
                name="Inactive Reward",
                weight=10.0,
                pieces_required=5,
                active=False,
            )

            await DjangoRewardProgress.objects.acreate(
                user=user, reward=active_reward, pieces_earned=2,
            )
            await DjangoRewardProgress.objects.acreate(
                user=user, reward=inactive_reward, pieces_earned=3,
            )

            repo = RewardProgressRepository()
            results = await repo.get_all_by_user(user.id)

            assert len(results) == 1
            assert results[0].reward_id == active_reward.id
        finally:
            await DjangoRewardProgress.objects.filter(user=user).adelete()
            await Reward.objects.filter(user=user).adelete()
            await user.adelete()

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
    async def test_one_piece_away_is_pending_not_achieved(self, service):
        """Reward at pieces_required-1 stays in pending group, not achieved."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=9, pieces_required=10, reward_id=1),  # 90% pending
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=2),  # achieved
            _make_progress(pieces_earned=0, pieces_required=1, reward_id=3),    # never-won (0/1)
        ]

        result = await service.get_user_reward_progress("1")

        ids = [r.reward_id for r in result]
        # 90% pending first, then achieved, then never-won
        assert ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_equal_percentage_preserves_repo_order(self, service):
        """Rewards with the same fill % keep their repository order (stable sort)."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),   # 50%
            _make_progress(pieces_earned=1, pieces_required=2, reward_id=2),    # 50%
            _make_progress(pieces_earned=3, pieces_required=6, reward_id=3),    # 50%
        ]

        result = await service.get_user_reward_progress("1")

        # Python's stable sort preserves insertion order for equal keys
        assert [r.reward_id for r in result] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_pieces_required_none_goes_to_never_won(self, service):
        """Reward with pieces_required=None is bucketed into never-won, not pending."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),     # pending 50%
            _make_progress(pieces_earned=3, pieces_required=None, reward_id=2),   # never-won
        ]

        result = await service.get_user_reward_progress("1")

        # pending first, then never-won (pieces_required=None)
        assert [r.reward_id for r in result] == [1, 2]

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, service):
        """Empty input returns empty output."""
        service.progress_repo.get_all_by_user.return_value = []

        result = await service.get_user_reward_progress("1")

        assert result == []
