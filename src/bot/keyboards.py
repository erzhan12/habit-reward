"""Inline keyboard builders for Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.habit import Habit
from src.models.reward import Reward
from src.models.reward_progress import RewardProgress
from src.bot.messages import msg


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


def build_claimable_rewards_keyboard(
    progress_list: list[RewardProgress],
    rewards_dict: dict[str, 'Reward'],
    language: str = 'en'
) -> InlineKeyboardMarkup | None:
    """
    Build inline keyboard for claiming achieved rewards with reward names.

    Args:
        progress_list: List of achieved RewardProgress objects
        rewards_dict: Dictionary mapping reward_id to Reward object
        language: Language code (not currently used, reserved for future use)

    Returns:
        InlineKeyboardMarkup with claim buttons or None if no rewards
    """
    if not progress_list:
        return None

    keyboard = []
    for progress in progress_list:
        reward = rewards_dict.get(progress.reward_id)
        if reward:
            # Format: "Reward Name (X/Y pieces)"
            button_text = f"{reward.name} ({progress.pieces_earned}/{progress.pieces_required})"
            button = InlineKeyboardButton(
                text=button_text,
                callback_data=f"claim_reward_{progress.reward_id}"
            )
            keyboard.append([button])

    return InlineKeyboardMarkup(keyboard) if keyboard else None


def build_settings_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for settings menu.

    Args:
        language: Language code for translating button text

    Returns:
        InlineKeyboardMarkup with settings options
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('SETTINGS_SELECT_LANGUAGE', language),
            callback_data="settings_language"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_language_selection_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for language selection.

    Args:
        language: Language code for translating back button text

    Returns:
        InlineKeyboardMarkup with language options
    """
    keyboard = [
        [InlineKeyboardButton(
            text="🇬🇧 English",
            callback_data="lang_en"
        )],
        [InlineKeyboardButton(
            text="🇰🇿 Қазақша",
            callback_data="lang_kk"
        )],
        [InlineKeyboardButton(
            text="🇷🇺 Русский",
            callback_data="lang_ru"
        )],
        [InlineKeyboardButton(
            text=msg('SETTINGS_BACK', language),
            callback_data="settings_back"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)
