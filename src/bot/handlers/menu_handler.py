"""Menu handlers for the unified start menu and submenus."""

import logging
from telegram import Update
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
from src.utils.async_compat import maybe_await
from src.core.repositories import user_repository

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
    from src.bot.handlers.streak_handler import streaks_command
    from src.bot.handlers.habit_management_handler import (
        add_habit_command
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
        'menu_habit_done': menu_habit_done_simple_show_habits,  # Simple flow (default)
        'menu_habit_done_date': menu_habit_done_show_habits,    # Advanced flow with date selection
        'menu_streaks': streaks_command,
        'menu_help': help_command,
        'menu_habits_add': add_habit_command,
        'menu_habits_revert': habit_revert_command,
        # 'menu_habits_edit': edit_habit_command,  # Handled by ConversationHandler
        # 'menu_habits_remove': now in direct_command_map
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
            # For menu_habit_done and menu_habit_done_date, use the original update (has callback_query)
            # For other handlers, use synthetic update (has message)
            if data in ('menu_habit_done', 'menu_habit_done_date'):
                await handler(update, context)
            else:
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


async def menu_habit_done_show_habits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Habit Done for Date' from menu - show habit selection with date options."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"📋 User {telegram_id} clicked 'Habit Done for Date' from menu")

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Get active habits
    from src.bot.keyboards import build_habit_selection_keyboard
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))

    if not habits:
        await query.edit_message_text(
            msg('ERROR_NO_HABITS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Show habit selection keyboard
    keyboard = build_habit_selection_keyboard(habits, lang)
    await query.edit_message_text(
        msg('HELP_HABIT_SELECTION', lang),
        reply_markup=keyboard
    )
    logger.info(f"📤 Showed habit selection to {telegram_id}")
    return 0


async def menu_habit_done_simple_show_habits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Habit Done' from menu - show only pending habits for immediate logging."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"📋 User {telegram_id} clicked 'Habit Done' (simple flow) from menu")

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # First check if user has any habits configured
    all_habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    if not all_habits:
        await query.edit_message_text(
            msg('ERROR_NO_HABITS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Get habits not yet completed today
    from src.bot.keyboards import build_simple_habit_selection_keyboard
    habits = await maybe_await(habit_service.get_active_habits_pending_for_today(user.id))

    if not habits:
        # All habits completed today (we know user has habits from check above)
        await query.edit_message_text(
            msg('INFO_ALL_HABITS_COMPLETED', lang),
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return 0

    # Show simple habit selection keyboard (one-click completion)
    keyboard = build_simple_habit_selection_keyboard(habits, lang)
    await query.edit_message_text(
        msg('HELP_SIMPLE_HABIT_SELECTION', lang),
        reply_markup=keyboard
    )
    logger.info(f"📤 Showed simple habit selection to {telegram_id} ({len(habits)} pending habits)")
    return 0


async def simple_habit_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection from simple flow - immediately log for today.

    This handler processes simple_habit_{id} callbacks from the one-click
    completion flow. It immediately logs the habit as completed for today
    without showing date selection options.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected habit from simple flow: {callback_data}")

    # Extract habit_id from callback_data: "simple_habit_{id}"
    if callback_data.startswith("simple_habit_"):
        habit_id = callback_data.replace("simple_habit_", "")

        # Get user for multi-user support
        user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
        if not user:
            logger.error(f"❌ User {telegram_id} not found")
            await query.edit_message_text(
                msg('ERROR_USER_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return 0

        # Get habit by ID
        habits = await maybe_await(habit_service.get_all_active_habits(user.id))
        habit = next((h for h in habits if str(h.id) == habit_id), None)

        if not habit:
            logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
            await query.edit_message_text(
                msg('ERROR_HABIT_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return 0

        # Process habit completion for today (target_date=None defaults to today)
        try:
            from src.bot.formatters import format_habit_completion_message

            logger.info(f"⚙️ Processing simple habit completion: user {telegram_id}, habit '{habit.name}'")
            result = await maybe_await(
                habit_service.process_habit_completion(
                    user_telegram_id=telegram_id,
                    habit_name=habit.name,
                    target_date=None  # None defaults to today
                )
            )

            message = format_habit_completion_message(result, lang)
            logger.info(f"✅ Habit '{habit.name}' completed for today. Streak: {result.streak_count}")
            await query.edit_message_text(
                text=message,
                reply_markup=build_back_to_menu_keyboard(lang),
                parse_mode="HTML"
            )

        except ValueError as e:
            from datetime import date
            error_msg = str(e)
            logger.error(f"❌ Error processing habit completion: {error_msg}")

            # Format error message with proper date display
            if "already completed" in error_msg.lower():
                today = date.today()
                date_display = today.strftime("%d %b %Y")  # Format: 09 Dec 2025
                user_message = msg('ERROR_BACKDATE_DUPLICATE', lang, habit_name=habit.name, date=date_display)
            else:
                user_message = msg('ERROR_GENERAL', lang, error=error_msg)

            await query.edit_message_text(
                user_message,
                reply_markup=build_back_to_menu_keyboard(lang),
                parse_mode="HTML"
            )

    return 0


async def habit_selected_standalone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection from habit_done menu - show date options.

    Note: This handler is in group 1, so it only runs when conversation handlers
    (group 0) don't process the callback.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected habit from menu: {callback_data}")

    # Extract habit_id from callback_data
    if callback_data.startswith("habit_"):
        habit_id = callback_data.replace("habit_", "")

        # Get user for multi-user support
        user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
        if not user:
            logger.error(f"❌ User {telegram_id} not found")
            await query.edit_message_text(
                msg('ERROR_USER_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return 0

        # Get habit by ID
        habits = await maybe_await(habit_service.get_all_active_habits(user.id))
        habit = next((h for h in habits if str(h.id) == habit_id), None)

        if not habit:
            logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
            await query.edit_message_text(
                msg('ERROR_HABIT_NOT_FOUND', lang),
                reply_markup=build_back_to_menu_keyboard(lang)
            )
            return 0

        # Store habit info in context for date selection handlers
        context.user_data['menu_habit_id'] = habit_id
        context.user_data['menu_habit_name'] = habit.name

        # Show date options keyboard
        from src.bot.keyboards import build_completion_date_options_keyboard
        keyboard = build_completion_date_options_keyboard(habit_id, lang)
        await query.edit_message_text(
            msg('HELP_SELECT_COMPLETION_DATE', lang, habit_name=habit.name),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"📤 Showed date options to {telegram_id} for habit '{habit.name}'")

    return 0


async def menu_habit_today_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Today' button click from menu habit_done flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    habit_name = context.user_data.get('menu_habit_name')
    if not habit_name:
        logger.error(f"❌ Missing habit_name in context for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_HABIT_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Process habit completion for today
    try:
        from src.bot.formatters import format_habit_completion_message

        logger.info(f"⚙️ Processing habit completion for today: user {telegram_id}, habit '{habit_name}'")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=None  # None defaults to today
            )
        )

        message = format_habit_completion_message(result, lang)
        logger.info(f"✅ Habit '{habit_name}' completed for today. Streak: {result.streak_count}")
        await query.edit_message_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    except ValueError as e:
        from datetime import date
        error_msg = str(e)
        logger.error(f"❌ Error processing habit completion: {error_msg}")

        # Format error message with proper date display
        if "already completed" in error_msg.lower():
            today = date.today()
            date_display = today.strftime("%d %b %Y")  # Format: 09 Dec 2025
            user_message = msg('ERROR_BACKDATE_DUPLICATE', lang, habit_name=habit_name, date=date_display)
        else:
            user_message = msg('ERROR_GENERAL', lang, error=error_msg)

        await query.edit_message_text(
            user_message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    # Clean up context
    context.user_data.pop('menu_habit_id', None)
    context.user_data.pop('menu_habit_name', None)
    return 0


async def menu_habit_yesterday_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Yesterday' button click from menu habit_done flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    habit_name = context.user_data.get('menu_habit_name')
    if not habit_name:
        logger.error(f"❌ Missing habit_name in context for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_HABIT_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Calculate yesterday's date
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)

    # Process habit completion for yesterday
    try:
        from src.bot.formatters import format_habit_completion_message

        logger.info(f"⚙️ Processing habit completion for yesterday ({yesterday}): user {telegram_id}, habit '{habit_name}'")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=yesterday
            )
        )

        date_display = yesterday.strftime("%d %b %Y")  # Format: 09 Dec 2025
        message = format_habit_completion_message(result, lang)
        message = msg('SUCCESS_BACKDATE_COMPLETED', lang, habit_name=habit_name, date=date_display) + "\n\n" + message

        logger.info(f"✅ Habit '{habit_name}' completed for yesterday. Streak: {result.streak_count}")
        await query.edit_message_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"❌ Error processing habit completion: {error_msg}")

        if "already completed" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_DUPLICATE', lang, habit_name=habit_name, date=yesterday.strftime("%d %b %Y"))
        elif "before habit was created" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_BEFORE_CREATED', lang, date=error_msg.split()[-1])
        else:
            user_message = msg('ERROR_GENERAL', lang, error=error_msg)

        await query.edit_message_text(
            user_message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    # Clean up context
    context.user_data.pop('menu_habit_id', None)
    context.user_data.pop('menu_habit_name', None)
    return 0


async def menu_select_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Select Date' button click - show date picker."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"📅 User {telegram_id} clicked 'Select Date': {callback_data}")

    # Extract habit_id from callback_data: "backdate_habit_{habit_id}"
    habit_id = callback_data.replace("backdate_habit_", "")

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(
            msg('ERROR_USER_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Get habit by ID
    habits = await maybe_await(habit_service.get_all_active_habits(user.id))
    habit = next((h for h in habits if str(h.id) == habit_id), None)

    if not habit:
        await query.edit_message_text(
            msg('ERROR_HABIT_NOT_FOUND', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Store habit info in context
    context.user_data['menu_habit_id'] = habit_id
    context.user_data['menu_habit_name'] = habit.name

    # Get completed dates for this habit (last 7 days)
    from datetime import date, timedelta
    today = date.today()
    start_date = today - timedelta(days=7)
    completed_dates = await maybe_await(
        habit_service.get_habit_completions_for_daterange(
            user.id, habit.id, start_date, today
        )
    )

    # Build and show date picker
    from src.bot.keyboards import build_date_picker_keyboard
    keyboard = build_date_picker_keyboard(habit_id, completed_dates, lang)
    await query.edit_message_text(
        msg('HELP_BACKDATE_SELECT_DATE', lang, habit_name=habit.name),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent date picker to {telegram_id}")
    return 0


async def menu_backdate_date_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date selection from picker - show confirmation."""
    query = update.callback_query
    # Don't answer the query yet - we'll do it conditionally below

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"📅 User {telegram_id} selected date: {callback_data}")

    # Check if date is already completed
    if callback_data.startswith("backdate_date_completed_"):
        parts = callback_data.split("_")
        if len(parts) >= 5:
            from datetime import date
            date_iso = parts[4]
            try:
                completed_date = date.fromisoformat(date_iso)
                date_str = completed_date.strftime("%d %b %Y")  # Format: 09 Dec 2025
            except ValueError:
                date_str = date_iso

            habit_name = context.user_data.get('menu_habit_name', 'Unknown')
            # Create plain text message for alert (no HTML formatting)
            alert_text = f"❌ You already logged {habit_name} on {date_str}"
            logger.info(f"⚠️ Showing duplicate alert to {telegram_id}: {alert_text}")
            await query.answer(
                text=alert_text,
                show_alert=True
            )
            logger.info(f"✅ Alert shown to {telegram_id}")
        return 0

    # Answer the query for valid date selection
    await query.answer()

    # Parse callback data: "backdate_date_{habit_id}_{date_iso}"
    parts = callback_data.split("_")
    if len(parts) < 4:
        logger.error(f"❌ Invalid callback format: {callback_data}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid date"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    habit_id = parts[2]
    date_str = parts[3]

    try:
        from datetime import date
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.error(f"❌ Invalid date format: {date_str}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Invalid date"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Store in context
    context.user_data['menu_backdate_date'] = target_date
    habit_name = context.user_data.get('menu_habit_name', 'Unknown')

    # Format date for display
    date_display = target_date.strftime("%d %b %Y")  # Format: 09 Dec 2025

    # Show confirmation
    from src.bot.keyboards import build_backdate_confirmation_keyboard
    keyboard = build_backdate_confirmation_keyboard(habit_id, target_date, lang)
    await query.edit_message_text(
        msg('HELP_BACKDATE_CONFIRM', lang, habit_name=habit_name, date=date_display),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent confirmation prompt to {telegram_id}")
    return 0


async def menu_backdate_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute the backdated habit completion."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"✅ User {telegram_id} confirmed backdate")

    # Get stored data from context
    habit_name = context.user_data.get('menu_habit_name')
    target_date = context.user_data.get('menu_backdate_date')

    if not habit_name or not target_date:
        logger.error(f"❌ Missing context data for user {telegram_id}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Session data lost"),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        return 0

    # Process habit completion with target_date
    try:
        from src.bot.formatters import format_habit_completion_message

        logger.info(f"⚙️ Processing backdated completion: user {telegram_id}, habit '{habit_name}', date {target_date}")
        result = await maybe_await(
            habit_service.process_habit_completion(
                user_telegram_id=telegram_id,
                habit_name=habit_name,
                target_date=target_date
            )
        )

        date_display = target_date.strftime("%d %b %Y")  # Format: 09 Dec 2025
        message = format_habit_completion_message(result, lang)
        message = msg('SUCCESS_BACKDATE_COMPLETED', lang, habit_name=habit_name, date=date_display) + "\n\n" + message

        logger.info(f"✅ Habit '{habit_name}' backdated to {target_date}. Streak: {result.streak_count}")
        await query.edit_message_text(
            text=message,
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"❌ Error processing backdate: {error_msg}")

        if "already completed" in error_msg.lower():
            user_message = msg('ERROR_BACKDATE_DUPLICATE', lang, habit_name=habit_name, date=target_date.strftime("%d %b %Y"))
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

    # Clean up context
    context.user_data.pop('menu_habit_id', None)
    context.user_data.pop('menu_habit_name', None)
    context.user_data.pop('menu_backdate_date', None)
    return 0


async def menu_backdate_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button from backdate confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"❌ User {telegram_id} cancelled backdate")

    # Clean up context
    context.user_data.pop('menu_habit_id', None)
    context.user_data.pop('menu_habit_name', None)
    context.user_data.pop('menu_backdate_date', None)

    # Return to menu
    await query.edit_message_text(
        msg('INFO_CANCELLED', lang),
        reply_markup=build_back_to_menu_keyboard(lang)
    )
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
        CallbackQueryHandler(bridge_command_callback, pattern="^(menu_habit_done|menu_habit_done_date|menu_habits_remove|menu_streaks|menu_help|menu_habits_add|menu_habits_revert|menu_rewards_list|menu_rewards_my|menu_rewards_claim)$"),
        CallbackQueryHandler(open_start_menu_callback, pattern="^menu_back_start$"),
        CallbackQueryHandler(open_habits_menu_callback, pattern="^menu_back_habits$"),
        CallbackQueryHandler(generic_back_callback, pattern="^menu_back$"),
        # Settings standalone handlers (work outside conversation)
        CallbackQueryHandler(settings_language_callback, pattern="^settings_language$"),
        CallbackQueryHandler(change_language_standalone_callback, pattern="^lang_(en|kk|ru)$"),
        CallbackQueryHandler(settings_back_callback, pattern="^settings_back$"),
        # Habit display handler (view only, no action)
        CallbackQueryHandler(view_habit_display_callback, pattern="^view_habit_"),
        # Simple habit flow handler (one-click completion for today)
        # This must come BEFORE habit_selected_standalone_callback
        CallbackQueryHandler(simple_habit_selected_callback, pattern="^simple_habit_"),
        # Menu habit_done flow handlers (Today/Yesterday/Select Date buttons)
        CallbackQueryHandler(menu_habit_today_callback, pattern="^habit_.*_today$"),
        CallbackQueryHandler(menu_habit_yesterday_callback, pattern="^habit_.*_yesterday$"),
        CallbackQueryHandler(menu_select_date_callback, pattern="^backdate_habit_"),
        CallbackQueryHandler(menu_backdate_date_selected_callback, pattern="^backdate_date_"),
        CallbackQueryHandler(menu_backdate_confirm_callback, pattern="^backdate_confirm_"),
        CallbackQueryHandler(menu_backdate_cancel_callback, pattern="^backdate_cancel$"),
        # Habit selection standalone handler (work outside conversation)
        # This must be LAST to avoid catching other habit_* patterns
        CallbackQueryHandler(habit_selected_standalone_callback, pattern="^habit_")
    ]
