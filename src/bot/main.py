"""Main Telegram bot application."""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

from src.config import settings
from src.utils.logging import setup_logging
from src.bot.handlers.habit_done_handler import habit_done_conversation
from src.bot.handlers.reward_handlers import (
    list_rewards_command,
    my_rewards_command,
    claim_reward_command,
    set_reward_status_command,
    add_reward_command
)
from src.bot.handlers.streak_handler import streaks_command
from src.airtable.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import get_message_language, detect_language_from_telegram

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


async def start_command(update: Update, context):
    """Handle /start command."""
    telegram_id = str(update.effective_user.id)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        lang = get_message_language(telegram_id, update)
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
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
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return

    await update.message.reply_text(
        msg('HELP_START_MESSAGE', lang),
        parse_mode="Markdown"
    )


async def help_command(update: Update, context):
    """Handle /help command."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return

    await update.message.reply_text(
        msg('HELP_COMMAND_MESSAGE', lang),
        parse_mode="HTML"
    )


def main():
    """Run the bot."""
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add conversation handler for habit_done
    application.add_handler(habit_done_conversation)

    # Add reward handlers
    application.add_handler(CommandHandler("list_rewards", list_rewards_command))
    application.add_handler(CommandHandler("my_rewards", my_rewards_command))
    application.add_handler(CommandHandler("claim_reward", claim_reward_command))
    application.add_handler(CommandHandler("set_reward_status", set_reward_status_command))
    application.add_handler(CommandHandler("add_reward", add_reward_command))

    # Add streak handler
    application.add_handler(CommandHandler("streaks", streaks_command))

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
