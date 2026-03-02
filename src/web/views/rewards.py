"""Reward progress and claiming views."""

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from inertia import render as inertia_render

from src.core.repositories import reward_repository
from src.services.reward_service import reward_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


async def rewards_page(request):
    """Reward progress cards with claim functionality."""
    user = request.user

    # In async context, service returns coroutine via run_sync_or_async
    progress_list = await maybe_await(
        reward_service.get_user_reward_progress(str(user.id))
    )

    rewards = []
    for progress in progress_list:
        reward = progress.reward
        if not reward:
            continue
        rewards.append({
            "id": reward.id,
            "name": reward.name,
            "piecesEarned": progress.pieces_earned,
            "piecesRequired": progress.get_pieces_required(),
            "status": progress.get_status().name,
            "isRecurring": reward.is_recurring,
        })

    # Get claimed rewards (any reward with times_claimed > 0)
    claimed_list = await maybe_await(
        reward_service.get_claimed_rewards(str(user.id))
    )

    claimed_rewards = []
    for progress in claimed_list:
        reward = progress.reward
        if not reward:
            continue
        claimed_rewards.append({
            "id": reward.id,
            "name": reward.name,
            "claimedAt": progress.updated_at.isoformat() if progress.updated_at else None,
            "timesClaimed": getattr(progress, 'times_claimed', 0),
        })

    return inertia_render(request, "Rewards", props={
        "rewards": rewards,
        "claimedRewards": claimed_rewards,
    })


@require_POST
async def claim_reward(request, reward_id):
    """Claim an achieved reward."""
    user = request.user

    # Verify reward belongs to user
    reward = await reward_repository.get_by_id(reward_id)
    if not reward or reward.user_id != user.id:
        logger.warning("User %s attempted to claim reward %s (not found or unauthorized)", user.id, reward_id)
        return redirect("/rewards/")

    try:
        await maybe_await(
            reward_service.mark_reward_claimed(str(user.id), str(reward_id))
        )
    except ValueError as e:
        logger.warning("Reward claim failed: %s", e)
        messages.error(request, str(e))

    return redirect("/rewards/")
