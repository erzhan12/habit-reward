"""User repository for Airtable Users table."""

import logging
from typing import Any
from pyairtable.formulas import match

from src.airtable.base_repository import BaseRepository
from src.models.user import User

# Configure logging
logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for Users table."""

    def __init__(self):
        """Initialize UserRepository."""
        super().__init__("Users")

    def create(self, user: User) -> User:
        """Create a new user."""
        logger.info(f"Creating new user: {user.name} (telegram_id: {user.telegram_id})")
        record = self.table.create({
            "telegram_id": user.telegram_id,
            "name": user.name,
            "is_active": user.is_active
        })
        return User(**self._record_to_dict(record))

    def get_by_telegram_id(self, telegram_id: str) -> User | None:
        """Get user by Telegram ID."""
        logger.debug(f"Looking up user by telegram_id: {telegram_id}")
        formula = match({"telegram_id": telegram_id})
        records = self.table.all(formula=formula)
        if not records:
            logger.debug(f"No user found with telegram_id: {telegram_id}")
            return None
        return User(**self._record_to_dict(records[0]))

    def get_by_id(self, user_id: str) -> User | None:
        """Get user by Airtable record ID."""
        logger.debug(f"Looking up user by id: {user_id}")
        try:
            record = self.table.get(user_id)
            return User(**self._record_to_dict(record))
        except Exception as e:
            logger.warning(f"Failed to get user {user_id}: {e}")
            return None

    def update(self, user_id: str, updates: dict[str, Any]) -> User:
        """Update user fields."""
        logger.info(f"Updating user {user_id} with: {updates}")
        record = self.table.update(user_id, updates)
        return User(**self._record_to_dict(record))


# Global repository instance
user_repository = UserRepository()
