"""Reward progress model for tracking cumulative reward completion."""

from enum import Enum
from pydantic import BaseModel, Field, computed_field, ConfigDict


class RewardStatus(str, Enum):
    """Status of reward progress."""
    PENDING = "🕒 Pending"
    ACHIEVED = "⏳ Achieved"
    CLAIMED = "✅ Claimed"


class RewardProgress(BaseModel):
    """Model for tracking progress toward rewards."""

    # --- Regular fields ---
    id: str | int | None = None  # Airtable or DB PK
    user_id: str | int = Field(..., description="Link to Users table")
    reward_id: str | int = Field(..., description="Link to Rewards table")
    pieces_earned: int = Field(default=0, description="Number of pieces earned so far")
    pieces_required: int | None = Field(default=None, description="Cached from reward for calculations")
    claimed: bool = Field(default=False, description="Whether user has claimed this reward")
    reward: object | None = Field(default=None, description="Optional reward payload for convenience")

    # --- Computed fields (always derived, never set directly) ---
    @computed_field
    @property
    def status(self) -> RewardStatus:
        """Derived from claimed/pieces_earned/pieces_required (mirrors Django model logic)."""
        if self.claimed:
            return RewardStatus.CLAIMED
        if self.pieces_required is not None and self.pieces_earned >= self.pieces_required:
            return RewardStatus.ACHIEVED
        return RewardStatus.PENDING

    @computed_field
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if not self.pieces_required or self.pieces_required == 0:
            return 0.0
        return min((self.pieces_earned / self.pieces_required) * 100, 100.0)

    @computed_field
    @property
    def status_emoji(self) -> str:
        """Get emoji for current status."""
        return self.status.value.split()[0]

    # --- Compatibility methods (match Django model interface) ---
    def get_status(self) -> RewardStatus:
        """Backwards-compatible helper for legacy call sites/tests."""
        return self.status

    def get_pieces_required(self) -> int:
        """Get pieces required for this reward.

        Returns the pieces_required field value, falling back to 1
        when pieces_required is None (no linked reward loaded).
        """
        if self.pieces_required is not None:
            return self.pieces_required
        # Fallback: try to get from reward object if available
        if self.reward and hasattr(self.reward, 'pieces_required'):
            return self.reward.pieces_required
        return 1  # Default fallback

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": "recXXXXXXXXXXXXXX",
                "reward_id": "recYYYYYYYYYYYYYY",
                "pieces_earned": 7,
                "pieces_required": 10,
                "status": "🕒 Pending"
            }
        }
    )
