"""Basic command handlers for the Telegram bot.

This module contains /start and /help command handlers.
These are separated from main.py to avoid Django reentrant initialization
when importing from webhook_handler.py.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.core.repositories import user_repository as default_user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


def _resolve_user_repository():
    """Return the user repository patched by tests when available."""

    try:
        from src.bot import main as bot_main  # Local import avoids circular import at module load
    except ModuleNotFoundError:
        return default_user_repository

    return getattr(bot_main, "user_repository", default_user_repository)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE | None):
    """Handle /start command."""
    from src.bot.messages import msg
    from src.bot.language import detect_language_from_telegram
    from src.bot.navigation import clear_navigation, push_navigation
    from src.bot.keyboards import build_start_menu_keyboard

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /start command from user {telegram_id} (@{username})")

    # Clear navigation stack on /start (fresh start)
    clear_navigation(context)

    user_repository = _resolve_user_repository()

    # Validate user exists (wrap in sync_to_async for Django ORM)
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        lang = detect_language_from_telegram(update) if update else 'en'
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Auto-detect and set language if not already set
    if not user.language or user.language == 'en':
        detected_lang = detect_language_from_telegram(update)
        if detected_lang != 'en' and detected_lang != user.language:
            try:
                await maybe_await(
                    user_repository.update(user.id, {"language": detected_lang})
                )
                user.language = detected_lang
                logger.info(f"Updated language for user {telegram_id} to {detected_lang}")
            except Exception as e:
                logger.warning(f"Failed to update user language: {e}")

    # Get final language for messages
    lang = user.language if user.language else 'en'

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    logger.info(f"✅ Sending start menu to user {telegram_id} in language: {lang}")

    # Note: /start command is not logged to audit trail (frequent, low-value event)

    sent_message = await update.message.reply_text(
        msg('START_MENU_TITLE', lang),
        reply_markup=build_start_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Push initial navigation state
    push_navigation(context, sent_message.message_id, 'start', lang, telegram_id=telegram_id)
    logger.info(f"📤 Sent START_MENU to {telegram_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE | None):
    """Handle /help command."""
    from src.bot.messages import msg
    from src.bot.language import get_message_language_async, detect_language_from_telegram
    from src.bot.keyboards import build_back_to_menu_keyboard

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /help command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    user_repository = _resolve_user_repository()

    # Validate user exists (wrap in sync_to_async for Django ORM)
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        fallback_lang = detect_language_from_telegram(update) if update else lang
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', fallback_lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    logger.info(f"✅ Sending help message to user {telegram_id} in language: {lang}")

    # Note: /help command is not logged to audit trail (frequent, low-value event)

    await update.message.reply_text(
        msg('HELP_COMMAND_MESSAGE', lang),
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent HELP_COMMAND_MESSAGE to {telegram_id}")
