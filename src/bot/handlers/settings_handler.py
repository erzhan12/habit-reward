"""Handler for /settings command and language selection."""

import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.core.repositories import user_repository
from src.bot.keyboards import build_settings_keyboard, build_language_selection_keyboard, build_no_reward_probability_keyboard, build_timezone_selection_keyboard
from src.bot.timezone_utils import validate_timezone
from src.bot.messages import msg
from src.bot.language import get_message_language_async, set_user_language
from src.bot.navigation import update_navigation_language
from src.bot.navigation import push_navigation
from src.utils.async_compat import maybe_await
from src.api.services.auth_code_service import api_key_service

# Configure logging
logger = logging.getLogger(__name__)

API_KEY_MESSAGE_DELETE_SECONDS = 300  # 5 minutes


async def _delete_api_key_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job callback to delete the API key message after timeout."""
    chat_id = context.job.data["chat_id"]
    message_id = context.job.data["message_id"]
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logger.warning(f"Could not delete API key message {message_id} in chat {chat_id}")

# Conversation states
AWAITING_SETTINGS_SELECTION = 1
AWAITING_LANGUAGE_SELECTION = 2
AWAITING_API_KEY_SELECTION = 3
AWAITING_API_KEY_NAME = 4
AWAITING_KEY_REVOKE_CONFIRMATION = 5
AWAITING_NO_REWARD_PROB_SELECTION = 6
AWAITING_NO_REWARD_PROB_CUSTOM = 7
AWAITING_TIMEZONE_SELECTION = 8
AWAITING_TIMEZONE_CUSTOM = 9


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


async def settings_menu_entry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for Settings when opened from the /start inline menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"🖱️ User {telegram_id} (@{username}) opened Settings from menu")

    lang = await get_message_language_async(telegram_id, None)

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
        return ConversationHandler.END

    push_navigation(context, query.message.message_id, 'menu_settings', lang, telegram_id=telegram_id)

    await query.edit_message_text(
        msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML",
    )
    return AWAITING_SETTINGS_SELECTION


async def menu_back_end_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Back button in Settings by ending the conversation.

    The actual navigation (message edit) is handled by the menu back handler registered in a later group.
    """
    return ConversationHandler.END


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


# API Key Management Handlers


def build_api_keys_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Build keyboard for API keys menu."""
    keyboard = [
        [InlineKeyboardButton(msg('API_KEY_CREATE', lang), callback_data="apikey_create")],
        [InlineKeyboardButton(msg('API_KEY_LIST', lang), callback_data="apikey_list")],
        [InlineKeyboardButton(msg('API_KEY_REVOKE', lang), callback_data="apikey_revoke")],
        [InlineKeyboardButton(msg('BACK_TO_SETTINGS', lang), callback_data="settings_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_api_key_revoke_keyboard(keys: list, lang: str) -> InlineKeyboardMarkup:
    """Build keyboard to select a key to revoke."""
    keyboard = []
    for key in keys:
        keyboard.append([
            InlineKeyboardButton(
                f"❌ {key.name}",
                callback_data=f"revoke_key_{key.id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(msg('BACK', lang), callback_data="apikey_menu")
    ])
    return InlineKeyboardMarkup(keyboard)


async def api_keys_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle API Keys menu button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} opened API Keys menu")

    lang = await get_message_language_async(telegram_id, None)

    await query.edit_message_text(
        text=msg('API_KEY_MENU', lang),
        reply_markup=build_api_keys_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_API_KEY_SELECTION


async def api_key_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Create API Key button - ask for key name."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} wants to create API key")

    lang = await get_message_language_async(telegram_id, None)

    await query.edit_message_text(
        text=msg('API_KEY_ENTER_NAME', lang),
        parse_mode="HTML"
    )

    return AWAITING_API_KEY_NAME


async def api_key_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user entering API key name."""
    telegram_id = str(update.effective_user.id)
    key_name = update.message.text.strip()

    logger.info(f"📨 User {telegram_id} entered API key name: {key_name}")

    lang = await get_message_language_async(telegram_id, None)

    # Validate name length
    if len(key_name) > 100:
        await update.message.reply_text(
            msg('API_KEY_NAME_TOO_LONG', lang),
            parse_mode="HTML"
        )
        return AWAITING_API_KEY_NAME

    if len(key_name) < 1:
        await update.message.reply_text(
            msg('API_KEY_NAME_EMPTY', lang),
            parse_mode="HTML"
        )
        return AWAITING_API_KEY_NAME

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    try:
        # Create API key
        api_key, raw_key = await api_key_service.create_api_key(
            user_id=user.id,
            name=key_name,
        )

        logger.info(f"✅ API key '{key_name}' created for user {telegram_id}")

        # Send the key (shown ONCE)
        message = msg('API_KEY_CREATED', lang).format(
            name=html.escape(key_name),
            key=raw_key,
        )

        key_message = await update.message.reply_text(
            message,
            parse_mode="HTML"
        )

        # Schedule auto-deletion of the key message after 5 minutes
        job_queue = getattr(context, "job_queue", None)
        if job_queue:
            job_queue.run_once(
                _delete_api_key_message,
                when=API_KEY_MESSAGE_DELETE_SECONDS,
                data={"chat_id": key_message.chat_id, "message_id": key_message.message_id},
            )
        else:
            logger.warning("JobQueue unavailable; API key message will not auto-delete.")

        # Return to API keys menu
        await update.message.reply_text(
            msg('API_KEY_MENU', lang),
            reply_markup=build_api_keys_keyboard(lang),
            parse_mode="HTML"
        )

        return AWAITING_API_KEY_SELECTION

    except ValueError as e:
        logger.warning(f"⚠️ Failed to create API key for {telegram_id}: {e}")
        await update.message.reply_text(
            msg('API_KEY_NAME_EXISTS', lang).format(name=html.escape(key_name)),
            parse_mode="HTML"
        )
        return AWAITING_API_KEY_NAME


