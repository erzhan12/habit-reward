"""Timezone utilities for user-local date calculations."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


def get_user_today(user_timezone: str = 'UTC') -> date:
    """Return today's date in the user's timezone.

    Args:
        user_timezone: IANA timezone name (e.g. 'Asia/Almaty', 'Europe/Moscow')

    Returns:
        Today's date from the user's perspective
    """
    try:
        return datetime.now(ZoneInfo(user_timezone)).date()
    except (KeyError, Exception):
        logger.warning("Invalid timezone '%s', falling back to UTC", user_timezone)
        return datetime.now(ZoneInfo('UTC')).date()


async def get_user_timezone(telegram_id: str) -> str:
    """Fetch user's timezone from database.

    Args:
        telegram_id: Telegram user ID

    Returns:
        IANA timezone string, defaults to 'UTC'
    """
    from src.core.repositories import user_repository
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if user and user.timezone:
        return user.timezone
    return 'UTC'
