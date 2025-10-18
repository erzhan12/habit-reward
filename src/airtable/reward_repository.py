"""Reward repository for Airtable Rewards table."""

import logging
from typing import Any
from pyairtable.formulas import match

from src.airtable.base_repository import BaseRepository
from src.models.reward import Reward, RewardType

# Configure logging
logger = logging.getLogger(__name__)


class RewardRepository(BaseRepository):
    """Repository for Rewards table."""

    def __init__(self):
        """Initialize RewardRepository."""
        super().__init__("Rewards")

    def create(self, reward: Reward) -> Reward:
        """Create a new reward."""
        logger.info(f"Creating new reward: {reward.name} (type: {reward.type})")
        data = {
            "name": reward.name,
            "weight": reward.weight,
            "type": reward.type.value,
            "is_cumulative": reward.is_cumulative
        }
        if reward.pieces_required is not None:
            data["pieces_required"] = reward.pieces_required
        if reward.piece_value is not None:
            data["piece_value"] = reward.piece_value

        record = self.table.create(data)
        return self._record_to_reward(record)

    def get_all_active(self) -> list[Reward]:
        """Get all active rewards."""
        logger.debug("Fetching all active rewards")
        records = self.table.all()
        rewards = [self._record_to_reward(record) for record in records]
        logger.debug(f"Found {len(rewards)} active rewards")
        return rewards

    def get_by_id(self, reward_id: str) -> Reward | None:
        """Get reward by Airtable record ID."""
        logger.debug(f"Looking up reward by id: {reward_id}")
        try:
            record = self.table.get(reward_id)
            return self._record_to_reward(record)
        except Exception as e:
            logger.warning(f"Failed to get reward {reward_id}: {e}")
            return None

    def get_by_name(self, name: str) -> Reward | None:
        """Get reward by name."""
        logger.debug(f"Looking up reward by name: {name}")
        formula = match({"name": name})
        records = self.table.all(formula=formula)
        if not records:
            logger.debug(f"No reward found with name: {name}")
            return None
        return self._record_to_reward(records[0])

    def _record_to_reward(self, record: dict[str, Any]) -> Reward:
        """Convert Airtable record to Reward model."""
        fields = self._record_to_dict(record)
        fields["type"] = RewardType(fields.get("type", "none"))
        return Reward(**fields)


# Global repository instance
reward_repository = RewardRepository()
