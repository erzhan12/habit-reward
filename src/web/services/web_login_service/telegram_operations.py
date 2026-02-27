"""Telegram notification operations for web login service."""

import logging

from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import InvalidToken

from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

WL_CONFIRM_PREFIX = "wl_c_"
WL_DENY_PREFIX = "wl_d_"


async def send_login_notification(
    chat_id: int, request_id: int, token: str, device_info: str | None,
    request_repo,
) -> None:
    """Send the Telegram message with Confirm/Deny buttons.

    Uses plain text (no parse_mode) to prevent Telegram parsing bugs
    from interpreting user-controlled device_info as markdown/HTML,
    even though device_info is already sanitized by
    ``_sanitize_user_agent()`` in ``auth.py``.  This is intentional
    defense-in-depth.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured")
        raise InvalidToken("Bot token is not configured")
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    device_text = device_info or "Unknown device"
    message_text = (
        "Web Login Request\n\n"
        "Someone is trying to log in to your account:\n"
        f"{device_text}\n\n"
        "If this was you, tap Confirm. Otherwise, tap Deny."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Confirm", callback_data=f"{WL_CONFIRM_PREFIX}{token}"),
            InlineKeyboardButton("Deny", callback_data=f"{WL_DENY_PREFIX}{token}"),
        ]
    ])

    async with bot:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
        )

    # Save telegram message ID for later editing
    await maybe_await(
        request_repo.update_telegram_message_id(
            request_id, sent_message.message_id
        )
    )

    logger.info(
        "Login notification sent",
        extra={"request_id": request_id, "operation": "send_notification"},
    )
