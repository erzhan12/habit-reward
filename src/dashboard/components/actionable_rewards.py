"""Actionable rewards component with claim buttons."""

import streamlit as st

from src.airtable.repositories import reward_repository, reward_progress_repository
from src.services.reward_service import reward_service


def render_actionable_rewards(user_id: str):
    """
    Render achieved rewards with action buttons.

    Args:
        user_id: Airtable record ID of the user
    """
    st.subheader("⏳ Rewards Ready to Claim")

    achieved_progress = reward_progress_repository.get_achieved_by_user(user_id)

    if not achieved_progress:
        st.info("No rewards ready to claim yet. Keep completing habits!")
        return

    for progress in achieved_progress:
        reward = reward_repository.get_by_id(progress.reward_id)

        if not reward:
            continue

        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### 🎁 {reward.name}")
                st.markdown(
                    f"**Progress:** {progress.pieces_earned}/{progress.pieces_required} pieces"
                )

                if reward.piece_value:
                    total_value = (progress.pieces_required or 0) * reward.piece_value
                    st.markdown(f"**Value:** ${total_value:.2f}")

            with col2:
                if st.button(
                    "✅ Claim",
                    key=f"claim_{progress.id}",
                    use_container_width=True
                ):
                    try:
                        reward_service.mark_reward_claimed(user_id, reward.id)
                        st.success(f"Claimed: {reward.name}!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")

            st.divider()
