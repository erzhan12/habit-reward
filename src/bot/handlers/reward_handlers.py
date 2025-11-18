"""Handlers for reward-related commands."""

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
    build_claimable_rewards_keyboard,
    build_reward_cancel_keyboard,
    build_reward_type_keyboard,
    build_reward_weight_keyboard,
    build_reward_pieces_keyboard,
    build_reward_piece_value_keyboard,
    build_reward_confirmation_keyboard,
    build_reward_post_create_keyboard,
    build_rewards_menu_keyboard
)
from src.bot.messages import msg
from src.bot.language import get_message_language_async, detect_language_from_telegram
from src.bot.navigation import push_navigation
from src.models.reward import RewardType
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
AWAITING_REWARD_TYPE = 11
AWAITING_REWARD_WEIGHT = 12
AWAITING_REWARD_PIECES = 13
AWAITING_REWARD_VALUE = 14
AWAITING_REWARD_CONFIRM = 15
AWAITING_REWARD_POST_ACTION = 16

REWARD_DATA_KEY = "reward_creation_data"


def _get_reward_context(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return mutable dict holding interim reward creation data."""
    return context.user_data.setdefault(REWARD_DATA_KEY, {})


def _clear_reward_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear stored reward creation data."""
    context.user_data.pop(REWARD_DATA_KEY, None)


def _format_reward_summary(lang: str, data: dict) -> str:
    """Render confirmation summary for reward creation."""
    type_mapping = {
        RewardType.VIRTUAL.value: msg('BUTTON_REWARD_TYPE_VIRTUAL', lang),
        RewardType.REAL.value: msg('BUTTON_REWARD_TYPE_REAL', lang),
        RewardType.NONE.value: msg('BUTTON_REWARD_TYPE_NONE', lang)
    }

    reward_type_value = data.get('type')
    type_key = reward_type_value.value if isinstance(reward_type_value, RewardType) else reward_type_value
    type_label = type_mapping.get(type_key, type_key or msg('TEXT_NOT_SET', lang))

    piece_value = data.get('piece_value')
    if piece_value is None:
        piece_value_display = msg('TEXT_NOT_SET', lang)
    else:
        piece_value_display = f"{piece_value:.2f}"

    weight = data.get('weight')
    weight_display = f"{weight:.2f}" if isinstance(weight, (int, float)) else msg('TEXT_NOT_SET', lang)

    return msg(
        'HELP_ADD_REWARD_CONFIRM',
        lang,
        name=html.escape(data.get('name', '')),
        type_label=type_label,
        weight=weight_display,
        pieces=data.get('pieces_required', msg('TEXT_NOT_SET', lang)),
        piece_value=piece_value_display
    )


async def list_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_rewards command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /list_rewards command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    rewards = await maybe_await(reward_service.get_active_rewards())
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
            reply_markup=build_back_to_menu_keyboard(lang)
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
            reply_markup=build_back_to_menu_keyboard(lang)
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
    logger.info(f"🖱️ User {telegram_id} (@{username}) clicked Back during claim reward flow")

    lang = await get_message_language_async(telegram_id, update)

    # Edit message to show cancellation and provide back to menu button
    await query.edit_message_text(
        msg('INFO_CANCELLED', lang),
        reply_markup=build_back_to_menu_keyboard(lang)
    )
    logger.info(f"📤 Sent claim flow cancelled message to {telegram_id}")
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
        await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_EMPTY', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_NAME

    if len(name) > REWARD_NAME_MAX_LENGTH:
        logger.warning(
            "⚠️ User %s submitted reward name exceeding max length (%s chars)",
            telegram_id,
            len(name)
        )
        await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_TOO_LONG', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_NAME

    existing = await maybe_await(reward_repository.get_by_name(name))
    if existing:
        logger.warning("⚠️ Reward name '%s' already exists", name)
        await update.message.reply_text(
            f"{msg('ERROR_REWARD_NAME_EXISTS', lang)}\n\n{msg('HELP_ADD_REWARD_NAME_PROMPT', lang)}",
            reply_markup=build_reward_cancel_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_NAME

    reward_data = _get_reward_context(context)
    reward_data['name'] = name
    logger.info("✅ Stored reward name '%s' for user %s", name, telegram_id)

    await update.message.reply_text(
        msg('HELP_ADD_REWARD_TYPE_PROMPT', lang),
        reply_markup=build_reward_type_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_TYPE


async def reward_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reward type selection via inline keyboard."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    callback_data = query.data.replace('reward_type_', '')

    type_mapping = {
        'virtual': RewardType.VIRTUAL,
        'real': RewardType.REAL,
        'none': RewardType.NONE
    }
    reward_type = type_mapping.get(callback_data)

    if reward_type is None:
        logger.error("❌ Unknown reward type callback '%s' from user %s", callback_data, telegram_id)
        await query.answer("Unknown reward type", show_alert=True)
        return AWAITING_REWARD_TYPE

    reward_data = _get_reward_context(context)
    reward_data['type'] = reward_type
    logger.info("✅ Stored reward type '%s' for user %s", reward_type, telegram_id)

    await query.edit_message_text(
        msg('HELP_ADD_REWARD_WEIGHT_PROMPT', lang),
        reply_markup=build_reward_weight_keyboard(lang),
        parse_mode="HTML"
    )
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
    logger.info("✅ Stored pieces_required=%s for user %s via button", pieces_required, telegram_id)

    await query.edit_message_text(
        msg('HELP_ADD_REWARD_PIECE_VALUE_PROMPT', lang),
        reply_markup=build_reward_piece_value_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_VALUE


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
    logger.info("✅ Stored pieces_required=%s for user %s", pieces_required, telegram_id)

    await update.message.reply_text(
        msg('HELP_ADD_REWARD_PIECE_VALUE_PROMPT', lang),
        reply_markup=build_reward_piece_value_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_VALUE


async def reward_piece_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle optional piece value input."""
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
        return AWAITING_REWARD_VALUE

    if value < 0:
        logger.warning("⚠️ User %s entered negative piece value %.2f", telegram_id, value)
        await update.message.reply_text(
            msg('ERROR_REWARD_PIECE_VALUE_INVALID', lang),
            reply_markup=build_reward_piece_value_keyboard(lang),
            parse_mode="HTML"
        )
        return AWAITING_REWARD_VALUE

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
    """Handle skip button for piece value."""
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
    reward_type = reward_data.get('type')
    weight = reward_data.get('weight')
    pieces_required = reward_data.get('pieces_required')

    if not all([name, reward_type, weight, pieces_required]):
        logger.error("❌ Reward data incomplete for user %s during save", telegram_id)
        await query.edit_message_text(
            msg('ERROR_GENERAL', lang, error="Missing reward data"),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    try:
        created_reward = await maybe_await(
            reward_service.create_reward(
                name=name,
                reward_type=reward_type,
                weight=float(weight),
                pieces_required=int(pieces_required),
                piece_value=reward_data.get('piece_value')
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
    await query.edit_message_text(
        msg('SUCCESS_REWARD_CREATED', lang, name=created_reward.name),
        reply_markup=build_reward_post_create_keyboard(lang),
        parse_mode="HTML"
    )
    return AWAITING_REWARD_POST_ACTION


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
    await query.edit_message_text(
        msg('INFO_REWARD_CANCEL', lang),
        parse_mode="HTML"
    )
    await query.message.reply_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def cancel_add_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback /cancel handler for reward creation conversation."""
    telegram_id = str(update.effective_user.id)
    lang = await get_message_language_async(telegram_id, update)
    logger.info("❌ User %s cancelled reward flow via command", telegram_id)

    _clear_reward_context(context)
    await update.message.reply_text(
        msg('INFO_REWARD_CANCEL', lang),
        parse_mode="HTML"
    )
    await update.message.reply_text(
        msg('REWARDS_MENU_TITLE', lang),
        reply_markup=build_rewards_menu_keyboard(lang),
        parse_mode="HTML"
    )
    return ConversationHandler.END


# Build conversation handler for add_reward
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
        AWAITING_REWARD_TYPE: [
            CallbackQueryHandler(reward_type_selected, pattern="^reward_type_(virtual|real|none)$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$")
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
        AWAITING_REWARD_VALUE: [
            CallbackQueryHandler(reward_piece_value_skip, pattern="^reward_value_skip$"),
            CallbackQueryHandler(cancel_reward_flow_callback, pattern="^cancel_reward_flow$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reward_piece_value_received)
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
            CallbackQueryHandler(claim_reward_callback, pattern="^claim_reward_"),
            CallbackQueryHandler(claim_back_callback, pattern="^menu_back$")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_claim_handler)]
)
