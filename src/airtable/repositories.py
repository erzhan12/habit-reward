"""Repository pattern implementation for Airtable tables."""

import logging
from datetime import date, datetime
from typing import Any
from pyairtable.api.table import Table
from pyairtable.formulas import match

from src.airtable.client import airtable_client
from src.models.user import User
from src.models.habit import Habit
from src.models.reward import Reward, RewardType
from src.models.reward_progress import RewardProgress, RewardStatus
from src.models.habit_log import HabitLog

# Configure logging
logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, table_name: str):
        """Initialize repository with table name."""
        self.table: Table = airtable_client.get_table(table_name)

    def _record_to_dict(self, record: dict[str, Any]) -> dict[str, Any]:
        """Convert Airtable record to dict with id."""
        fields = record.get("fields", {})
        fields["id"] = record.get("id")
        return fields


class UserRepository(BaseRepository):
    """Repository for Users table."""

    def __init__(self):
        """Initialize UserRepository."""
        super().__init__("Users")

    def create(self, user: User) -> User:
        """Create a new user."""
        record = self.table.create({
            "telegram_id": user.telegram_id,
            "name": user.name,
            "is_active": user.is_active,
            "language": user.language
        })
        return User(**self._record_to_dict(record))

    def get_by_telegram_id(self, telegram_id: str) -> User | None:
        """Get user by Telegram ID."""
        formula = match({"telegram_id": telegram_id})
        records = self.table.all(formula=formula)
        if not records:
            return None
        return User(**self._record_to_dict(records[0]))

    def get_by_id(self, user_id: str) -> User | None:
        """Get user by Airtable record ID."""
        try:
            record = self.table.get(user_id)
            return User(**self._record_to_dict(record))
        except Exception:
            return None

    def update(self, user_id: str, updates: dict[str, Any]) -> User:
        """Update user fields."""
        record = self.table.update(user_id, updates)
        return User(**self._record_to_dict(record))


class HabitRepository(BaseRepository):
    """Repository for Habits table."""

    def __init__(self):
        """Initialize HabitRepository."""
        super().__init__("Habits")

    def create(self, habit: Habit) -> Habit:
        """Create a new habit."""
        record = self.table.create({
            "name": habit.name,
            "weight": habit.weight,
            "category": habit.category,
            "active": habit.active
        })
        return Habit(**self._record_to_dict(record))

    def get_by_name(self, name: str) -> Habit | None:
        """Get habit by name."""
        formula = match({"name": name})
        records = self.table.all(formula=formula)
        if not records:
            return None
        return Habit(**self._record_to_dict(records[0]))

    def get_all_active(self) -> list[Habit]:
        """Get all active habits."""
        formula = match({"active": True})
        records = self.table.all(formula=formula)
        return [Habit(**self._record_to_dict(record)) for record in records]

    def get_by_id(self, habit_id: str) -> Habit | None:
        """Get habit by Airtable record ID."""
        try:
            record = self.table.get(habit_id)
            return Habit(**self._record_to_dict(record))
        except Exception:
            return None

    def update(self, habit_id: str, updates: dict[str, Any]) -> Habit:
        """Update habit fields in Airtable.

        Args:
            habit_id: Airtable record ID
            updates: Dict with fields to update (name, weight, category, active)

        Returns:
            Updated Habit object
        """
        record = self.table.update(habit_id, updates)
        return Habit(**self._record_to_dict(record))

    def soft_delete(self, habit_id: str) -> Habit:
        """Soft delete habit by setting active=false.

        Args:
            habit_id: Airtable record ID

        Returns:
            Updated Habit object with active=False
        """
        return self.update(habit_id, {"active": False})


