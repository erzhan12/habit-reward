"""Habit repository for Airtable Habits table."""

import logging
from pyairtable.formulas import match

from src.airtable.base_repository import BaseRepository
from src.models.habit import Habit

# Configure logging
logger = logging.getLogger(__name__)


class HabitRepository(BaseRepository):
    """Repository for Habits table."""

    def __init__(self):
        """Initialize HabitRepository."""
        super().__init__("Habits")

    def create(self, habit: Habit) -> Habit:
        """Create a new habit."""
        logger.info(f"Creating new habit: {habit.name} (category: {habit.category})")
        record = self.table.create({
            "name": habit.name,
            "weight": habit.weight,
            "category": habit.category,
            "active": habit.active
        })
        return Habit(**self._record_to_dict(record))

    def get_by_name(self, name: str) -> Habit | None:
        """Get habit by name."""
        logger.debug(f"Looking up habit by name: {name}")
        formula = match({"name": name})
        records = self.table.all(formula=formula)
        if not records:
            logger.debug(f"No habit found with name: {name}")
            return None
        return Habit(**self._record_to_dict(records[0]))

    def get_all_active(self) -> list[Habit]:
        """Get all active habits."""
        logger.debug("Fetching all active habits")
        formula = match({"active": True})
        records = self.table.all(formula=formula)
        habits = [Habit(**self._record_to_dict(record)) for record in records]
        logger.debug(f"Found {len(habits)} active habits")
        return habits

    def get_by_id(self, habit_id: str) -> Habit | None:
        """Get habit by Airtable record ID."""
        logger.debug(f"Looking up habit by id: {habit_id}")
        try:
            record = self.table.get(habit_id)
            return Habit(**self._record_to_dict(record))
        except Exception as e:
            logger.warning(f"Failed to get habit {habit_id}: {e}")
            return None


# Global repository instance
habit_repository = HabitRepository()
