"""Handler for /habit_done command with conversation flow."""

import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from src.services.habit_service import habit_service
from src.services.nlp_service import nlp_service
from src.bot.keyboards import (
    build_habit_selection_keyboard,
    build_back_to_menu_keyboard,
    build_completion_date_options_keyboard,
    build_date_picker_keyboard,
    build_backdate_confirmation_keyboard,
)
from src.bot.formatters import format_habit_completion_message
from src.core.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import (
    get_message_language_async,
    detect_language_from_telegram,
)
from src.utils.async_compat import maybe_await
from src.bot.timezone_utils import get_user_today, get_user_timezone

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_HABIT_SELECTION = 1
SELECTING_DATE_OPTION = 2
SELECTING_BACKDATE_DATE = 3
CONFIRMING_BACKDATE = 4


async def habit_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start /habit_done conversation flow.

    Shows inline keyboard with active habits or allows custom text input.
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /habit_done command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        fallback_lang = detect_language_from_telegram(update) if update else lang
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', fallback_lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        fallback_lang = detect_language_from_telegram(update) if update else lang
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', fallback_lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    lang = user.language or lang

    # Fetch all active habits for menu display
    all_habits = await maybe_await(habit_service.get_all_active_habits(user.id))

    # Attempt to filter habits already completed today (service method optional)
    habits = all_habits
    try:
        user_tz = await get_user_timezone(telegram_id)
        user_today = get_user_today(user_tz)
        pending_candidates = await maybe_await(
            habit_service.get_active_habits_pending_for_today(user.id, target_date=user_today)
        )
        if isinstance(pending_candidates, list):
            habits = pending_candidates
    except AttributeError:
        logger.debug("Habit service lacks get_active_habits_pending_for_today; using all habits")

    logger.info(
        "🔍 Found %s total active habits and %s remaining today for user %s",
        len(all_habits),
        len(habits),
        telegram_id,
    )

    if not all_habits:
        logger.warning("⚠️ No active habits configured for user %s", telegram_id)
        await update.message.reply_text(
            msg('ERROR_NO_HABITS', lang)
        )
        logger.info(f"📤 Sent ERROR_NO_HABITS message to {telegram_id}")
        return ConversationHandler.END

    if not habits:
        logger.info("🎉 All active habits already completed today for user %s", telegram_id)
        await update.message.reply_text(
            msg('INFO_ALL_HABITS_COMPLETED', lang),
            reply_markup=build_back_to_menu_keyboard(lang),
        )
        logger.info(f"📤 Sent INFO_ALL_HABITS_COMPLETED message to {telegram_id}")
        return ConversationHandler.END

    # Build and send keyboard
    keyboard = build_habit_selection_keyboard(habits, lang)
    habit_names = [h.name for h in habits]
    logger.info(f"✅ Showing habit selection keyboard to {telegram_id} with habits: {habit_names}")

    await update.message.reply_text(
        msg('HELP_HABIT_SELECTION', lang),
        reply_markup=keyboard
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return AWAITING_HABIT_SELECTION


async def habit_selected_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle habit selection from inline keyboard.
    Shows date options (Today/Yesterday/Select Date).
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🖱️ Received callback '{callback_data}' from user {telegram_id} (@{username})")

    if callback_data == "habit_custom":
        # User wants to enter custom text
        logger.info(f"✏️ User {telegram_id} chose custom text input")
        await query.edit_message_text(
            msg('HELP_CUSTOM_TEXT', lang)
        )
        logger.info(f"📤 Sent custom text prompt to {telegram_id}")
        return AWAITING_HABIT_SELECTION

    # Extract habit_id from callback_data
    if callback_data.startswith("habit_"):
        habit_id = callback_data.replace("habit_", "")
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

        # Store habit info in context for date selection
        context.user_data['habit_id'] = habit_id
        context.user_data['habit_name'] = habit.name

        # Show date options keyboard
        keyboard = build_completion_date_options_keyboard(habit_id, lang)
        await query.edit_message_text(
            msg('HELP_SELECT_COMPLETION_DATE', lang, habit_name=habit.name),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent date selection keyboard to {telegram_id}")

        return SELECTING_DATE_OPTION

    return ConversationHandler.END


async def habit_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle custom text input for habit classification.
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    user_text = update.message.text

    logger.info(f"📨 Received custom text from user {telegram_id} (@{username}): '{user_text}'")

    # Get user for multi-user support
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.error(f"❌ User {telegram_id} not found")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Get all active habits
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    habit_names = [h.name for h in habits]

    # Use NLP to classify
    logger.info(f"🤖 Using NLP to classify text '{user_text}' against habits: {habit_names}")
    matched_habits = nlp_service.classify_habit_from_text(user_text, habit_names)

    if not matched_habits:
        logger.warning(f"⚠️ No habits matched for user {telegram_id} with text: '{user_text}'")
        await update.message.reply_text(
            msg('ERROR_NO_MATCH_HABIT', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent ERROR_NO_MATCH_HABIT message to {telegram_id}")
        return ConversationHandler.END

    # Process first matched habit (can be extended to process all)
    habit_name = matched_habits[0]
    logger.info(f"✅ Matched habits for user {telegram_id}: {matched_habits}. Processing first: '{habit_name}'")

    try:
        logger.info(f"⚙️ Processing habit completion for user {telegram_id}, habit '{habit_name}'")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name
            )
        )

        # Format and send response
        message = format_habit_completion_message(result, lang)
        logger.info(f"✅ Habit '{habit_name}' completed successfully for user {telegram_id}. Total weight: {result.total_weight_applied}, Current streak: {result.streak_count}")
        await update.message.reply_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent habit completion success message to {telegram_id}")

        # If multiple habits matched, notify user
        if len(matched_habits) > 1:
            logger.info(f"ℹ️ Multiple habits matched for user {telegram_id}: {matched_habits[1:]}")
            await update.message.reply_text(
                msg('INFO_MULTIPLE_HABITS', lang,
                    other_habits=', '.join(matched_habits[1:]))
            )
            logger.info(f"📤 Sent multiple habits notification to {telegram_id}")

    except ValueError as e:
        logger.error(f"❌ Error processing habit completion for user {telegram_id}: {str(e)}")
        await update.message.reply_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    return ConversationHandler.END


async def handle_today_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle 'Log for Today' button click."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🖱️ User {telegram_id} (@{username}) selected 'Today'")

    # Get habit info from context
    habit_name = context.user_data.get('habit_name')
    if not habit_name:
        logger.error(f"❌ Missing habit_name in context for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Session data lost"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Process habit completion for today
    user_tz = await get_user_timezone(telegram_id)
    try:
        logger.info(f"⚙️ Processing habit completion for today: user {telegram_id}, habit '{habit_name}'")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=None,  # None defaults to today in user's timezone
                user_timezone=user_tz,
            )
        )

        # Format and send response
        message = format_habit_completion_message(result, lang)
        logger.info(f"✅ Habit '{habit_name}' completed for today. Streak: {result.streak_count}")
        await query.edit_message_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent habit completion success message to {telegram_id}")

    except ValueError as e:
        logger.error(f"❌ Error processing habit completion for user {telegram_id}: {str(e)}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    # Clean up context
    context.user_data.pop('habit_id', None)
    context.user_data.pop('habit_name', None)

    return ConversationHandler.END


async def handle_yesterday_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle 'Log for Yesterday' button click."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🖱️ User {telegram_id} (@{username}) selected 'Yesterday'")

    # Get habit info from context
    habit_name = context.user_data.get('habit_name')
    habit_id = context.user_data.get('habit_id')
    if not habit_name:
        logger.error(f"❌ Missing habit_name in context for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Session data lost"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Calculate yesterday's date in user's timezone
    user_tz = await get_user_timezone(telegram_id)
    yesterday = get_user_today(user_tz) - timedelta(days=1)

    # Store in context for confirmation handler
    context.user_data['backdate_date'] = yesterday

    # Format date for display
    date_display = yesterday.strftime("%d %b %Y")  # Format: 09 Dec 2025

    # Show confirmation message (same as "for date" flow)
    keyboard = build_backdate_confirmation_keyboard(habit_id, yesterday, lang)
    await query.edit_message_text(
        msg('HELP_BACKDATE_CONFIRM', lang, habit_name=habit_name, date=date_display),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent yesterday confirmation prompt to {telegram_id} for '{habit_name}' on {yesterday}")

    return CONFIRMING_BACKDATE


async def handle_select_date(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle 'Select Date' button click - show date picker."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🖱️ User {telegram_id} (@{username}) clicked 'Select Date': {callback_data}")

    # Extract habit_id from callback_data: "backdate_habit_{habit_id}"
    if not callback_data.startswith("backdate_habit_"):
        logger.error(f"❌ Invalid callback pattern: {callback_data}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid callback"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    habit_id = callback_data.replace("backdate_habit_", "")
    logger.info(f"🎯 User {telegram_id} wants to select date for habit_id: {habit_id}")

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.error(f"❌ User {telegram_id} not found")
        await query.edit_message_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Get habit by ID
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    habit = next((h for h in habits if str(h.id) == habit_id), None)

    if not habit:
        logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_HABIT_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Store habit info in context (may already be there, but ensure it's set)
    context.user_data['habit_id'] = habit_id
    context.user_data['habit_name'] = habit.name

    # Get completed dates for this habit (last 7 days back from today)
    user_tz = await get_user_timezone(telegram_id)
    today = get_user_today(user_tz)
    start_date = today - timedelta(days=7)
    completed_dates = await maybe_await(
        habit_service.get_habit_completions_for_daterange(
            user.id, habit.id, start_date, today
        )
    )

    logger.info(f"📅 Habit '{habit.name}' has {len(completed_dates)} completions in date range")

    # Build and show date picker
    keyboard = build_date_picker_keyboard(habit_id, completed_dates, lang, user_today=today)
    await query.edit_message_text(
        msg('HELP_BACKDATE_SELECT_DATE', lang, habit_name=habit.name),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent date picker keyboard to {telegram_id}")

    return SELECTING_BACKDATE_DATE


async def handle_backdate_date_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle date selection from picker - show confirmation."""
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
        parts = callback_data.split("_")
        if len(parts) >= 5:
            date_str = parts[4]
            await query.answer(
                msg('ERROR_BACKDATE_DUPLICATE', lang, date=date_str),
                show_alert=True
            )
        return SELECTING_BACKDATE_DATE

    # Parse callback data: "backdate_date_{habit_id}_{date_iso}"
    if not callback_data.startswith("backdate_date_"):
        logger.error(f"❌ Invalid callback pattern: {callback_data}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid callback"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    parts = callback_data.split("_")
    if len(parts) < 4:
        logger.error(f"❌ Invalid callback format: {callback_data}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid callback format"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    habit_id = parts[2]
    date_str = parts[3]

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.error(f"❌ Invalid date format: {date_str}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid date"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    logger.info(f"📅 User {telegram_id} selected date: {target_date}")

    # Store in context
    context.user_data['backdate_date'] = target_date
    habit_name = context.user_data.get('habit_name', 'Unknown')

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

    return CONFIRMING_BACKDATE


async def handle_backdate_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Execute the backdated habit completion."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🖱️ User {telegram_id} (@{username}) confirmed backdate from habit_done flow")

    # Get stored data from context
    habit_name = context.user_data.get('habit_name')
    target_date = context.user_data.get('backdate_date')

    if not habit_name or not target_date:
        logger.error(f"❌ Missing context data for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Session data lost"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    # Process habit completion with target_date
    user_tz = await get_user_timezone(telegram_id)
    try:
        logger.info(f"⚙️ Processing backdated habit completion for user {telegram_id}, habit '{habit_name}', date {target_date}")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=target_date,
                user_timezone=user_tz,
            )
        )

        # Format date for display
        date_display = target_date.strftime("%d %b %Y")  # Format: 09 Dec 2025

        # Format and send response
        message = format_habit_completion_message(result, lang)
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
            user_message = msg(
                'ERROR_BACKDATE_DUPLICATE',
                lang,
                habit_name=habit_name,
                date=target_date.strftime("%d %b %Y")
            )
        elif "future date" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_FUTURE', lang)
        elif "more than" in error_msg.lower() and "days" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_TOO_OLD', lang)
        elif "before habit was created" in error_msg.lower():
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
    context.user_data.pop('habit_id', None)
    context.user_data.pop('habit_name', None)
    context.user_data.pop('backdate_date', None)

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received cancel from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg('INFO_CANCELLED', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            msg('INFO_CANCELLED', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
    logger.info(f"📤 Sent conversation cancelled message to {telegram_id}")

    # Clean up context
    context.user_data.pop('habit_id', None)
    context.user_data.pop('habit_name', None)
    context.user_data.pop('backdate_date', None)

    return ConversationHandler.END


# Build conversation handler
habit_done_conversation = ConversationHandler(
    entry_points=[CommandHandler("habit_done", habit_done_command)],
    states={
        AWAITING_HABIT_SELECTION: [
            CallbackQueryHandler(habit_selected_callback, pattern="^habit_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_custom_text)
        ],
        SELECTING_DATE_OPTION: [
            CallbackQueryHandler(handle_today_selection, pattern="^habit_.*_today$"),
            CallbackQueryHandler(handle_yesterday_selection, pattern="^habit_.*_yesterday$"),
            CallbackQueryHandler(handle_select_date, pattern="^backdate_habit_"),
        ],
        SELECTING_BACKDATE_DATE: [
            CallbackQueryHandler(handle_backdate_date_selection, pattern="^backdate_date_"),
        ],
        CONFIRMING_BACKDATE: [
            CallbackQueryHandler(handle_backdate_confirmation, pattern="^backdate_confirm_"),
            CallbackQueryHandler(cancel_handler, pattern="^backdate_cancel$"),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)]
)
