"""Handler for /habit_done command with conversation flow."""

import logging
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
from src.bot.keyboards import build_habit_selection_keyboard, build_back_to_menu_keyboard
from src.bot.formatters import format_habit_completion_message
from src.core.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import (
    get_message_language_async,
    detect_language_from_telegram,
)
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_HABIT_SELECTION = 1


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
        pending_candidates = await maybe_await(
            habit_service.get_active_habits_pending_for_today(user.id)
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

        # Process habit completion
        try:
            logger.info(f"⚙️ Processing habit completion for user {telegram_id}, habit '{habit.name}'")
            result = await maybe_await(
                habit_service.process_habit_completion(
                    user_telegram_id=telegram_id,
                    habit_name=habit.name
                )
            )

            # Format and send response
            message = format_habit_completion_message(result, lang)
            logger.info(f"✅ Habit '{habit.name}' completed successfully for user {telegram_id}. Total weight: {result.total_weight_applied}, Current streak: {result.streak_count}")
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
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            logger.info(f"📤 Sent error message to {telegram_id}")

        return ConversationHandler.END

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


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)
    await update.message.reply_text(
        msg('INFO_CANCELLED', lang),
        reply_markup=build_back_to_menu_keyboard(lang)
    )
    logger.info(f"📤 Sent conversation cancelled message to {telegram_id}")
    return ConversationHandler.END


# Build conversation handler
habit_done_conversation = ConversationHandler(
    entry_points=[CommandHandler("habit_done", habit_done_command)],
    states={
        AWAITING_HABIT_SELECTION: [
            CallbackQueryHandler(habit_selected_callback, pattern="^habit_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_custom_text)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_handler)]
)
