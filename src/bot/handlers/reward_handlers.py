"""Handlers for reward-related commands."""

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


async def list_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list_rewards command."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    rewards = reward_service.get_active_rewards()
    message = format_rewards_list_message(rewards, lang)
    await update.message.reply_text(message, parse_mode="Markdown")


async def my_rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_rewards command - show cumulative reward progress."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return

    # Get all reward progress
    progress_list = reward_service.get_user_reward_progress(user.id)

    if not progress_list:
        await update.message.reply_text(msg('INFO_NO_REWARD_PROGRESS', lang))
        return

    # Format each progress entry
    message_parts = [msg('HEADER_REWARD_PROGRESS', lang)]

    for progress in progress_list:
        reward = reward_repository.get_by_id(progress.reward_id)
        if reward:
            progress_msg = format_reward_progress_message(progress, reward, lang)
            message_parts.append(progress_msg + "\n")

    await update.message.reply_text(
        "\n".join(message_parts),
        parse_mode="Markdown"
    )


async def claim_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claim_reward <reward_name> command."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    if not context.args:
        await update.message.reply_text(
            msg('HELP_CLAIM_REWARD_USAGE', lang)
        )
        return

    reward_name = " ".join(context.args)

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return

    # Get reward by name
    reward = reward_repository.get_by_name(reward_name)
    if not reward:
        await update.message.reply_text(
            msg('ERROR_REWARD_NOT_FOUND', lang, reward_name=reward_name)
        )
        return

    try:
        # Mark as completed
        updated_progress = reward_service.mark_reward_completed(user.id, reward.id)

        await update.message.reply_text(
            msg('SUCCESS_REWARD_CLAIMED', lang,
                reward_name=reward.name,
                status=updated_progress.status.value),
            parse_mode="Markdown"
        )

    except ValueError as e:
        await update.message.reply_text(
            msg('ERROR_GENERAL', lang, error=str(e))
        )


async def set_reward_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_reward_status <reward_name> <status> command."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    if len(context.args) < 2:
        await update.message.reply_text(
            msg('HELP_SET_STATUS_USAGE', lang)
        )
        return

    status_str = context.args[-1].lower()
    reward_name = " ".join(context.args[:-1])

    # Map status string to enum
    status_map = {
        "pending": RewardStatus.PENDING,
        "achieved": RewardStatus.ACHIEVED,
        "completed": RewardStatus.COMPLETED
    }

    if status_str not in status_map:
        await update.message.reply_text(
            msg('ERROR_INVALID_STATUS', lang)
        )
        return

    new_status = status_map[status_str]

    # Validate user exists
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        await update.message.reply_text(
            msg('ERROR_USER_NOT_FOUND', lang)
        )
        return

    # Check if user is active
    if not user.active:
        await update.message.reply_text(
            msg('ERROR_USER_INACTIVE', lang)
        )
        return

    # Get reward by name
    reward = reward_repository.get_by_name(reward_name)
    if not reward:
        await update.message.reply_text(
            msg('ERROR_REWARD_NOT_FOUND', lang, reward_name=reward_name)
        )
        return

    try:
        # Set status
        updated_progress = reward_service.set_reward_status(
            user.id,
            reward.id,
            new_status
        )

        await update.message.reply_text(
            msg('SUCCESS_STATUS_UPDATED', lang,
                reward_name=reward.name,
                status=updated_progress.status.value),
            parse_mode="Markdown"
        )

    except ValueError as e:
        await update.message.reply_text(
            msg('ERROR_GENERAL', lang, error=str(e))
        )


async def add_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add_reward command - conversational reward creation."""
    telegram_id = str(update.effective_user.id)
    lang = get_message_language(telegram_id, update)

    await update.message.reply_text(
        msg('INFO_FEATURE_COMING_SOON', lang),
        parse_mode="Markdown"
    )
