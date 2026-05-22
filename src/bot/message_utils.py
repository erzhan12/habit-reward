"""Shared Telegram message cleanup utilities.

Global task tracking enables graceful cleanup; call cancel_pending_deletions()
before bot shutdown to prevent orphaned deletion animations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from telegram import Message

logger = logging.getLogger(__name__)

# Global set tracking pending message deletion tasks for lifecycle management.
# Tasks self-remove on completion via done_callback. Tests should clear this set
# between test runs using _pending_message_delete_tasks.clear().
_pending_message_delete_tasks = set()
# 2.5 seconds gives users time to read short status messages before cleanup.
_MESSAGE_DELETE_DELAY_SECONDS = 2.5
# The final 0.5 seconds shows an explicit deleting state instead of vanishing.
_MESSAGE_DELETE_ANIMATION_SECONDS = 0.5


def schedule_message_delete(
    message_obj: Message,
    telegram_id: str,
    description: str,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> None:
    """Schedule deletion for a short-lived bot message.

    The bot waits 2.5 seconds so the user can read the message, then shows a
    brief deleting state for 0.5 seconds before removing it. The created task is
    tracked until completion so shutdown/test cleanup can inspect or cancel it.

    Args:
        message_obj: Telegram message object with edit_text() and delete() methods.
        telegram_id: User's Telegram ID for logging.
        description: Human-readable message description for logs.
        context: Optional context to track the task for test cleanup.
    """
    if (
        not message_obj
        or not callable(getattr(message_obj, "edit_text", None))
        or not callable(getattr(message_obj, "delete", None))
    ):
        logger.warning("⚠️ Could not schedule %s deletion for user %s: invalid message object", description, telegram_id)
        return

    async def delete_message():
        try:
            await asyncio.sleep(_MESSAGE_DELETE_DELAY_SECONDS)
            try:
                await message_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
                await asyncio.sleep(_MESSAGE_DELETE_ANIMATION_SECONDS)
            except Exception as e:
                logger.debug("Could not edit %s message for user %s before deletion: %s", description, telegram_id, e)
            await message_obj.delete()
            logger.info("🗑️ Deleted %s message for user %s", description, telegram_id)
        except asyncio.CancelledError:
            logger.info("🗑️ Cancelled %s message deletion for user %s", description, telegram_id)
            raise
        except Exception as e:
            logger.warning("⚠️ Could not delete %s message for user %s: %s", description, telegram_id, e)

    task = asyncio.create_task(delete_message())
    _pending_message_delete_tasks.add(task)
    # Task self-removes from tracking set when done (success, failure, or cancellation).
    task.add_done_callback(_discard_completed_task)

    # Also track in context for test inspection; user_data is cleared at conversation end.
    if context is not None and hasattr(context, "user_data") and isinstance(context.user_data, dict):
        context.user_data.setdefault("pending_deletions", []).append(task)


def _discard_completed_task(task: asyncio.Task) -> None:
    """Remove a completed deletion task from the tracking set."""
    try:
        _pending_message_delete_tasks.discard(task)
    except Exception as e:
        logger.warning("⚠️ Could not remove completed message deletion task from tracking: %s", e)


def cancel_pending_deletions() -> int:
    """Cancel pending message deletion tasks and return the number requested."""
    tasks_to_cancel = list(_pending_message_delete_tasks)
    cancelled_count = 0
    for task in tasks_to_cancel:
        if not task.done():
            task.cancel()
            cancelled_count += 1
        else:
            _pending_message_delete_tasks.discard(task)

    logger.info("🛑 Requested cancellation for %d pending message deletion tasks", cancelled_count)
    return cancelled_count
