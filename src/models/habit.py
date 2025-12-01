"""Habit model representing trackable habits."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class Habit(BaseModel):
    """Habit model with weight and category."""

    id: str | int | None = None  # Airtable record ID (str) or Django PK (int)
    user_id: str | int | None = Field(default=None, description="Owning user id")
    name: str = Field(..., description="Habit name")
    weight: int = Field(default=10, ge=1, le=100, description="Habit base weight for reward calculations (1-100)")
    category: str | None = Field(default=None, description="Habit category (e.g., health, productivity)")
    allowed_skip_days: int = Field(default=0, ge=0, description="Number of consecutive days user can skip without breaking streak (0 for strict)")
    exempt_weekdays: list[int] = Field(default_factory=list, description="List of weekday numbers (1=Mon, 7=Sun) that don't count against streak")
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
                "weight": 10,
                "category": "health",
                "allowed_skip_days": 0,
                "exempt_weekdays": [],
                "active": True
            }
        }
    )