async def api_key_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle List API Keys button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} viewing API keys list")

    lang = await get_message_language_async(telegram_id, None)

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Get API keys
    keys = await api_key_service.list_user_keys(user.id)

    if not keys:
        message = msg('API_KEY_LIST_EMPTY', lang)
    else:
        lines = [msg('API_KEY_LIST_HEADER', lang)]
        for key in keys:
            created = key.created_at.strftime("%d %b %Y")
            if key.last_used_at:
                last_used = key.last_used_at.strftime("%d %b %Y %H:%M")
            else:
                last_used = msg('API_KEY_NEVER_USED', lang)
            lines.append(f"• <b>{html.escape(key.name)}</b>")
            lines.append(f"  📅 {msg('API_KEY_CREATED_AT', lang)}: {created}")
            lines.append(f"  🕐 {msg('API_KEY_LAST_USED', lang)}: {last_used}")
            lines.append("")
        message = "\n".join(lines)

    keyboard = [[InlineKeyboardButton(msg('BACK', lang), callback_data="apikey_menu")]]

    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    return AWAITING_API_KEY_SELECTION


async def api_key_revoke_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Revoke API Key button - show list of keys to revoke."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} wants to revoke API key")

    lang = await get_message_language_async(telegram_id, None)

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Get API keys
    keys = await api_key_service.list_user_keys(user.id)

    if not keys:
        keyboard = [[InlineKeyboardButton(msg('BACK', lang), callback_data="apikey_menu")]]
        await query.edit_message_text(
            text=msg('API_KEY_LIST_EMPTY', lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return AWAITING_API_KEY_SELECTION

    await query.edit_message_text(
        text=msg('API_KEY_SELECT_TO_REVOKE', lang),
        reply_markup=build_api_key_revoke_keyboard(keys, lang),
        parse_mode="HTML"
    )

    return AWAITING_KEY_REVOKE_CONFIRMATION


async def api_key_revoke_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle API key revoke confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    callback_data = query.data

    # Extract key ID from callback data (e.g., "revoke_key_123" -> "123")
    key_id = callback_data.replace("revoke_key_", "")

    logger.info(f"🖱️ User {telegram_id} revoking API key {key_id}")

    lang = await get_message_language_async(telegram_id, None)

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Revoke key
    revoked = await api_key_service.revoke_key(key_id, user.id)

    if revoked:
        logger.info(f"✅ API key '{revoked.name}' revoked for user {telegram_id}")
        message = msg('API_KEY_REVOKED', lang).format(name=html.escape(revoked.name))
    else:
        logger.warning(f"⚠️ Failed to revoke API key {key_id} for user {telegram_id}")
        message = msg('API_KEY_REVOKE_FAILED', lang)

    # Return to API keys menu
    await query.edit_message_text(
        text=message + "\n\n" + msg('API_KEY_MENU', lang),
        reply_markup=build_api_keys_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_API_KEY_SELECTION


async def back_to_apikey_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back to API keys menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, None)

    await query.edit_message_text(
        text=msg('API_KEY_MENU', lang),
        reply_markup=build_api_keys_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_API_KEY_SELECTION


# No Reward Probability Handlers


async def no_reward_prob_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle No Reward Probability menu button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} opened No Reward Probability menu")

    lang = await get_message_language_async(telegram_id, None)

    # Get current value from user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    current_value = getattr(user, 'no_reward_probability', 50.0)

    await query.edit_message_text(
        text=msg('NO_REWARD_PROB_MENU', lang).format(current=current_value),
        reply_markup=build_no_reward_probability_keyboard(current_value, lang),
        parse_mode="HTML"
    )

    return AWAITING_NO_REWARD_PROB_SELECTION


async def no_reward_prob_preset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle preset selection (25%, 50%, 75%)."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    callback_data = query.data

    # Extract value from callback data (e.g., "no_reward_prob_25" -> 25)
    value = float(callback_data.replace("no_reward_prob_", ""))

    logger.info(f"🖱️ User {telegram_id} selected preset no_reward_probability: {value}%")

    lang = await get_message_language_async(telegram_id, None)

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Update user's no_reward_probability
    await maybe_await(user_repository.update(user.id, {'no_reward_probability': value}))

    logger.info(f"✅ Updated no_reward_probability to {value}% for user {telegram_id}")

    # Show success and return to settings
    await query.edit_message_text(
        text=msg('NO_REWARD_PROB_UPDATED', lang).format(value=value) + "\n\n" + msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_SETTINGS_SELECTION


async def no_reward_prob_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Custom button - prompt for custom value."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} wants to enter custom no_reward_probability")

    lang = await get_message_language_async(telegram_id, None)

    await query.edit_message_text(
        text=msg('NO_REWARD_PROB_ENTER_CUSTOM', lang),
        parse_mode="HTML"
    )

    return AWAITING_NO_REWARD_PROB_CUSTOM


async def no_reward_prob_custom_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user entering custom probability value."""
    telegram_id = str(update.effective_user.id)
    user_input = update.message.text.strip()

    logger.info(f"📨 User {telegram_id} entered custom no_reward_probability: {user_input}")

    lang = await get_message_language_async(telegram_id, None)

    # Validate input
    try:
        value = float(user_input)
        if value < 0.01 or value > 99.99:
            raise ValueError("Out of range")
    except ValueError:
        logger.warning(f"⚠️ Invalid no_reward_probability value from user {telegram_id}: {user_input}")
        await update.message.reply_text(
            msg('NO_REWARD_PROB_INVALID', lang),
            parse_mode="HTML"
        )
        return AWAITING_NO_REWARD_PROB_CUSTOM

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Update user's no_reward_probability
    await maybe_await(user_repository.update(user.id, {'no_reward_probability': value}))

    logger.info(f"✅ Updated no_reward_probability to {value}% for user {telegram_id}")

    # Show success and return to settings
    await update.message.reply_text(
        text=msg('NO_REWARD_PROB_UPDATED', lang).format(value=value) + "\n\n" + msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_SETTINGS_SELECTION


# Timezone Handlers


async def timezone_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Timezone menu button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} opened Timezone menu")

    lang = await get_message_language_async(telegram_id, None)

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    current_tz = user.timezone or 'UTC'

    await query.edit_message_text(
        text=msg('TIMEZONE_MENU', lang, current=current_tz),
        reply_markup=build_timezone_selection_keyboard(current_tz, lang),
        parse_mode="HTML"
    )

    return AWAITING_TIMEZONE_SELECTION


async def change_timezone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone selection button callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"

    # Extract timezone from callback data (e.g., "tz_Asia/Almaty" -> "Asia/Almaty")
    callback_data = query.data
    lang = await get_message_language_async(telegram_id, None)

    if not callback_data.startswith("tz_"):
        logger.error(f"⚠️ Invalid callback_data format: {callback_data}")
        return AWAITING_SETTINGS_SELECTION

    timezone = callback_data[3:]

    logger.info(f"🖱️ User {telegram_id} (@{username}) selected timezone: {timezone}")

    if not validate_timezone(timezone):
        logger.warning(f"⚠️ Invalid timezone '{timezone}' from user {telegram_id}")
        await query.edit_message_text(
            text=msg('ERROR_GENERAL', lang, error="Invalid timezone"),
            reply_markup=build_settings_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_SETTINGS_SELECTION

    # Update user timezone
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    await maybe_await(user_repository.update(user.id, {'timezone': timezone}))

    logger.info(f"🕐 Timezone updated to '{timezone}' for user {telegram_id}")

    # Show success and return to settings
    await query.edit_message_text(
        text=msg('TIMEZONE_UPDATED', lang, timezone=timezone) + "\n\n" + msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_SETTINGS_SELECTION


async def timezone_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Type custom' timezone button - prompt for text input."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🖱️ User {telegram_id} wants to enter custom timezone")

    lang = await get_message_language_async(telegram_id, None)

    await query.edit_message_text(
        text=msg('TIMEZONE_ENTER_CUSTOM', lang),
        parse_mode="HTML"
    )

    return AWAITING_TIMEZONE_CUSTOM


async def timezone_custom_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user entering custom timezone name."""
    telegram_id = str(update.effective_user.id)
    user_input = update.message.text.strip()

    logger.info(f"📨 User {telegram_id} entered custom timezone: {user_input}")

    lang = await get_message_language_async(telegram_id, None)

    if not validate_timezone(user_input):
        logger.warning(f"⚠️ Invalid timezone '{user_input}' from user {telegram_id}")
        await update.message.reply_text(
            msg('TIMEZONE_INVALID', lang),
            parse_mode="HTML"
        )
        return AWAITING_TIMEZONE_CUSTOM

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Update user timezone
    await maybe_await(user_repository.update(user.id, {'timezone': user_input}))

    logger.info(f"🕐 Timezone updated to '{user_input}' for user {telegram_id}")

    # Show success and return to settings
    await update.message.reply_text(
        text=msg('TIMEZONE_UPDATED', lang, timezone=user_input) + "\n\n" + msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )

    return AWAITING_SETTINGS_SELECTION


# Conversation handler setup
settings_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("settings", settings_command),
        CallbackQueryHandler(settings_menu_entry_callback, pattern="^menu_settings$"),
    ],
    states={
        AWAITING_SETTINGS_SELECTION: [
            CallbackQueryHandler(select_language_callback, pattern="^settings_language$"),
            CallbackQueryHandler(timezone_menu_callback, pattern="^settings_timezone$"),
            CallbackQueryHandler(api_keys_menu_callback, pattern="^settings_api_keys$"),
            CallbackQueryHandler(no_reward_prob_menu_callback, pattern="^settings_no_reward_prob$"),
            CallbackQueryHandler(menu_back_end_conversation, pattern="^menu_back$")
        ],
        AWAITING_LANGUAGE_SELECTION: [
            CallbackQueryHandler(change_language_callback, pattern="^lang_(en|kk|ru)$"),
            CallbackQueryHandler(back_to_settings_callback, pattern="^settings_back$")
        ],
        AWAITING_API_KEY_SELECTION: [
            CallbackQueryHandler(api_key_create_callback, pattern="^apikey_create$"),
            CallbackQueryHandler(api_key_list_callback, pattern="^apikey_list$"),
            CallbackQueryHandler(api_key_revoke_callback, pattern="^apikey_revoke$"),
            CallbackQueryHandler(back_to_settings_callback, pattern="^settings_back$"),
            CallbackQueryHandler(back_to_apikey_menu_callback, pattern="^apikey_menu$"),
        ],
        AWAITING_API_KEY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, api_key_name_entered),
        ],
        AWAITING_KEY_REVOKE_CONFIRMATION: [
            CallbackQueryHandler(api_key_revoke_confirm_callback, pattern="^revoke_key_"),
            CallbackQueryHandler(back_to_apikey_menu_callback, pattern="^apikey_menu$"),
        ],
        AWAITING_NO_REWARD_PROB_SELECTION: [
            CallbackQueryHandler(no_reward_prob_preset_callback, pattern="^no_reward_prob_(25|50|75)$"),
            CallbackQueryHandler(no_reward_prob_custom_callback, pattern="^no_reward_prob_custom$"),
            CallbackQueryHandler(back_to_settings_callback, pattern="^settings_back$"),
        ],
        AWAITING_NO_REWARD_PROB_CUSTOM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, no_reward_prob_custom_entered),
        ],
        AWAITING_TIMEZONE_SELECTION: [
            CallbackQueryHandler(timezone_custom_callback, pattern="^tz_custom$"),
            CallbackQueryHandler(change_timezone_callback, pattern="^tz_"),
            CallbackQueryHandler(back_to_settings_callback, pattern="^settings_back$"),
        ],
        AWAITING_TIMEZONE_CUSTOM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, timezone_custom_entered),
        ],
    },
    fallbacks=[],
    allow_reentry=True
)
