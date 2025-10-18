"""Habit logs table component for Streamlit dashboard."""

import streamlit as st
import pandas as pd

from src.airtable.repositories import habit_log_repository, habit_repository


def render_habit_logs(user_id: str, limit: int = 50):
    """
    Render habit logs table showing recent completions.

    Args:
        user_id: Airtable record ID of the user
        limit: Maximum number of logs to display
    """
    st.subheader("📋 Recent Habit Completions")

    logs = habit_log_repository.get_logs_by_user(user_id, limit=limit)

    if not logs:
        st.info("No habit logs yet. Start completing habits!")
        return

    # Prepare data for table
    data = []
    for log in logs:
        habit = habit_repository.get_by_id(log.habit_id)
        habit_name = habit.name if habit else "Unknown"

        data.append({
            "Date": log.last_completed_date.strftime("%Y-%m-%d"),
            "Habit": habit_name,
            "Streak": f"🔥 {log.streak_count}",
            "Got Reward": "✅" if log.got_reward else "❌",
            "Total Weight": f"{log.total_weight_applied:.2f}",
            "Time": log.timestamp.strftime("%H:%M")
        })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Show summary stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Completions", len(logs))

    with col2:
        rewards_earned = sum(1 for log in logs if log.got_reward)
        reward_rate = (rewards_earned / len(logs) * 100) if logs else 0
        st.metric("Reward Rate", f"{reward_rate:.1f}%")

    with col3:
        max_streak = max((log.streak_count for log in logs), default=0)
        st.metric("Max Streak", f"🔥 {max_streak}")
