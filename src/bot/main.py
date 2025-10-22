"""Main Telegram bot application."""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

from src.config import settings
from src.utils.logging import setup_logging
from src.bot.handlers.habit_done_handler import habit_done_conversation
from src.bot.handlers.habit_management_handler import (
    add_habit_conversation,
    edit_habit_conversation,
    remove_habit_conversation
)
from src.bot.handlers.reward_handlers import (
    list_rewards_command,
    my_rewards_command,
    claim_reward_conversation,
    add_reward_command
)
from src.bot.handlers.streak_handler import streaks_command
from src.bot.handlers.menu_handler import get_menu_handlers
from src.bot.handlers.settings_handler import settings_conversation
from src.airtable.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import get_message_language, detect_language_from_telegram

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


async def start_command(update: Update, context):
    """Handle /start command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /start command from user {telegram_id} (@{username})")

    # Clear navigation stack on /start (fresh start)
    from src.bot.navigation import clear_navigation
    clear_navigation(context)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        lang = get_message_language(telegram_id, update)
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
                user_repository.update(user.id, {"language": detected_lang})
                user.language = detected_lang
                logger.info(f"Updated language for user {telegram_id} to {detected_lang}")
            except Exception as e:
                logger.warning(f"Failed to update user language: {e}")

    # Get final language for messages
    lang = user.language if user.language else 'en'

    # Check if user is active
    if not user.active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    logger.info(f"✅ Sending start menu to user {telegram_id} in language: {lang}")
    from src.bot.keyboards import build_start_menu_keyboard
    from src.bot.navigation import push_navigation

    sent_message = await update.message.reply_text(
        msg('START_MENU_TITLE', lang),
        reply_markup=build_start_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Push initial navigation state
    push_navigation(context, sent_message.message_id, 'start', lang)
    logger.info(f"📤 Sent START_MENU to {telegram_id}")


async def help_command(update: Update, context):
    """Handle /help command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /help command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    logger.info(f"✅ Sending help message to user {telegram_id} in language: {lang}")
    from src.bot.keyboards import build_back_to_menu_keyboard
    await update.message.reply_text(
        msg('HELP_COMMAND_MESSAGE', lang),
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent HELP_COMMAND_MESSAGE to {telegram_id}")


def main():
    """Run the bot."""
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add conversation handler for habit_done
    application.add_handler(habit_done_conversation)

    # Add habit management conversation handlers
    application.add_handler(add_habit_conversation)
    application.add_handler(edit_habit_conversation)
    application.add_handler(remove_habit_conversation)

    # Add reward handlers
    application.add_handler(CommandHandler("list_rewards", list_rewards_command))
    application.add_handler(CommandHandler("my_rewards", my_rewards_command))
    application.add_handler(claim_reward_conversation)
    application.add_handler(CommandHandler("add_reward", add_reward_command))

    # Add streak handler
    application.add_handler(CommandHandler("streaks", streaks_command))

    # Add settings handler
    application.add_handler(settings_conversation)

    # Register menu callbacks
    for handler in get_menu_handlers():
        application.add_handler(handler)

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
