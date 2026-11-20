"""Habit model representing trackable habits."""

from datetime import date, datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class Habit(BaseModel):
    """Habit model with weight and category."""

    id: str | int | None = None  # Airtable record ID (str) or Django PK (int)
    user_id: str | int | None = Field(default=None, description="Owning user id")
    name: str = Field(..., description="Habit name")
    weight: int = Field(default=0, ge=0, le=30, description="Habit weight (0-30); counts toward daily points only, does not affect the reward chance since feature 0048")
    category: str | None = Field(default=None, description="Habit category (e.g., health, productivity)")
    allowed_skip_days: int = Field(default=0, ge=0, description="Number of consecutive days user can skip without breaking streak (0 for strict)")
    exempt_weekdays: list[int] = Field(default_factory=list, description="List of weekday numbers (1=Mon, 7=Sun) that don't count against streak")
    streak_epoch: date | None = Field(default=None, description="User-local date from which completions count toward the streak (feature 0048); null: all history counts")
    active: bool = Field(default=True, description="Whether habit is active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the habit was created",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Walking",
                "weight": 0,
                "category": "health",
                "allowed_skip_days": 0,
                "exempt_weekdays": [],
                "active": True
            }
        }
    )
