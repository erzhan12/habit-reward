"""Streak visualization component."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.services.streak_service import streak_service
from src.airtable.repositories import habit_repository


def render_streak_chart(user_id: str):
    """
    Render bar chart showing current streaks for each habit.

    Args:
        user_id: Airtable record ID of the user
    """
    st.subheader("🔥 Current Streaks by Habit")

    streaks_dict = streak_service.get_all_streaks_for_user(user_id)

    if not streaks_dict:
        st.info("No streaks yet. Complete habits to start building streaks!")
        return

    # Prepare data
    data = []
    for habit_id, streak_count in streaks_dict.items():
        habit = habit_repository.get_by_id(habit_id)
        if habit:
            data.append({
                "Habit": habit.name,
                "Streak": streak_count,
                "Emoji": "🔥" * min(streak_count, 5)
            })

    # Sort by streak count
    data.sort(key=lambda x: x["Streak"], reverse=True)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create bar chart
    fig = px.bar(
        df,
        x="Habit",
        y="Streak",
        title="Current Streaks",
        text="Streak",
        color="Streak",
        color_continuous_scale="Reds"
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Days",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show table with emojis
    st.dataframe(
        df[["Habit", "Emoji", "Streak"]],
        use_container_width=True,
        hide_index=True
    )