class RewardRepository(BaseRepository):
    """Repository for Rewards table."""

    def __init__(self):
        """Initialize RewardRepository."""
        super().__init__("Rewards")

    def create(self, reward: Reward) -> Reward:
        """Create a new reward."""
        data = {
            "name": reward.name,
            "weight": reward.weight,
            "type": reward.type.value,
            "pieces_required": reward.pieces_required
        }
        if reward.piece_value is not None:
            data["piece_value"] = reward.piece_value

        record = self.table.create(data)
        return self._record_to_reward(record)

    def get_all_active(self) -> list[Reward]:
        """Get all active rewards."""
        records = self.table.all()
        return [self._record_to_reward(record) for record in records]

    def get_by_id(self, reward_id: str) -> Reward | None:
        """Get reward by Airtable record ID."""
        try:
            record = self.table.get(reward_id)
            return self._record_to_reward(record)
        except Exception:
            return None

    def get_by_name(self, name: str) -> Reward | None:
        """Get reward by name."""
        formula = match({"name": name})
        records = self.table.all(formula=formula)
        if not records:
            return None
        return self._record_to_reward(records[0])

    def _record_to_reward(self, record: dict[str, Any]) -> Reward:
        """Convert Airtable record to Reward model."""
        fields = self._record_to_dict(record)
        # Handle numeric fields that might come as arrays
        if isinstance(fields.get("weight"), list):
            fields["weight"] = fields["weight"][0] if fields["weight"] else None
        if isinstance(fields.get("pieces_required"), list):
            fields["pieces_required"] = fields["pieces_required"][0] if fields["pieces_required"] else 1
        if isinstance(fields.get("piece_value"), list):
            fields["piece_value"] = fields["piece_value"][0] if fields["piece_value"] else None
        # Default pieces_required to 1 if not present
        if "pieces_required" not in fields or fields["pieces_required"] is None:
            fields["pieces_required"] = 1
        fields["type"] = RewardType(fields.get("type", "none"))
        return Reward(**fields)


class RewardProgressRepository(BaseRepository):
    """Repository for Reward Progress table."""

    def __init__(self):
        """Initialize RewardProgressRepository."""
        super().__init__("RewardProgress")

    def create(self, progress: RewardProgress) -> RewardProgress:
        """Create a new reward progress entry."""
        record = self.table.create({
            "user_id": [progress.user_id],
            "reward_id": [progress.reward_id],
            "pieces_earned": progress.pieces_earned
            # Note: pieces_required is a computed field in Airtable (from linked Reward)
        })
        return self._record_to_progress(record)

    def get_by_user_and_reward(self, user_id: str, reward_id: str) -> RewardProgress | None:
        """Get progress for specific user and reward."""
        # Note: Airtable linked fields need special handling
        records = self.table.all()
        for record in records:
            fields = record.get("fields", {})
            record_user_ids = fields.get("user_id", [])
            record_reward_ids = fields.get("reward_id", [])
            if user_id in record_user_ids and reward_id in record_reward_ids:
                return self._record_to_progress(record)
        return None

    def get_all_by_user(self, user_id: str) -> list[RewardProgress]:
        """Get all reward progress for a user."""
        records = self.table.all()
        result = []
        for record in records:
            fields = record.get("fields", {})
            record_user_ids = fields.get("user_id", [])
            if user_id in record_user_ids:
                result.append(self._record_to_progress(record))
        return result

    def get_achieved_by_user(self, user_id: str) -> list[RewardProgress]:
        """Get all achieved (actionable) rewards for a user."""
        all_progress = self.get_all_by_user(user_id)
        return [p for p in all_progress if p.status == RewardStatus.ACHIEVED]

    def update(self, progress_id: str, updates: dict[str, Any]) -> RewardProgress:
        """Update reward progress fields."""
        record = self.table.update(progress_id, updates)
        return self._record_to_progress(record)

    def _record_to_progress(self, record: dict[str, Any]) -> RewardProgress:
        """Convert Airtable record to RewardProgress model."""
        fields = self._record_to_dict(record)
        # Handle linked fields (they come as arrays)
        if isinstance(fields.get("user_id"), list):
            fields["user_id"] = fields["user_id"][0] if fields["user_id"] else None
        if isinstance(fields.get("reward_id"), list):
            fields["reward_id"] = fields["reward_id"][0] if fields["reward_id"] else None
        # Handle numeric fields that might come as arrays
        if isinstance(fields.get("pieces_earned"), list):
            fields["pieces_earned"] = fields["pieces_earned"][0] if fields["pieces_earned"] else None
        if isinstance(fields.get("pieces_required"), list):
            fields["pieces_required"] = fields["pieces_required"][0] if fields["pieces_required"] else None
        # Handle claimed field (checkbox)
        fields["claimed"] = fields.get("claimed", False)
        # Parse status enum
        status_value = fields.get("status", "🕒 Pending")
        fields["status"] = RewardStatus(status_value)
        return RewardProgress(**fields)


