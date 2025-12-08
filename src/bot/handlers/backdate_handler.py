"""Handler for /backdate command - log habits for past dates."""

import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

from src.services.habit_service import habit_service
from src.bot.keyboards import (
    build_habit_selection_keyboard,
    build_date_picker_keyboard,
    build_backdate_confirmation_keyboard,
    build_back_to_menu_keyboard,
)
from src.bot.formatters import format_habit_completion_message
from src.core.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import get_message_language_async
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_HABIT = 1
SELECTING_DATE = 2
CONFIRMING_COMPLETION = 3


async def backdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start /backdate conversation flow or handle callback from habit_done.

    Shows list of habits to backdate.
    """
    # Handle both command and callback entry points
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        telegram_id = str(update.effective_user.id)
        username = update.effective_user.username or "N/A"
        logger.info(f"🖱️ Received backdate callback from user {telegram_id} (@{username})")
        message_method = query.edit_message_text
    else:
        telegram_id = str(update.effective_user.id)
        username = update.effective_user.username or "N/A"
        logger.info(f"📨 Received /backdate command from user {telegram_id} (@{username})")
        message_method = update.message.reply_text

    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await message_method(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await message_method(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    lang = user.language or lang

    # Fetch all active habits
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    logger.info(f"🔍 Found {len(habits)} active habits for user {telegram_id}")

    if not habits:
        logger.warning(f"⚠️ No active habits configured for user {telegram_id}")
        await message_method(
            msg('ERROR_NO_HABITS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent ERROR_NO_HABITS message to {telegram_id}")
        return ConversationHandler.END

    # Build and send keyboard
    keyboard = build_habit_selection_keyboard(habits, lang)
    habit_names = [h.name for h in habits]
    logger.info(f"✅ Showing habit selection keyboard to {telegram_id} with habits: {habit_names}")

    await message_method(
        msg('HELP_BACKDATE_SELECT_HABIT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return SELECTING_HABIT


async def habit_selected_for_backdate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle habit selection - show date picker.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🖱️ Received callback '{callback_data}' from user {telegram_id} (@{username})")

    # Extract habit_id from callback_data
    if not callback_data.startswith("backdate_habit_"):
        logger.error(f"❌ Invalid callback pattern: {callback_data}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid callback"))
        return ConversationHandler.END

    habit_id = callback_data.replace("backdate_habit_", "")
    logger.info(f"🎯 User {telegram_id} selected habit_id: {habit_id}")

    # Get user for multi-user support
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.error(f"❌ User {telegram_id} not found")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Get habit by ID
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    habit = next((h for h in habits if str(h.id) == habit_id), None)

    if not habit:
        logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
        await query.edit_message_text(msg('ERROR_HABIT_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Store habit_id in context for later use
    context.user_data['backdate_habit_id'] = habit_id
    context.user_data['backdate_habit_name'] = habit.name

    # Get completed dates for this habit (last 7 days back from today)
    today = date.today()
    start_date = today - timedelta(days=7)
    completed_dates = await maybe_await(
        habit_service.get_habit_completions_for_daterange(
            user.id, habit.id, start_date, today
        )
    )

    logger.info(f"📅 Habit '{habit.name}' has {len(completed_dates)} completions in last 7 days")

    # Build and show date picker
    keyboard = build_date_picker_keyboard(habit_id, completed_dates, lang)
    await query.edit_message_text(
        msg('HELP_BACKDATE_SELECT_DATE', lang, habit_name=habit.name),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent date picker keyboard to {telegram_id}")

    return SELECTING_DATE


async def date_selected_for_backdate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle date selection - show confirmation.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🖱️ Received callback '{callback_data}' from user {telegram_id} (@{username})")

    # Check if date is already completed (disabled button)
    if callback_data.startswith("backdate_date_completed_"):
        logger.info(f"ℹ️ User {telegram_id} clicked already completed date")
        # Extract date for error message
        parts = callback_data.split("_")
        if len(parts) >= 5:
            date_str = parts[4]
            await query.answer(
                msg('ERROR_BACKDATE_DUPLICATE', lang, date=date_str),
                show_alert=True
            )
        return SELECTING_DATE

    # Parse callback data: "backdate_date_{habit_id}_{date_iso}"
    if not callback_data.startswith("backdate_date_"):
        logger.error(f"❌ Invalid callback pattern: {callback_data}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid callback"))
        return ConversationHandler.END

    parts = callback_data.split("_")
    if len(parts) < 4:
        logger.error(f"❌ Invalid callback format: {callback_data}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid callback format"))
        return ConversationHandler.END

    habit_id = parts[2]
    date_str = parts[3]

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.error(f"❌ Invalid date format: {date_str}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid date"))
        return ConversationHandler.END

    logger.info(f"📅 User {telegram_id} selected date: {target_date}")

    # Store in context
    context.user_data['backdate_date'] = target_date
    habit_name = context.user_data.get('backdate_habit_name', 'Unknown')

    # Format date for display
    date_display = target_date.strftime("%d %b %Y")  # Format: 09 Dec 2025

    # Show confirmation
    keyboard = build_backdate_confirmation_keyboard(habit_id, target_date, lang)
    await query.edit_message_text(
        msg('HELP_BACKDATE_CONFIRM', lang, habit_name=habit_name, date=date_display),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent confirmation prompt to {telegram_id}")

    return CONFIRMING_COMPLETION


async def confirm_backdate_completion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Execute the backdated habit completion.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🖱️ User {telegram_id} (@{username}) confirmed backdate")

    # Get stored data from context
    habit_name = context.user_data.get('backdate_habit_name')
    target_date = context.user_data.get('backdate_date')

    if not habit_name or not target_date:
        logger.error(f"❌ Missing context data for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Session data lost"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Process habit completion with target_date
    try:
        logger.info(f"⚙️ Processing backdated habit completion for user {telegram_id}, habit '{habit_name}', date {target_date}")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=target_date
            )
        )

        # Format date for display
        date_display = target_date.strftime("%d %b %Y")  # Format: 09 Dec 2025

        # Format and send response
        message = format_habit_completion_message(result, lang)
        # Add date information to the message
        message = msg('SUCCESS_BACKDATE_COMPLETED', lang, habit_name=habit_name, date=date_display) + "\n\n" + message

        logger.info(f"✅ Habit '{habit_name}' backdated to {target_date} for user {telegram_id}. Streak: {result.streak_count}")
        await query.edit_message_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent backdate success message to {telegram_id}")

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"❌ Error processing backdate for user {telegram_id}: {error_msg}")

        # Map error messages to user-friendly messages
        if "already completed" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_DUPLICATE', lang, date=target_date.strftime("%d %b %Y"))
        elif "future date" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_FUTURE', lang)
        elif "more than" in error_msg.lower() and "days" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_TOO_OLD', lang)
        elif "before habit was created" in error_msg.lower():
            # Extract creation date from error if possible
            user_message = msg('ERROR_BACKDATE_BEFORE_CREATED', lang, date=error_msg.split()[-1])
        else:
            user_message = msg('ERROR_GENERAL', lang, error=error_msg)

        await query.edit_message_text(
            user_message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    # Clean up context
    context.user_data.pop('backdate_habit_id', None)
    context.user_data.pop('backdate_habit_name', None)
    context.user_data.pop('backdate_date', None)

    return ConversationHandler.END


async def cancel_backdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the backdate conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 User {telegram_id} (@{username}) cancelled backdate")
    lang = await get_message_language_async(telegram_id, update)

    # Clean up context
    context.user_data.pop('backdate_habit_id', None)
    context.user_data.pop('backdate_habit_name', None)
    context.user_data.pop('backdate_date', None)

    # Handle both command and callback cancellations
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            msg('INFO_CANCELLED', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            msg('INFO_CANCELLED', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )

    logger.info(f"📤 Sent cancellation message to {telegram_id}")
    return ConversationHandler.END


# Build conversation handler
backdate_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("backdate", backdate_command),
        CallbackQueryHandler(backdate_command, pattern="^backdate_start$")
    ],
    states={
        SELECTING_HABIT: [
            CallbackQueryHandler(habit_selected_for_backdate, pattern="^backdate_habit_")
        ],
        SELECTING_DATE: [
            CallbackQueryHandler(date_selected_for_backdate, pattern="^backdate_date_")
        ],
        CONFIRMING_COMPLETION: [
            CallbackQueryHandler(confirm_backdate_completion, pattern="^backdate_confirm_")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_backdate),
        CallbackQueryHandler(cancel_backdate, pattern="^backdate_cancel$")
    ]
)
