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

# Conversation states
AWAITING_HABIT_SELECTION = 1


async def habit_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start /habit_done conversation flow.

    Shows inline keyboard with active habits or allows custom text input.
    """
    telegram_id = str(update.effective_user.id)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please contact admin to register."
        )
        return ConversationHandler.END

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            "❌ Your account is not active. Please contact admin."
        )
        return ConversationHandler.END

    # Get all active habits
    habits = habit_service.get_all_active_habits()

    if not habits:
        await update.message.reply_text(
            "No active habits found. Please add habits first."
        )
        return ConversationHandler.END

    # Build and send keyboard
    keyboard = build_habit_selection_keyboard(habits)
    await update.message.reply_text(
        "Which habit did you complete? 🎯\n\n"
        "Select from the list below:",
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
    callback_data = query.data

    if callback_data == "habit_custom":
        # User wants to enter custom text
        await query.edit_message_text(
            "Please type what habit you completed:"
        )
        return AWAITING_HABIT_SELECTION

    # Extract habit_id from callback_data
    if callback_data.startswith("habit_"):
        habit_id = callback_data.replace("habit_", "")

        # Get habit by ID
        habits = habit_service.get_all_active_habits()
        habit = next((h for h in habits if h.id == habit_id), None)

        if not habit:
            await query.edit_message_text("Habit not found. Please try again.")
            return ConversationHandler.END

        # Process habit completion
        try:
            result = habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit.name
            )

            # Format and send response
            message = format_habit_completion_message(result)
            await query.edit_message_text(
                text=message,
                parse_mode="Markdown"
            )

        except ValueError as e:
            await query.edit_message_text(f"Error: {str(e)}")

        return ConversationHandler.END

    return ConversationHandler.END


async def habit_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle custom text input for habit classification.
    """
    telegram_id = str(update.effective_user.id)
    user_text = update.message.text

    # Get all active habits
    habits = habit_service.get_all_active_habits()
    habit_names = [h.name for h in habits]

    # Use NLP to classify
    matched_habits = nlp_service.classify_habit_from_text(user_text, habit_names)

    if not matched_habits:
        await update.message.reply_text(
            "I couldn't match your text to any known habit. "
            "Please select from the list using /habit_done again."
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
        message = format_habit_completion_message(result)
        await update.message.reply_text(
            text=message,
            parse_mode="Markdown"
        )

        # If multiple habits matched, notify user
        if len(matched_habits) > 1:
            await update.message.reply_text(
                f"I also detected: {', '.join(matched_habits[1:])}. "
                "Use /habit_done to log those separately."
            )

    except ValueError as e:
        await update.message.reply_text(f"Error: {str(e)}")

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Habit logging cancelled.")
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
