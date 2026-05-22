Total output lines: 2016

"""Handlers for habit management commands: /add_habit, /edit_habit, /remove_habit."""

import asyncio
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
from src.bot.keyboards import (
    build_weight_selection_keyboard,
    build_grace_days_keyboard,
    build_exempt_days_keyboard,
    build_habits_for_edit_keyboard,
    build_habit_confirmation_keyboard,
    build_remove_confirmation_keyboard,
    build_no_habits_to_edit_keyboard,
    build_post_create_habit_keyboard,
    build_cancel_only_keyboard,
    build_skip_cancel_keyboard
)
from src.bot.messages import msg
from src.bot.language import get_message_language_async
from src.config import HABIT_NAME_MAX_LENGTH
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states for /add_habit
AWAITING_HABIT_NAME = 1
AWAITING_HABIT_WEIGHT = 2
AWAITING_HABIT_CATEGORY = 3
AWAITING_GRACE_DAYS = 4
AWAITING_EXEMPT_DAYS = 5
AWAITING_HABIT_CONFIRMATION = 6

# Conversation states for /edit_habit
AWAITING_HABIT_SELECTION = 10
AWAITING_EDIT_NAME = 11
AWAITING_EDIT_WEIGHT = 12
AWAITING_EDIT_CATEGORY = 13
AWAITING_EDIT_GRACE_DAYS = 14
AWAITING_EDIT_EXEMPT_DAYS = 15
AWAITING_EDIT_CONFIRMATION = 16

# Conversation states for /remove_habit
AWAITING_REMOVE_SELECTION = 20
AWAITING_REMOVE_CONFIRMATION = 21


