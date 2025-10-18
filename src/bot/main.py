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

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)


async def start_command(update: Update, context):
    """Handle /start command."""
    telegram_id = str(update.effective_user.id)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please contact admin to register."
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            "❌ Your account is not active. Please contact admin."
        )
        return

    await update.message.reply_text(
        "🎯 *Welcome to Habit Reward System!*\n\n"
        "Track your habits and earn rewards!\n\n"
        "*Available commands:*\n"
        "/habit_done - Log a completed habit\n"
        "/streaks - View your current streaks\n"
        "/list_rewards - See all available rewards\n"
        "/my_rewards - Check your reward progress\n"
        "/claim_reward <name> - Claim an achieved reward\n"
        "/set_reward_status <name> <status> - Update reward status\n"
        "/help - Show this help message",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context):
    """Handle /help command."""
    telegram_id = str(update.effective_user.id)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please contact admin to register."
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            "❌ Your account is not active. Please contact admin."
        )
        return

    await update.message.reply_text(
        "🎯 <b>Habit Reward System Help</b>\n\n"
        "<b>Core Commands:</b>\n"
        "/habit_done - Log a habit completion and earn rewards\n"
        "/streaks - View your current streaks for all habits\n\n"
        "<b>Reward Commands:</b>\n"
        "/list_rewards - List all available rewards\n"
        "/my_rewards - View your cumulative reward progress\n"
        "/claim_reward &lt;name&gt; - Mark an achieved reward as completed\n"
        "/set_reward_status &lt;name&gt; &lt;status&gt; - Manually update reward status\n\n"
        "<b>How it works:</b>\n"
        "1. Complete a habit using /habit_done\n"
        "2. Build streaks by completing habits daily\n"
        "3. Earn reward pieces (cumulative rewards)\n"
        "4. Claim rewards when you have enough pieces\n\n"
        "Your streak multiplier increases your chances of getting rewards!",
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
