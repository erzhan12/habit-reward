"""Audit log service for tracking high-level bot interactions."""

import logging
from datetime import datetime, timedelta
from typing import Awaitable
from asgiref.sync import sync_to_async

from src.core.models import BotAuditLog, Habit, Reward, HabitLog
from src.utils.async_compat import run_sync_or_async

# Configure logging
logger = logging.getLogger(__name__)

# Import EventType from model
EventType = BotAuditLog.EventType


class AuditLogService:
    """Service for managing bot audit logs."""

    def __init__(self):
        """Initialize AuditLogService."""
        pass

    def log_command(
        self,
        user_id: int | str,
        command: str,
        snapshot: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log a command execution.

        Args:
            user_id: User ID who executed the command
            command: Command name (e.g., /habit_done, /streaks)
            snapshot: Optional state snapshot

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            logger.debug(f"Logging command: {command} for user {user_id}")

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.COMMAND,
                command=command,
                snapshot=snapshot or {},
            )
            await sync_to_async(log_entry.save)()

            logger.info(f"✅ Logged command {command} for user {user_id}")
            return log_entry

        return run_sync_or_async(_impl())

    def log_habit_completion(
        self,
        user_id: int | str,
        habit: Habit | None,
        reward: Reward | None,
        habit_log: HabitLog | None,
        snapshot: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log a habit completion event.

        Args:
            user_id: User ID who completed the habit
            habit: Habit that was completed
            reward: Reward that was awarded (if any)
            habit_log: Created HabitLog entry
            snapshot: State snapshot containing:
                - reward_progress: dict with pieces_earned, pieces_required, claimed
                - streak_count: int
                - total_weight: float
                - selected_reward_name: str

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            habit_id = habit.id if habit else None
            reward_id = reward.id if reward else None
            habit_log_id = habit_log.id if habit_log else None

            logger.debug(
                f"Logging habit completion: user={user_id}, habit={habit_id}, "
                f"reward={reward_id}, log={habit_log_id}"
            )

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.HABIT_COMPLETED,
                habit_id=habit_id,
                reward_id=reward_id,
                habit_log_id=habit_log_id,
                snapshot=snapshot or {},
            )
            await sync_to_async(log_entry.save)()

            logger.info(
                f"✅ Logged habit completion for user {user_id}, habit {habit_id}"
            )
            return log_entry

        return run_sync_or_async(_impl())

    def log_reward_claim(
        self,
        user_id: int | str,
        reward: Reward,
        progress_snapshot: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log a reward claim event.

        Args:
            user_id: User ID who claimed the reward
            reward: Reward that was claimed
            progress_snapshot: State snapshot with pieces_earned before/after claim

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            logger.debug(
                f"Logging reward claim: user={user_id}, reward={reward.id}"
            )

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.REWARD_CLAIMED,
                reward_id=reward.id,
                snapshot=progress_snapshot or {},
            )
            await sync_to_async(log_entry.save)()

            logger.info(
                f"✅ Logged reward claim for user {user_id}, reward {reward.id}"
            )
            return log_entry

        return run_sync_or_async(_impl())

    def log_reward_revert(
        self,
        user_id: int | str,
        reward: Reward,
        habit_log: HabitLog | None,
        progress_snapshot: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log a reward revert event.

        Args:
            user_id: User ID
            reward: Reward that was reverted
            habit_log: HabitLog that was deleted
            progress_snapshot: State snapshot with pieces_earned before/after revert

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            habit_log_id = habit_log.id if habit_log else None

            logger.debug(
                f"Logging reward revert: user={user_id}, reward={reward.id}, "
                f"habit_log={habit_log_id}"
            )

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.REWARD_REVERTED,
                reward_id=reward.id,
                habit_log_id=habit_log_id,
                snapshot=progress_snapshot or {},
            )
            await sync_to_async(log_entry.save)()

            logger.info(
                f"✅ Logged reward revert for user {user_id}, reward {reward.id}"
            )
            return log_entry

        return run_sync_or_async(_impl())

    def log_error(
        self,
        user_id: int | str,
        error_message: str,
        context: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log an error event.

        Args:
            user_id: User ID who encountered the error
            error_message: Error message and traceback
            context: Context snapshot (command, state, etc.)

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            logger.debug(f"Logging error for user {user_id}: {error_message[:100]}")

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.ERROR,
                error_message=error_message,
                snapshot=context or {},
            )
            await sync_to_async(log_entry.save)()

            logger.info(f"✅ Logged error for user {user_id}")
            return log_entry

        return run_sync_or_async(_impl())

    def log_button_click(
        self,
        user_id: int | str,
        callback_data: str,
        snapshot: dict | None = None
    ) -> BotAuditLog | Awaitable[BotAuditLog]:
        """Log a button click event.

        Args:
            user_id: User ID who clicked the button
            callback_data: Callback data from inline keyboard button
            snapshot: Optional state snapshot

        Returns:
            Created BotAuditLog entry
        """

        async def _impl() -> BotAuditLog:
            logger.debug(
                f"Logging button click: user={user_id}, callback={callback_data}"
            )

            log_entry = BotAuditLog(
                user_id=user_id,
                event_type=EventType.BUTTON_CLICK,
                callback_data=callback_data,
                snapshot=snapshot or {},
            )
            await sync_to_async(log_entry.save)()

            logger.debug(f"✅ Logged button click for user {user_id}")
            return log_entry

        return run_sync_or_async(_impl())

    def get_user_timeline(
        self,
        user_id: int | str,
        hours: int = 24
    ) -> list[BotAuditLog] | Awaitable[list[BotAuditLog]]:
        """Get chronological event timeline for a user.

        Args:
            user_id: User ID
            hours: Number of hours to look back (default: 24)

        Returns:
            List of BotAuditLog entries ordered by timestamp
        """

        async def _impl() -> list[BotAuditLog]:
            since = datetime.now() - timedelta(hours=hours)

            logger.debug(
                f"Fetching user timeline: user={user_id}, since={since}"
            )

            logs = await sync_to_async(list)(
                BotAuditLog.objects.filter(
                    user_id=user_id,
                    timestamp__gte=since
                ).select_related('user', 'habit', 'reward', 'habit_log').order_by('timestamp')
            )

            logger.info(
                f"📊 Retrieved {len(logs)} events for user {user_id} (last {hours}h)"
            )
            return logs

        return run_sync_or_async(_impl())

    def trace_reward_corruption(
        self,
        user_id: int | str,
        reward_id: int | str
    ) -> list[BotAuditLog] | Awaitable[list[BotAuditLog]]:
        """Trace all events related to a specific reward for debugging corruption.

        Args:
            user_id: User ID
            reward_id: Reward ID

        Returns:
            List of BotAuditLog entries showing reward state changes
        """

        async def _impl() -> list[BotAuditLog]:
            logger.debug(
                f"Tracing reward corruption: user={user_id}, reward={reward_id}"
            )

            logs = await sync_to_async(list)(
                BotAuditLog.objects.filter(
                    user_id=user_id,
                    reward_id=reward_id
                ).select_related('user', 'habit', 'reward', 'habit_log').order_by('timestamp')
            )

            logger.info(
                f"🔍 Retrieved {len(logs)} events for user {user_id}, reward {reward_id}"
            )
            return logs

        return run_sync_or_async(_impl())

    def cleanup_old_logs(
        self,
        days: int = 90
    ) -> int | Awaitable[int]:
        """Delete audit logs older than retention period.

        Args:
            days: Number of days to retain (default: 90)

        Returns:
            Number of deleted records
        """

        async def _impl() -> int:
            cutoff_date = datetime.now() - timedelta(days=days)

            logger.info(f"Cleaning up audit logs older than {cutoff_date}")

            deleted_count, _ = await sync_to_async(
                BotAuditLog.objects.filter(timestamp__lt=cutoff_date).delete
            )()

            logger.info(f"✅ Deleted {deleted_count} old audit log entries")
            return deleted_count

        return run_sync_or_async(_impl())


# Global service instance
audit_log_service = AuditLogService()
