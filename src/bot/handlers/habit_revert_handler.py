"""Handlers for /revert_habit command."""

import logging
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from src.bot.keyboards import (
    build_back_to_menu_keyboard,
    build_habit_revert_keyboard,
    build_habits_menu_keyboard,
)
from src.bot.language import get_message_language_async
from src.bot.messages import msg
from src.bot.navigation import get_current_navigation, pop_navigation
from src.core.repositories import user_repository
from src.services.habit_service import habit_service
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_REVERT_SELECTION = 1


async def habit_revert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the /revert_habit flow by listing available habits."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info("📨 Received /revert_habit command from user %s (@%s)", telegram_id, username)

    lang = await get_message_language_async(telegram_id, update)
    message = update.message or update.effective_message

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning("⚠️ User %s not found while attempting revert", telegram_id)
        await message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    if not user.is_active:
        logger.warning("⚠️ User %s is inactive, aborting revert flow", telegram_id)
        await message.reply_text(
            msg('ERROR_USER_INACTIVE', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    if not habits:
        logger.warning("⚠️ No active habits available for user %s during revert", telegram_id)
        await message.reply_text(
            msg('ERROR_NO_HABITS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    context.user_data['revert_habit_map'] = {str(habit.id): habit for habit in habits}
    keyboard = build_habit_revert_keyboard(habits, lang)

    await message.reply_text(
        msg('HELP_REVERT_HABIT_SELECTION', lang),
        reply_markup=keyboard
    )
    logger.info("📤 Sent revert habit selection keyboard to %s", telegram_id)
    return AWAITING_REVERT_SELECTION


async def habit_revert_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection for revert."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data
    logger.info("🖱️ Revert selection callback '%s' received from user %s", callback_data, telegram_id)

    habit_id = callback_data.replace("revert_habit_", "", 1)
    habit_map = context.user_data.get('revert_habit_map', {})
    habit = habit_map.get(habit_id)

    if not habit:
        # Get user for multi-user support
        user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
        if not user:
            logger.error(f"❌ User {telegram_id} not found")
            await query.edit_message_text(
                msg('ERROR_USER_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return ConversationHandler.END

        habits = await maybe_await(habit_service.get_all_active_habits(user.id))
        habit = next((h for h in habits if str(h.id) == habit_id), None)
        context.user_data['revert_habit_map'] = {str(h.id): h for h in habits}

    if not habit:
        logger.error("❌ Habit %s not found during revert for user %s", habit_id, telegram_id)
        await query.edit_message_text(
            msg('ERROR_HABIT_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return ConversationHandler.END

    try:
        result = await maybe_await(
            habit_service.revert_habit_completion(telegram_id, habit.id)
        )
    except ValueError as exc:
        error_message = str(exc)
        logger.error("❌ Revert failed for user %s, habit %s: %s", telegram_id, habit_id, error_message)

        if "No habit completion found to revert" in error_message:
            text = msg('ERROR_NO_LOG_TO_REVERT', lang)
        elif "User with telegram_id" in error_message:
            text = msg('ERROR_USER_NOT_FOUND', lang)
        elif "User is inactive" in error_message:
            text = msg('ERROR_USER_INACTIVE', lang)
        elif "Habit" in error_message and "not found" in error_message:
            text = msg('ERROR_HABIT_NOT_FOUND', lang)
        else:
            text = msg('ERROR_GENERAL', lang, error=error_message)

        await query.edit_message_text(
            text,
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        context.user_data.pop('revert_habit_map', None)
        return ConversationHandler.END

    message_lines = [msg('SUCCESS_HABIT_REVERTED', lang, habit_name=result.habit_name)]

    if result.reward_reverted and result.reward_progress is not None:
        pieces_required = result.reward_progress.get_pieces_required() or 0
        message_lines.append(
            msg(
                'SUCCESS_REWARD_REVERTED',
                lang,
                reward_name=result.reward_name or result.reward_progress.reward_id,
                pieces_earned=result.reward_progress.pieces_earned,
                pieces_required=pieces_required
            )
        )

    message_text = "\n\n".join(message_lines)

    navigation_state = get_current_navigation(context)
    came_from_habits_menu = bool(
        navigation_state and navigation_state.get('menu_type') == 'menu_habits_revert'
    )

    if came_from_habits_menu:
        await query.message.reply_text(
            message_text,
            parse_mode="HTML"
        )

        pop_navigation(context)
        previous_state = get_current_navigation(context)
        menu_lang = previous_state.get('lang', lang) if previous_state else lang

        await query.edit_message_text(
            msg('HABITS_MENU_TITLE', menu_lang),
            reply_markup=build_habits_menu_keyboard(menu_lang),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            message_text,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    logger.info("✅ Habit revert completed for user %s, habit %s", telegram_id, habit_id)

    context.user_data.pop('revert_habit_map', None)
    return ConversationHandler.END


async def cancel_revert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of the revert flow."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    context.user_data.pop('revert_habit_map', None)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            msg('INFO_CANCELLED_REVERT', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
    else:
        message = update.message or update.effective_message
        await message.reply_text(
            msg('INFO_CANCELLED_REVERT', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )

    logger.info("⛔ Revert flow cancelled for user %s", telegram_id)
    return ConversationHandler.END


habit_revert_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("revert_habit", habit_revert_command),
        CallbackQueryHandler(habit_revert_command, pattern="^menu_habits_revert$")
    ],
    states={
        AWAITING_REVERT_SELECTION: [
            CallbackQueryHandler(habit_revert_selected_callback, pattern="^revert_habit_"),
            CallbackQueryHandler(cancel_revert_handler, pattern="^menu_back$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_revert_handler)],
)
