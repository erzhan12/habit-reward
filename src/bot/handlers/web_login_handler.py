"""Handler for web login Confirm/Deny callback buttons."""

import logging
import re
from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from django.db import transaction
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

    # Convert both IDs to strings for comparison (telegram_id is CharField,
    # effective_user.id is int).
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

    # Atomically check status and update inside a transaction with a row
    # lock.  This prevents two concurrent button presses from both seeing
    # status == PENDING and proceeding (TOCTOU race).
    new_status = (
        WebLoginRequest.Status.CONFIRMED.value if action == 'c'
        else WebLoginRequest.Status.DENIED.value
    )

    def _atomic_status_transition():
        """Re-fetch with SELECT FOR UPDATE and transition if still PENDING."""
        with transaction.atomic():
            try:
                lr = (
                    WebLoginRequest.objects
                    .select_for_update()
                    .get(token=token)
                )
            except WebLoginRequest.DoesNotExist:
                return 0, None  # disappeared between fetches
            if lr.status != WebLoginRequest.Status.PENDING.value:
                return 0, lr.status  # already handled
            lr.status = new_status
            lr.save(update_fields=['status'])
            return 1, new_status

    updated, current_status = await sync_to_async(_atomic_status_transition)()

    if updated == 1:
        # Clear cache keys after successful status transition.
        await maybe_await(
            web_login_request_repository.clear_login_cache_keys(token)
        )
        if action == 'c':
            await query.edit_message_text("✅ Login confirmed. You can close this message.")
            logger.info("Web login confirmed for user %s", login_request.user_id)
        else:
            await query.edit_message_text("❌ Login denied. The request has been rejected.")
            logger.info("Web login denied for user %s", login_request.user_id)
    else:
        # Already handled — show appropriate message based on current status.
        if current_status == WebLoginRequest.Status.USED.value:
            await query.edit_message_text("✅ This login request was already completed.")
        elif current_status == WebLoginRequest.Status.CONFIRMED.value:
            await query.edit_message_text("This login request was already confirmed.")
        elif current_status == WebLoginRequest.Status.DENIED.value:
            await query.edit_message_text("This login request was already denied.")
        else:
            await query.edit_message_text("⚠️ This login request has already been processed.")


# Handler instance for registration
web_login_handler = CallbackQueryHandler(
    web_login_callback,
    pattern=WEB_LOGIN_PATTERN,
)
