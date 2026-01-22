"""Handlers for reward-related commands."""

import asyncio
import html
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

from src.services.reward_service import reward_service
from src.services.audit_log_service import audit_log_service
from src.core.repositories import user_repository, reward_repository
from src.bot.formatters import (
    format_reward_progress_message,
    format_rewards_list_message,
    format_claim_success_with_progress
)
from src.bot.keyboards import (
    # build_back_to_menu_keyboard,
    build_claimable_rewards_keyboard,
    build_reward_cancel_keyboard,
    build_reward_weight_keyboard,
    build_reward_pieces_keyboard,
    build_recurring_keyboard,
    # Dormant keyboards kept for potential future reactivation of piece_value editing
    build_reward_piece_value_keyboard,
    build_reward_confirmation_keyboard,
    # build_reward_post_create_keyboard,
    build_rewards_menu_keyboard,
    build_rewards_for_edit_keyboard,
    build_rewards_for_toggle_keyboard,
    build_reward_skip_cancel_keyboard,
    build_reward_edit_weight_keyboard,
    build_reward_edit_pieces_keyboard,
    build_reward_edit_piece_value_keyboard,
    build_reward_edit_confirm_keyboard,
    build_reward_edit_recurring_keyboard,
)
from src.bot.messages import msg
from src.bot.language import get_message_language_async, detect_language_from_telegram
from src.bot.navigation import push_navigation, pop_navigation
from src.config import (
    REWARD_NAME_MAX_LENGTH,
    REWARD_WEIGHT_MIN,
    REWARD_WEIGHT_MAX,
    REWARD_PIECES_MIN
)
from src.utils.async_compat import maybe_await

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_REWARD_SELECTION = 1

AWAITING_REWARD_NAME = 10
AWAITING_REWARD_WEIGHT = 12
AWAITING_REWARD_PIECES = 13
AWAITING_REWARD_RECURRING = 14
AWAITING_REWARD_CONFIRM = 15
AWAITING_REWARD_POST_ACTION = 16

# Conversation states for reward edit
AWAITING_REWARD_EDIT_SELECTION = 30
AWAITING_REWARD_EDIT_NAME = 31
AWAITING_REWARD_EDIT_WEIGHT = 33
AWAITING_REWARD_EDIT_PIECES = 34
AWAITING_REWARD_EDIT_RECURRING = 35
AWAITING_REWARD_EDIT_CONFIRM = 36

# Conversation state for reward toggle
AWAITING_REWARD_TOGGLE_SELECTION = 40

REWARD_DATA_KEY = "reward_creation_data"
REWARD_EDIT_DATA_KEY = "reward_edit_data"


