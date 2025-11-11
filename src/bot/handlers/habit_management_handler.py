"""Handlers for habit management commands: /add_habit, /edit_habit, /remove_habit."""

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

from src.core.repositories import user_repository, habit_repository
from src.services.habit_service import habit_service
from asgiref.sync import sync_to_async
from src.bot.keyboards import (
    build_weight_selection_keyboard,
    build_category_selection_keyboard,
    build_habits_for_edit_keyboard,
    build_habit_confirmation_keyboard,
    build_remove_confirmation_keyboard,
    build_no_habits_to_edit_keyboard,
    build_post_create_habit_keyboard,
    build_cancel_only_keyboard
)
from src.bot.messages import msg
from src.bot.language import get_message_language, get_message_language_async
from src.models.habit import Habit
from src.config import HABIT_NAME_MAX_LENGTH
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states for /add_habit
AWAITING_HABIT_NAME = 1
AWAITING_HABIT_WEIGHT = 2
AWAITING_HABIT_CATEGORY = 3
AWAITING_HABIT_CONFIRMATION = 4

# Conversation states for /edit_habit
AWAITING_HABIT_SELECTION = 10
AWAITING_EDIT_NAME = 11
AWAITING_EDIT_WEIGHT = 12
AWAITING_EDIT_CATEGORY = 13
AWAITING_EDIT_CONFIRMATION = 14

# Conversation states for /remove_habit
AWAITING_REMOVE_SELECTION = 20
AWAITING_REMOVE_CONFIRMATION = 21


# ============================================================================
# /add_habit CONVERSATION HANDLER
# ============================================================================

