"""Repository pattern implementation for Django ORM.

This module provides a compatibility layer that maintains the same interface
as the Airtable repositories, allowing services to work without changes.
"""

import logging
from datetime import date
from typing import Any
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.db.models import F

from src.core.models import User, Habit, HabitLog, Reward, RewardProgress, AuthCode, APIKey

# Configure logging
logger = logging.getLogger(__name__)


class UserRepository:
    """User repository using Django ORM."""

    async def get_by_telegram_id(self, telegram_id: str) -> User | None:
        """Get user by Telegram ID."""
        try:
            return await sync_to_async(User.objects.get)(telegram_id=telegram_id)
        except User.DoesNotExist:
            return None

    async def get_by_id(self, user_id: int | str) -> User | None:
        """Get user by primary key.

        Args:
            user_id: Django primary key (int) or string representation

        Returns:
            User instance or None
        """
        try:
            # Convert to int if string (for compatibility with Airtable IDs)
            pk = int(user_id) if isinstance(user_id, str) else user_id
            return await sync_to_async(User.objects.get)(pk=pk)
        except (User.DoesNotExist, ValueError):
            return None

    async def create(self, user: User | dict) -> User:
        """Create new user.

        Args:
            user: User model instance or dict with user fields

        Returns:
            Created User instance
        """
        if isinstance(user, dict):
            # Map 'active' to 'is_active' if present (for backward compatibility)
            if "active" in user:
                user["is_active"] = user.pop("active")

            # Set default is_active=False for security if not specified
            if "is_active" not in user:
                user["is_active"] = False

            # Auto-generate username from telegram_id if not provided
            if "username" not in user and "telegram_id" in user:
                user["username"] = f"tg_{user['telegram_id']}"

            return await sync_to_async(User.objects.create)(**user)
        else:
            # If it's a User instance, extract fields
            return await sync_to_async(User.objects.create)(
                telegram_id=user.telegram_id,
                name=user.name,
                is_active=user.is_active,
                language=user.language,
                username=f"tg_{user.telegram_id}",
            )

    async def update(self, user_id: int | str, updates: dict[str, Any]) -> User:
        """Update user fields.

        Args:
            user_id: Django primary key
            updates: Dict with fields to update

        Returns:
            Updated User instance
        """
        pk = int(user_id) if isinstance(user_id, str) else user_id

        # Map 'active' to 'is_active' if present (for backward compatibility)
        if "active" in updates:
            updates["is_active"] = updates.pop("active")

        await sync_to_async(User.objects.filter(pk=pk).update)(**updates)
        return await sync_to_async(User.objects.get)(pk=pk)


