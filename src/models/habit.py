"""Habit model representing trackable habits."""

from pydantic import BaseModel, Field


class Habit(BaseModel):
    """Habit model with weight and category."""

    id: str | None = None  # Airtable record ID
    name: str = Field(..., description="Habit name")
    weight: float = Field(default=1.0, description="Habit base weight for reward calculations")
    category: str | None = Field(default=None, description="Habit category (e.g., health, productivity)")
    active: bool = Field(default=True, description="Whether habit is active")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "name": "Walking",
                "weight": 1.0,
                "category": "health",
                "active": True
            }
        }
