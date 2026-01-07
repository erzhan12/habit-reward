"""Main Streamlit dashboard application."""

import asyncio
import streamlit as st

from src.config import settings
from src.core.repositories import user_repository
from src.dashboard.components.habit_logs import render_habit_logs
from src.dashboard.components.reward_progress import render_reward_progress
from src.dashboard.components.actionable_rewards import render_actionable_rewards
from src.dashboard.components.stats_overview import render_stats_overview
from src.dashboard.components.streak_chart import render_streak_chart


# Page configuration
st.set_page_config(
    page_title="Habit Reward Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🎯 Habit Reward Dashboard")

# Sidebar - User selection
with st.sidebar:
    st.header("User Selection")

    # For now, use default telegram_id from settings
    # In production, this could be a dropdown of all users
    if settings.default_user_telegram_id:
        telegram_id = settings.default_user_telegram_id
        user = asyncio.run(user_repository.get_by_telegram_id(telegram_id))

        if user:
            st.success(f"Logged in as: {user.name}")
            user_id = user.id
        else:
            st.error("Default user not found in database")
            st.stop()
    else:
        st.warning("No default user configured")
        telegram_id = st.text_input("Enter your Telegram ID:")

        if telegram_id:
            user = asyncio.run(user_repository.get_by_telegram_id(telegram_id))
            if user:
                st.success(f"Found: {user.name}")
                user_id = user.id
            else:
                st.error("User not found")
                st.stop()
        else:
            st.stop()

    st.divider()

    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.divider()

    # Info
    st.caption("Habit Reward System v1.0")
    st.caption("Built with Streamlit & Django")


# Main content
if 'user_id' in locals():
    # Overview stats
    render_stats_overview(user_id)

    st.divider()

    # Actionable rewards
    render_actionable_rewards(user_id)

    st.divider()

    # Two-column layout
    col1, col2 = st.columns(2)

    with col1:
        # Reward progress
        render_reward_progress(user_id)

    with col2:
        # Streak chart
        render_streak_chart(user_id)

    st.divider()

    # Habit logs (full width)
    render_habit_logs(user_id, limit=50)
