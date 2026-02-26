"""Handler for web login Confirm/Deny callback buttons."""

import logging
import re
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.core.repositories import web_login_request_repository
from src.utils.async_compat import maybe_await
from src.web.services.web_login_service import WL_CONFIRM_PREFIX, WL_DENY_PREFIX

logger = logging.getLogger(__name__)

# Derive pattern from shared constants so button creation and matching stay in sync.
_c = re.escape(WL_CONFIRM_PREFIX)
_d = re.escape(WL_DENY_PREFIX)
WEB_LOGIN_PATTERN = re.compile(rf"^(?:{_c}|{_d})(.+)$")


async def web_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Confirm/Deny button press for web login requests."""
    query = update.callback_query
    await query.answer()

    match = WEB_LOGIN_PATTERN.match(query.data)
    if not match:
        return

    action = 'c' if query.data.startswith(WL_CONFIRM_PREFIX) else 'd'
    token = match.group(1)

    # Get the login request
    login_request = await maybe_await(
        web_login_request_repository.get_by_token(token)
    )

    if not login_request:
        await query.edit_message_text("⚠️ This login request has expired or was not found.")
        return

    # Verify the user pressing the button is the request owner
    if str(update.effective_user.id) != str(login_request.user.telegram_id):
        logger.warning(
            "User %s tried to respond to login request for user %s",
            update.effective_user.id,
            login_request.user.telegram_id,
        )
        return

    # Check expiry before processing
    if datetime.now(timezone.utc) > login_request.expires_at:
        await query.edit_message_text("⚠️ This login request has expired.")
        return

    # Check if already handled
    if login_request.status != 'pending':
        status_text = "confirmed" if login_request.status == 'confirmed' else "denied"
        await query.edit_message_text(f"This login request was already {status_text}.")
        return

    if action == 'c':
        updated = await maybe_await(
            web_login_request_repository.update_status(token, 'confirmed')
        )
        if updated:
            await query.edit_message_text("✅ Login confirmed. You can close this message.")
            logger.info("Web login confirmed for user %s", login_request.user_id)
        else:
            await query.edit_message_text("⚠️ This login request has already been processed.")
    else:
        updated = await maybe_await(
            web_login_request_repository.update_status(token, 'denied')
        )
        if updated:
            await query.edit_message_text("❌ Login denied. The request has been rejected.")
            logger.info("Web login denied for user %s", login_request.user_id)
        else:
            await query.edit_message_text("⚠️ This login request has already been processed.")


# Handler instance for registration
web_login_handler = CallbackQueryHandler(
    web_login_callback,
    pattern=WEB_LOGIN_PATTERN,
)
