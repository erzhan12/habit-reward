"""Handler for /settings command and language selection."""

import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler
)

from src.core.repositories import user_repository
from src.bot.keyboards import build_settings_keyboard, build_language_selection_keyboard
from src.bot.messages import msg
from src.bot.language import get_message_language_async, set_user_language
from src.bot.navigation import update_navigation_language
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_SETTINGS_SELECTION = 1
AWAITING_LANGUAGE_SELECTION = 2


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /settings command - entry point for settings menu.

    Returns:
        AWAITING_SETTINGS_SELECTION state
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /settings command from user {telegram_id} (@{username})")

    # Get current language
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Display settings menu
    logger.info(f"✅ Displaying settings menu to user {telegram_id} in language: {lang}")
    await update.message.reply_text(
        msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent settings menu to {telegram_id}")

    return AWAITING_SETTINGS_SELECTION


async def select_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle "Select Language" button callback.

    Returns:
        AWAITING_LANGUAGE_SELECTION state
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"🖱️ User {telegram_id} (@{username}) tapped 'Select Language' button")

    # Get current language
    lang = await get_message_language_async(telegram_id, None)

    # Edit message to show language selection
    logger.info(f"📤 Displaying language selection menu to user {telegram_id}")
    await query.edit_message_text(
        text=msg('LANGUAGE_SELECTION_MENU', lang),
        reply_markup=build_language_selection_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent language selection menu to {telegram_id}")

    return AWAITING_LANGUAGE_SELECTION


async def change_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle language selection button callback.

    Returns:
        AWAITING_SETTINGS_SELECTION state
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"

    # Extract language code from callback data (e.g., "lang_en" -> "en")
    callback_data = query.data
    language_code = callback_data.replace("lang_", "")

    logger.info(f"🖱️ User {telegram_id} (@{username}) selected language: {language_code}")

    # Get old language for logging
    old_lang = await get_message_language_async(telegram_id, None)

    # Update user language
    success = await set_user_language(telegram_id, language_code)

    if success:
        logger.info(f"🌐 Language updated successfully for user {telegram_id}: {old_lang} → {language_code}")
        logger.info(f"✅ User {telegram_id} language changed to {language_code}")

        # Ensure navigation history reflects the new language
        update_navigation_language(context, language_code)

        # Edit message to show settings menu in newly selected language
        await query.edit_message_text(
            text=msg('SETTINGS_MENU', language_code),
            reply_markup=build_settings_keyboard(language_code),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent settings menu in {language_code} to {telegram_id}")
    else:
        logger.error(f"❌ Failed to update language for user {telegram_id}")
        # Show settings menu in old language
        await query.edit_message_text(
            text=msg('SETTINGS_MENU', old_lang),
            reply_markup=build_settings_keyboard(old_lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent settings menu (language update failed) to {telegram_id}")

    return AWAITING_SETTINGS_SELECTION


async def back_to_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle "Back to Settings" button callback.

    Returns:
        AWAITING_SETTINGS_SELECTION state
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"🖱️ User {telegram_id} (@{username}) tapped 'Back to Settings' button")

    # Get current language
    lang = await get_message_language_async(telegram_id, None)

    # Edit message to show settings menu
    logger.info(f"📤 Returning to settings menu for user {telegram_id}")
    await query.edit_message_text(
        text=msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent settings menu to {telegram_id}")

    return AWAITING_SETTINGS_SELECTION


# Conversation handler setup
settings_conversation = ConversationHandler(
    entry_points=[CommandHandler("settings", settings_command)],
    states={
        AWAITING_SETTINGS_SELECTION: [
            CallbackQueryHandler(select_language_callback, pattern="^settings_language$"),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^menu_back$")
        ],
        AWAITING_LANGUAGE_SELECTION: [
            CallbackQueryHandler(change_language_callback, pattern="^lang_(en|kk|ru)$"),
            CallbackQueryHandler(back_to_settings_callback, pattern="^settings_back$")
        ]
    },
    fallbacks=[],
    allow_reentry=True
)