class HabitLogRepository(BaseRepository):
    """Repository for Habit Log table."""

    def __init__(self):
        """Initialize HabitLogRepository."""
        super().__init__("HabitLog")

    def create(self, log: HabitLog) -> HabitLog:
        """Create a new habit log entry."""
        data = {
            "user_id": [log.user_id],
            "habit_id": [log.habit_id],
            "timestamp": log.timestamp.isoformat(),
            "got_reward": log.got_reward,
            "streak_count": log.streak_count,
            "total_weight_applied": log.total_weight_applied,
            "last_completed_date": log.last_completed_date.isoformat()
        }
        if log.reward_id:
            data["reward_id"] = [log.reward_id]

        record = self.table.create(data)
        return self._record_to_log(record)

    def get_last_log_for_habit(self, user_id: str, habit_id: str) -> HabitLog | None:
        """Get the most recent log entry for a specific user and habit."""
        records = self.table.all(sort=["-timestamp"])
        for record in records:
            fields = record.get("fields", {})
            record_user_ids = fields.get("user_id", [])
            record_habit_ids = fields.get("habit_id", [])
            if user_id in record_user_ids and habit_id in record_habit_ids:
                return self._record_to_log(record)
        return None

    def get_logs_by_user(self, user_id: str, limit: int = 50) -> list[HabitLog]:
        """Get recent logs for a user."""
        records = self.table.all(sort=["-timestamp"], max_records=limit)
        result = []
        for record in records:
            fields = record.get("fields", {})
            record_user_ids = fields.get("user_id", [])
            if user_id in record_user_ids:
                result.append(self._record_to_log(record))
        return result

    def get_todays_logs_by_user(self, user_id: str, target_date: date | None = None) -> list[HabitLog]:
        """
        Get today's habit log entries for a user.

        Args:
            user_id: Airtable record ID of the user
            target_date: Optional date to query (defaults to today)

        Returns:
            List of HabitLog entries for the specified date
        """
        if target_date is None:
            target_date = date.today()

        logger.debug(f"Fetching logs for user={user_id} on date={target_date}")
        records = self.table.all()
        result = []
        for record in records:
            fields = record.get("fields", {})
            record_user_ids = fields.get("user_id", [])

            # Check if this log belongs to the user
            if user_id not in record_user_ids:
                continue

            # Check if last_completed_date matches target_date
            record_date_str = fields.get("last_completed_date")
            if record_date_str:
                # Parse the date string
                if isinstance(record_date_str, str):
                    record_date = date.fromisoformat(record_date_str)
                else:
                    record_date = record_date_str

                if record_date == target_date:
                    result.append(self._record_to_log(record))

        logger.debug(f"Found {len(result)} logs for user={user_id} on date={target_date}")
        return result

    def _record_to_log(self, record: dict[str, Any]) -> HabitLog:
        """Convert Airtable record to HabitLog model."""
        fields = self._record_to_dict(record)
        # Handle linked fields
        if isinstance(fields.get("user_id"), list):
            fields["user_id"] = fields["user_id"][0] if fields["user_id"] else None
        if isinstance(fields.get("habit_id"), list):
            fields["habit_id"] = fields["habit_id"][0] if fields["habit_id"] else None
        if isinstance(fields.get("reward_id"), list):
            fields["reward_id"] = fields["reward_id"][0] if fields.get("reward_id") else None
        # Handle numeric fields that might come as arrays
        if isinstance(fields.get("habit_weight"), list):
            fields["habit_weight"] = fields["habit_weight"][0] if fields["habit_weight"] else None
        if isinstance(fields.get("streak_count"), list):
            fields["streak_count"] = fields["streak_count"][0] if fields["streak_count"] else None
        if isinstance(fields.get("total_weight_applied"), list):
            fields["total_weight_applied"] = fields["total_weight_applied"][0] if fields["total_weight_applied"] else None
        # Parse datetime fields
        if isinstance(fields.get("timestamp"), str):
            fields["timestamp"] = datetime.fromisoformat(fields["timestamp"])
        if isinstance(fields.get("last_completed_date"), str):
            fields["last_completed_date"] = date.fromisoformat(fields["last_completed_date"])
        return HabitLog(**fields)


# Global repository instances
user_repository = UserRepository()
habit_repository = HabitRepository()
reward_repository = RewardRepository()
reward_progress_repository = RewardProgressRepository()
habit_log_repository = HabitLogRepository()
