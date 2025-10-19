"""Habit log model for tracking habit completions."""

from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict


class HabitLog(BaseModel):
    """Model for logging habit completions with streak tracking."""

    id: str | None = None  # Airtable record ID
    user_id: str = Field(..., description="Link to Users table (Airtable record ID)")
    habit_id: str = Field(..., description="Link to Habits table (Airtable record ID)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When habit was completed")
    reward_id: str | None = Field(default=None, description="Link to Rewards table (Airtable record ID)")
    got_reward: bool = Field(default=False, description="Whether a reward was given")
    streak_count: int = Field(default=1, description="Current streak for this habit")
    habit_weight: int = Field(..., description="Habit weight at time of completion (1-100)")
    total_weight_applied: float = Field(..., description="Total calculated weight (habit × user × streak multiplier)")
    last_completed_date: date = Field(default_factory=date.today, description="Date of completion (for streak tracking)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "recXXXXXXXXXXXXXX",
                "habit_id": "recYYYYYYYYYYYYYY",
                "reward_id": "recZZZZZZZZZZZZZZ",
                "got_reward": True,
                "streak_count": 5,
                "habit_weight": 10,
                "total_weight_applied": 15.0,
                "last_completed_date": "2024-01-15"
            }
        }
    )
