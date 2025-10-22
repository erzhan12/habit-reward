"""Result model for habit completion responses."""

from pydantic import BaseModel, Field, ConfigDict
from src.models.reward import Reward
from src.models.reward_progress import RewardProgress


class HabitCompletionResult(BaseModel):
    """Response model for habit completion containing all relevant data."""

    habit_confirmed: bool = Field(..., description="Whether habit was successfully logged")
    habit_name: str = Field(..., description="Name of the completed habit")
    reward: Reward | None = Field(default=None, description="Reward received (if any)")
    streak_count: int = Field(..., description="Current streak for this habit")
    cumulative_progress: RewardProgress | None = Field(default=None, description="Progress on cumulative reward (if applicable)")
    motivational_quote: str | None = Field(default=None, description="Optional motivational message")
    # Boolean flag indicating if user received a meaningful reward (not "none" type)
    # Used for: reward deduplication, progress tracking, analytics, and user feedback
    # True = real/virtual/cumulative reward awarded, False = "none" reward (no actual reward)
    got_reward: bool = Field(default=False, description="Whether a non-none reward was received")
    total_weight_applied: float = Field(..., description="Total weight used in calculation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "habit_confirmed": True,
                "habit_name": "Walking",
                "reward": {
                    "name": "Coffee at favorite cafe",
                    "type": "real",
                    "pieces_required": 10
                },
                "streak_count": 5,
                "got_reward": True,
                "total_weight_applied": 1.5
            }
        }
    )