async def add_habit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /add_habit and /new_habit commands."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /add_habit command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Prompt for habit name with Cancel button
    keyboard = build_cancel_only_keyboard(language=lang)
    await update.message.reply_text(
        msg('HELP_ADD_HABIT_NAME_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit name prompt with Cancel button to {telegram_id}")
    logger.error(f"🔵 CONVERSATION STATE: Returning {AWAITING_HABIT_NAME} for user {telegram_id}")

    return AWAITING_HABIT_NAME


async def menu_add_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for adding habit via menu button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"📨 Received menu_habits_add callback from user {telegram_id}")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
        return ConversationHandler.END

    # Prompt for habit name with Cancel button
    keyboard = build_cancel_only_keyboard(language=lang)
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_NAME_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit name prompt with Cancel button to {telegram_id} (via menu)")
    logger.error(f"🔵 CONVERSATION STATE: Returning {AWAITING_HABIT_NAME} for user {telegram_id} (menu)")

    return AWAITING_HABIT_NAME


async def post_create_add_another_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for adding another habit after creating one (via callback)."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"📨 Received post_create_add_another callback from user {telegram_id}")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Prompt for habit name with Cancel button (edit the current message)
    keyboard = build_cancel_only_keyboard(language=lang)
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_NAME_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit name prompt with Cancel button to {telegram_id} (via callback)")

    return AWAITING_HABIT_NAME


async def habit_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit name input."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    habit_name = update.message.text.strip()

    logger.info(f"📝 User {telegram_id} entered habit name: '{habit_name}'")

    # Validate name
    if not habit_name:
        logger.warning(f"⚠️ User {telegram_id} entered empty habit name")
        await update.message.reply_text(msg('ERROR_HABIT_NAME_EMPTY', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NAME_EMPTY to {telegram_id}")
        return AWAITING_HABIT_NAME

    if len(habit_name) > HABIT_NAME_MAX_LENGTH:
        logger.warning(f"⚠️ User {telegram_id} entered habit name too long: {len(habit_name)} chars")
        await update.message.reply_text(msg('ERROR_HABIT_NAME_TOO_LONG', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NAME_TOO_LONG to {telegram_id}")
        return AWAITING_HABIT_NAME

    # Store in context
    context.user_data['habit_name'] = habit_name
    logger.info(f"✅ Stored habit name in context for user {telegram_id}")

    # Show weight selection keyboard
    keyboard = build_weight_selection_keyboard(language=lang)
    await update.message.reply_text(
        msg('HELP_ADD_HABIT_WEIGHT_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent weight selection keyboard to {telegram_id}")

    return AWAITING_HABIT_WEIGHT


async def habit_weight_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle weight selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected weight callback: {callback_data}")

    # Extract weight from callback_data (format: weight_10, weight_20, etc.)
    try:
        weight = int(callback_data.replace("weight_", ""))
        logger.info(f"🎯 User {telegram_id} selected weight: {weight}")
    except ValueError:
        logger.error(f"❌ Invalid weight callback data: {callback_data}")
        await query.edit_message_text(msg('ERROR_WEIGHT_INVALID', lang))
        return ConversationHandler.END

    # Store in context
    context.user_data['habit_weight'] = weight
    logger.info(f"✅ Stored habit weight in context for user {telegram_id}")

    # Show category selection keyboard
    keyboard = build_category_selection_keyboard(language=lang)
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_CATEGORY_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent category selection keyboard to {telegram_id}")

    return AWAITING_HABIT_CATEGORY


async def habit_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected category callback: {callback_data}")

    # Extract category from callback_data (format: category_health, category_productivity, etc.)
    category = callback_data.replace("category_", "")
    logger.info(f"🎯 User {telegram_id} selected category: {category}")

    # Store in context
    context.user_data['habit_category'] = category
    logger.info(f"✅ Stored habit category in context for user {telegram_id}")

    # Show confirmation with summary
    habit_name = context.user_data.get('habit_name')
    habit_weight = context.user_data.get('habit_weight')

    confirmation_message = msg(
        'HELP_ADD_HABIT_CONFIRM',
        lang,
        name=habit_name,
        weight=habit_weight,
        category=category
    )

    keyboard = build_remove_confirmation_keyboard(language=lang)
    await query.edit_message_text(
        confirmation_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent confirmation message to {telegram_id}")

    return AWAITING_HABIT_CONFIRMATION


async def habit_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation (Yes/No) for creating habit."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} confirmed habit: {callback_data}")

    if callback_data == "confirm_no":
        logger.info(f"❌ User {telegram_id} cancelled habit creation")
        await query.edit_message_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
        logger.info(f"📤 Sent cancellation message to {telegram_id}")

        # Show Habits menu
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")

        # Clear context
        context.user_data.clear()
        return ConversationHandler.END

    # User confirmed - create the habit
    habit_name = context.user_data.get('habit_name')
    habit_weight = context.user_data.get('habit_weight')
    habit_category = context.user_data.get('habit_category')

    try:
        logger.info(f"⚙️ Creating habit for user {telegram_id}: name='{habit_name}', weight={habit_weight}, category={habit_category}")

        new_habit = Habit(
            name=habit_name,
            weight=habit_weight,
            category=habit_category,
            active=True
        )

        created_habit = await maybe_await(habit_repository.create(new_habit))
        logger.info(f"✅ Created habit '{created_habit.name}' (ID: {created_habit.id}) for user {telegram_id}")

        # Show success message
        success_message = msg('SUCCESS_HABIT_CREATED', lang, name=created_habit.name)
        await query.edit_message_text(success_message, parse_mode="HTML")
        logger.info(f"📤 Sent success message to {telegram_id}")

        # Fetch all active habits including the newly created one
        all_habits = await maybe_await(habit_repository.get_all_active())
        logger.info(f"🔍 Fetched {len(all_habits)} active habits for post-creation menu")

        # Show the post-creation menu with habits list
        keyboard = build_post_create_habit_keyboard(all_habits, lang)
        next_message = msg('HELP_HABIT_CREATED_NEXT', lang)

        # Send as a new message to show the habits list
        await query.message.reply_text(
            next_message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent post-creation menu with {len(all_habits)} habits to {telegram_id}")

    except Exception as e:
        logger.error(f"❌ Error creating habit for user {telegram_id}: {str(e)}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def debug_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Debug handler to catch all callbacks."""
    query = update.callback_query
    telegram_id = str(update.effective_user.id)
    logger.error(f"🟡 DEBUG: Caught callback in AWAITING_HABIT_NAME - user: {telegram_id}, data: {query.data}")
    await query.answer("DEBUG: Callback received but not handled")
    return AWAITING_HABIT_NAME


async def cancel_habit_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button click during habit creation/editing."""
    query = update.callback_query

    telegram_id = str(update.effective_user.id)
    logger.error(f"🔴 CANCEL BUTTON CLICKED by user {telegram_id} - callback_data: {query.data}")

    await query.answer()

    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"❌ User {telegram_id} cancelled habit flow via Cancel button")

    # Show cancellation message
    await query.edit_message_text(
        msg('INFO_HABIT_CANCEL', lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Show Habits menu
    from src.bot.keyboards import build_habits_menu_keyboard
    await query.message.reply_text(
        msg('HABITS_MENU_TITLE', lang),
        reply_markup=build_habits_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent Habits menu to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_add_habit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel /add_habit conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel from user {telegram_id} (@{username}) in add_habit flow")
    lang = await get_message_language_async(telegram_id, update)

    await update.message.reply_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


# ============================================================================
# /edit_habit CONVERSATION HANDLER
# ============================================================================

async def edit_habit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /edit_habit command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /edit_habit command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Get all active habits
    habits = await maybe_await(habit_repository.get_all_active())
    logger.info(f"🔍 Found {len(habits)} active habits for user {telegram_id}")

    if not habits:
        logger.warning(f"⚠️ No active habits found for user {telegram_id}")
        await update.message.reply_text(msg('ERROR_NO_HABITS_TO_EDIT', lang), parse_mode="HTML")
        logger.info(f"📤 Sent ERROR_NO_HABITS_TO_EDIT to {telegram_id}")
        return ConversationHandler.END

    # Show habit selection keyboard
    keyboard = build_habits_for_edit_keyboard(habits, operation="edit", language=lang)
    await update.message.reply_text(
        msg('HELP_EDIT_HABIT_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return AWAITING_HABIT_SELECTION


async def edit_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for edit habit via menu callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"📨 Received edit_habit callback from user {telegram_id}")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Get all active habits
    habits = await maybe_await(habit_repository.get_all_active())
    logger.info(f"🔍 Found {len(habits)} active habits for user {telegram_id}")

    if not habits:
        logger.warning(f"⚠️ No active habits found for user {telegram_id}")
        keyboard = build_no_habits_to_edit_keyboard(lang)
        await query.edit_message_text(
            msg('ERROR_NO_HABITS_TO_EDIT_PROMPT', lang),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent ERROR_NO_HABITS_TO_EDIT_PROMPT with Add Habit option to {telegram_id}")
        return AWAITING_HABIT_SELECTION

    # Show habit selection keyboard
    keyboard = build_habits_for_edit_keyboard(habits, operation="edit", language=lang)
    await query.edit_message_text(
        msg('HELP_EDIT_HABIT_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return AWAITING_HABIT_SELECTION


async def habit_edit_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection for editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected habit for editing: {callback_data}")

    # Extract habit_id from callback_data (format: edit_habit_<habit_id>)
    habit_id = callback_data.replace("edit_habit_", "")

    # Load habit from database
    habit = await maybe_await(habit_repository.get_by_id(habit_id))
    if not habit:
        logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
        await query.edit_message_text(msg('ERROR_HABIT_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NOT_FOUND to {telegram_id}")
        return ConversationHandler.END

    # Store habit info in context
    context.user_data['editing_habit_id'] = habit.id
    context.user_data['old_habit_name'] = habit.name
    context.user_data['old_habit_weight'] = habit.weight
    context.user_data['old_habit_category'] = habit.category or "None"
    logger.info(f"✅ Stored habit info in context for user {telegram_id}")

    # Prompt for new name with Cancel button
    prompt_message = msg('HELP_EDIT_HABIT_NAME_PROMPT', lang, current_name=habit.name)
    keyboard = build_cancel_only_keyboard(language=lang)
    await query.edit_message_text(
        prompt_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent edit name prompt with Cancel button to {telegram_id}")

    return AWAITING_EDIT_NAME


async def habit_edit_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new habit name input."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    new_name = update.message.text.strip()

    logger.info(f"📝 User {telegram_id} entered new habit name: '{new_name}'")

    # Validate name
    if not new_name:
        logger.warning(f"⚠️ User {telegram_id} entered empty habit name")
        await update.message.reply_text(msg('ERROR_HABIT_NAME_EMPTY', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NAME_EMPTY to {telegram_id}")
        return AWAITING_EDIT_NAME

    if len(new_name) > HABIT_NAME_MAX_LENGTH:
        logger.warning(f"⚠️ User {telegram_id} entered habit name too long: {len(new_name)} chars")
        await update.message.reply_text(msg('ERROR_HABIT_NAME_TOO_LONG', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NAME_TOO_LONG to {telegram_id}")
        return AWAITING_EDIT_NAME

    # Store in context
    context.user_data['new_habit_name'] = new_name
    logger.info(f"✅ Stored new habit name in context for user {telegram_id}")

    # Show weight selection keyboard
    current_weight = context.user_data.get('old_habit_weight')
    keyboard = build_weight_selection_keyboard(current_weight=current_weight, language=lang)

    prompt_message = msg('HELP_EDIT_HABIT_WEIGHT_PROMPT', lang, current_weight=current_weight)
    await update.message.reply_text(
        prompt_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent weight selection keyboard to {telegram_id}")

    return AWAITING_EDIT_WEIGHT


async def habit_edit_weight_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle weight selection for editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected new weight: {callback_data}")

    # Extract weight
    try:
        new_weight = int(callback_data.replace("weight_", ""))
        logger.info(f"🎯 User {telegram_id} selected new weight: {new_weight}")
    except ValueError:
        logger.error(f"❌ Invalid weight callback data: {callback_data}")
        await query.edit_message_text(msg('ERROR_WEIGHT_INVALID', lang))
        return ConversationHandler.END

    # Store in context
    context.user_data['new_habit_weight'] = new_weight
    logger.info(f"✅ Stored new habit weight in context for user {telegram_id}")

    # Show category selection keyboard
    current_category = context.user_data.get('old_habit_category')
    keyboard = build_category_selection_keyboard(current_category=current_category, language=lang)

    prompt_message = msg('HELP_EDIT_HABIT_CATEGORY_PROMPT', lang, current_category=current_category)
    await query.edit_message_text(
        prompt_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent category selection keyboard to {telegram_id}")

    return AWAITING_EDIT_CATEGORY


async def habit_edit_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection for editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected new category: {callback_data}")

    # Extract category
    new_category = callback_data.replace("category_", "")
    logger.info(f"🎯 User {telegram_id} selected new category: {new_category}")

    # Store in context
    context.user_data['new_habit_category'] = new_category
    logger.info(f"✅ Stored new habit category in context for user {telegram_id}")

    # Show confirmation with before/after comparison
    old_name = context.user_data.get('old_habit_name')
    old_weight = context.user_data.get('old_habit_weight')
    old_category = context.user_data.get('old_habit_category')
    new_name = context.user_data.get('new_habit_name')
    new_weight = context.user_data.get('new_habit_weight')

    confirmation_message = msg(
        'HELP_EDIT_HABIT_CONFIRM',
        lang,
        old_name=old_name,
        new_name=new_name,
        old_weight=old_weight,
        new_weight=new_weight,
        old_category=old_category,
        new_category=new_category
    )

    keyboard = build_habit_confirmation_keyboard(language=lang)
    await query.edit_message_text(
        confirmation_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent edit confirmation message to {telegram_id}")

    return AWAITING_EDIT_CONFIRMATION


async def habit_edit_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for editing habit."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} confirmed habit edit: {callback_data}")

    if callback_data == "confirm_no":
        logger.info(f"❌ User {telegram_id} cancelled habit editing")
        await query.edit_message_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
        logger.info(f"📤 Sent cancellation message to {telegram_id}")

        # Show Habits menu
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")

        # Clear context
        context.user_data.clear()
        return ConversationHandler.END

    # User confirmed - update the habit
    habit_id = context.user_data.get('editing_habit_id')
    new_name = context.user_data.get('new_habit_name')
    new_weight = context.user_data.get('new_habit_weight')
    new_category = context.user_data.get('new_habit_category')

    try:
        logger.info(f"⚙️ Updating habit {habit_id} for user {telegram_id}")

        updates = {
            "name": new_name,
            "weight": new_weight,
            "category": new_category
        }

        updated_habit = await maybe_await(
            habit_repository.update(habit_id, updates)
        )
        logger.info(f"✅ Updated habit '{updated_habit.name}' (ID: {updated_habit.id}) for user {telegram_id}")

        success_message = msg('SUCCESS_HABIT_UPDATED', lang, name=updated_habit.name)
        await query.edit_message_text(success_message, parse_mode="HTML")
        logger.info(f"📤 Sent success message to {telegram_id}")

    except Exception as e:
        logger.error(f"❌ Error updating habit for user {telegram_id}: {str(e)}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def edit_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back from habit selection to habits menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🔙 User {telegram_id} pressed Back from edit habit selection")

    # Return to habits menu
    from src.bot.keyboards import build_habits_menu_keyboard
    await query.edit_message_text(
        msg('HABITS_MENU_TITLE', lang),
        reply_markup=build_habits_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def edit_to_add_habit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Redirect from edit habit (no habits) to add habit flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"🔄 User {telegram_id} clicked Add Habit from edit habit (no habits) screen")
    lang = await get_message_language_async(telegram_id, update)

    # Clear any edit context
    context.user_data.clear()

    # Start add habit flow by sending the first prompt
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_NAME_PROMPT', lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit name prompt to {telegram_id} (from edit redirect)")

    return AWAITING_HABIT_NAME


async def cancel_edit_habit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel /edit_habit conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel from user {telegram_id} (@{username}) in edit_habit flow")
    lang = await get_message_language_async(telegram_id, update)

    await update.message.reply_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


# ============================================================================
# /remove_habit CONVERSATION HANDLER
# ============================================================================

async def remove_habit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /remove_habit command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /remove_habit command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Get all active habits
    habits = await maybe_await(habit_repository.get_all_active())
    logger.info(f"🔍 Found {len(habits)} active habits for user {telegram_id}")

    if not habits:
        logger.warning(f"⚠️ No active habits found for user {telegram_id}")
        await update.message.reply_text(msg('ERROR_NO_HABITS_TO_REMOVE', lang), parse_mode="HTML")
        logger.info(f"📤 Sent ERROR_NO_HABITS_TO_REMOVE to {telegram_id}")
        return ConversationHandler.END

    # Show habit selection keyboard
    keyboard = build_habits_for_edit_keyboard(habits, operation="remove", language=lang)
    await update.message.reply_text(
        msg('HELP_REMOVE_HABIT_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return AWAITING_REMOVE_SELECTION


async def remove_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for remove habit via menu callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"📨 Received remove_habit callback from user {telegram_id}")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Get all active habits
    habits = await maybe_await(habit_repository.get_all_active())
    logger.info(f"🔍 Found {len(habits)} active habits for user {telegram_id}")

    if not habits:
        logger.warning(f"⚠️ No active habits found for user {telegram_id}")
        await query.edit_message_text(msg('ERROR_NO_HABITS_TO_REMOVE', lang), parse_mode="HTML")
        logger.info(f"📤 Sent ERROR_NO_HABITS_TO_REMOVE to {telegram_id}")
        return ConversationHandler.END

    # Show habit selection keyboard
    keyboard = build_habits_for_edit_keyboard(habits, operation="remove", language=lang)
    await query.edit_message_text(
        msg('HELP_REMOVE_HABIT_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent habit selection keyboard to {telegram_id}")

    return AWAITING_REMOVE_SELECTION


async def habit_remove_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle habit selection for removal."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected habit for removal: {callback_data}")

    # Extract habit_id from callback_data (format: remove_habit_<habit_id>)
    habit_id = callback_data.replace("remove_habit_", "")

    # Load habit from database
    habit = await maybe_await(habit_repository.get_by_id(habit_id))
    if not habit:
        logger.error(f"❌ Habit {habit_id} not found for user {telegram_id}")
        await query.edit_message_text(msg('ERROR_HABIT_NOT_FOUND', lang))
        logger.info(f"📤 Sent ERROR_HABIT_NOT_FOUND to {telegram_id}")
        return ConversationHandler.END

    # Store habit info in context
    context.user_data['removing_habit_id'] = habit.id
    context.user_data['removing_habit_name'] = habit.name
    logger.info(f"✅ Stored habit info in context for user {telegram_id}")

    # Show confirmation warning
    confirmation_message = msg('HELP_REMOVE_HABIT_CONFIRM', lang, name=habit.name)
    keyboard = build_habit_confirmation_keyboard(language=lang)

    await query.edit_message_text(
        confirmation_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent removal confirmation message to {telegram_id}")

    return AWAITING_REMOVE_CONFIRMATION


async def habit_remove_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for removing habit."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} confirmed habit removal: {callback_data}")

    if callback_data == "confirm_no":
        logger.info(f"❌ User {telegram_id} cancelled habit removal")
        await query.edit_message_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
        logger.info(f"📤 Sent cancellation message to {telegram_id}")

        # Show Habits menu
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")

        # Clear context
        context.user_data.clear()
        return ConversationHandler.END

    # User confirmed - soft delete the habit
    habit_id = context.user_data.get('removing_habit_id')
    habit_name = context.user_data.get('removing_habit_name')

    try:
        logger.info(f"⚙️ Soft deleting habit {habit_id} for user {telegram_id}")

        removed_habit = await maybe_await(habit_repository.soft_delete(habit_id))
        logger.info(f"✅ Soft deleted habit '{removed_habit.name}' (ID: {removed_habit.id}) for user {telegram_id}")

        success_message = msg('SUCCESS_HABIT_REMOVED', lang, name=habit_name)
        await query.edit_message_text(success_message, parse_mode="HTML")
        logger.info(f"📤 Sent success message to {telegram_id}")

        # Show Habits menu after successful removal
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")

    except Exception as e:
        logger.error(f"❌ Error removing habit for user {telegram_id}: {str(e)}")
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent error message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_remove_habit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel /remove_habit conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel from user {telegram_id} (@{username}) in remove_habit flow")
    lang = await get_message_language_async(telegram_id, update)

    await update.message.reply_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def remove_back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back from confirmation to the habit selection list or close if unavailable."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    # Re-fetch active habits
    habits = await maybe_await(habit_repository.get_all_active())
    if not habits:
        # Nothing to show, delete the message
        try:
            await query.delete_message()
        except Exception:
            pass
        return ConversationHandler.END

    keyboard = build_habits_for_edit_keyboard(habits, operation="remove", language=lang)
    await query.edit_message_text(
        msg('HELP_REMOVE_HABIT_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return AWAITING_REMOVE_SELECTION


async def remove_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back from habit selection to habits menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"🔙 User {telegram_id} pressed Back from remove habit selection")

    # Return to habits menu
    from src.bot.keyboards import build_habits_menu_keyboard
    await query.edit_message_text(
        msg('HABITS_MENU_TITLE', lang),
        reply_markup=build_habits_menu_keyboard(lang),
        parse_mode="HTML"
    )

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


# ============================================================================
# CONVERSATION HANDLER DEFINITIONS
# ============================================================================

# /add_habit conversation handler
add_habit_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("add_habit", add_habit_command),
        CommandHandler("new_habit", add_habit_command),
        CallbackQueryHandler(edit_to_add_habit, pattern="^edit_add_habit$"),
        CallbackQueryHandler(post_create_add_another_callback, pattern="^post_create_add_another$"),
        CallbackQueryHandler(menu_add_habit_callback, pattern="^menu_habits_add$")
    ],
    states={
        AWAITING_HABIT_NAME: [
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$"),
            CallbackQueryHandler(debug_callback_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_name_received)
        ],
        AWAITING_HABIT_WEIGHT: [
            CallbackQueryHandler(habit_weight_selected, pattern="^weight_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_HABIT_CATEGORY: [
            CallbackQueryHandler(habit_category_selected, pattern="^category_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_HABIT_CONFIRMATION: [
            CallbackQueryHandler(habit_confirmed, pattern="^confirm_(yes|no)$"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_add_habit)],
    per_message=False
)

# /edit_habit conversation handler
edit_habit_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("edit_habit", edit_habit_command),
        CallbackQueryHandler(edit_habit_callback, pattern="^menu_habits_edit$")
    ],
    states={
        AWAITING_HABIT_SELECTION: [
            CallbackQueryHandler(habit_edit_selected, pattern="^edit_habit_"),
            CallbackQueryHandler(edit_back_to_menu, pattern="^edit_back$")
        ],
        AWAITING_EDIT_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_edit_name_received),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_WEIGHT: [
            CallbackQueryHandler(habit_edit_weight_selected, pattern="^weight_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_CATEGORY: [
            CallbackQueryHandler(habit_edit_category_selected, pattern="^category_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_CONFIRMATION: [
            CallbackQueryHandler(habit_edit_confirmed, pattern="^confirm_(yes|no)$"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_edit_habit)],
    per_message=False
)

# /remove_habit conversation handler
remove_habit_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("remove_habit", remove_habit_command),
        CallbackQueryHandler(remove_habit_callback, pattern="^menu_habits_remove$")
    ],
    states={
        AWAITING_REMOVE_SELECTION: [
            CallbackQueryHandler(habit_remove_selected, pattern="^remove_habit_"),
            CallbackQueryHandler(remove_back_to_menu, pattern="^remove_back$"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_REMOVE_CONFIRMATION: [
            CallbackQueryHandler(habit_remove_confirmed, pattern="^confirm_(yes|no)$"),
            CallbackQueryHandler(remove_back_to_list, pattern="^remove_back_to_list$"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_remove_habit)],
    per_message=False
)
