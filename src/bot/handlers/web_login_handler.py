"""Handler for web login Confirm/Deny callback buttons."""

import logging
import re
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.core.models import WebLoginRequest
from src.core.repositories import web_login_request_repository
from src.utils.async_compat import maybe_await
from src.web.services.web_login_service import (
    TOKEN_MIN_LENGTH,
    TOKEN_MAX_LENGTH,
    WL_CONFIRM_PREFIX,
    WL_DENY_PREFIX,
    _ensure_utc,
)

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

    # Validate token format before DB query to reject obviously invalid
    # tokens without touching the database (defense-in-depth).
    if not (TOKEN_MIN_LENGTH <= len(token) <= TOKEN_MAX_LENGTH):
        await query.edit_message_text("⚠️ This login request has expired or was not found.")
        return

    # Get the login request
    login_request = await maybe_await(
        web_login_request_repository.get_by_token(token)
    )

    if not login_request:
        await query.edit_message_text("⚠️ This login request has expired or was not found.")
        return

    # Verify the user pressing the button is the request owner.
    # Both telegram_id values must be compared as strings because:
    #   - login_request.user.telegram_id is a Django CharField (str)
    #   - update.effective_user.id is an int from the Telegram API
    # Without str() conversion, the comparison would always fail due to
    # type mismatch (e.g. "123456" != 123456).
    request_owner_id = str(login_request.user.telegram_id).strip() if login_request.user and login_request.user.telegram_id else ""
    callback_user_id = str(update.effective_user.id).strip()
    if not request_owner_id or callback_user_id != request_owner_id:
        logger.warning(
            "User %s tried to respond to login request for user %s",
            update.effective_user.id,
            login_request.user.telegram_id,
        )
        return

    # Check expiry before processing — use _ensure_utc() to handle naive
    # datetimes when USE_TZ=False (matches the pattern in check_status).
    if login_request.expires_at is None or datetime.now(timezone.utc) > _ensure_utc(login_request.expires_at):
        await query.edit_message_text("⚠️ This login request has expired.")
        return

    # Validate status is a known value
    valid_statuses = [s.value for s in WebLoginRequest.Status]
    if login_request.status not in valid_statuses:
        logger.error(
            "Invalid status '%s' for login request %s",
            login_request.status,
            login_request.id,
        )
        await query.edit_message_text("⚠️ This login request is in an invalid state.")
        return

    # Check if already handled.
    # login_request.status is a plain string from the DB (e.g. "pending"),
    # so we compare against .value (also a string), NOT the enum member.
    if login_request.status != WebLoginRequest.Status.PENDING.value:
        status_text = "confirmed" if login_request.status == WebLoginRequest.Status.CONFIRMED.value else "denied"
        await query.edit_message_text(f"This login request was already {status_text}.")
        return

    if action == 'c':
        updated = await maybe_await(
            web_login_request_repository.update_status(token, WebLoginRequest.Status.CONFIRMED.value)
        )
        if updated == 1:
            await query.edit_message_text("✅ Login confirmed. You can close this message.")
            logger.info("Web login confirmed for user %s", login_request.user_id)
        elif updated == 0:
            await query.edit_message_text("⚠️ This login request has already been processed.")
    else:
        updated = await maybe_await(
            web_login_request_repository.update_status(token, WebLoginRequest.Status.DENIED.value)
        )
        if updated == 1:
            await query.edit_message_text("❌ Login denied. The request has been rejected.")
            logger.info("Web login denied for user %s", login_request.user_id)
        elif updated == 0:
            await query.edit_message_text("⚠️ This login request has already been processed.")


# Handler instance for registration
web_login_handler = CallbackQueryHandler(
    web_login_callback,
    pattern=WEB_LOGIN_PATTERN,
)