class HabitRepository:
    """Habit repository using Django ORM."""

    async def get_by_name(self, user_id: int | str, name: str) -> Habit | None:
        """Get habit by name for a specific user (active habits only)."""
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            return await sync_to_async(Habit.objects.get)(
                user_id=user_pk, name=name, active=True
            )
        except Habit.DoesNotExist:
            return None

    async def get_all_active(self, user_id: int | str) -> list[Habit]:
        """Get all active habits for a specific user."""
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        habits = await sync_to_async(list)(
            Habit.objects.filter(user_id=user_pk, active=True).order_by("name")
        )
        return habits

    async def get_all(
        self, user_id: int | str, active: bool | None = None
    ) -> list[Habit]:
        """Get all habits for a specific user, optionally filtered by active status.

        Args:
            user_id: User primary key
            active: Optional filter by active status (True/False), or None for all habits

        Returns:
            List of Habit instances
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        queryset = Habit.objects.filter(user_id=user_pk)
        if active is not None:
            queryset = queryset.filter(active=active)
        habits = await sync_to_async(list)(queryset.order_by("name"))
        return habits

    async def get_by_id(self, habit_id: int | str) -> Habit | None:
        """Get habit by primary key."""
        try:
            pk = int(habit_id) if isinstance(habit_id, str) else habit_id
            return await sync_to_async(Habit.objects.get)(pk=pk)
        except (Habit.DoesNotExist, ValueError):
            return None

    async def create(self, habit: Habit | dict) -> Habit:
        """Create new habit.

        Args:
            habit: Habit model instance or dict with habit fields (must include user_id)

        Returns:
            Created Habit instance
        """
        if isinstance(habit, dict):
            # Convert string user_id to int if needed
            if "user_id" in habit and isinstance(habit["user_id"], str):
                habit["user_id"] = int(habit["user_id"])
            return await sync_to_async(Habit.objects.create)(**habit)
        else:
            user_id = (
                int(habit.user_id) if isinstance(habit.user_id, str) else habit.user_id
            )
            return await sync_to_async(Habit.objects.create)(
                user_id=user_id,
                name=habit.name,
                weight=habit.weight,
                category=habit.category,
                active=habit.active,
            )

    async def update(self, habit_id: int | str, updates: dict[str, Any]) -> Habit:
        """Update habit fields.

        Args:
            habit_id: Django primary key
            updates: Dict with fields to update (name, weight, category, active)

        Returns:
            Updated Habit instance
        """
        pk = int(habit_id) if isinstance(habit_id, str) else habit_id
        await sync_to_async(Habit.objects.filter(pk=pk).update)(**updates)
        return await sync_to_async(Habit.objects.get)(pk=pk)

    async def soft_delete(self, habit_id: int | str) -> Habit:
        """Soft delete habit by setting active=False.

        Args:
            habit_id: Django primary key

        Returns:
            Updated Habit instance with active=False
        """
        return await self.update(habit_id, {"active": False})


class RewardRepository:
    """Reward repository using Django ORM."""

    async def get_all_active(self, user_id: int | str) -> list[Reward]:
        """Get all active rewards for a specific user."""
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        rewards = await sync_to_async(list)(
            Reward.objects.filter(user_id=user_pk, active=True).order_by("name")
        )
        return rewards

    async def get_all(self, user_id: int | str) -> list[Reward]:
        """Get ALL rewards for a specific user (both active and inactive).

        Used for toggle reward active/inactive flow where we need to show all rewards.
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        rewards = await sync_to_async(list)(
            Reward.objects.filter(user_id=user_pk).order_by("name")
        )
        return rewards

    async def get_by_id(self, reward_id: int | str) -> Reward | None:
        """Get reward by primary key."""
        try:
            pk = int(reward_id) if isinstance(reward_id, str) else reward_id
            return await sync_to_async(Reward.objects.get)(pk=pk)
        except (Reward.DoesNotExist, ValueError):
            return None

    async def get_by_name(self, user_id: int | str, name: str) -> Reward | None:
        """Get reward by name for a specific user (all rewards, active and inactive).
        
        Used for duplicate name validation, which must check all rewards since
        the DB constraint is on (user, name) for all rewards.
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            return await sync_to_async(Reward.objects.get)(
                user_id=user_pk, name=name
            )
        except Reward.DoesNotExist:
            return None

    async def create(self, reward: Reward | dict) -> Reward:
        """Create new reward.

        Args:
            reward: Reward model instance or dict with reward fields (must include user_id)

        Returns:
            Created Reward instance
        """
        if isinstance(reward, dict):
            # Convert string user_id to int if needed
            if "user_id" in reward and isinstance(reward["user_id"], str):
                reward["user_id"] = int(reward["user_id"])
            return await sync_to_async(Reward.objects.create)(**reward)
        else:
            user_id = (
                int(reward.user_id)
                if isinstance(reward.user_id, str)
                else reward.user_id
            )
            data = {
                "user_id": user_id,
                "name": reward.name,
                "weight": reward.weight,
                "type": reward.type
                if isinstance(reward.type, str)
                else reward.type.value,
                "pieces_required": reward.pieces_required,
            }
            if reward.piece_value is not None:
                data["piece_value"] = reward.piece_value
            return await sync_to_async(Reward.objects.create)(**data)

    async def update(self, reward_id: int | str, updates: dict[str, Any]) -> Reward:
        """Update reward fields.

        Args:
            reward_id: Django primary key
            updates: Dict with fields to update (name, weight, type, pieces_required, piece_value, max_daily_claims, active)

        Returns:
            Updated Reward instance
        """
        pk = int(reward_id) if isinstance(reward_id, str) else reward_id

        # Normalize piece_value to Decimal when provided as float/int/str
        if "piece_value" in updates and updates["piece_value"] is not None:
            value = updates["piece_value"]
            if isinstance(value, Decimal):
                normalized = value
            else:
                normalized = Decimal(str(value))
            updates["piece_value"] = normalized

        await sync_to_async(Reward.objects.filter(pk=pk).update)(**updates)
        return await sync_to_async(Reward.objects.get)(pk=pk)


class RewardProgressRepository:
    """Reward progress repository using Django ORM."""

    @staticmethod
    def _attach_cached_pieces_required(progress: RewardProgress) -> RewardProgress:
        """Attach cached pieces_required to avoid ForeignKey access in async contexts.

        This prevents SynchronousOnlyOperation errors when get_status() is called
        from async contexts by caching the pieces_required value directly on the instance.

        Args:
            progress: RewardProgress instance with reward loaded via select_related

        Returns:
            Same RewardProgress instance with _cached_pieces_required attached
        """
        if progress and hasattr(progress, "reward"):
            # Access reward.pieces_required now (in sync context) and cache it
            progress._cached_pieces_required = progress.reward.pieces_required
        return progress

    async def get_by_user_and_reward(
        self, user_id: int | str, reward_id: int | str
    ) -> RewardProgress | None:
        """Get progress for specific user and reward.

        Args:
            user_id: User primary key
            reward_id: Reward primary key

        Returns:
            RewardProgress instance or None
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            reward_pk = int(reward_id) if isinstance(reward_id, str) else reward_id
            progress = await sync_to_async(
                RewardProgress.objects.select_related("reward", "user").get
            )(user_id=user_pk, reward_id=reward_pk)
            return self._attach_cached_pieces_required(progress)
        except (RewardProgress.DoesNotExist, ValueError):
            return None

    async def get_all_by_user(self, user_id: int | str) -> list[RewardProgress]:
        """Get all reward progress for a user.

        Args:
            user_id: User primary key

        Returns:
            List of RewardProgress instances
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        progress_list = await sync_to_async(list)(
            RewardProgress.objects.filter(user_id=user_pk)
            .select_related("reward", "user")
            .order_by("reward__name")
        )
        # Attach cached pieces_required to each progress object
        return [self._attach_cached_pieces_required(p) for p in progress_list]

    async def get_achieved_by_user(self, user_id: int | str) -> list[RewardProgress]:
        """Get all achieved (actionable) rewards for a user.

        Achieved means: pieces_earned >= pieces_required AND not claimed

        Args:
            user_id: User primary key

        Returns:
            List of RewardProgress instances with achieved status
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        achieved_list = await sync_to_async(list)(
            RewardProgress.objects.filter(
                user_id=user_pk,
                pieces_earned__gte=F("reward__pieces_required"),
                claimed=False,
            ).select_related("reward", "user")
        )
        # Attach cached pieces_required to each progress object
        return [self._attach_cached_pieces_required(p) for p in achieved_list]

    async def decrement_pieces_earned(
        self, user_id: int | str, reward_id: int | str
    ) -> RewardProgress | None:
        """Decrement pieces_earned by one and reset claimed when necessary."""
        progress = await self.get_by_user_and_reward(user_id, reward_id)
        if not progress:
            return None

        new_pieces = max(0, progress.pieces_earned - 1)
        updates: dict[str, Any] = {}

        if new_pieces != progress.pieces_earned:
            updates["pieces_earned"] = new_pieces

        if progress.claimed or new_pieces < progress.pieces_earned:
            updates["claimed"] = False

        if not updates:
            return progress

        return await self.update(progress.id, updates)

    async def create(self, progress: RewardProgress | dict) -> RewardProgress:
        """Create new progress entry.

        Uses get_or_create to prevent duplicates.

        Args:
            progress: RewardProgress instance or dict with progress fields

        Returns:
            RewardProgress instance (created or existing)
        """
        if isinstance(progress, dict):
            user_id = (
                int(progress["user_id"])
                if isinstance(progress["user_id"], str)
                else progress["user_id"]
            )
            reward_id = (
                int(progress["reward_id"])
                if isinstance(progress["reward_id"], str)
                else progress["reward_id"]
            )
            pieces_earned = progress.get("pieces_earned", 0)
        else:
            user_id = (
                int(progress.user_id)
                if isinstance(progress.user_id, str)
                else progress.user_id
            )
            reward_id = (
                int(progress.reward_id)
                if isinstance(progress.reward_id, str)
                else progress.reward_id
            )
            pieces_earned = progress.pieces_earned

        progress_obj, created = await sync_to_async(
            RewardProgress.objects.get_or_create
        )(
            user_id=user_id,
            reward_id=reward_id,
            defaults={"pieces_earned": pieces_earned},
        )
        # Refetch to ensure related objects are loaded (prevents sync queries in async contexts)
        progress = await sync_to_async(
            RewardProgress.objects.select_related("reward", "user").get
        )(pk=progress_obj.pk)
        return self._attach_cached_pieces_required(progress)

    async def update(
        self, progress_id: int | str, updates: dict[str, Any]
    ) -> RewardProgress:
        """Update reward progress fields.

        Args:
            progress_id: RewardProgress primary key
            updates: Dict with fields to update

        Returns:
            Updated RewardProgress instance
        """
        pk = int(progress_id) if isinstance(progress_id, str) else progress_id
        await sync_to_async(RewardProgress.objects.filter(pk=pk).update)(**updates)
        progress = await sync_to_async(
            RewardProgress.objects.select_related("reward", "user").get
        )(pk=pk)
        return self._attach_cached_pieces_required(progress)


