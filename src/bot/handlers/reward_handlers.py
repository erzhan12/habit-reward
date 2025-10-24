"""Handlers for reward-related commands."""

import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler
)

from src.services.reward_service import reward_service
from src.core.repositories import user_repository, reward_repository
from src.bot.formatters import (
    format_reward_progress_message,
    format_rewards_list_message,
    format_claim_success_with_progress
)
from src.bot.keyboards import build_claimable_rewards_keyboard
from src.bot.messages import msg
from src.bot.language import get_message_language_async

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_REWARD_SELECTION = 1


async def list_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_rewards command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /list_rewards command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    rewards = await reward_service.get_active_rewards()
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
    user = await user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    # Get all reward progress
    progress_list = await reward_service.get_user_reward_progress(user.id)
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
        reward = await reward_repository.get_by_id(progress.reward_id)
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
    user = await user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return ConversationHandler.END

    # Check if user is active
    if not user.is_active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return ConversationHandler.END

    # Get achieved rewards
    achieved_rewards = await reward_service.get_actionable_rewards(user.id)
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
        user = await user_repository.get_by_telegram_id(telegram_id)
        if not user:
            logger.error(f"❌ User {telegram_id} not found in database")
            await query.edit_message_text(msg('ERROR_USER_NOT_FOUND', lang))
            logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
            return ConversationHandler.END

        if not user.is_active:
            logger.error(f"❌ User {telegram_id} is inactive")
            await query.edit_message_text(msg('ERROR_USER_INACTIVE', lang))
            logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
            return ConversationHandler.END

        # Get reward details for logging
        reward = await reward_repository.get_by_id(reward_id)
        reward_name = reward.name if reward else reward_id

        try:
            # Mark reward as claimed
            logger.info(f"⚙️ Marking reward '{reward_name}' as claimed for user {telegram_id}")
            updated_progress = await reward_service.mark_reward_claimed(user.id, reward_id)

            # Fetch updated progress
            progress_list = await reward_service.get_user_reward_progress(user.id)
            rewards_dict = await _get_rewards_dict(progress_list)

            # Format and send response
            message = format_claim_success_with_progress(
                reward_name,
                progress_list,
                rewards_dict,
                lang
            )
            logger.info(f"✅ Reward '{reward_name}' claimed successfully by user {telegram_id}. Status: {updated_progress.status.value}")

            from src.bot.keyboards import build_back_to_menu_keyboard
            await query.edit_message_text(
                text=message,
                reply_markup=build_back_to_menu_keyboard(lang),
                parse_mode="HTML"
            )
            logger.info(f"📤 Sent claim success message with updated progress to {telegram_id}")

        except ValueError as e:
            logger.error(f"❌ Error claiming reward for user {telegram_id}: {str(e)}")
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
        reward = await reward_repository.get_by_id(progress.reward_id)
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


async def add_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add_reward command - conversational reward creation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /add_reward command from user {telegram_id} (@{username})")
    lang = await get_message_language_async(telegram_id, update)

    logger.info(f"ℹ️ User {telegram_id} requested unimplemented feature: add_reward")
    from src.bot.keyboards import build_back_to_menu_keyboard
    await update.message.reply_text(
        msg('INFO_FEATURE_COMING_SOON', lang),
        reply_markup=build_back_to_menu_keyboard(lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent feature coming soon message to {telegram_id}")


# Build conversation handler for claim_reward
claim_reward_conversation = ConversationHandler(
    entry_points=[CommandHandler("claim_reward", claim_reward_command)],
    states={
        AWAITING_REWARD_SELECTION: [
            CallbackQueryHandler(claim_reward_callback, pattern="^claim_reward_")
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel_claim_handler)]
)
