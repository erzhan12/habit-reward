"""Handler for /habit_done command with conversation flow."""

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
from src.bot.keyboards import build_habit_selection_keyboard
from src.bot.formatters import format_habit_completion_message
from src.airtable.repositories import user_repository
from src.bot.messages import msg
from src.bot.language import get_message_language

# Conversation states
AWAITING_HABIT_SELECTION = 1


async def habit_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start /habit_done conversation flow.

    Shows inline keyboard with active habits or allows custom text input.
    """
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        return ConversationHandler.END

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return ConversationHandler.END

    # Get all active habits
    habits = habit_service.get_all_active_habits()

    if not habits:
        await update.message.reply_text(
            msg('ERROR_NO_HABITS', lang)
        )
        return ConversationHandler.END

    # Build and send keyboard
    keyboard = build_habit_selection_keyboard(habits)
    await update.message.reply_text(
        msg('HELP_HABIT_SELECTION', lang),
        reply_markup=keyboard
    )

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
    lang = get_message_language(telegram_id, update)
    callback_data = query.data

    if callback_data == "habit_custom":
        # User wants to enter custom text
        await query.edit_message_text(
            msg('HELP_CUSTOM_TEXT', lang)
        )
        return AWAITING_HABIT_SELECTION

    # Extract habit_id from callback_data
    if callback_data.startswith("habit_"):
        habit_id = callback_data.replace("habit_", "")

        # Get habit by ID
        habits = habit_service.get_all_active_habits()
        habit = next((h for h in habits if h.id == habit_id), None)

        if not habit:
            await query.edit_message_text(msg('ERROR_HABIT_NOT_FOUND', lang))
            return ConversationHandler.END

        # Process habit completion
        try:
            result = habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit.name
            )

            # Format and send response
            message = format_habit_completion_message(result, lang)
            await query.edit_message_text(
                text=message,
                parse_mode="Markdown"
            )

        except ValueError as e:
            await query.edit_message_text(msg('ERROR_GENERAL', lang, error=str(e)))

        return ConversationHandler.END

    return ConversationHandler.END


async def habit_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle custom text input for habit classification.
    """
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)
    user_text = update.message.text

    # Get all active habits
    habits = habit_service.get_all_active_habits()
    habit_names = [h.name for h in habits]

    # Use NLP to classify
    matched_habits = nlp_service.classify_habit_from_text(user_text, habit_names)

    if not matched_habits:
        await update.message.reply_text(
            msg('ERROR_NO_MATCH_HABIT', lang)
        )
        return ConversationHandler.END

    # Process first matched habit (can be extended to process all)
    habit_name = matched_habits[0]

    try:
        result = habit_service.process_habit_completion(
            user_telegram_id=telegram_id,
            habit_name=habit_name
        )

        # Format and send response
        message = format_habit_completion_message(result, lang)
        await update.message.reply_text(
            text=message,
            parse_mode="Markdown"
        )

        # If multiple habits matched, notify user
        if len(matched_habits) > 1:
            await update.message.reply_text(
                msg('INFO_MULTIPLE_HABITS', lang,
                    other_habits=', '.join(matched_habits[1:]))
            )

    except ValueError as e:
        await update.message.reply_text(msg('ERROR_GENERAL', lang, error=str(e)))

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)
    await update.message.reply_text(msg('INFO_CANCELLED', lang))
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
