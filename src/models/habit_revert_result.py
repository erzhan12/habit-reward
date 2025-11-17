"""Result model for habit revert responses."""

from pydantic import BaseModel, Field, ConfigDict, computed_field

from src.models.reward_progress import RewardProgress as RewardProgressModel


class HabitRevertResult(BaseModel):
    """Response model for reverting habit completions."""

    habit_name: str = Field(..., description="Name of the habit being reverted")
    reward_reverted: bool = Field(default=False, description="Whether a reward was rolled back")
    reward_name: str | None = Field(default=None, description="Name of the reward affected, if any")
    reward_progress: RewardProgressModel | None = Field(default=None, description="Updated reward progress snapshot")
    success: bool = Field(default=True, description="Indicates the revert succeeded")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "habit_name": "Walking",
                "reward_reverted": True,
                "reward_name": "Coffee at favorite cafe",
                "reward_progress": {
                    "user_id": "user123",
                    "reward_id": "reward456",
                    "pieces_earned": 2,
                    "pieces_required": 5,
                    "claimed": False
                },
                "success": True
            }
        }
    )

    @computed_field
    @property
    def pieces_earned(self) -> int | None:
        """Expose pieces earned from nested progress for convenience."""
        if self.reward_progress is None:
            return None
        return self.reward_progress.pieces_earned

    @computed_field
    @property
    def pieces_required(self) -> int | None:
        """Expose pieces required from nested progress for convenience."""
        if self.reward_progress is None:
            return None
        return self.reward_progress.pieces_required
