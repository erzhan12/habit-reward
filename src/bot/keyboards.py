"""Inline keyboard builders for Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.habit import Habit
from src.models.reward_progress import RewardProgress


def build_habit_selection_keyboard(habits: list[Habit]) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit selection.

    Args:
        habits: List of active habits

    Returns:
        InlineKeyboardMarkup with habit buttons
    """
    keyboard = []
    for habit in habits:
        button = InlineKeyboardButton(
            text=habit.name,
            callback_data=f"habit_{habit.id}"
        )
        keyboard.append([button])

    # Add custom text option (commented out for now)
    # keyboard.append([
    #     InlineKeyboardButton(
    #         text="📝 Enter custom text",
    #         callback_data="habit_custom"
    #     )
    # ])

    return InlineKeyboardMarkup(keyboard)


def build_reward_status_keyboard(progress: RewardProgress) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for changing reward status.

    Args:
        progress: RewardProgress object

    Returns:
        InlineKeyboardMarkup with status buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text="✅ Mark as Completed",
            callback_data=f"complete_reward_{progress.reward_id}"
        )],
        [InlineKeyboardButton(
            text="🕒 Reset to Pending",
            callback_data=f"reset_reward_{progress.reward_id}"
        )]
    ]

    return InlineKeyboardMarkup(keyboard)


def build_actionable_rewards_keyboard(rewards: list[RewardProgress]) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for claiming achieved rewards.

    Args:
        rewards: List of achieved RewardProgress objects

    Returns:
        InlineKeyboardMarkup with claim buttons
    """
    if not rewards:
        return None

    keyboard = []
    for progress in rewards:
        button = InlineKeyboardButton(
            text=f"✅ Claim: {progress.pieces_earned}/{progress.pieces_required} pieces",
            callback_data=f"claim_reward_{progress.reward_id}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)