class HabitLogRepository:
    """Habit log repository using Django ORM."""

    async def get_by_id(self, log_id: int | str) -> HabitLog | None:
        """Get habit log by primary key.

        Args:
            log_id: HabitLog primary key

        Returns:
            HabitLog instance with related objects loaded, or None
        """
        try:
            pk = int(log_id) if isinstance(log_id, str) else log_id
            return await sync_to_async(
                HabitLog.objects.select_related("habit", "user", "reward").get
            )(pk=pk)
        except (HabitLog.DoesNotExist, ValueError):
            return None

    async def create(self, log: HabitLog | dict) -> HabitLog:
        """Create new habit log entry.

        Args:
            log: HabitLog instance or dict with log fields

        Returns:
            Created HabitLog instance
        """
        if isinstance(log, dict):
            # Convert string IDs to ints
            if "user_id" in log and isinstance(log["user_id"], str):
                log["user_id"] = int(log["user_id"])
            if "habit_id" in log and isinstance(log["habit_id"], str):
                log["habit_id"] = int(log["habit_id"])
            if "reward_id" in log and isinstance(log["reward_id"], str):
                log["reward_id"] = int(log["reward_id"]) if log["reward_id"] else None
            return await sync_to_async(HabitLog.objects.create)(**log)
        else:
            data = {
                "user_id": int(log.user_id)
                if isinstance(log.user_id, str)
                else log.user_id,
                "habit_id": int(log.habit_id)
                if isinstance(log.habit_id, str)
                else log.habit_id,
                "got_reward": log.got_reward,
                "streak_count": log.streak_count,
                "habit_weight": log.habit_weight,
                "total_weight_applied": log.total_weight_applied,
                "last_completed_date": log.last_completed_date,
            }
            if log.reward_id:
                data["reward_id"] = (
                    int(log.reward_id)
                    if isinstance(log.reward_id, str)
                    else log.reward_id
                )
            # Note: timestamp will be auto-set by auto_now_add
            return await sync_to_async(HabitLog.objects.create)(**data)

    async def get_last_log_for_habit(
        self, user_id: int | str, habit_id: int | str
    ) -> HabitLog | None:
        """Get the most recent log entry for a specific user and habit.

        Args:
            user_id: User primary key
            habit_id: Habit primary key

        Returns:
            Most recent HabitLog instance or None
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            habit_pk = int(habit_id) if isinstance(habit_id, str) else habit_id
            return await sync_to_async(
                HabitLog.objects.filter(user_id=user_pk, habit_id=habit_pk)
                .select_related("habit", "user", "reward")
                .latest
            )("timestamp")
        except (HabitLog.DoesNotExist, ValueError):
            return None

    async def delete(self, log_id: int | str) -> int:
        """Delete habit log entry by ID."""
        try:
            pk = int(log_id) if isinstance(log_id, str) else log_id
        except (TypeError, ValueError):
            return 0

        deleted, _ = await sync_to_async(HabitLog.objects.filter(pk=pk).delete)()
        return deleted

    async def get_logs_by_user(
        self, user_id: int | str, limit: int = 50
    ) -> list[HabitLog]:
        """Get recent logs for a user.

        Args:
            user_id: User primary key
            limit: Maximum number of logs to return

        Returns:
            List of HabitLog instances (most recent first)
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        logs = await sync_to_async(list)(
            HabitLog.objects.filter(user_id=user_pk)
            .select_related("habit", "user", "reward")
            .order_by("-timestamp")[:limit]
        )
        return logs

    async def get_todays_logs_by_user(
        self, user_id: int | str, target_date: date | None = None
    ) -> list[HabitLog]:
        """Get today's habit log entries for a user.

        Args:
            user_id: User primary key
            target_date: Optional date to query (defaults to today)

        Returns:
            List of HabitLog entries for the specified date
        """
        if target_date is None:
            target_date = date.today()

        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        logger.debug(f"Fetching logs for user={user_pk} on date={target_date}")

        logs = await sync_to_async(list)(
            HabitLog.objects.filter(
                user_id=user_pk, last_completed_date=target_date
            ).select_related("habit", "user", "reward")
        )

        logger.debug(f"Found {len(logs)} logs for user={user_pk} on date={target_date}")
        return logs

    async def get_log_for_habit_on_date(
        self, user_id: int | str, habit_id: int | str, target_date: date
    ) -> HabitLog | None:
        """Check if a habit was already completed on a specific date.

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            target_date: Date to check for completion

        Returns:
            HabitLog instance if found, None otherwise
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            habit_pk = int(habit_id) if isinstance(habit_id, str) else habit_id

            return await sync_to_async(
                HabitLog.objects.filter(
                    user_id=user_pk, habit_id=habit_pk, last_completed_date=target_date
                )
                .select_related("habit", "user", "reward")
                .first
            )()
        except (ValueError, HabitLog.DoesNotExist):
            return None

    async def get_last_log_before_date(
        self, user_id: int | str, habit_id: int | str, target_date: date
    ) -> HabitLog | None:
        """Get the most recent log entry BEFORE a specific date.

        Used for backdate streak calculation to find the previous completion
        before the target date.

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            target_date: Date to search before (exclusive)

        Returns:
            Most recent HabitLog before target_date or None
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            habit_pk = int(habit_id) if isinstance(habit_id, str) else habit_id

            return await sync_to_async(
                HabitLog.objects.filter(
                    user_id=user_pk,
                    habit_id=habit_pk,
                    last_completed_date__lt=target_date,
                )
                .select_related("habit", "user", "reward")
                .order_by("-last_completed_date")
                .first
            )()
        except (ValueError, HabitLog.DoesNotExist):
            return None

    async def get_logs_for_habit_in_daterange(
        self, user_id: int | str, habit_id: int | str, start_date: date, end_date: date
    ) -> list[HabitLog]:
        """Get all habit logs for a specific habit within a date range.

        Args:
            user_id: User primary key
            habit_id: Habit primary key
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of HabitLog instances
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        habit_pk = int(habit_id) if isinstance(habit_id, str) else habit_id

        logs = await sync_to_async(list)(
            HabitLog.objects.filter(
                user_id=user_pk,
                habit_id=habit_pk,
                last_completed_date__gte=start_date,
                last_completed_date__lte=end_date,
            )
            .select_related("habit", "user", "reward")
            .order_by("last_completed_date")
        )

        return logs

    async def update(self, log_id: int | str, updates: dict[str, Any]) -> HabitLog:
        """Update a habit log entry.

        Args:
            log_id: HabitLog primary key
            updates: Dictionary of fields to update

        Returns:
            Updated HabitLog instance

        Raises:
            ValueError: If log not found
        """
        try:
            pk = int(log_id) if isinstance(log_id, str) else log_id
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid log_id: {log_id}") from e

        log = await sync_to_async(
            HabitLog.objects.filter(pk=pk)
            .select_related("habit", "user", "reward")
            .first
        )()
        if not log:
            raise ValueError(f"HabitLog with id {log_id} not found")

        for field, value in updates.items():
            setattr(log, field, value)

        await sync_to_async(log.save)()
        return log


class AuthCodeRepository:
    """Auth code repository for one-time login codes."""

    async def create(
        self,
        user_id: int | str,
        code: str,
        expires_at,
        device_info: str | None = None,
    ) -> AuthCode:
        """Create a new auth code.

        Args:
            user_id: User primary key
            code: 6-digit code string
            expires_at: Expiration datetime
            device_info: Optional device/browser info

        Returns:
            Created AuthCode instance
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        return await sync_to_async(AuthCode.objects.create)(
            user_id=user_pk,
            code=code,
            expires_at=expires_at,
            device_info=device_info,
        )

    async def get_valid_code(
        self, user_id: int | str, code: str
    ) -> AuthCode | None:
        """Get a valid (not used, not expired) code for user.

        Args:
            user_id: User primary key
            code: 6-digit code string

        Returns:
            AuthCode instance if valid, None otherwise
        """
        from datetime import datetime, timezone

        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            now = datetime.now(timezone.utc)
            return await sync_to_async(
                AuthCode.objects.select_related("user").get
            )(
                user_id=user_pk,
                code=code,
                used=False,
                expires_at__gt=now,
            )
        except AuthCode.DoesNotExist:
            return None

    async def verify_and_consume_code(
        self, user_id: int | str, code: str
    ) -> AuthCode | None:
        """Verify and consume a code atomically.

        Args:
            user_id: User primary key
            code: 6-digit code string

        Returns:
            AuthCode instance if valid and successfully consumed, None otherwise
        """
        from datetime import datetime, timezone

        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        # First, try to fetch the valid code to return it
        try:
            auth_code = await sync_to_async(
                AuthCode.objects.select_related("user").get
            )(
                user_id=user_pk,
                code=code,
                used=False,
                expires_at__gt=now,
            )
        except AuthCode.DoesNotExist:
            return None

        # Check if code is locked
        if auth_code.locked_until and auth_code.locked_until > now:
            return None

        # Now try to mark it as used atomically
        # If another request beat us to it, update will return 0
        updated_count = await sync_to_async(
            AuthCode.objects.filter(
                id=auth_code.id,
                used=False,  # Ensure it's still unused
                locked_until__isnull=True, # Ensure not locked
            ).update
        )(used=True)

        if updated_count == 0:
            # Race condition: code was used or locked between get and update
            return None

        return auth_code

    async def register_failed_attempt(self, user_id: int | str) -> bool:
        """Register a failed attempt for the user's latest active code.

        Increments failed_attempts and locks if threshold reached.

        Args:
            user_id: User primary key

        Returns:
            True if a code was found and updated, False otherwise
        """
        from datetime import datetime, timezone, timedelta

        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        # Get latest active code for user
        # We need to find the code that is valid (not expired, not used)
        # to increment attempts on it.
        try:
            auth_code = await sync_to_async(
                AuthCode.objects.filter(
                    user_id=user_pk,
                    used=False,
                    expires_at__gt=now
                ).latest
            )("created_at")
        except AuthCode.DoesNotExist:
            return False

        # Increment attempts
        auth_code.failed_attempts += 1
        
        # Check if should lock (5 max attempts)
        if auth_code.failed_attempts >= 5:
            auth_code.locked_until = now + timedelta(minutes=15)
        
        await sync_to_async(auth_code.save)()
        return True

    async def mark_used(self, code_id: int | str) -> AuthCode:
        """Mark an auth code as used.

        Args:
            code_id: AuthCode primary key

        Returns:
            Updated AuthCode instance
        """
        pk = int(code_id) if isinstance(code_id, str) else code_id
        await sync_to_async(AuthCode.objects.filter(pk=pk).update)(used=True)
        return await sync_to_async(AuthCode.objects.get)(pk=pk)

    async def delete_expired(self) -> int:
        """Delete all expired auth codes.

        Returns:
            Number of deleted codes
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        deleted, _ = await sync_to_async(
            AuthCode.objects.filter(expires_at__lt=now).delete
        )()
        return deleted

    async def invalidate_user_codes(self, user_id: int | str) -> int:
        """Invalidate all pending codes for a user (when new code requested).

        Args:
            user_id: User primary key

        Returns:
            Number of codes invalidated
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        count = await sync_to_async(
            AuthCode.objects.filter(user_id=user_pk, used=False).update
        )(used=True)
        return count

    async def count_recent_requests(
        self, user_id: int | str, hours: int = 1
    ) -> int:
        """Count how many codes were requested in the last N hours.

        Used for rate limiting.

        Args:
            user_id: User primary key
            hours: Number of hours to look back

        Returns:
            Number of codes created in the time window
        """
        from datetime import datetime, timezone, timedelta

        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return await sync_to_async(
            AuthCode.objects.filter(
                user_id=user_pk,
                created_at__gte=cutoff,
            ).count
        )()


