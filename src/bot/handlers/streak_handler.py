"""Handler for /streaks command."""

from telegram import Update
from telegram.ext import ContextTypes

from src.services.streak_service import streak_service
from src.airtable.repositories import user_repository, habit_repository
from src.bot.formatters import format_streaks_message
from src.bot.messages import msg
from src.bot.language import get_message_language


async def streaks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /streaks command - show current streaks for all habits.
    """
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

    # Get all streaks
    streaks_dict = streak_service.get_all_streaks_for_user(user.id)

    if not streaks_dict:
        await update.message.reply_text(
            msg('ERROR_NO_HABITS_LOGGED', lang)
        )
        return

    # Get habit names
    habits_with_names = {}
    for habit_id, streak_count in streaks_dict.items():
        habit = habit_repository.get_by_id(habit_id)
        if habit:
            habits_with_names[habit_id] = (habit.name, streak_count)

    # Format and send message
    message = format_streaks_message(habits_with_names, lang)
    await update.message.reply_text(message, parse_mode="Markdown")
