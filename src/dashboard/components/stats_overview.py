"""Statistics overview component for dashboard."""

import asyncio
from decimal import Decimal
import streamlit as st

from src.core.repositories import reward_progress_repository, reward_repository
from src.models.reward_progress import RewardStatus


def render_stats_overview(user_id: int):
    """
    Render summary statistics cards.

    Args:
        user_id: Django user ID (integer)
    """
    st.subheader("📊 Reward Value Overview")

    progress_list = asyncio.run(reward_progress_repository.get_all_by_user(user_id))

    if not progress_list:
        st.info("No reward data yet")
        return

    # Calculate totals
    # Use Decimal to match Django's DecimalField type for piece_value
    total_value_earned = Decimal(0)
    total_value_claimed = Decimal(0)
    pending_value = Decimal(0)

    for progress in progress_list:
        reward = asyncio.run(reward_repository.get_by_id(progress.reward_id))

        if not reward or not reward.piece_value:
            continue

        earned_value = progress.pieces_earned * reward.piece_value

        if progress.get_status() == RewardStatus.COMPLETED:
            total_value_claimed += earned_value
        elif progress.get_status() == RewardStatus.ACHIEVED:
            pending_value += earned_value
        else:
            # Pending status
            pass

        total_value_earned += earned_value

    # Display metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="💰 Total Value Earned",
            value=f"${total_value_earned:.2f}"
        )

    with col2:
        st.metric(
            label="✅ Value Claimed",
            value=f"${total_value_claimed:.2f}"
        )

    with col3:
        st.metric(
            label="⏳ Pending Value",
            value=f"${pending_value:.2f}"
        )

    # Progress toward claimed
    if total_value_earned > 0:
        claim_rate = (total_value_claimed / total_value_earned) * 100
        st.progress(claim_rate / 100)
        st.caption(f"Claim Rate: {claim_rate:.1f}%")
