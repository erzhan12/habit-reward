"""Reward progress cards component for Streamlit dashboard."""

import asyncio
import streamlit as st

from src.core.repositories import reward_repository, reward_progress_repository
from src.core.models import RewardProgress


def render_reward_progress(user_id: int):
    """
    Render reward progress cards with progress bars.

    Args:
        user_id: Django user ID (integer)
    """
    st.subheader("🎁 Cumulative Reward Progress")

    progress_list = asyncio.run(reward_progress_repository.get_all_by_user(user_id))

    if not progress_list:
        st.info("No reward progress yet. Complete habits to earn reward pieces!")
        return

    # Group by status
    pending = [p for p in progress_list if p.get_status() == RewardProgress.RewardStatus.PENDING]
    achieved = [p for p in progress_list if p.get_status() == RewardProgress.RewardStatus.ACHIEVED]
    completed = [p for p in progress_list if p.get_status() == RewardProgress.RewardStatus.CLAIMED]

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        f"🕒 Pending ({len(pending)})",
        f"⏳ Achieved ({len(achieved)})",
        f"✅ Completed ({len(completed)})"
    ])

    with tab1:
        if pending:
            for progress in pending:
                render_progress_card(progress)
        else:
            st.info("No pending rewards")

    with tab2:
        if achieved:
            for progress in achieved:
                render_progress_card(progress)
        else:
            st.info("No achieved rewards")

    with tab3:
        if completed:
            for progress in completed:
                render_progress_card(progress)
        else:
            st.info("No completed rewards")


def render_progress_card(progress):
    """
    Render a single reward progress card.

    Args:
        progress: RewardProgress object
    """
    reward = asyncio.run(reward_repository.get_by_id(progress.reward_id))

    if not reward:
        return

    with st.container():
        # Card header
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{progress.get_status_emoji()} {reward.name}**")

        with col2:
            st.markdown(f"*{progress.pieces_earned}/{progress.get_pieces_required()}*")

        # Progress bar
        progress_value = progress.pieces_earned / (progress.get_pieces_required() or 1)
        st.progress(min(progress_value, 1.0))

        # Additional info
        if reward.piece_value:
            total_value = progress.pieces_earned * reward.piece_value
            target_value = (progress.get_pieces_required() or 0) * reward.piece_value
            st.caption(f"Value: ${total_value:.2f} / ${target_value:.2f}")

        if progress.get_status() == RewardProgress.RewardStatus.ACHIEVED:
            st.success("⏳ Ready to claim!")

        st.divider()
