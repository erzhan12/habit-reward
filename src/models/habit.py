"""Habit model representing trackable habits."""

from pydantic import BaseModel, Field, ConfigDict


class Habit(BaseModel):
    """Habit model with weight and category."""

    id: str | None = None  # Airtable record ID
    name: str = Field(..., description="Habit name")
    weight: int = Field(default=10, ge=1, le=100, description="Habit base weight for reward calculations (1-100)")
    category: str | None = Field(default=None, description="Habit category (e.g., health, productivity)")
    active: bool = Field(default=True, description="Whether habit is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Walking",
                "weight": 10,
                "category": "health",
                "active": True
            }
        }
    )
