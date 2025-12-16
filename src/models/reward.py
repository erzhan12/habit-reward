"""Reward model with support for cumulative rewards."""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class RewardType(str, Enum):
    """Types of rewards available in the system."""
    VIRTUAL = "virtual"
    REAL = "real"
    NONE = "none"


class Reward(BaseModel):
    """Reward model with unified progress tracking."""

    id: str | int | None = None  # Airtable record ID (str) or Django PK (int)
    name: str = Field(..., description="Reward name")
    weight: float = Field(default=1.0, description="Reward weight for selection probability")
    type: RewardType = Field(..., description="Reward type")
    pieces_required: int = Field(default=1, description="Number of pieces needed (1 for instant rewards)")
    piece_value: float | None = Field(default=None, description="Value of each piece earned")
    max_daily_claims: int | None = Field(default=None, description="Maximum times this reward can be claimed per day (NULL or 0 = unlimited)")
    is_recurring: bool = Field(default=True, description="If True, reward can be claimed multiple times. If False, reward auto-deactivates after first claim.")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Coffee at favorite cafe",
                "weight": 1.0,
                "type": "real",
                "pieces_required": 10,
                "piece_value": 0.5
            }
        }
    )
