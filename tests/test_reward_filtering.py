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
        # Zero-piece (0/5) first, then non-zero (4/10)
        assert [r.reward_id for r in result] == [1, 2]

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
        # Recurring claimed treated as zero-piece (fresh cycle) → first
        assert [r.reward_id for r in result] == [1, 2]

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
        # Synthetic zero-piece reward (no progress row) first, then non-zero (5/10)
        assert result[0].reward_id == 99
        assert result[0].pieces_earned == 0
        assert result[0].pieces_required == 3
        assert result[1].reward_id == 1

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
    async def test_pending_sorted_by_completion_ratio_descending(self, service):
        """PENDING rewards sorted by completion ratio descending (closest-to-ready first)."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=7, pieces_required=10, reward_id=1),  # 70%
            _make_progress(pieces_earned=3, pieces_required=10, reward_id=2),  # 30%
            _make_progress(pieces_earned=1, pieces_required=10, reward_id=3),  # 10%
        ]

        result = await service.get_user_reward_progress("1")

        assert [r.reward_id for r in result] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_achieved_appears_after_pending(self, service):
        """ACHIEVED rewards are ordered last, after all PENDING rewards,
        regardless of pieces_earned. They sit just before the separate
        claimed-rewards block in the UI."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=5, reward_id=1),     # achieved (low pieces_earned)
            _make_progress(pieces_earned=20, pieces_required=100, reward_id=2),  # pending (high pieces_earned)
        ]

        result = await service.get_user_reward_progress("1")

        # pending comes first even though pieces_earned (20) > achieved's (5)
        assert [r.reward_id for r in result] == [2, 1]

    @pytest.mark.asyncio
    async def test_zero_piece_rewards_appear_first(self, service):
        """Rewards with 0 pieces earned appear first in the list."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),   # non-zero
            _make_progress(pieces_earned=0, pieces_required=10, reward_id=2),   # zero-piece
        ]

        result = await service.get_user_reward_progress("1")

        assert result[0].reward_id == 2   # zero-piece first
        assert result[1].reward_id == 1   # non-zero last

    @pytest.mark.asyncio
    async def test_mixed_ordering_all_groups(self, service):
        """Full ordering: zero-piece → pending (descending by completion ratio) → achieved; claimed excluded."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=7, pieces_required=10, reward_id=1),   # pending 70%
            _make_progress(pieces_earned=0, pieces_required=5, reward_id=2),    # zero-piece
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=3),  # achieved
            _make_progress(pieces_earned=3, pieces_required=10, reward_id=4),   # pending 30%
            _make_progress(pieces_earned=5, pieces_required=5, claimed=True, reward_id=5),  # claimed
        ]

        result = await service.get_user_reward_progress("1")

        ids = [r.reward_id for r in result]
        # claimed (id=5) excluded; zero-piece (id=2) first;
        # pending descending by ratio (70% → 30%), then achieved last (id=3)
        assert ids == [2, 1, 4, 3]

    @pytest.mark.asyncio
    async def test_achieved_low_pieces_after_pending_high_pieces(self, service):
        """Regression: an achieved reward with a small pieces_earned must still
        appear after a pending reward with a larger pieces_earned — the
        group rank takes precedence over numeric pieces_earned."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=2, pieces_required=2, reward_id=1),    # achieved
            _make_progress(pieces_earned=50, pieces_required=100, reward_id=2), # pending
            _make_progress(pieces_earned=0, pieces_required=10, reward_id=3),   # zero-piece
        ]

        result = await service.get_user_reward_progress("1")

        # zero-piece first, then pending, then achieved — regardless of pieces_earned magnitude
        assert [r.reward_id for r in result] == [3, 2, 1]

    @pytest.mark.asyncio
    async def test_multiple_achieved_sorted_by_pieces_earned(self, service):
        """Multiple ACHIEVED rewards inside the ready_to_claim bucket are sorted
        by pieces_earned ascending."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=1),  # achieved
            _make_progress(pieces_earned=2, pieces_required=2, reward_id=2),    # achieved
            _make_progress(pieces_earned=5, pieces_required=5, reward_id=3),    # achieved
        ]

        result = await service.get_user_reward_progress("1")

        # all achieved, ascending by pieces_earned: 2 → 5 → 10
        assert [r.reward_id for r in result] == [2, 3, 1]

    @pytest.mark.asyncio
    async def test_instant_reward_zero_required_goes_to_zero_bucket(self, service):
        """An instant ACHIEVED reward (pieces_earned=0, pieces_required=0)
        belongs to the zero-piece bucket, not ready_to_claim — the zero-piece
        check takes precedence over status."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=0, pieces_required=0, reward_id=1),    # instant achieved
            _make_progress(pieces_earned=4, pieces_required=10, reward_id=2),   # pending
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=3),  # achieved
        ]

        result = await service.get_user_reward_progress("1")

        # instant reward (id=1) goes to zero-piece bucket → comes first,
        # ahead of both pending and ready_to_claim
        assert [r.reward_id for r in result] == [1, 2, 3]

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_one_piece_away_is_ordered_by_pieces_earned(self, service):
        """Zero-piece rewards appear first, then pending sorted by pieces_earned, then achieved rewards last."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=9, pieces_required=10, reward_id=1),   # pending
            _make_progress(pieces_earned=10, pieces_required=10, reward_id=2),  # achieved
            _make_progress(pieces_earned=0, pieces_required=1, reward_id=3),    # zero-piece
        ]

        result = await service.get_user_reward_progress("1")

        ids = [r.reward_id for r in result]
        # zero-piece (id=3) first, then pending (id=1), then achieved (id=2)
        assert ids == [3, 1, 2]

    @pytest.mark.asyncio
    async def test_equal_completion_ratio_preserves_repo_order(self, service):
        """Rewards with the same completion ratio keep their repository order (stable sort)."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),  # 50%
            _make_progress(pieces_earned=2, pieces_required=4, reward_id=2),   # 50%
            _make_progress(pieces_earned=3, pieces_required=6, reward_id=3),   # 50%
        ]

        result = await service.get_user_reward_progress("1")

        assert [r.reward_id for r in result] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_pieces_required_none_goes_to_zero_piece_group(self, service):
        """Reward with pieces_required=None is bucketed into zero-piece (first)."""
        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=5, pieces_required=10, reward_id=1),     # non-zero
            _make_progress(pieces_earned=3, pieces_required=None, reward_id=2),   # zero-piece (no required)
        ]

        result = await service.get_user_reward_progress("1")

        # zero-piece (pieces_required=None) first, then non-zero
        assert [r.reward_id for r in result] == [2, 1]

    @pytest.mark.asyncio
    async def test_django_model_pieces_required_via_safe_getter(self, service):
        """Regression: real Django RewardProgress has no `pieces_required` field
        directly — it lives on the related Reward and is exposed via
        `_get_pieces_required_safe()`. Service must read through that method,
        not assume `p.pieces_required` is a direct attribute, or every reward
        falls into the zero-piece bucket and the order collapses to the
        repository's alphabetical sort.
        """
        from types import SimpleNamespace
        from src.models.reward_progress import RewardStatus

        def _django_like(*, pieces_earned, pieces_required, reward_id, claimed=False):
            obj = SimpleNamespace(
                user_id=42,
                reward_id=reward_id,
                pieces_earned=pieces_earned,
                claimed=claimed,
                times_claimed=0,
                _cached_pieces_required=pieces_required,
                reward=SimpleNamespace(id=reward_id, pieces_required=pieces_required, is_recurring=False),
            )
            obj._get_pieces_required_safe = lambda: obj._cached_pieces_required
            obj.get_status = lambda: (
                RewardStatus.CLAIMED if obj.claimed
                else RewardStatus.ACHIEVED if obj.pieces_earned >= obj._cached_pieces_required
                else RewardStatus.PENDING
            )
            return obj

        service.progress_repo.get_all_by_user.return_value = [
            _django_like(pieces_earned=10, pieces_required=10, reward_id=1),  # achieved
            _django_like(pieces_earned=5, pieces_required=7, reward_id=2),    # pending
            _django_like(pieces_earned=5, pieces_required=5, reward_id=3),    # achieved
            _django_like(pieces_earned=8, pieces_required=20, reward_id=4),   # pending
        ]

        result = await service.get_user_reward_progress("1")
        ids = [r.reward_id for r in result]
        # pending sorted by completion ratio DESC: id=2 (5/7=71%), id=4 (8/20=40%)
        # then ready_to_claim sorted by pieces_earned ASC: id=3 (5), id=1 (10)
        assert ids == [2, 4, 3, 1], (
            "Service must bucket Django-style RewardProgress correctly; "
            f"got alphabetical/insertion order {ids}"
        )

    @pytest.mark.asyncio
    async def test_synthetic_active_reward_appears_in_zero_piece_group(self, service):
        """An active reward without a progress row is synthesized as zero-piece and appears first."""
        from unittest.mock import Mock

        reward_no_progress = Mock()
        reward_no_progress.id = 42
        reward_no_progress.pieces_required = 4
        reward_no_progress.is_recurring = False

        service.progress_repo.get_all_by_user.return_value = [
            _make_progress(pieces_earned=2, pieces_required=10, reward_id=1),  # non-zero
        ]
        service.reward_repo.get_all_active.return_value = [reward_no_progress]

        result = await service.get_user_reward_progress("1")

        assert [r.reward_id for r in result] == [42, 1]
        assert result[0].pieces_earned == 0

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, service):
        """Empty input returns empty output."""
        service.progress_repo.get_all_by_user.return_value = []

        result = await service.get_user_reward_progress("1")

        assert result == []