class APIKeyRepository:
    """API key repository for automated integrations."""

    async def create(
        self,
        user_id: int | str,
        key_hash: str,
        name: str,
        expires_at=None,
    ) -> APIKey:
        """Create a new API key.

        Args:
            user_id: User primary key
            key_hash: SHA256 hash of the key
            name: User-friendly name for the key
            expires_at: Optional expiration datetime

        Returns:
            Created APIKey instance
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        return await sync_to_async(APIKey.objects.create)(
            user_id=user_pk,
            key_hash=key_hash,
            name=name,
            expires_at=expires_at,
        )

    async def get_by_key_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by its hash.

        Args:
            key_hash: SHA256 hash of the key

        Returns:
            APIKey instance if found, None otherwise
        """
        try:
            return await sync_to_async(
                APIKey.objects.select_related("user").get
            )(key_hash=key_hash, is_active=True)
        except APIKey.DoesNotExist:
            return None

    async def list_by_user(self, user_id: int | str) -> list[APIKey]:
        """Get all API keys for a user.

        Args:
            user_id: User primary key

        Returns:
            List of APIKey instances (active only)
        """
        user_pk = int(user_id) if isinstance(user_id, str) else user_id
        return await sync_to_async(list)(
            APIKey.objects.filter(user_id=user_pk, is_active=True).order_by("-created_at")
        )

    async def revoke(self, key_id: int | str) -> APIKey:
        """Revoke an API key.

        Args:
            key_id: APIKey primary key

        Returns:
            Updated APIKey instance
        """
        pk = int(key_id) if isinstance(key_id, str) else key_id
        await sync_to_async(APIKey.objects.filter(pk=pk).update)(is_active=False)
        return await sync_to_async(APIKey.objects.get)(pk=pk)

    async def update_last_used(self, key_id: int | str) -> None:
        """Update last_used_at timestamp.

        Args:
            key_id: APIKey primary key
        """
        from datetime import datetime, timezone

        pk = int(key_id) if isinstance(key_id, str) else key_id
        await sync_to_async(APIKey.objects.filter(pk=pk).update)(
            last_used_at=datetime.now(timezone.utc)
        )

    async def get_by_id(self, key_id: int | str) -> APIKey | None:
        """Get API key by primary key.

        Args:
            key_id: APIKey primary key

        Returns:
            APIKey instance or None
        """
        try:
            pk = int(key_id) if isinstance(key_id, str) else key_id
            return await sync_to_async(
                APIKey.objects.select_related("user").get
            )(pk=pk)
        except (APIKey.DoesNotExist, ValueError):
            return None

    async def get_by_user_and_name(
        self, user_id: int | str, name: str
    ) -> APIKey | None:
        """Get API key by user and name.

        Args:
            user_id: User primary key
            name: Key name

        Returns:
            APIKey instance or None
        """
        try:
            user_pk = int(user_id) if isinstance(user_id, str) else user_id
            return await sync_to_async(
                APIKey.objects.select_related("user").get
            )(user_id=user_pk, name=name, is_active=True)
        except APIKey.DoesNotExist:
            return None


# Global repository instances (for backward compatibility with Airtable pattern)
user_repository = UserRepository()
habit_repository = HabitRepository()
reward_repository = RewardRepository()
reward_progress_repository = RewardProgressRepository()
habit_log_repository = HabitLogRepository()
auth_code_repository = AuthCodeRepository()
api_key_repository = APIKeyRepository()