def _schedule_message_delete(message_obj, telegram_id: str, description: str) -> None:
    """Delete a short-lived bot message after the user has time to read it."""
    async def delete_message():
        try:
            await asyncio.sleep(2.5)
            await message_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            await message_obj.delete()
            logger.info("🗑️ Deleted %s message for user %s", description, telegram_id)
        except Exception as e:
            logger.warning("⚠️ Could not delete %s message for user %s: %s", description, telegram_id, e)

    asyncio.create_task(delete_message())


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
    prompt_msg = await update.message.reply_text(
        msg('HELP_ADD_HABIT_NAME_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    # Store the active conversation message for in-place editing later
    context.user_data['active_msg_chat_id'] = prompt_msg.chat_id
    context.user_data['active_msg_id'] = prompt_msg.message_id
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
    # Store the active conversation message for in-place editing later
    context.user_data['active_msg_chat_id'] = query.message.chat_id
    context.user_data['active_msg_id'] = query.message.message_id
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
    # Store the active conversation message for in-place editing later
    context.user_data['active_msg_chat_id'] = query.message.chat_id
    context.user_data['active_msg_id'] = query.message.message_id
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

    # Check if duplicate
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if user:
        existing_habit = await maybe_await(habit_repository.get_by_name(user.id, habit_name))
        if existing_habit and getattr(existing_habit, 'active', True):
            logger.warning(f"⚠️ User {telegram_id} entered duplicate habit name: {habit_name}")
            keyboard = build_cancel_only_keyboard(language=lang)
            error_msg_obj = await update.message.reply_text(
                msg('ERROR_HABIT_NAME_EXISTS', lang, name=habit_name),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            # Update active message ID so next prompt edits this error message instead of the old one
            context.user_data['active_msg_chat_id'] = error_msg_obj.chat_id
            context.user_data['active_msg_id'] = error_msg_obj.message_id
            return AWAITING_HABIT_NAME

    # Store in context
    context.user_data['habit_name'] = habit_name
    logger.info(f"✅ Stored habit name in context for user {telegram_id}")

    # Show weight selection keyboard
    keyboard = build_weight_selection_keyboard(language=lang)
    
    # Try to edit the active conversation message in-place
    active_chat_id = context.user_data.get('active_msg_chat_id')
    active_msg_id = context.user_data.get('active_msg_id')
    
    if active_chat_id and active_msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=active_chat_id,
                message_id=active_msg_id,
                text=msg('HELP_ADD_HABIT_WEIGHT_PROMPT', lang),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"📤 Edited active message to weight selection keyboard for {telegram_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not edit active message for {telegram_id}, falling back to reply_text: {e}")
            await update.message.reply_text(
                msg('HELP_ADD_HABIT_WEIGHT_PROMPT', lang),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"📤 Sent weight selection keyboard (fallback) to {telegram_id}")
    else:
        # Fallback if no active message stored
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

    # Skip category selection - go directly to grace days
    keyboard = build_grace_days_keyboard(language=lang)
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_GRACE_DAYS_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent grace days selection keyboard to {telegram_id}")

    return AWAITING_GRACE_DAYS


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

    # Show grace days selection keyboard
    keyboard = build_grace_days_keyboard(language=lang)
    await query.edit_message_text(
        msg('HELP_ADD_HABIT_GRACE_DAYS_PROMPT', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent grace days selection keyboard to {telegram_id}")

    return AWAITING_GRACE_DAYS


async def habit_grace_days_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle grace days selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected grace days callback: {callback_data}")

    # Extract grace days from callback_data (format: grace_days_0, grace_days_1, etc.)
    try:
        grace_days = int(callback_data.replace("grace_days_", ""))
        logger.info(f"🎯 User {telegram_id} selected grace days: {grace_days}")
    except ValueError:
        logger.error(f"❌ Invalid grace days callback data: {callback_data}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid grace days"))
        return ConversationHandler.END

    # Store in context
    context.user_data['habit_grace_days'] = grace_days
    logger.info(f"✅ Stored habit grace days in context for user {telegram_id}")

    # Show exempt days selection keyboard
    keyboard = build_exempt_days_keyboard(language=lang)
    
    # Custom prompt text
    prompt = msg('HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT', lang) + msg('HELP_EXEMPT_DAYS_OR_MANUAL', lang)
    
    await query.edit_message_text(
        prompt,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent exempt days selection keyboard to {telegram_id}")

    return AWAITING_EXEMPT_DAYS


async def habit_exempt_days_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle exempt days selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🎯 User {telegram_id} selected exempt days callback: {callback_data}")

    # Parse exempt days from callback
    exempt_days = []
    exempt_days_display = msg('BUTTON_EXEMPT_NONE', lang)

    if callback_data == "exempt_days_none":
        exempt_days = []
        exempt_days_display = msg('BUTTON_EXEMPT_NONE', lang)
        logger.info(f"🎯 User {telegram_id} selected exempt days: None")
    elif callback_data == "exempt_days_weekends":
        exempt_days = [6, 7]  # Saturday=6, Sunday=7
        exempt_days_display = msg('BUTTON_EXEMPT_WEEKENDS', lang)
        logger.info(f"🎯 User {telegram_id} selected exempt days: Weekends")
    elif callback_data == "exempt_days_custom":
        # Custom button logic is replaced by direct text input in AWAITING_EXEMPT_DAYS
        # But if we keep the button, we can just show a prompt
        prompt_text = msg('HELP_EXEMPT_DAYS_MANUAL_ENTRY', lang)
        keyboard = build_cancel_only_keyboard(language=lang)
        await query.edit_message_text(
            prompt_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        # Stay in same state to receive text
        return AWAITING_EXEMPT_DAYS
    else:
        logger.error(f"❌ Invalid exempt days callback data: {callback_data}")
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Invalid exempt days"))
        return ConversationHandler.END

    # Store in context
    context.user_data['habit_exempt_days'] = exempt_days
    context.user_data['habit_exempt_days_display'] = exempt_days_display
    logger.info(f"✅ Stored habit exempt days in context for user {telegram_id}")

    # Show confirmation with summary (no category)
    habit_name = context.user_data.get('habit_name')
    habit_weight = context.user_data.get('habit_weight')
    habit_grace_days = context.user_data.get('habit_grace_days')

    confirmation_message = msg(
        'HELP_ADD_HABIT_CONFIRM',
        lang,
        name=habit_name,
        weight=habit_weight,
        grace_days=habit_grace_days,
        exempt_days=exempt_days_display
    )

    keyboard = build_remove_confirmation_keyboard(language=lang)
    await query.edit_message_text(
        confirmation_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent confirmation message to {telegram_id}")

    return AWAITING_HABIT_CONFIRMATION


async def habit_exempt_days_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle exempt days text input (e.g. '2, 4')."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = update.message.text.strip()

    logger.info(f"📝 User {telegram_id} entered custom exempt days: '{text}'")

    try:
        # Parse "2, 4" -> [2, 4]
        raw_days = [d.strip() for d in text.split(',')]
        days = []
        for d in raw_days:
            if not d.isdigit():
                raise ValueError("Non-digit characters found")
            val = int(d)
            if not (1 <= val <= 7):
                raise ValueError(f"Day {val} out of range 1-7")
            days.append(val)

        # Deduplicate and sort
        unique_days = sorted(list(set(days)))
        if not unique_days:
            raise ValueError("No valid days found")

        # Store in context
        context.user_data['habit_exempt_days'] = unique_days
        
        # Create display string (e.g., "Tue, Thu")
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        display_names = [day_names[d-1] for d in unique_days]
        display_str = ", ".join(display_names)
        context.user_data['habit_exempt_days_display'] = display_str

        logger.info(f"✅ Stored custom exempt days: {unique_days} ({display_str})")

        # Proceed to Confirmation (no category)
        habit_name = context.user_data.get('habit_name')
        habit_weight = context.user_data.get('habit_weight')
        habit_grace_days = context.user_data.get('habit_grace_days')

        confirmation_message = msg(
            'HELP_ADD_HABIT_CONFIRM',
            lang,
            name=habit_name,
            weight=habit_weight…10787 tokens truncated…rse_mode="HTML"
    )
    context.user_data['active_msg_chat_id'] = query.message.chat_id
    context.user_data['active_msg_id'] = query.message.message_id
    logger.info(f"📤 Sent habit name prompt to {telegram_id} (from edit redirect)")

    return AWAITING_HABIT_NAME


async def cancel_edit_habit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel /edit_habit conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel from user {telegram_id} (@{username}) in edit_habit flow")
    lang = await get_message_language_async(telegram_id, update)

    cancel_msg_obj = await update.message.reply_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Delete cancellation message with animation after a short delay
    async def delete_cancel_message():
        try:
            # Wait 2.5 seconds
            await asyncio.sleep(2.5)
            
            # Animation: Show deleting indicator
            await cancel_msg_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            
            # Delete the message
            await cancel_msg_obj.delete()
            logger.info(f"🗑️ Deleted cancellation message for user {telegram_id}")
        except Exception as e:
            # If deletion fails (e.g., message too old or already deleted), just log it
            logger.warning(f"⚠️ Could not delete cancellation message for user {telegram_id}: {e}")
    
    # Run deletion in background
    asyncio.create_task(delete_cancel_message())

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

    # Get all active habits for this user
    habits = await maybe_await(habit_repository.get_all_active(user.id))
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

    # Get all active habits for this user
    habits = await maybe_await(habit_repository.get_all_active(user.id))
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
        cancel_msg_obj = await query.edit_message_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
        logger.info(f"📤 Sent cancellation message to {telegram_id}")

        # Show Habits menu
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")

        # Delete cancellation message with animation after a short delay
        async def delete_cancel_message():
            try:
                # Wait 2.5 seconds
                await asyncio.sleep(2.5)
                
                # Animation: Show deleting indicator
                await cancel_msg_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
                await asyncio.sleep(0.5)
                
                # Delete the message
                await cancel_msg_obj.delete()
                logger.info(f"🗑️ Deleted cancellation message for user {telegram_id}")
            except Exception as e:
                # If deletion fails (e.g., message too old or already deleted), just log it
                logger.warning(f"⚠️ Could not delete cancellation message for user {telegram_id}: {e}")
        
        # Run deletion in background
        asyncio.create_task(delete_cancel_message())

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
        success_msg_obj = await query.edit_message_text(success_message, parse_mode="HTML")
        logger.info(f"📤 Sent success message to {telegram_id}")

        # Show Habits menu after successful removal
        from src.bot.keyboards import build_habits_menu_keyboard
        await query.message.reply_text(
            msg('HABITS_MENU_TITLE', lang),
            reply_markup=build_habits_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Habits menu to {telegram_id}")
        _schedule_message_delete(success_msg_obj, telegram_id, "habit removal success")

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

    cancel_msg_obj = await update.message.reply_text(msg('INFO_HABIT_CANCEL', lang), parse_mode="HTML")
    logger.info(f"📤 Sent cancellation message to {telegram_id}")

    # Delete cancellation message with animation after a short delay
    async def delete_cancel_message():
        try:
            # Wait 2.5 seconds
            await asyncio.sleep(2.5)
            
            # Animation: Show deleting indicator
            await cancel_msg_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            
            # Delete the message
            await cancel_msg_obj.delete()
            logger.info(f"🗑️ Deleted cancellation message for user {telegram_id}")
        except Exception as e:
            # If deletion fails (e.g., message too old or already deleted), just log it
            logger.warning(f"⚠️ Could not delete cancellation message for user {telegram_id}: {e}")
    
    # Run deletion in background
    asyncio.create_task(delete_cancel_message())

    # Clear context
    context.user_data.clear()
    return ConversationHandler.END


async def remove_back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Go back from confirmation to the habit selection list or close if unavailable."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    # Get user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
        return ConversationHandler.END

    # Re-fetch active habits for this user
    habits = await maybe_await(habit_repository.get_all_active(user.id))
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
# Note: AWAITING_HABIT_CATEGORY removed - category step skipped, defaults to None
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
        AWAITING_GRACE_DAYS: [
            CallbackQueryHandler(habit_grace_days_selected, pattern="^grace_days_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EXEMPT_DAYS: [
            CallbackQueryHandler(habit_exempt_days_selected, pattern="^exempt_days_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_exempt_days_text_received),
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
# Note: AWAITING_EDIT_CATEGORY removed - category step skipped to preserve existing value
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
            CallbackQueryHandler(habit_edit_name_skip, pattern="^skip_name$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_edit_name_received),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_WEIGHT: [
            CallbackQueryHandler(habit_edit_weight_skip, pattern="^skip_weight$"),
            CallbackQueryHandler(habit_edit_weight_selected, pattern="^weight_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_GRACE_DAYS: [
            CallbackQueryHandler(habit_edit_grace_days_skip, pattern="^skip_grace_days$"),
            CallbackQueryHandler(habit_edit_grace_days_selected, pattern="^grace_days_"),
            CallbackQueryHandler(cancel_habit_flow_callback, pattern="^cancel_habit_flow$")
        ],
        AWAITING_EDIT_EXEMPT_DAYS: [
            CallbackQueryHandler(habit_edit_exempt_days_skip, pattern="^skip_exempt_days$"),
            CallbackQueryHandler(habit_edit_exempt_days_selected, pattern="^exempt_days_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, habit_edit_exempt_days_text_received),
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
