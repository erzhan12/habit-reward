"""Async regression tests for reward service."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.services.reward_service import RewardService
from src.core.repositories import RewardRepository
from src.core.models import User, Reward


class ExplodingProgress:
    """Progress stand-in that verifies status calculation works correctly in async flows."""

    def __init__(self, pieces_earned: int, *, claimed: bool = False, progress_id: str = "prog1", reward = None) -> None:
        self.pieces_earned = pieces_earned
        self.claimed = claimed
        self.id = progress_id
        self.reward = reward

    def get_status(self):
        """Calculate status inline without synchronous ORM access."""
        from src.core.models import RewardProgress
        if self.claimed:
            return RewardProgress.RewardStatus.CLAIMED
        elif self.reward and self.pieces_earned >= self.reward.pieces_required:
            return RewardProgress.RewardStatus.ACHIEVED
        else:
            return RewardProgress.RewardStatus.PENDING


@pytest.mark.asyncio
async def test_update_reward_progress_skips_sync_status_lookup() -> None:
    """Ensure update path does not rely on synchronous RewardProgress.status property."""

    service = RewardService()
    reward = SimpleNamespace(pieces_required=2)
    progress = ExplodingProgress(pieces_earned=0, reward=reward)

    reward_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=reward)
    )

    updated_progress = SimpleNamespace(id="prog1", pieces_earned=1, claimed=False)

    progress_repo = SimpleNamespace(
        get_by_user_and_reward=AsyncMock(return_value=progress),
        update=AsyncMock(return_value=updated_progress)
    )

    service.reward_repo = reward_repo
    service.progress_repo = progress_repo

    result = await service.update_reward_progress(user_id=5, reward_id=2)

    assert result is updated_progress
    progress_repo.get_by_user_and_reward.assert_awaited_once()
    progress_repo.update.assert_awaited_once_with(progress.id, {"pieces_earned": 1})


@pytest.mark.asyncio
async def test_mark_reward_claimed_requires_achieved_without_status_property() -> None:
    """Validate claim guard rails work without ever touching RewardProgress.status."""

    service = RewardService()
    reward = SimpleNamespace(pieces_required=2)
    progress = ExplodingProgress(pieces_earned=0, reward=reward)

    reward_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=reward)
    )

    update_mock = AsyncMock()
    progress_repo = SimpleNamespace(
        get_by_user_and_reward=AsyncMock(return_value=progress),
        update=update_mock
    )

    service.reward_repo = reward_repo
    service.progress_repo = progress_repo

    with pytest.raises(ValueError):
        await service.mark_reward_claimed(user_id=5, reward_id=2)

    update_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reward_repository_create_with_pydantic_object() -> None:
    """Test creating reward via Pydantic object instance (not dict).

    This integration test ensures the repository's object-based creation path
    works correctly after the type field was removed.
    """
    from src.models.reward import Reward as PydanticReward

    # Create a test user
    user = await User.objects.acreate(
        telegram_id="999888777",
        name="Repository Test User",
        username="repo_test_user",
    )

    try:
        repo = RewardRepository()

        # Create reward using Pydantic object (not dict)
        pydantic_reward = PydanticReward(
            user_id=user.id,
            name="Test Repository Reward",
            weight=15.0,
            pieces_required=3,
            is_recurring=True,
            piece_value=2.5,
            max_daily_claims=2,
        )

        created = await repo.create(pydantic_reward)

        assert created.id is not None
        assert created.name == "Test Repository Reward"
        assert created.weight == 15.0
        assert created.pieces_required == 3
        assert created.is_recurring is True
        assert float(created.piece_value) == 2.5
        assert created.max_daily_claims == 2
    finally:
        # Cleanup
        await Reward.objects.filter(user=user).adelete()
        await user.adelete()


@pytest.mark.asyncio
async def test_reward_progress_repository_no_n_plus_one_queries() -> None:
    """Test that get_all_by_user uses select_related to avoid N+1 queries.

    This integration test ensures that fetching reward progress doesn't
    cause a separate query for each reward.
    """
    from src.core.repositories import RewardProgressRepository
    from src.core.models import RewardProgress
    from django.db import connection, reset_queries
    from django.conf import settings

    # Create test user
    user = await User.objects.acreate(
        telegram_id="888777666",
        name="N+1 Test User",
        username="n_plus_one_test",
    )

    rewards = []
    try:
        # Create 5 rewards with progress
        for i in range(5):
            reward = await Reward.objects.acreate(
                user=user,
                name=f"N+1 Test Reward {i}",
                weight=10.0,
                pieces_required=3,
            )
            rewards.append(reward)
            await RewardProgress.objects.acreate(
                user=user,
                reward=reward,
                pieces_earned=i,
            )

        repo = RewardProgressRepository()

        # Enable query logging
        reset_queries()

        # Fetch all progress - should be 1 query with select_related
        progress_list = await repo.get_all_by_user(user.id)

        # Verify we got all progress entries
        assert len(progress_list) == 5

        # Access reward on each progress - should NOT cause additional queries
        for progress in progress_list:
            _ = progress.reward.name  # This should use cached data

        # Check query count - should be 1 (or 2 if Django adds a transaction query)
        query_count = len(connection.queries)
        assert query_count <= 2, f"Expected 1-2 queries, got {query_count}: {connection.queries}"

    finally:
        # Cleanup
        await RewardProgress.objects.filter(user=user).adelete()
        await Reward.objects.filter(user=user).adelete()
        await user.adelete()
