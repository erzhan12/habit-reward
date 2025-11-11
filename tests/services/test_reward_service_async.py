"""Async regression tests for reward service."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.services.reward_service import RewardService


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
