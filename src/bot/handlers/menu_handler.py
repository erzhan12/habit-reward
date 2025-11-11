"""Menu handlers for the unified start menu and submenus."""

import logging
from telegram import Update, Message
from telegram.ext import ContextTypes, CallbackQueryHandler

from src.bot.messages import msg
from src.bot.language import get_message_language_async, set_user_language
from src.bot.keyboards import (
    build_start_menu_keyboard,
    build_habits_menu_keyboard,
    build_rewards_menu_keyboard,
    build_settings_keyboard,
    build_language_selection_keyboard,
    build_back_to_menu_keyboard,
)
from src.bot.navigation import (
    push_navigation,
    pop_navigation,
    clear_navigation,
    update_navigation_language,
    get_current_navigation,
)
from src.services.habit_service import habit_service
from asgiref.sync import sync_to_async
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


async def open_start_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    edited_message = await query.edit_message_text(
        msg('START_MENU_TITLE', lang),
        reply_markup=build_start_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Push navigation state
    push_navigation(context, edited_message.message_id, 'start', lang)
    logger.info(f"📋 Opened start menu for user {telegram_id}")

    return 0


async def open_habits_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    edited_message = await query.edit_message_text(
        msg('HABITS_MENU_TITLE', lang),
        reply_markup=build_habits_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Push navigation state
    push_navigation(context, edited_message.message_id, 'habits', lang)
    logger.info(f"📋 Opened habits menu for user {telegram_id}")

    return 0


async def open_rewards_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    edited_message = await query.edit_message_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Push navigation state
    push_navigation(context, edited_message.message_id, 'rewards', lang)
    logger.info(f"📋 Opened rewards menu for user {telegram_id}")

    return 0


async def close_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close menu by deleting the message."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)

    try:
        # Delete the message completely
        await query.delete_message()
        # Clear navigation stack when menu is closed
        clear_navigation(context)
        logger.info(f"🔒 Menu closed for user {telegram_id}")
    except Exception as e:
        logger.error(f"❌ Failed to close menu for user {telegram_id}: {e}")
    return 0


async def generic_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle back button from any screen.
    Pops navigation stack and returns to previous menu by editing message.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🔙 User {telegram_id} pressed Back button")

    # Pop current state and get previous
    prev_state = pop_navigation(context)
    lang = prev_state.get('lang', 'en')

    # Route to appropriate menu based on previous state
    if not prev_state or prev_state['menu_type'] == 'start':
        # Return to start menu
        try:
            await query.edit_message_text(
                msg('START_MENU_TITLE', lang),
                reply_markup=build_start_menu_keyboard(lang),
                parse_mode="HTML"
            )
            logger.info(f"↩️ Returned user {telegram_id} to start menu")
        except Exception as e:
            logger.error(f"❌ Failed to edit message for user {telegram_id}: {e}")
            # Fallback: send new message if edit fails
            await query.message.reply_text(
                msg('START_MENU_TITLE', lang),
                reply_markup=build_start_menu_keyboard(lang),
                parse_mode="HTML"
            )
    elif prev_state['menu_type'] == 'habits':
        # Return to habits menu
        try:
            await query.edit_message_text(
                msg('HABITS_MENU_TITLE', lang),
                reply_markup=build_habits_menu_keyboard(lang),
                parse_mode="HTML"
            )
            logger.info(f"↩️ Returned user {telegram_id} to habits menu")
        except Exception as e:
            logger.error(f"❌ Failed to edit message for user {telegram_id}: {e}")
            await query.message.reply_text(
                msg('HABITS_MENU_TITLE', lang),
                reply_markup=build_habits_menu_keyboard(lang),
                parse_mode="HTML"
            )
    elif prev_state['menu_type'] == 'rewards':
        # Return to rewards menu
        try:
            await query.edit_message_text(
                msg('REWARDS_MENU_TITLE', lang),
                reply_markup=build_rewards_menu_keyboard(lang),
                parse_mode="HTML"
            )
            logger.info(f"↩️ Returned user {telegram_id} to rewards menu")
        except Exception as e:
            logger.error(f"❌ Failed to edit message for user {telegram_id}: {e}")
            await query.message.reply_text(
                msg('REWARDS_MENU_TITLE', lang),
                reply_markup=build_rewards_menu_keyboard(lang),
                parse_mode="HTML"
            )

    return 0


async def bridge_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Bridge menu callbacks to existing command handlers.
    Creates a proper mock Update that handlers can use.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    data = query.data
    logger.info(f"🔀 Bridging menu callback '{data}' to command handler for user {telegram_id}")

    # Certain actions should trigger command text directly for conversation handlers
    direct_command_map = {
        'menu_habits_remove': '/remove_habit',
    }
    if data in direct_command_map:
        command_text = direct_command_map[data]
        await query.message.chat.send_message(command_text)
        logger.info("📤 Forwarded command %s for user %s", command_text, telegram_id)
        return 0

    # Import handlers dynamically
    from src.bot.main import help_command
    from src.bot.handlers.habit_done_handler import habit_done_command
    from src.bot.handlers.streak_handler import streaks_command
    from src.bot.handlers.settings_handler import settings_command
    from src.bot.handlers.habit_management_handler import (
        add_habit_command,
        edit_habit_command,
        remove_habit_command
    )
    from src.bot.handlers.habit_revert_handler import habit_revert_command
    from src.bot.handlers.reward_handlers import (
        list_rewards_command,
        my_rewards_command,
        claim_reward_command
    )

    # Create a mock message object that handlers can use
    # This mock will edit the original menu message instead of sending new ones
    class MockMessage:
        def __init__(self, original_message, user, should_edit=True):
            self._original = original_message
            self._should_edit = should_edit
            self.message_id = original_message.message_id
            self.date = original_message.date
            self.chat = original_message.chat
            self.from_user = user
            self._bot = original_message._bot

        async def reply_text(self, text, **kwargs):
            """Edit original message or send new message as fallback."""
            if self._should_edit and self._original:
                try:
                    # Edit the menu message in-place
                    logger.info(f"✏️ Editing message {self.message_id} with command output")
                    return await self._original.edit_text(
                        text=text,
                        **kwargs
                    )
                except Exception as e:
                    # Fallback: send new message if edit fails (message too old, etc.)
                    logger.warning(f"⚠️ Failed to edit message {self.message_id}, sending new: {e}")
                    return await self.chat.send_message(text=text, **kwargs)
            else:
                # Send new message
                return await self.chat.send_message(text=text, **kwargs)

        def get_bot(self):
            return self._bot

    mock_message = MockMessage(query.message, update.effective_user)
    
    # Create synthetic update with the mock message
    synthetic_update = Update(
        update_id=update.update_id,
        message=mock_message
    )
    synthetic_update._effective_user = update.effective_user
    synthetic_update._effective_chat = query.message.chat

    mapping = {
        'menu_habit_done': habit_done_command,
        'menu_streaks': streaks_command,
        'menu_settings': settings_command,
        'menu_help': help_command,
        'menu_habits_add': add_habit_command,
        'menu_habits_revert': habit_revert_command,
        # 'menu_habits_edit': edit_habit_command,  # Handled by ConversationHandler
        'menu_habits_remove': remove_habit_command,
        'menu_rewards_list': list_rewards_command,
        'menu_rewards_my': my_rewards_command,
        'menu_rewards_claim': claim_reward_command
    }

    handler = mapping.get(data)
    if handler:
        current_state = get_current_navigation(context)
        if current_state:
            lang = current_state.get('lang', 'en')
        else:
            lang = await get_message_language_async(telegram_id, update)

        push_navigation(
            context,
            query.message.message_id,
            data,
            lang
        )

        try:
            await handler(synthetic_update, context)
        except Exception:
            pop_navigation(context)
            raise
        return 0

    # Fallback: show start menu (only fetch language if needed)
    logger.warning(f"⚠️ Unknown callback data '{data}' from user {telegram_id}, showing start menu")
    lang = await get_message_language_async(telegram_id, update)
    await query.edit_message_text(
        msg('START_MENU_TITLE', lang),
        reply_markup=build_start_menu_keyboard(lang),
        parse_mode="HTML"
    )
    return 0


async def settings_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Select Language button from settings menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    await query.edit_message_text(
        msg('LANGUAGE_SELECTION_MENU', lang),
        reply_markup=build_language_selection_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Showed language selection to {telegram_id}")
    return 0


async def change_language_standalone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    callback_data = query.data
    language_code = callback_data.replace("lang_", "")

    # Update user language
    success = await set_user_language(telegram_id, language_code)

    if success:
        logger.info(f"🌐 Language updated to {language_code} for user {telegram_id}")
        update_navigation_language(context, language_code)
        await query.edit_message_text(
            msg('SETTINGS_MENU', language_code),
            reply_markup=build_settings_keyboard(language_code),
            parse_mode="HTML"
        )
    else:
        logger.error(f"❌ Failed to update language for user {telegram_id}")
        lang = await get_message_language_async(telegram_id, update)
        await query.edit_message_text(
            msg('SETTINGS_MENU', lang),
            reply_markup=build_settings_keyboard(lang),
            parse_mode="HTML"
        )
    return 0


async def settings_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Back button from language selection."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    await query.edit_message_text(
        msg('SETTINGS_MENU', lang),
        reply_markup=build_settings_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Returned to settings menu for {telegram_id}")
    return 0


async def habit_selected_standalone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection from habit_done menu (standalone, outside conversation)."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected habit: {callback_data}")

    # Extract habit_id from callback_data
    if callback_data.startswith("habit_"):
        habit_id = callback_data.replace("habit_", "")

        # Get habit by ID
        habits = await maybe_await(habit_service.get_all_active_habits())
        habit = next((h for h in habits if str(h.id) == habit_id), None)

        if not habit:
            logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
            await query.edit_message_text(
                msg('ERROR_HABIT_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return 0

        # Process habit completion
        try:
            from src.bot.formatters import format_habit_completion_message

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

    return 0


async def view_habit_display_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for view_habit_ callbacks (display only, no action)."""
    query = update.callback_query
    await query.answer()
    # Just acknowledge the callback, don't do anything
    return 0


# Factory to register all menu callbacks in main
def get_menu_handlers():
    return [
        CallbackQueryHandler(open_start_menu_callback, pattern="^menu_start$"),
        CallbackQueryHandler(open_habits_menu_callback, pattern="^menu_habits$"),
        CallbackQueryHandler(open_rewards_menu_callback, pattern="^menu_rewards$"),
        CallbackQueryHandler(close_menu_callback, pattern="^menu_close$"),
        CallbackQueryHandler(bridge_command_callback, pattern="^(menu_habit_done|menu_streaks|menu_settings|menu_help|menu_habits_add|menu_habits_revert|menu_habits_remove|menu_rewards_list|menu_rewards_my|menu_rewards_claim)$"),
        CallbackQueryHandler(open_start_menu_callback, pattern="^menu_back_start$"),
        CallbackQueryHandler(open_habits_menu_callback, pattern="^menu_back_habits$"),
        CallbackQueryHandler(generic_back_callback, pattern="^menu_back$"),
        # Settings standalone handlers (work outside conversation)
        CallbackQueryHandler(settings_language_callback, pattern="^settings_language$"),
        CallbackQueryHandler(change_language_standalone_callback, pattern="^lang_(en|kk|ru)$"),
        CallbackQueryHandler(settings_back_callback, pattern="^settings_back$"),
        # Habit display handler (view only, no action)
        CallbackQueryHandler(view_habit_display_callback, pattern="^view_habit_"),
        # Habit selection standalone handler (work outside conversation)
        CallbackQueryHandler(habit_selected_standalone_callback, pattern="^habit_")
    ]
