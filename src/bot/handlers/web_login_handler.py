"""Handler for web login Confirm/Deny callback buttons."""

import logging
import re

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.core.repositories import web_login_request_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

WEB_LOGIN_PATTERN = re.compile(r"^web_login_(confirm|deny)_(.+)$")


async def web_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Confirm/Deny button press for web login requests."""
    query = update.callback_query
    await query.answer()

    match = WEB_LOGIN_PATTERN.match(query.data)
    if not match:
        return

    action = match.group(1)  # 'confirm' or 'deny'
    token = match.group(2)

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

    # Check if already handled
    if login_request.status != 'pending':
        status_text = "confirmed" if login_request.status == 'confirmed' else "denied"
        await query.edit_message_text(f"This login request was already {status_text}.")
        return

    if action == 'confirm':
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
