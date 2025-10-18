"""Handlers for reward-related commands."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.services.reward_service import reward_service
from src.airtable.repositories import user_repository, reward_repository
from src.bot.formatters import (
    format_reward_progress_message,
    format_rewards_list_message
)
from src.models.reward_progress import RewardStatus
from src.bot.messages import msg
from src.bot.language import get_message_language

# Configure logging
logger = logging.getLogger(__name__)


async def list_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_rewards command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /list_rewards command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    rewards = reward_service.get_active_rewards()
    logger.info(f"🔍 Found {len(rewards)} active rewards for user {telegram_id}")
    message = format_rewards_list_message(rewards, lang)
    await update.message.reply_text(message, parse_mode="HTML")
    logger.info(f"📤 Sent rewards list to {telegram_id}")


async def my_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_rewards command - show cumulative reward progress."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /my_rewards command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    # Get all reward progress
    progress_list = reward_service.get_user_reward_progress(user.id)
    logger.info(f"🔍 Found {len(progress_list)} reward progress entries for user {telegram_id}")

    if not progress_list:
        logger.info(f"ℹ️ No reward progress found for user {telegram_id}")
        await update.message.reply_text(msg('INFO_NO_REWARD_PROGRESS', lang))
        logger.info(f"📤 Sent INFO_NO_REWARD_PROGRESS message to {telegram_id}")
        return

    # Format each progress entry
    message_parts = [msg('HEADER_REWARD_PROGRESS', lang)]

    for progress in progress_list:
        reward = reward_repository.get_by_id(progress.reward_id)
        if reward:
            progress_msg = format_reward_progress_message(progress, reward, lang)
            message_parts.append(progress_msg + "\n")

    logger.info(f"✅ Sending reward progress for {len(progress_list)} rewards to user {telegram_id}")
    await update.message.reply_text(
        "\n".join(message_parts),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent reward progress to {telegram_id}")


async def claim_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claim_reward <reward_name> command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /claim_reward command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    if not context.args:
        logger.warning(f"⚠️ User {telegram_id} called /claim_reward without arguments")
        await update.message.reply_text(
            msg('HELP_CLAIM_REWARD_USAGE', lang)
        )
        logger.info(f"📤 Sent usage help to {telegram_id}")
        return

    reward_name = " ".join(context.args)
    logger.info(f"🎁 User {telegram_id} attempting to claim reward: '{reward_name}'")

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    # Get reward by name
    reward = reward_repository.get_by_name(reward_name)
    if not reward:
        logger.warning(f"⚠️ Reward '{reward_name}' not found for user {telegram_id}")
        await update.message.reply_text(
            msg('ERROR_REWARD_NOT_FOUND', lang, reward_name=reward_name)
        )
        logger.info(f"📤 Sent ERROR_REWARD_NOT_FOUND message to {telegram_id}")
        return

    try:
        # Mark as completed
        logger.info(f"⚙️ Marking reward '{reward_name}' as completed for user {telegram_id}")
        updated_progress = reward_service.mark_reward_completed(user.id, reward.id)

        logger.info(f"✅ Reward '{reward_name}' claimed successfully by user {telegram_id}. Status: {updated_progress.status.value}")
        await update.message.reply_text(
            msg('SUCCESS_REWARD_CLAIMED', lang,
                reward_name=reward.name,
                status=updated_progress.status.value),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent success message to {telegram_id}")

    except ValueError as e:
        logger.error(f"❌ Error claiming reward for user {telegram_id}: {str(e)}")
        await update.message.reply_text(
            msg('ERROR_GENERAL', lang, error=str(e))
        )
        logger.info(f"📤 Sent error message to {telegram_id}")


async def set_reward_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_reward_status <reward_name> <status> command."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /set_reward_status command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    if len(context.args) < 2:
        logger.warning(f"⚠️ User {telegram_id} called /set_reward_status with insufficient arguments")
        await update.message.reply_text(
            msg('HELP_SET_STATUS_USAGE', lang)
        )
        logger.info(f"📤 Sent usage help to {telegram_id}")
        return

    status_str = context.args[-1].lower()
    reward_name = " ".join(context.args[:-1])
    logger.info(f"🔄 User {telegram_id} attempting to set reward '{reward_name}' status to '{status_str}'")

    # Map status string to enum
    status_map = {
        "pending": RewardStatus.PENDING,
        "achieved": RewardStatus.ACHIEVED,
        "completed": RewardStatus.COMPLETED
    }

    if status_str not in status_map:
        logger.warning(f"⚠️ Invalid status '{status_str}' provided by user {telegram_id}")
        await update.message.reply_text(
            msg('ERROR_INVALID_STATUS', lang)
        )
        logger.info(f"📤 Sent ERROR_INVALID_STATUS message to {telegram_id}")
        return

    new_status = status_map[status_str]

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"⚠️ User {telegram_id} not found in database")
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_NOT_FOUND message to {telegram_id}")
        return

    # Check if user is active
    if not user.active:
        logger.warning(f"⚠️ User {telegram_id} is inactive")
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        logger.info(f"📤 Sent ERROR_USER_INACTIVE message to {telegram_id}")
        return

    # Get reward by name
    reward = reward_repository.get_by_name(reward_name)
    if not reward:
        logger.warning(f"⚠️ Reward '{reward_name}' not found for user {telegram_id}")
        await update.message.reply_text(
            msg('ERROR_REWARD_NOT_FOUND', lang, reward_name=reward_name)
        )
        logger.info(f"📤 Sent ERROR_REWARD_NOT_FOUND message to {telegram_id}")
        return

    try:
        # Set status
        logger.info(f"⚙️ Setting reward '{reward_name}' status to '{new_status.value}' for user {telegram_id}")
        updated_progress = reward_service.set_reward_status(
            user.id,
            reward.id,
            new_status
        )

        logger.info(f"✅ Reward '{reward_name}' status updated successfully for user {telegram_id} to {updated_progress.status.value}")
        await update.message.reply_text(
            msg('SUCCESS_STATUS_UPDATED', lang,
                reward_name=reward.name,
                status=updated_progress.status.value),
            parse_mode="HTML"
        )
        logger.info(f"📤 Sent success message to {telegram_id}")

    except ValueError as e:
        logger.error(f"❌ Error setting reward status for user {telegram_id}: {str(e)}")
        await update.message.reply_text(
            msg('ERROR_GENERAL', lang, error=str(e))
        )
        logger.info(f"📤 Sent error message to {telegram_id}")


async def add_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add_reward command - conversational reward creation."""
    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or "N/A"
    logger.info(f"📨 Received /add_reward command from user {telegram_id} (@{username})")
    lang = get_message_language(telegram_id, update)

    logger.info(f"ℹ️ User {telegram_id} requested unimplemented feature: add_reward")
    await update.message.reply_text(
        msg('INFO_FEATURE_COMING_SOON', lang),
        parse_mode="HTML"
    )
    logger.info(f"📤 Sent feature coming soon message to {telegram_id}")
