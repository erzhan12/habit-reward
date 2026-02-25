"""Handler for /streaks command."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.services.streak_service import streak_service
from src.core.repositories import user_repository, habit_repository
from src.bot.formatters import format_streaks_message
from src.bot.messages import msg
from src.bot.language import get_message_language_async, detect_language_from_telegram
from src.bot.keyboards import build_back_to_menu_keyboard
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)


async def streaks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /streaks command - show current streaks for all habits.
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /streaks command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    # Get all streaks (timezone-aware; broken streaks return 0)
    streaks_dict = await maybe_await(
        streak_service.get_all_streaks_for_user(user.id, user_timezone=user.timezone or 'UTC')
    )
    logger.info(f"🔍 Found {len(streaks_dict)} habit streaks for user {telegram_id}")

    if not streaks_dict:
        logger.info(f"ℹ️ No habit logs found for user {telegram_id}")
        await update.message.reply_text(
            msg('ERROR_NO_HABITS_LOGGED', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent ERROR_NO_HABITS_LOGGED message to {telegram_id}")
        return

    # Get habit names, skipping habits with broken streaks (streak_count == 0)
    habits_with_names = {}
    for habit_id, streak_count in streaks_dict.items():
        if streak_count == 0:
            continue
        habit = await maybe_await(habit_repository.get_by_id(habit_id))
        if habit:
            habits_with_names[habit_id] = (habit.name, streak_count)
            logger.info(f"🔥 User {telegram_id} - Habit '{habit.name}': {streak_count} day streak")

    if not habits_with_names:
        logger.info(f"ℹ️ All streaks are broken for user {telegram_id}, sending no-active-streaks message")
        await update.message.reply_text(
            msg('FORMAT_NO_STREAKS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent FORMAT_NO_STREAKS message to {telegram_id}")
        return

    # Format and send message
    message = format_streaks_message(habits_with_names, lang)
    logger.info(f"✅ Sending streak information for {len(habits_with_names)} habits to user {telegram_id}")
    await update.message.reply_text(
        message,
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent streaks message to {telegram_id}")
