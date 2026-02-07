"""Timezone utilities for user-local date calculations."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


def validate_timezone(tz_string: str) -> bool:
    """Validate an IANA timezone string.

    Args:
        tz_string: Timezone name to validate (e.g. 'Asia/Almaty')

    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(tz_string)
        return True
    except (KeyError, ZoneInfoNotFoundError, ValueError):
        return False


def get_user_today(user_timezone: str = 'UTC') -> date:
    """Return today's date in the user's timezone.

    Args:
        user_timezone: IANA timezone name (e.g. 'Asia/Almaty', 'Europe/Moscow')

    Returns:
        Today's date from the user's perspective
    """
    try:
        return datetime.now(ZoneInfo(user_timezone)).date()
    except (KeyError, ZoneInfoNotFoundError, ValueError):
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
