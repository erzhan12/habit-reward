"""Reward model with support for cumulative rewards."""

from enum import Enum
from pydantic import BaseModel, Field


class RewardType(str, Enum):
    """Types of rewards available in the system."""
    VIRTUAL = "virtual"
    REAL = "real"
    NONE = "none"
    CUMULATIVE = "cumulative"


class Reward(BaseModel):
    """Reward model with cumulative reward support."""

    id: str | None = None  # Airtable record ID
    name: str = Field(..., description="Reward name")
    weight: float = Field(default=1.0, description="Reward weight for selection probability")
    type: RewardType = Field(..., description="Reward type")
    is_cumulative: bool = Field(default=False, description="Whether reward accumulates pieces")
    pieces_required: int | None = Field(default=None, description="Number of pieces needed for cumulative rewards")
    piece_value: float | None = Field(default=None, description="Value of each piece earned")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "name": "Coffee at favorite cafe",
                "weight": 1.0,
                "type": "cumulative",
                "is_cumulative": True,
                "pieces_required": 10,
                "piece_value": 0.5
            }
        }

    def validate_cumulative(self) -> bool:
        """Validate cumulative reward has required fields."""
        if self.is_cumulative:
            return self.pieces_required is not None and self.piece_value is not None
        return True
