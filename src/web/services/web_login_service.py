"""Web login service for bot-based Confirm/Deny authentication."""

import html
import logging
import secrets
from datetime import datetime, timezone, timedelta

from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from src.core.repositories import user_repository, web_login_request_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

LOGIN_REQUEST_EXPIRY_MINUTES = 5


class WebLoginService:
    """Service for bot-based web login flow."""

    def __init__(self):
        self.user_repo = user_repository
        self.request_repo = web_login_request_repository

    async def create_login_request(
        self, username: str, device_info: str | None = None
    ) -> dict | None:
        """Create a login request and send Confirm/Deny to user via bot.

        Args:
            username: Telegram @username (with or without @)
            device_info: Browser/device info string

        Returns:
            Dict with {token, expires_at} on success, None if user not found

        Raises:
            ValueError: If rate limited or other validation error
        """
        user = await maybe_await(self.user_repo.get_by_telegram_username(username))
        if not user:
            logger.warning("Web login request for unknown username: @%s", username)
            return None

        if not user.telegram_id:
            logger.warning("User @%s has no telegram_id", username)
            return None

        # Invalidate any pending requests for this user
        await maybe_await(self.request_repo.invalidate_pending_for_user(user.id))

        # Create new request
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_REQUEST_EXPIRY_MINUTES)

        login_request = await maybe_await(
            self.request_repo.create(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
                device_info=device_info,
            )
        )

        # Send Telegram message with Confirm/Deny buttons
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            device_text = html.escape(device_info or "Unknown device")
            message_text = (
                f"🔐 <b>Web Login Request</b>\n\n"
                f"Someone is trying to log in to your account:\n"
                f"📱 {device_text}\n\n"
                f"If this was you, tap <b>Confirm</b>. Otherwise, tap <b>Deny</b>."
            )

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"wl_c_{token}"),
                    InlineKeyboardButton("❌ Deny", callback_data=f"wl_d_{token}"),
                ]
            ])

            async with bot:
                sent_message = await bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )

            # Save telegram message ID for later editing
            await maybe_await(
                self.request_repo.update_telegram_message_id(
                    login_request.id, sent_message.message_id
                )
            )

            logger.info(
                "Web login request created for user %s (token=%s...)",
                user.id,
                token[:8],
            )

        except Exception as e:
            logger.error("Failed to send Telegram login message: %s", e)
            # Failed to send — return None so view returns generic message
            return None

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    async def check_status(self, token: str) -> str:
        """Check the status of a login request.

        Returns:
            One of: 'pending', 'confirmed', 'denied', 'expired', 'not_found'
        """
        login_request = await maybe_await(self.request_repo.get_by_token(token))
        if not login_request:
            return "not_found"

        # Check expiry
        if datetime.now(timezone.utc) > login_request.expires_at:
            return "expired"

        return login_request.status

    async def complete_login(self, token: str):
        """Complete the login after confirmation.

        Args:
            token: Login request token

        Returns:
            User instance if login is valid, None otherwise
        """
        login_request = await maybe_await(self.request_repo.get_by_token(token))
        if not login_request:
            logger.warning("Complete login attempt with unknown token: %s...", token[:8])
            return None

        # Must be confirmed
        if login_request.status != 'confirmed':
            logger.warning(
                "Complete login attempt with status=%s for token=%s...",
                login_request.status,
                token[:8],
            )
            return None

        # Must not be expired
        if datetime.now(timezone.utc) > login_request.expires_at:
            logger.warning("Complete login attempt with expired token: %s...", token[:8])
            return None

        # Atomically mark as used to prevent token replay
        updated = await maybe_await(self.request_repo.mark_as_used(token))
        if not updated:
            logger.warning("Token replay attempt — already used: %s...", token[:8])
            return None

        logger.info("Web login completed for user %s", login_request.user_id)
        return login_request.user


# Global service instance
web_login_service = WebLoginService()