def _get_reward_context(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return mutable dict holding interim reward creation data."""
    return context.user_data.setdefault(REWARD_DATA_KEY, {})


def _clear_reward_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear stored reward creation data."""
    context.user_data.pop(REWARD_DATA_KEY, None)


def _get_reward_edit_context(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return mutable dict holding interim reward edit data."""
    return context.user_data.setdefault(REWARD_EDIT_DATA_KEY, {})


def _clear_reward_edit_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear stored reward edit data."""
    context.user_data.pop(REWARD_EDIT_DATA_KEY, None)


def _format_piece_value_display(lang: str, value) -> str:
    if value is None:
        return msg('TEXT_NOT_SET', lang)
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _format_reward_summary(lang: str, data: dict) -> str:
    """Render confirmation summary for reward creation.

    Note: Type is no longer shown in add flow (Feature 0030) - defaults to REAL.
    """
    weight = data.get('weight')
    weight_display = f"{weight:.2f}" if isinstance(weight, (int, float)) else msg('TEXT_NOT_SET', lang)

    # Recurring field
    is_recurring = data.get('is_recurring', True)  # Default to True for backward compatibility
    recurring_display = msg('BUTTON_RECURRING_YES', lang) if is_recurring else msg('BUTTON_RECURRING_NO', lang)

    return msg(
        'HELP_ADD_REWARD_CONFIRM',
        lang,
        name=html.escape(data.get('name', '')),
        weight=weight_display,
        pieces=data.get('pieces_required', msg('TEXT_NOT_SET', lang)),
        recurring=recurring_display
    )


async def list_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_rewards command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /list_rewards command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Get user to fetch user-specific rewards
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        return

    rewards = await maybe_await(reward_service.get_active_rewards(user.id))
    logger.info(f"🔍 Found {len(rewards)} active rewards for user {telegram_id}")
    message = format_rewards_list_message(rewards, lang)

    from src.bot.keyboards import build_back_to_menu_keyboard
    await update.message.reply_text(
        message,
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent rewards list to {telegram_id}")


async def my_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_rewards command - show cumulative reward progress."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /my_rewards command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    lang = (user.language or lang)

    # Get all reward progress
    progress_list = await maybe_await(
        reward_service.get_user_reward_progress(user.id)
    )
    logger.info(f"🔍 Found {len(progress_list)} reward progress entries for user {telegram_id}")

    from src.bot.keyboards import build_back_to_menu_keyboard

    if not progress_list:
        logger.info(f"ℹ️ No reward progress found for user {telegram_id}")
        await update.message.reply_text(
            msg('INFO_NO_REWARD_PROGRESS', lang),
            reply_markup=build_back_to_menu_keyboard(lang)
        )
        logger.info(f"📤 Sent INFO_NO_REWARD_PROGRESS message to {telegram_id}")
        return

    # Format each progress entry
    message_parts = [msg('HEADER_REWARD_PROGRESS', lang)]

    for progress in progress_list:
        reward = await maybe_await(reward_repository.get_by_id(progress.reward_id))
        if reward:
            progress_msg = format_reward_progress_message(progress, reward, lang)
            message_parts.append(progress_msg + "\n")

    logger.info(f"✅ Sending reward progress for {len(progress_list)} rewards to user {telegram_id}")
    await update.message.reply_text(
        "\n".join(message_parts),
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent reward progress to {telegram_id}")


async def claim_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Start /claim_reward conversation flow.

    Shows inline keyboard with achieved rewards or informative message if none.
    """
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /claim_reward command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', detect_language_from_telegram(update))
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    lang = (user.language or lang)

    # Get achieved rewards
    achieved_rewards = await maybe_await(
        reward_service.get_actionable_rewards(user.id)
    )
    logger.info(f"🔍 Found {len(achieved_rewards)} achieved rewards for user {telegram_id}")

    if not achieved_rewards:
        logger.info(f"ℹ️ No achieved rewards found for user {telegram_id}")
        from src.bot.keyboards import build_back_to_menu_keyboard
        await update.message.reply_text(
            msg('INFO_NO_REWARDS_TO_CLAIM', lang),
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent INFO_NO_REWARDS_TO_CLAIM message to {telegram_id}")
        return ConversationHandler.END

    # Build rewards dictionary for keyboard
    rewards_dict = await _get_rewards_dict(achieved_rewards)

    # Build and send keyboard
    keyboard = build_claimable_rewards_keyboard(achieved_rewards, rewards_dict, lang)
    logger.info(f"✅ Showing claimable rewards keyboard to {telegram_id} with {len(achieved_rewards)} rewards")
    await update.message.reply_text(
        msg('HELP_SELECT_REWARD_TO_CLAIM', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent claimable rewards keyboard to {telegram_id}")

    return AWAITING_REWARD_SELECTION


async def menu_claim_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point when reward claim starts from menu callback.

    Shows inline keyboard with achieved rewards or informative message if none.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received menu_rewards_claim callback from user {telegram_id} (@{username})")

    # Validate user exists
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    fallback_lang = detect_language_from_telegram(update)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', fallback_lang))
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', fallback_lang))
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    lang = user.language or await get_message_language_async(telegram_id, update)

    # Push navigation state for back button
    push_navigation(
        context,
        query.message.message_id,
        'menu_rewards_claim',
        lang
    )

    # Get achieved rewards
    achieved_rewards = await maybe_await(
        reward_service.get_actionable_rewards(user.id)
    )
    logger.info(f"🔍 Found {len(achieved_rewards)} achieved rewards for user {telegram_id}")

    if not achieved_rewards:
        logger.info(f"ℹ️ No achieved rewards found for user {telegram_id}")
        from src.bot.keyboards import build_back_to_menu_keyboard
        await query.edit_message_text(
            msg('INFO_NO_REWARDS_TO_CLAIM', lang),
            reply_markup=build_back_to_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent INFO_NO_REWARDS_TO_CLAIM message to {telegram_id}")
        return ConversationHandler.END

    # Build rewards dictionary for keyboard
    rewards_dict = await _get_rewards_dict(achieved_rewards)

    # Build and send keyboard
    keyboard = build_claimable_rewards_keyboard(achieved_rewards, rewards_dict, lang)
    logger.info(f"✅ Showing claimable rewards keyboard to {telegram_id} with {len(achieved_rewards)} rewards")
    await query.edit_message_text(
        msg('HELP_SELECT_REWARD_TO_CLAIM', lang),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent claimable rewards keyboard to {telegram_id}")

    return AWAITING_REWARD_SELECTION


async def claim_reward_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle reward selection from inline keyboard.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    logger.info(f"🖱️ Received callback '{callback_data}' from user {telegram_id} (@{username})")

    # Extract reward_id from callback_data
    if callback_data.startswith("claim_reward_"):
        reward_id = callback_data.replace("claim_reward_", "")
        logger.info(f"🎁 User {telegram_id} selected reward_id: {reward_id}")

        # Validate user exists and is active
        user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
        fallback_lang = detect_language_from_telegram(update)
        if not user:
            logger.error(f"❌ User {telegram_id} not found in database")
            await query.edit_message_text(
                msg('ERROR_USER_NOT_FOUND', fallback_lang)
            )
            logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
            return ConversationHandler.END

        if not user.is_active:
            logger.error(f"❌ User {telegram_id} is inactive")
            await query.edit_message_text(
                msg('ERROR_USER_INACTIVE', fallback_lang)
            )
            logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
            return ConversationHandler.END

        lang = (user.language or lang)

        # Get reward details for logging
        reward = await maybe_await(reward_repository.get_by_id(reward_id))
        reward_name = reward.name if reward else reward_id

        try:
            # Mark reward as claimed
            logger.info(f"⚙️ Marking reward '{reward_name}' as claimed for user {telegram_id}")
            updated_progress = await maybe_await(
                reward_service.mark_reward_claimed(user.id, reward_id)
            )

            # Log reward claim to audit trail
            claim_snapshot = {
                "reward_name": reward_name,
                "pieces_earned_before": updated_progress.get_pieces_required(),  # Was at pieces_required before claim
                "pieces_earned_after": updated_progress.pieces_earned,  # Now 0 after claim
                "claimed": updated_progress.claimed,
            }
            await maybe_await(
                audit_log_service.log_reward_claim(
                    user_id=user.id,
                    reward=reward,
                    progress_snapshot=claim_snapshot,
                )
            )

            # Fetch updated progress
            progress_list = await maybe_await(
                reward_service.get_user_reward_progress(user.id)
            )
            rewards_dict = await _get_rewards_dict(progress_list)

            # Format and send response
            message = format_claim_success_with_progress(
                reward_name,
                progress_list,
                rewards_dict,
                lang
            )
            logger.info(f"✅ Reward '{reward_name}' claimed successfully by user {telegram_id}. Status: {updated_progress.get_status().value}")

            # Check if reward was auto-deactivated (non-recurring)
            updated_reward = await maybe_await(reward_repository.get_by_id(reward_id))
            if updated_reward and not updated_reward.active and not updated_reward.is_recurring:
                # Add auto-deactivation message
                message += f"\n\n{msg('INFO_REWARD_NON_RECURRING_DEACTIVATED', lang)}"

            from src.bot.keyboards import build_back_to_menu_keyboard
            await query.edit_message_text(
                text=message,
                reply_markup=build_back_to_menu_keyboard(lang),
                parse_mode="HTML"
            )
            logger.info(f"📤 Sent claim success message with updated progress to {telegram_id}")

        except ValueError as e:
            logger.error(f"❌ Error claiming reward for user {telegram_id}: {str(e)}")

            # Log error to audit trail
            await maybe_await(
                audit_log_service.log_error(
                    user_id=user.id,
                    error_message=f"Error claiming reward: {str(e)}",
                    context={
                        "command": "claim_reward",
                        "reward_id": reward_id,
                        "reward_name": reward_name,
                    }
                )
            )

            await query.edit_message_text(msg('ERROR_GENERAL', lang, error=str(e)))
            logger.info(f"📤 Sent error message to {telegram_id}")

        return ConversationHandler.END

    return ConversationHandler.END


async def _get_rewards_dict(progress_list: list) -> dict:
    """
    Get rewards dictionary from progress list.

    Args:
        progress_list: List of RewardProgress objects

    Returns:
        Dictionary mapping reward_id to Reward object
    """
    rewards_dict = {}
    for progress in progress_list:
        reward = await maybe_await(reward_repository.get_by_id(progress.reward_id))
        if reward:
            rewards_dict[progress.reward_id] = reward
    return rewards_dict


async def cancel_claim_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the claim reward conversation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /cancel command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)
    await update.message.reply_text(msg('INFO_CANCELLED', lang))
    logger.info(f"📤 Sent conversation cancelled message to {telegram_id}")
    return ConversationHandler.END


async def claim_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Back button click during reward claim flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"🔙 User {telegram_id} (@{username}) clicked Back during claim reward flow")

    # Pop navigation stack and get previous state
    prev_state = pop_navigation(context)
    lang = prev_state.get('lang', 'en')

    # Return to previous menu (should be rewards menu)
    await query.edit_message_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"↩️ Returned user {telegram_id} to Rewards menu")
    return ConversationHandler.END


async def add_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /add_reward command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /add_reward command from user {telegram_id} (@{username})")
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update))
        )
        return ConversationHandler.END

    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', detect_language_from_telegram(update))
        )
        return ConversationHandler.END

    lang = user.language or await get_message_language_async(telegram_id, update)

    _clear_reward_context(context)
    await update.message.reply_text(
        msg('HELP_ADD_REWARD_NAME_PROMPT', lang),
        reply_markup=build_reward_cancel_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Prompted user {telegram_id} for reward name")
    return AWAITING_REWARD_NAME


async def menu_add_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point when reward creation starts from menu callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info(f"📨 Received menu_rewards_add callback from user {telegram_id}")

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        fallback_lang = detect_language_from_telegram(update)
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', fallback_lang))
        return ConversationHandler.END

    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        fallback_lang = detect_language_from_telegram(update)
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', fallback_lang))
        return ConversationHandler.END

    lang = user.language or await get_message_language_async(telegram_id, update)

    _clear_reward_context(context)
    edited_message = await query.edit_message_text(
        msg('HELP_ADD_REWARD_NAME_PROMPT', lang),
        reply_markup=build_reward_cancel_keyboard(lang),
        parse_mode="HTML"
    )

    push_navigation(context, edited_message.message_id, 'rewards_add', lang)
    logger.info(f"📤 Prompted user {telegram_id} for reward name via menu")
    return AWAITING_REWARD_NAME


async def reward_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reward name input."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    name = (update.message.text or "").strip()

    if not name:
        logger.warning(f"⚠️ User {telegram_id} submitted empty reward name")
        error_msg_obj = await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_EMPTY', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        # Store error message ID so it can be edited when valid name is entered
        context.user_data['active_msg_chat_id'] = error_msg_obj.chat_id
        context.user_data['active_msg_id'] = error_msg_obj.message_id
        return AWAITING_REWARD_NAME

    if len(name) > REWARD_NAME_MAX_LENGTH:
        logger.warning(
            "⚠️ User %s submitted reward name exceeding max length (%s chars)",
            telegram_id,
            len(name)
        )
        error_msg_obj = await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_TOO_LONG', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        # Store error message ID so it can be edited when valid name is entered
        context.user_data['active_msg_chat_id'] = error_msg_obj.chat_id
        context.user_data['active_msg_id'] = error_msg_obj.message_id
        return AWAITING_REWARD_NAME

    # Get user to check for duplicate names per user
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        return ConversationHandler.END

    existing = await maybe_await(reward_repository.get_by_name(user.id, name))
    if existing:
        logger.warning("⚠️ Reward name '%s' already exists for user %s", name, user.id)
        error_msg_obj = await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_EXISTS', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        # Store error message ID so it can be edited when valid name is entered
        context.user_data['active_msg_chat_id'] = error_msg_obj.chat_id
        context.user_data['active_msg_id'] = error_msg_obj.message_id
        return AWAITING_REWARD_NAME

    reward_data = _get_reward_context(context)
    reward_data['name'] = name
    logger.info("✅ Stored reward name '%s' for user %s", name, telegram_id)

    # Try to edit the active conversation message in-place
    active_chat_id = context.user_data.get('active_msg_chat_id')
    active_msg_id = context.user_data.get('active_msg_id')

    # Skip type selection, go directly to weight prompt
    keyboard = build_reward_weight_keyboard(lang)

    if active_chat_id and active_msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=active_chat_id,
                message_id=active_msg_id,
                text=msg('HELP_ADD_REWARD_WEIGHT_PROMPT', lang),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"📤 Edited active message to weight selection keyboard for {telegram_id}")
            # Clear stored message IDs after successful edit
            context.user_data.pop('active_msg_chat_id', None)
            context.user_data.pop('active_msg_id', None)
        except Exception as e:
            logger.warning(f"⚠️ Could not edit active message for {telegram_id}, falling back to reply_text: {e}")
            await update.message.reply_text(
                msg('HELP_ADD_REWARD_WEIGHT_PROMPT', lang),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"📤 Sent weight selection keyboard (fallback) to {telegram_id}")
    else:
        # Fallback if no active message stored
        await update.message.reply_text(
            msg('HELP_ADD_REWARD_WEIGHT_PROMPT', lang),
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent weight selection keyboard to {telegram_id}")

    return AWAITING_REWARD_WEIGHT


async def reward_weight_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quick weight selection from inline buttons."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    try:
        weight_value = float(query.data.replace('reward_weight_', ''))
    except ValueError:
        logger.error("❌ Invalid weight callback '%s' from user %s", query.data, telegram_id)
        await query.answer("Invalid weight", show_alert=True)
        return AWAITING_REWARD_WEIGHT

    if not (REWARD_WEIGHT_MIN <= weight_value <= REWARD_WEIGHT_MAX):
        logger.warning(
            "⚠️ Weight %.2f selected by user %s out of range",
            weight_value,
            telegram_id
        )
        await query.answer(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            show_alert=True
        )
        return AWAITING_REWARD_WEIGHT

    reward_data = _get_reward_context(context)
    reward_data['weight'] = weight_value
    logger.info("✅ Stored reward weight %.2f for user %s", weight_value, telegram_id)

    await query.edit_message_text(
        msg('HELP_ADD_REWARD_PIECES_PROMPT', lang),
        reply_markup=build_reward_pieces_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_PIECES


async def reward_weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manually entered reward weight."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip().replace(',', '.')

    try:
        weight_value = float(text)
    except ValueError:
        logger.warning("⚠️ User %s entered non-numeric reward weight '%s'", telegram_id, text)
        await update.message.reply_text(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            reply_markup=build_reward_weight_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_WEIGHT

    if not (REWARD_WEIGHT_MIN <= weight_value <= REWARD_WEIGHT_MAX):
        logger.warning(
            "⚠️ User %s entered reward weight out of range: %.2f",
            telegram_id,
            weight_value
        )
        await update.message.reply_text(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            reply_markup=build_reward_weight_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_WEIGHT

    reward_data = _get_reward_context(context)
    reward_data['weight'] = weight_value
    logger.info("✅ Stored reward weight %.2f for user %s", weight_value, telegram_id)

    await update.message.reply_text(
        msg('HELP_ADD_REWARD_PIECES_PROMPT', lang),
        reply_markup=build_reward_pieces_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_PIECES


async def reward_pieces_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quick selection of pieces required (button click for '1')."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    # The callback is 'reward_pieces_1', so pieces_required = 1
    pieces_required = 1

    reward_data = _get_reward_context(context)
    reward_data['pieces_required'] = pieces_required
    reward_data['is_recurring'] = True  # Default to True
    logger.info("✅ Stored pieces_required=%s for user %s via button", pieces_required, telegram_id)

    await query.edit_message_text(
        msg('HELP_ADD_REWARD_RECURRING_PROMPT', lang),
        reply_markup=build_recurring_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_RECURRING


async def reward_pieces_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pieces required input."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip()

    try:
        pieces_required = int(text)
    except ValueError:
        logger.warning("⚠️ User %s entered non-integer pieces '%s'", telegram_id, text)
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECES_INVALID', lang),
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_PIECES

    if pieces_required < REWARD_PIECES_MIN:
        logger.warning(
            "⚠️ User %s entered pieces below minimum: %s",
            telegram_id,
            pieces_required
        )
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECES_INVALID', lang),
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_PIECES

    reward_data = _get_reward_context(context)
    reward_data['pieces_required'] = pieces_required
    reward_data['is_recurring'] = True  # Default to True
    logger.info("✅ Stored pieces_required=%s for user %s", pieces_required, telegram_id)

    await update.message.reply_text(
        msg('HELP_ADD_REWARD_RECURRING_PROMPT', lang),
        reply_markup=build_recurring_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_RECURRING


async def reward_recurring_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Yes' selection for recurring reward."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    reward_data = _get_reward_context(context)
    reward_data['is_recurring'] = True
    logger.info("✅ User %s selected recurring=True", telegram_id)

    # Show confirmation summary
    summary = _format_reward_summary(lang, reward_data)
    await query.edit_message_text(
        summary,
        reply_markup=build_reward_confirmation_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_CONFIRM


async def reward_recurring_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'No' selection for recurring reward (one-time only)."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    reward_data = _get_reward_context(context)
    reward_data['is_recurring'] = False
    logger.info("✅ User %s selected recurring=False (one-time)", telegram_id)

    # Show confirmation summary
    summary = _format_reward_summary(lang, reward_data)
    await query.edit_message_text(
        summary,
        reply_markup=build_reward_confirmation_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_CONFIRM


async def reward_piece_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle optional piece value input.

    NOTE: This handler is DORMANT - not registered in add_reward_conversation states.
    Kept for potential future reactivation of piece_value editing via Telegram.
    """
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip()

    skip_keyword = msg('KEYWORD_SKIP', lang).lower()
    if text.lower() == skip_keyword:
        logger.info("ℹ️ User %s typed skip for piece value", telegram_id)
        reward_data = _get_reward_context(context)
        reward_data['piece_value'] = None
        summary = _format_reward_summary(lang, reward_data)
        await update.message.reply_text(
            summary,
            reply_markup=build_reward_confirmation_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_CONFIRM

    text_normalized = text.replace(',', '.')
    try:
        value = float(text_normalized)
    except ValueError:
        logger.warning("⚠️ User %s entered invalid piece value '%s'", telegram_id, text)
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECE_VALUE_INVALID', lang),
            reply_markup=build_reward_piece_value_keyboard(lang),
            parse_mode="HTML"
        )
        # DORMANT: Would return to piece_value state, but state removed in Feature 0023
        return ConversationHandler.END

    if value < 0:
        logger.warning("⚠️ User %s entered negative piece value %.2f", telegram_id, value)
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECE_VALUE_INVALID', lang),
            reply_markup=build_reward_piece_value_keyboard(lang),
            parse_mode="HTML"
        )
        # DORMANT: Would return to piece_value state, but state removed in Feature 0023
        return ConversationHandler.END

    reward_data = _get_reward_context(context)
    reward_data['piece_value'] = round(value, 2)
    logger.info("✅ Stored piece_value=%.2f for user %s", reward_data['piece_value'], telegram_id)

    summary = _format_reward_summary(lang, reward_data)
    await update.message.reply_text(
        summary,
        reply_markup=build_reward_confirmation_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_CONFIRM


async def reward_piece_value_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle skip button for piece value.

    NOTE: This handler is DORMANT - not registered in add_reward_conversation states.
    Kept for potential future reactivation of piece_value editing via Telegram.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    reward_data = _get_reward_context(context)
    reward_data['piece_value'] = None
    logger.info("ℹ️ User %s skipped piece value", telegram_id)

    summary = _format_reward_summary(lang, reward_data)
    await query.edit_message_text(
        summary,
        reply_markup=build_reward_confirmation_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_CONFIRM


async def reward_confirm_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persist reward after confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    reward_data = _get_reward_context(context)

    name = reward_data.get('name')
    weight = reward_data.get('weight')
    pieces_required = reward_data.get('pieces_required')
    is_recurring = reward_data.get('is_recurring', True)  # Default to True for backward compatibility

    if not all([name, weight, pieces_required]):
        logger.error("❌ Reward data incomplete for user %s during save", telegram_id)
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Missing reward data"),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    # Get user to create reward with user_id
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        return ConversationHandler.END

    try:
        # Note: piece_value is not collected via Telegram; rely on service defaults
        created_reward = await maybe_await(
            reward_service.create_reward(
                user_id=user.id,
                name=name,
                weight=float(weight),
                pieces_required=int(pieces_required),
                piece_value=None,
                is_recurring=is_recurring
            )
        )
    except ValueError as error:
        logger.warning("⚠️ Failed to create reward for user %s: %s", telegram_id, error)
        _clear_reward_context(context)
        await query.edit_message_text(
            f"{msg('ERROR_GENERAL', lang, error=str(error))}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_NAME
    except Exception as error:  # Unexpected errors
        logger.exception("❌ Unexpected error creating reward for user %s", telegram_id)
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(error)),
            parse_mode="HTML"
        )
        _clear_reward_context(context)
        return ConversationHandler.END

    logger.info(
        "✅ Reward '%s' (id=%s) created for user %s",
        created_reward.name,
        getattr(created_reward, 'id', None),
        telegram_id
    )

    _clear_reward_context(context)
    
    # Show success message (without keyboard)
    success_message = msg('SUCCESS_REWARD_CREATED', lang, name=created_reward.name)
    success_msg_obj = await query.edit_message_text(success_message, parse_mode="HTML")
    logger.info(f"📤 Sent success message to {telegram_id}")
    
    # Send full Rewards menu as a new message
    await query.message.reply_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent Rewards menu to {telegram_id}")
    
    # Delete success message with animation after user has time to read it
    async def delete_success_message():
        try:
            # Wait 2.5 seconds for user to read the success message
            await asyncio.sleep(2.5)
            
            # Animation: Show deleting indicator
            await success_msg_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
            await asyncio.sleep(0.5)
            
            # Delete the message
            await success_msg_obj.delete()
            logger.info(f"🗑️ Deleted success message for user {telegram_id}")
        except Exception as e:
            # If deletion fails (e.g., message too old or already deleted), just log it
            logger.warning(f"⚠️ Could not delete success message for user {telegram_id}: {e}")
    
    # Run deletion in background (don't await to avoid blocking)
    asyncio.create_task(delete_success_message())
    
    return ConversationHandler.END


async def reward_confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to first step to edit reward details."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("📝 User %s requested to edit reward details", telegram_id)

    _clear_reward_context(context)
    await query.edit_message_text(
        msg('HELP_ADD_REWARD_NAME_PROMPT', lang),
        reply_markup=build_reward_cancel_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_NAME


async def reward_add_another_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Restart reward creation after success."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("➕ User %s opted to add another reward", telegram_id)

    _clear_reward_context(context)
    await query.edit_message_text(
        msg('HELP_ADD_REWARD_NAME_PROMPT', lang),
        reply_markup=build_reward_cancel_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_NAME


async def reward_back_to_rewards_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return user to rewards menu after creation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("↩️ User %s returned to rewards menu", telegram_id)

    _clear_reward_context(context)
    await query.edit_message_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def cancel_reward_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button clicks during reward creation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("❌ User %s cancelled reward flow via button", telegram_id)

    _clear_reward_context(context)
    cancel_msg_obj = await query.edit_message_text(
        msg('INFO_REWARD_CANCEL', lang),
        parse_mode="HTML"
    )
    await query.message.reply_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    
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
    
    return ConversationHandler.END


async def cancel_add_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback /cancel handler for reward creation conversation."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("❌ User %s cancelled reward flow via command", telegram_id)

    _clear_reward_context(context)
    cancel_msg_obj = await update.message.reply_text(
        msg('INFO_REWARD_CANCEL', lang),
        parse_mode="HTML"
    )
    await update.message.reply_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    
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
    
    return ConversationHandler.END


# ============================================================================
# /edit_reward CONVERSATION HANDLER (Rewards submenu)
# ============================================================================

async def edit_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /edit_reward command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info("📨 Received /edit_reward command from user %s (@%s)", telegram_id, username)

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        return ConversationHandler.END
    if not user.is_active:
        await update.message.reply_text(msg('ERROR_USER_INACTIVE', detect_language_from_telegram(update)))
        return ConversationHandler.END

    lang = user.language or await get_message_language_async(telegram_id, update)
    rewards = await maybe_await(reward_repository.get_all_active(user.id))
    if not rewards:
        await update.message.reply_text(
            msg('ERROR_NO_REWARDS_TO_EDIT', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    keyboard = build_rewards_for_edit_keyboard(rewards, lang)
    await update.message.reply_text(
        msg('HELP_EDIT_REWARD_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_SELECTION


async def menu_edit_reward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point when reward editing starts from Rewards submenu button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    logger.info("📨 Received menu_rewards_edit callback from user %s", telegram_id)

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    fallback_lang = detect_language_from_telegram(update)
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', fallback_lang))
        return ConversationHandler.END
    if not user.is_active:
        await query.edit_message_text(msg('ERROR_USER_INACTIVE', fallback_lang))
        return ConversationHandler.END

    lang = user.language or await get_message_language_async(telegram_id, update)
    rewards = await maybe_await(reward_repository.get_all_active(user.id))
    if not rewards:
        await query.edit_message_text(
            msg('ERROR_NO_REWARDS_TO_EDIT', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    _clear_reward_edit_context(context)
    keyboard = build_rewards_for_edit_keyboard(rewards, lang)
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_SELECT', lang),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_SELECTION


async def reward_edit_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Back from reward selection to rewards menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    _clear_reward_edit_context(context)
    await query.edit_message_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def reward_edit_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reward selection for editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    reward_id = callback_data.replace("edit_reward_", "")
    reward = await maybe_await(reward_repository.get_by_id(reward_id))
    if not reward:
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Reward not found"), parse_mode="HTML")
        return ConversationHandler.END

    # Validate ownership (multi-user safety)
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user or reward.user_id != user.id:
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error="Access denied"), parse_mode="HTML")
        return ConversationHandler.END

    data = _get_reward_edit_context(context)
    data.clear()
    data["reward_id"] = reward.id
    data["old_name"] = reward.name
    data["old_weight"] = float(reward.weight)
    data["old_pieces_required"] = int(reward.pieces_required)
    data["old_is_recurring"] = reward.is_recurring

    # Prompt for name
    keyboard = build_reward_skip_cancel_keyboard(lang, skip_callback="reward_edit_skip_name")
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_NAME_PROMPT', lang, current_name=html.escape(reward.name)),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_NAME


async def reward_edit_name_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip name edit -> proceed to weight."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_name"] = data.get("old_name")

    current_weight = data.get("old_weight")
    keyboard = build_reward_edit_weight_keyboard(current_weight=current_weight, language=lang)
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_WEIGHT_PROMPT', lang, current_weight=f"{current_weight:.2f}"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_WEIGHT


async def reward_edit_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new reward name input."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    name = (update.message.text or "").strip()

    if not name:
        await update.message.reply_text(
            msg('ERROR_REWARD_NAME_EMPTY', lang),
            reply_markup=build_reward_skip_cancel_keyboard(lang, skip_callback="reward_edit_skip_name"),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_NAME

    if len(name) > REWARD_NAME_MAX_LENGTH:
        await update.message.reply_text(
            msg('ERROR_REWARD_NAME_TOO_LONG', lang),
            reply_markup=build_reward_skip_cancel_keyboard(lang, skip_callback="reward_edit_skip_name"),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_NAME

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await update.message.reply_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        return ConversationHandler.END

    data = _get_reward_edit_context(context)
    reward_id = data.get("reward_id")
    existing = await maybe_await(reward_repository.get_by_name(user.id, name))
    if existing and str(getattr(existing, "id", "")) != str(reward_id):
        await update.message.reply_text(
            msg('ERROR_REWARD_NAME_EXISTS', lang),
            reply_markup=build_reward_skip_cancel_keyboard(lang, skip_callback="reward_edit_skip_name"),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_NAME

    data["new_name"] = name

    current_weight = data.get("old_weight")
    keyboard = build_reward_edit_weight_keyboard(current_weight=current_weight, language=lang)
    await update.message.reply_text(
        msg('HELP_EDIT_REWARD_WEIGHT_PROMPT', lang, current_weight=f"{current_weight:.2f}"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_WEIGHT


async def reward_edit_weight_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip weight edit -> proceed to pieces."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_weight"] = data.get("old_weight")

    current_pieces = data.get("old_pieces_required")
    keyboard = build_reward_edit_pieces_keyboard(lang)
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_PIECES_PROMPT', lang, current_pieces=current_pieces),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_PIECES


async def reward_edit_weight_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quick weight selection for editing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    try:
        weight_value = float(query.data.replace("edit_reward_weight_", ""))
    except ValueError:
        await query.answer("Invalid weight", show_alert=True)
        return AWAITING_REWARD_EDIT_WEIGHT

    if not (REWARD_WEIGHT_MIN <= weight_value <= REWARD_WEIGHT_MAX):
        await query.answer(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            show_alert=True
        )
        return AWAITING_REWARD_EDIT_WEIGHT

    data = _get_reward_edit_context(context)
    data["new_weight"] = weight_value

    current_pieces = data.get("old_pieces_required")
    keyboard = build_reward_edit_pieces_keyboard(lang)
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_PIECES_PROMPT', lang, current_pieces=current_pieces),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_PIECES


async def reward_edit_weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manually entered reward weight for editing."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip().replace(",", ".")

    try:
        weight_value = float(text)
    except ValueError:
        await update.message.reply_text(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            reply_markup=build_reward_edit_weight_keyboard(language=lang),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_WEIGHT

    if not (REWARD_WEIGHT_MIN <= weight_value <= REWARD_WEIGHT_MAX):
        await update.message.reply_text(
            msg('ERROR_REWARD_WEIGHT_INVALID', lang, min=REWARD_WEIGHT_MIN, max=REWARD_WEIGHT_MAX),
            reply_markup=build_reward_edit_weight_keyboard(language=lang),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_WEIGHT

    data = _get_reward_edit_context(context)
    data["new_weight"] = weight_value

    current_pieces = data.get("old_pieces_required")
    keyboard = build_reward_edit_pieces_keyboard(lang)
    await update.message.reply_text(
        msg('HELP_EDIT_REWARD_PIECES_PROMPT', lang, current_pieces=current_pieces),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_PIECES


async def reward_edit_pieces_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip pieces edit -> proceed to recurring selection."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_pieces_required"] = data.get("old_pieces_required")

    # Ask about recurring
    return await _reward_edit_show_recurring(query, context, lang)


async def reward_edit_pieces_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quick pieces selection (1) for editing -> proceed to recurring selection."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_pieces_required"] = 1

    # Proceed to recurring selection
    return await _reward_edit_show_recurring(query, context, lang)


async def reward_edit_pieces_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manually entered pieces required for editing -> proceed to recurring selection."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip()

    try:
        pieces_required = int(text)
    except ValueError:
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECES_INVALID', lang),
            reply_markup=build_reward_edit_pieces_keyboard(lang),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_PIECES

    if pieces_required < REWARD_PIECES_MIN:
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECES_INVALID', lang),
            reply_markup=build_reward_edit_pieces_keyboard(lang),
            parse_mode="HTML",
        )
        return AWAITING_REWARD_EDIT_PIECES

    data = _get_reward_edit_context(context)
    data["new_pieces_required"] = pieces_required

    current_recurring = data.get("old_is_recurring", True)
    current_text = msg('BUTTON_RECURRING_YES', lang) if current_recurring else msg('BUTTON_RECURRING_NO', lang)
    await update.message.reply_text(
        msg('HELP_EDIT_REWARD_RECURRING_PROMPT', lang, current_value=current_text),
        reply_markup=build_reward_edit_recurring_keyboard(
            current_is_recurring=current_recurring,
            language=lang,
        ),
        parse_mode="HTML",
    )
    return AWAITING_REWARD_EDIT_RECURRING


async def reward_edit_value_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip piece value edit -> proceed to confirmation.

    NOTE: This handler is DORMANT - not registered in edit_reward_conversation states.
    Kept for potential future reactivation of piece_value editing via Telegram.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_piece_value"] = data.get("old_piece_value")

    return await _reward_edit_show_confirm(query, context, lang)


async def reward_edit_value_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Clear piece value -> proceed to confirmation.

    NOTE: This handler is DORMANT - not registered in edit_reward_conversation states.
    Kept for potential future reactivation of piece_value editing via Telegram.
    """
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_piece_value"] = None

    return await _reward_edit_show_confirm(query, context, lang)


async def reward_edit_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manually entered piece value for editing.

    NOTE: This handler is DORMANT - not registered in edit_reward_conversation states.
    Kept for potential future reactivation of piece_value editing via Telegram.
    """
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    text = (update.message.text or "").strip()

    # Support typing the localized skip keyword
    skip_keyword = msg('KEYWORD_SKIP', lang).lower()
    if text.lower() == skip_keyword:
        data = _get_reward_edit_context(context)
        data["new_piece_value"] = data.get("old_piece_value")
        # We don't have a query here; reply with confirmation message
        confirm_message, keyboard = _reward_edit_build_confirm(lang, data)
        await update.message.reply_text(confirm_message, reply_markup=keyboard, parse_mode="HTML")
        return AWAITING_REWARD_EDIT_CONFIRM

    text_normalized = text.replace(",", ".")
    try:
        value = float(text_normalized)
    except ValueError:
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECE_VALUE_INVALID', lang),
            reply_markup=build_reward_edit_piece_value_keyboard(lang),
            parse_mode="HTML",
        )
        # DORMANT: Would return to edit piece_value state, but state removed in Feature 0023
        return ConversationHandler.END

    if value < 0:
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECE_VALUE_INVALID', lang),
            reply_markup=build_reward_edit_piece_value_keyboard(lang),
            parse_mode="HTML",
        )
        # DORMANT: Would return to edit piece_value state, but state removed in Feature 0023
        return ConversationHandler.END

    data = _get_reward_edit_context(context)
    data["new_piece_value"] = round(value, 2)

    confirm_message, keyboard = _reward_edit_build_confirm(lang, data)
    await update.message.reply_text(confirm_message, reply_markup=keyboard, parse_mode="HTML")
    return AWAITING_REWARD_EDIT_CONFIRM


def _reward_edit_build_confirm(lang: str, data: dict) -> tuple[str, object]:
    """Build confirmation message for reward editing (without piece_value)."""
    old_name = html.escape(str(data.get("old_name", "")))
    new_name = html.escape(str(data.get("new_name", "")))
    old_weight = f"{float(data.get('old_weight', 0.0)):.2f}"
    new_weight = f"{float(data.get('new_weight', data.get('old_weight', 0.0))):.2f}"
    old_pieces = str(int(data.get("old_pieces_required", 1)))
    new_pieces = str(int(data.get("new_pieces_required", data.get("old_pieces_required", 1))))

    # Recurring values
    old_is_recurring = data.get("old_is_recurring", True)
    new_is_recurring = data.get("new_is_recurring", old_is_recurring)
    old_recurring = msg('BUTTON_RECURRING_YES', lang) if old_is_recurring else msg('BUTTON_RECURRING_NO', lang)
    new_recurring = msg('BUTTON_RECURRING_YES', lang) if new_is_recurring else msg('BUTTON_RECURRING_NO', lang)

    message = msg(
        "HELP_EDIT_REWARD_CONFIRM",
        lang,
        old_name=old_name,
        new_name=new_name,
        old_weight=old_weight,
        new_weight=new_weight,
        old_pieces=old_pieces,
        new_pieces=new_pieces,
        old_recurring=old_recurring,
        new_recurring=new_recurring,
    )
    keyboard = build_reward_edit_confirm_keyboard(lang)
    return message, keyboard


async def _reward_edit_show_recurring(query, context: ContextTypes.DEFAULT_TYPE, lang: str) -> int:
    """Show recurring selection prompt for edit flow."""
    data = _get_reward_edit_context(context)
    current_recurring = data.get("old_is_recurring", True)
    current_text = msg('BUTTON_RECURRING_YES', lang) if current_recurring else msg('BUTTON_RECURRING_NO', lang)
    await query.edit_message_text(
        msg('HELP_EDIT_REWARD_RECURRING_PROMPT', lang, current_value=current_text),
        reply_markup=build_reward_edit_recurring_keyboard(
            current_is_recurring=current_recurring,
            language=lang,
        ),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_EDIT_RECURRING


async def _reward_edit_show_confirm(query, context: ContextTypes.DEFAULT_TYPE, lang: str) -> int:
    data = _get_reward_edit_context(context)
    confirm_message, keyboard = _reward_edit_build_confirm(lang, data)
    await query.edit_message_text(confirm_message, reply_markup=keyboard, parse_mode="HTML")
    return AWAITING_REWARD_EDIT_CONFIRM


async def reward_edit_recurring_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip recurring edit -> keep current value and proceed to confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_is_recurring"] = data.get("old_is_recurring", True)

    return await _reward_edit_show_confirm(query, context, lang)


async def reward_edit_recurring_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Yes' selection for recurring in edit flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_is_recurring"] = True
    logger.info("✅ User %s set recurring=True in edit flow", telegram_id)

    return await _reward_edit_show_confirm(query, context, lang)


async def reward_edit_recurring_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'No' selection for recurring in edit flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    data = _get_reward_edit_context(context)
    data["new_is_recurring"] = False
    logger.info("✅ User %s set recurring=False in edit flow", telegram_id)

    return await _reward_edit_show_confirm(query, context, lang)


async def reward_edit_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for editing a reward."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    if query.data == "reward_edit_confirm_no":
        _clear_reward_edit_context(context)
        await query.edit_message_text(
            msg('INFO_REWARD_EDIT_CANCEL', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    data = _get_reward_edit_context(context)
    reward_id = data.get("reward_id")
    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', detect_language_from_telegram(update)))
        _clear_reward_edit_context(context)
        return ConversationHandler.END

    # Final duplicate check (in case race conditions)
    new_name = data.get("new_name", data.get("old_name"))
    existing = await maybe_await(reward_repository.get_by_name(user.id, new_name))
    if existing and str(getattr(existing, "id", "")) != str(reward_id):
        await query.edit_message_text(
            msg('ERROR_REWARD_NAME_EXISTS', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML",
        )
        _clear_reward_edit_context(context)
        return ConversationHandler.END

    # Note: piece_value is not edited via Telegram; preserve existing value
    updates = {
        "name": new_name,
        "weight": float(data.get("new_weight", data.get("old_weight"))),
        "pieces_required": int(data.get("new_pieces_required", data.get("old_pieces_required"))),
        "is_recurring": data.get("new_is_recurring", data.get("old_is_recurring", True)),
    }

    try:
        updated = await maybe_await(reward_repository.update(reward_id, updates))
    except Exception as e:
        logger.exception("❌ Failed to update reward %s for user %s", reward_id, telegram_id)
        await query.edit_message_text(msg('ERROR_GENERAL', lang, error=str(e)), parse_mode="HTML")
        _clear_reward_edit_context(context)
        return ConversationHandler.END

    _clear_reward_edit_context(context)
    await query.edit_message_text(
        msg('SUCCESS_REWARD_UPDATED', lang, name=html.escape(updated.name)),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel_reward_edit_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel reward edit flow via Cancel button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("❌ User %s cancelled reward edit flow via button", telegram_id)

    _clear_reward_edit_context(context)
    await query.edit_message_text(
        msg('INFO_REWARD_EDIT_CANCEL', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel_edit_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel /edit_reward conversation via /cancel."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("❌ User %s cancelled reward edit flow via command", telegram_id)

    _clear_reward_edit_context(context)
    await update.message.reply_text(
        msg('INFO_REWARD_EDIT_CANCEL', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML",
    )
    return ConversationHandler.END


# ======================================
# Toggle Reward Active/Inactive Handlers
# ======================================

async def menu_reward_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for toggling reward active status from menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang), parse_mode="HTML")
        return ConversationHandler.END

    # Get ALL rewards (both active and inactive)
    rewards = await maybe_await(reward_repository.get_all(user.id))

    if not rewards:
        await query.edit_message_text(
            msg('ERROR_NO_REWARDS_TO_TOGGLE', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    # Show rewards with status indicators
    await query.edit_message_text(
        msg('HELP_TOGGLE_REWARD_SELECT', lang),
        reply_markup=build_rewards_for_toggle_keyboard(rewards, lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_TOGGLE_SELECTION


async def reward_toggle_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reward selection for toggling active status."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data

    # Extract reward_id from callback_data (format: "toggle_reward_{reward_id}")
    reward_id = callback_data.replace("toggle_reward_", "")

    user = await maybe_await(user_repository.get_by_telegram_id(telegram_id))
    if not user:
        await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang), parse_mode="HTML")
        return ConversationHandler.END

    try:
        # Get current reward to determine new status
        reward = await maybe_await(reward_repository.get_by_id(reward_id))
        if not reward:
            await query.edit_message_text(
                msg('ERROR_GENERAL', lang, error="Reward not found"),
                reply_markup=build_rewards_menu_keyboard(lang),
                parse_mode="HTML"
            )
            return ConversationHandler.END

        # Toggle the active status
        new_active_status = not reward.active
        updated_reward = await maybe_await(
            reward_service.toggle_reward_active(user.id, reward_id, new_active_status)
        )

        # Show success message (without keyboard)
        if updated_reward.active:
            success_message = msg('SUCCESS_REWARD_ACTIVATED', lang, name=html.escape(updated_reward.name))
        else:
            success_message = msg('SUCCESS_REWARD_DEACTIVATED', lang, name=html.escape(updated_reward.name))

        success_msg_obj = await query.edit_message_text(success_message, parse_mode="HTML")
        logger.info(f"📤 Sent success message to {telegram_id}")

        # Send Rewards menu as a new message
        await query.message.reply_text(
            msg('REWARDS_MENU_TITLE', lang),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent Rewards menu to {telegram_id}")

        # Delete success message with animation after user has time to read it
        async def delete_success_message():
            try:
                # Wait 2.5 seconds for user to read the success message
                await asyncio.sleep(2.5)
                
                # Animation: Show deleting indicator
                await success_msg_obj.edit_text("🗑️ <i>Deleting...</i>", parse_mode="HTML")
                await asyncio.sleep(0.5)
                
                # Delete the message
                await success_msg_obj.delete()
                logger.info(f"🗑️ Deleted success message for user {telegram_id}")
            except Exception as e:
                # If deletion fails (e.g., message too old or already deleted), just log it
                logger.warning(f"⚠️ Could not delete success message for user {telegram_id}: {e}")
        
        # Run deletion in background (don't await to avoid blocking)
        asyncio.create_task(delete_success_message())

        logger.info("✅ User %s toggled reward %s to active=%s", telegram_id, reward_id, new_active_status)
        return ConversationHandler.END

    except ValueError as e:
        logger.warning("⚠️ Error toggling reward for user %s: %s", telegram_id, e)
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error=str(e)),
            reply_markup=build_rewards_menu_keyboard(lang),
            parse_mode="HTML"
        )
        return ConversationHandler.END


async def reward_toggle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back button in toggle flow."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)

    await query.edit_message_text(
        msg('MENU_REWARDS_TEXT', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    return ConversationHandler.END


# Build conversation handler for edit_reward
# Note: AWAITING_REWARD_EDIT_VALUE and AWAITING_REWARD_EDIT_TYPE states removed
edit_reward_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("edit_reward", edit_reward_command),
        CallbackQueryHandler(menu_edit_reward_callback, pattern="^menu_rewards_edit$"),
    ],
    states={
        AWAITING_REWARD_EDIT_SELECTION: [
            CallbackQueryHandler(reward_edit_selected, pattern="^edit_reward_"),
            CallbackQueryHandler(reward_edit_back_to_menu, pattern="^reward_edit_back$"),
        ],
        AWAITING_REWARD_EDIT_NAME: [
            CallbackQueryHandler(reward_edit_name_skip, pattern="^reward_edit_skip_name$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_edit_name_received),
            CallbackQueryHandler(cancel_reward_edit_flow_callback, pattern="^cancel_reward_flow$"),
        ],
        AWAITING_REWARD_EDIT_WEIGHT: [
            CallbackQueryHandler(reward_edit_weight_selected, pattern="^edit_reward_weight_(\\d+)$"),
            CallbackQueryHandler(reward_edit_weight_skip, pattern="^edit_reward_weight_skip$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_edit_weight_received),
            CallbackQueryHandler(cancel_reward_edit_flow_callback, pattern="^cancel_reward_flow$"),
        ],
        AWAITING_REWARD_EDIT_PIECES: [
            CallbackQueryHandler(reward_edit_pieces_selected, pattern="^edit_reward_pieces_1$"),
            CallbackQueryHandler(reward_edit_pieces_skip, pattern="^edit_reward_pieces_skip$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_edit_pieces_received),
            CallbackQueryHandler(cancel_reward_edit_flow_callback, pattern="^cancel_reward_flow$"),
        ],
        AWAITING_REWARD_EDIT_RECURRING: [
            CallbackQueryHandler(reward_edit_recurring_yes, pattern="^reward_recurring_yes$"),
            CallbackQueryHandler(reward_edit_recurring_no, pattern="^reward_recurring_no$"),
            CallbackQueryHandler(reward_edit_recurring_skip, pattern="^reward_edit_recurring_skip$"),
            CallbackQueryHandler(cancel_reward_edit_flow_callback, pattern="^cancel_reward_flow$"),
        ],
        AWAITING_REWARD_EDIT_CONFIRM: [
            CallbackQueryHandler(reward_edit_confirmed, pattern="^reward_edit_confirm_(yes|no)$"),
            CallbackQueryHandler(cancel_reward_edit_flow_callback, pattern="^cancel_reward_flow$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_edit_reward)],
    per_message=False,
)

# Build conversation handler for add_reward
# Note: AWAITING_REWARD_VALUE and type selection states removed
add_reward_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("add_reward", add_reward_command),
        CallbackQueryHandler(menu_add_reward_callback, pattern="^menu_rewards_add$")
    ],
    states={
        AWAITING_REWARD_NAME: [
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_name_received)
        ],
        AWAITING_REWARD_WEIGHT: [
            CallbackQueryHandler(reward_weight_selected, pattern="^reward_weight_(\\d+)$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_weight_received)
        ],
        AWAITING_REWARD_PIECES: [
            CallbackQueryHandler(reward_pieces_selected, pattern="^reward_pieces_1$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_pieces_received)
        ],
        AWAITING_REWARD_RECURRING: [
            CallbackQueryHandler(reward_recurring_yes, pattern="^reward_recurring_yes$"),
            CallbackQueryHandler(reward_recurring_no, pattern="^reward_recurring_no$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$")
        ],
        AWAITING_REWARD_CONFIRM: [
            CallbackQueryHandler(reward_confirm_save, pattern="^reward_confirm_save$"),
            CallbackQueryHandler(reward_confirm_edit, pattern="^reward_confirm_edit$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$")
        ],
        AWAITING_REWARD_POST_ACTION: [
            CallbackQueryHandler(reward_add_another_callback, pattern="^reward_add_another$"),
            CallbackQueryHandler(reward_back_to_rewards_callback, pattern="^reward_back_to_rewards$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_add_reward)],
    per_message=False
)


# Build conversation handler for claim_reward
claim_reward_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("claim_reward", claim_reward_command),
        CallbackQueryHandler(menu_claim_reward_callback, pattern="^menu_rewards_claim$")
    ],
    states={
        AWAITING_REWARD_SELECTION: [
            CallbackQueryHandler(claim_back_callback, pattern="^claim_reward_back$"),
            CallbackQueryHandler(claim_reward_callback, pattern="^claim_reward_"),
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_claim_handler)]
)

# Build conversation handler for toggle_reward (activate/deactivate)
toggle_reward_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(menu_reward_toggle_callback, pattern="^menu_reward_toggle$")
    ],
    states={
        AWAITING_REWARD_TOGGLE_SELECTION: [
            CallbackQueryHandler(reward_toggle_selected, pattern="^toggle_reward_"),
            CallbackQueryHandler(reward_toggle_back, pattern="^reward_toggle_back$")
        ]
    },
    fallbacks=[],
    per_message=False
)
