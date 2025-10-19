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

    id: str | None = None  # Airtable record ID
    name: str = Field(..., description="Reward name")
    weight: float = Field(default=1.0, description="Reward weight for selection probability")
    type: RewardType = Field(..., description="Reward type")
    pieces_required: int = Field(default=1, description="Number of pieces needed (1 for instant rewards)")
    piece_value: float | None = Field(default=None, description="Value of each piece earned")

    model_config = ConfigDict(
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
