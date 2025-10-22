"""Handler for /streaks command."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.services.streak_service import streak_service
from src.airtable.repositories import user_repository, habit_repository
from src.bot.formatters import format_streaks_message
from src.bot.messages import msg
from src.bot.language import get_message_language

# Configure logging
logger = logging.getLogger(__name__)


async def streaks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /streaks command - show current streaks for all habits.
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /streaks command from user {telegram_id} (@{username})")
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

    # Get all streaks
    streaks_dict = streak_service.get_all_streaks_for_user(user.id)
    logger.info(f"🔍 Found {len(streaks_dict)} habit streaks for user {telegram_id}")

    if not streaks_dict:
        logger.info(f"ℹ️ No habit logs found for user {telegram_id}")
        await update.message.reply_text(
            msg('ERROR_NO_HABITS_LOGGED', lang)
        )
        logger.info(f"📤 Sent ERROR_NO_HABITS_LOGGED message to {telegram_id}")
        return

    # Get habit names
    habits_with_names = {}
    for habit_id, streak_count in streaks_dict.items():
        habit = habit_repository.get_by_id(habit_id)
        if habit:
            habits_with_names[habit_id] = (habit.name, streak_count)
            logger.info(f"🔥 User {telegram_id} - Habit '{habit.name}': {streak_count} day streak")

    # Format and send message
    from src.bot.keyboards import build_back_to_menu_keyboard
    message = format_streaks_message(habits_with_names, lang)
    logger.info(f"✅ Sending streak information for {len(habits_with_names)} habits to user {telegram_id}")
    await update.message.reply_text(
        message,
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent streaks message to {telegram_id}")
