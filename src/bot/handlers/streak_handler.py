"""Handler for /streaks command."""

from telegram import Update
from telegram.ext import ContextTypes

from src.services.streak_service import streak_service
from src.airtable.repositories import user_repository, habit_repository
from src.bot.formatters import format_streaks_message


async def streaks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /streaks command - show current streaks for all habits.
    """
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

    # Get all streaks
    streaks_dict = streak_service.get_all_streaks_for_user(user.id)

    if not streaks_dict:
        await update.message.reply_text(
            "No habits logged yet. Use /habit_done to start building your streaks!"
        )
        return

    # Get habit names
    habits_with_names = {}
    for habit_id, streak_count in streaks_dict.items():
        habit = habit_repository.get_by_id(habit_id)
        if habit:
            habits_with_names[habit_id] = (habit.name, streak_count)

    # Format and send message
    message = format_streaks_message(habits_with_names)
    await update.message.reply_text(message, parse_mode="Markdown")
