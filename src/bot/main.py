"""Main Telegram bot application."""
# ruff: noqa: E402

import os
import django

# Configure Django before any imports that use Django models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
django.setup()

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from src.utils.logging import setup_logging
from src.bot.handlers.command_handlers import start_command, help_command
from src.bot.handlers.habit_done_handler import habit_done_conversation
from src.bot.handlers.habit_revert_handler import habit_revert_conversation
from src.bot.handlers.backdate_handler import backdate_conversation
from src.bot.handlers.habit_management_handler import (
    add_habit_conversation,
    edit_habit_conversation,
    remove_habit_conversation
)
from src.bot.handlers.reward_handlers import (
    list_rewards_command,
    my_rewards_command,
    claim_reward_conversation,
    add_reward_conversation,
    edit_reward_conversation,
    toggle_reward_conversation,
)
from src.bot.handlers.streak_handler import streaks_command
from src.bot.handlers.menu_handler import get_menu_handlers
from src.bot.handlers.settings_handler import settings_conversation

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Run the bot in polling mode (for development).

    Note: In production, use webhook mode via Django ASGI server.
    This polling mode is kept for local development without webhooks.
    """
    # Initialize Django for development mode
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
    import django
    django.setup()

    # Import settings after Django setup
    from django.conf import settings

    # Create application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add conversation handler for habit_done
    application.add_handler(habit_done_conversation)
    application.add_handler(habit_revert_conversation)
    application.add_handler(backdate_conversation)

    # Add habit management conversation handlers
    application.add_handler(add_habit_conversation)
    application.add_handler(edit_habit_conversation)
    application.add_handler(remove_habit_conversation)

    # Add reward handlers
    application.add_handler(CommandHandler("list_rewards", list_rewards_command))
    application.add_handler(CommandHandler("my_rewards", my_rewards_command))
    application.add_handler(claim_reward_conversation)
    application.add_handler(add_reward_conversation)
    application.add_handler(edit_reward_conversation)
    application.add_handler(toggle_reward_conversation)

    # Add streak handler
    application.add_handler(CommandHandler("streaks", streaks_command))

    # Add settings handler
    application.add_handler(settings_conversation)

    # Register menu callbacks in group 1 (after conversation handlers in group 0)
    # This ensures conversation handlers take precedence when active
    for handler in get_menu_handlers():
        application.add_handler(handler, group=1)

    # Start the bot in polling mode (development)
    logger.info("🤖 Running bot in POLLING mode (development)")
    logger.info("ℹ️ For production, use: uvicorn src.habit_reward_project.asgi:application")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
