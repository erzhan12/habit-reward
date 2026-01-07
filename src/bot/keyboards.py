"""Inline keyboard builders for Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.models.habit import Habit
from src.models.reward import Reward
from src.models.reward_progress import RewardProgress
from src.bot.messages import msg


def build_habit_selection_keyboard(habits: list[Habit], language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit selection.

    Args:
        habits: List of active habits
        language: Language code for translating Back button text

    Returns:
        InlineKeyboardMarkup with habit buttons and Back button
    """
    keyboard = []
    for habit in habits:
        button = InlineKeyboardButton(
            text=habit.name,
            callback_data=f"habit_{habit.id}"
        )
        keyboard.append([button])

    # Add Back button to return to main menu
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_simple_habit_selection_keyboard(habits: list[Habit], language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for simple habit selection (one-click completion).

    Used in the simple habit_done flow where clicking a habit immediately
    logs it as completed for today.

    Args:
        habits: List of active habits not yet completed today
        language: Language code for translating Back button text

    Returns:
        InlineKeyboardMarkup with habit buttons (simple_ prefix) and Back button
    """
    keyboard = []
    for habit in habits:
        button = InlineKeyboardButton(
            text=habit.name,
            callback_data=f"simple_habit_{habit.id}"
        )
        keyboard.append([button])

    # Add Back button to return to main menu
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_habit_revert_keyboard(habits: list[Habit], language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for selecting a habit completion to revert.

    Args:
        habits: List of habits available for reverting
        language: Language code for translating Back button text

    Returns:
        InlineKeyboardMarkup with habit buttons and Back button
    """
    keyboard = []
    for habit in habits:
        keyboard.append([
            InlineKeyboardButton(
                text=habit.name,
                callback_data=f"revert_habit_{habit.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )
    ])

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
            text=f"✅ Claim: {progress.pieces_earned}/{progress.get_pieces_required() or 1} pieces",
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
            button_text = f"{reward.name} ({progress.pieces_earned}/{progress.get_pieces_required() or 1})"
            button = InlineKeyboardButton(
                text=button_text,
                callback_data=f"claim_reward_{progress.reward_id}"
            )
            keyboard.append([button])

    # Add Back button to return to rewards menu
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="claim_reward_back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_settings_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for settings menu.

    Args:
        language: Language code for translating button text

    Returns:
        InlineKeyboardMarkup with settings options and Back button
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('SETTINGS_SELECT_LANGUAGE', language),
            callback_data="settings_language"
        )],
        [InlineKeyboardButton(
            text=msg('SETTINGS_API_KEYS', language),
            callback_data="settings_api_keys"
        )],
        [InlineKeyboardButton(
            text=msg('SETTINGS_NO_REWARD_PROB', language),
            callback_data="settings_no_reward_prob"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_no_reward_probability_keyboard(current_value: float, language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for no reward probability selection.

    Args:
        current_value: Current probability value
        language: Language code for translating button text

    Returns:
        InlineKeyboardMarkup with preset options (25%, 50%, 75%), Custom, and Cancel
    """
    # Preset buttons in a row
    presets = [
        InlineKeyboardButton(text="25%", callback_data="no_reward_prob_25"),
        InlineKeyboardButton(text="50%", callback_data="no_reward_prob_50"),
        InlineKeyboardButton(text="75%", callback_data="no_reward_prob_75"),
    ]

    keyboard = [
        presets,  # 25%, 50%, 75% in one row
        [InlineKeyboardButton(
            text=msg('NO_REWARD_PROB_CUSTOM', language),
            callback_data="no_reward_prob_custom"
        )],
        [InlineKeyboardButton(
            text=msg('SETTINGS_BACK', language),
            callback_data="settings_back"
        )],
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



def build_weight_selection_keyboard(
    current_weight: int | None = None, 
    language: str = 'en',
    skip_callback: str | None = None
) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit weight selection (10, 20, 30...100).

    Args:
        current_weight: Current weight value (will be highlighted with ✓)
        language: Language code (reserved for future use)
        skip_callback: If provided, adds a Skip button with this callback data

    Returns:
        InlineKeyboardMarkup with weight buttons
    """
    keyboard = []
    row = []

    for weight in range(10, 101, 10):
        # Highlight current weight with checkmark
        button_text = f"✓ {weight}" if current_weight == weight else str(weight)
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"weight_{weight}"
        )
        row.append(button)

        # Create rows of 5 buttons each
        if len(row) == 5:
            keyboard.append(row)
            row = []

    # Add remaining buttons
    if row:
        keyboard.append(row)

    # Add Skip button if requested
    if skip_callback:
        keyboard.append([
            InlineKeyboardButton(
                text=msg('BUTTON_SKIP', language),
                callback_data=skip_callback
            )
        ])

    # Add Cancel button
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )
    ])

    return InlineKeyboardMarkup(keyboard)



def build_category_selection_keyboard(
    current_category: str | None = None, 
    language: str = 'en',
    skip_callback: str | None = None
) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit category selection.

    Args:
        current_category: Current category value (will be highlighted with ✓)
        language: Language code (reserved for future use)
        skip_callback: If provided, adds a Skip button with this callback data

    Returns:
        InlineKeyboardMarkup with category buttons
    """
    from src.config import HABIT_CATEGORIES

    keyboard = []

    for category_id, category_display in HABIT_CATEGORIES:
        # Highlight current category with checkmark
        button_text = f"✓ {category_display}" if current_category == category_id else category_display
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"category_{category_id}"
        )
        keyboard.append([button])

    # Add Skip button if requested
    if skip_callback:
        keyboard.append([
            InlineKeyboardButton(
                text=msg('BUTTON_SKIP', language),
                callback_data=skip_callback
            )
        ])

    # Add Cancel button
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )
    ])

    return InlineKeyboardMarkup(keyboard)



def build_habits_for_edit_keyboard(habits: list[Habit], operation: str, language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit selection in edit/remove operations.

    Args:
        habits: List of Habit objects to display
        operation: 'edit' or 'remove' - determines callback_data prefix
        language: Language code for translating Back button text

    Returns:
        InlineKeyboardMarkup with habit buttons and Back button
    """
    keyboard = []

    for habit in habits:
        # Display format: "Habit Name" (no category)
        display_text = habit.name

        callback_prefix = "edit_habit" if operation == "edit" else "remove_habit"
        button = InlineKeyboardButton(
            text=display_text,
            callback_data=f"{callback_prefix}_{habit.id}"
        )
        keyboard.append([button])

    # Add Back button to return to habits menu
    callback_back = "edit_back" if operation == "edit" else "remove_back"
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data=callback_back
        )
    ])

    return InlineKeyboardMarkup(keyboard)



def build_post_create_habit_keyboard(habits: list[Habit], language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard to show after creating a habit.

    Shows the list of all habits with action buttons.

    Args:
        habits: List of all active Habit objects (including newly created one)
        language: Language code for translating button text

    Returns:
        InlineKeyboardMarkup with habit list display and action buttons
    """
    keyboard = []

    # Display all habits (non-clickable, just for display) - no category
    for habit in habits:
        display_text = f"• {habit.name}"
        # Use a dummy callback to make it non-interactive
        button = InlineKeyboardButton(
            text=display_text,
            callback_data=f"view_habit_{habit.id}"
        )
        keyboard.append([button])

    # Add action buttons
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Add Another",
            callback_data="post_create_add_another"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            text="✏️ Edit Habit",
            callback_data="menu_habits_edit"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back_habits"
        )
    ])

    return InlineKeyboardMarkup(keyboard)



def build_cancel_only_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard with only a Cancel button.

    Used for text input steps in habit flows where users type responses.

    Args:
        language: Language code for translating Cancel button

    Returns:
        InlineKeyboardMarkup with Cancel button only
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_skip_cancel_keyboard(language: str = 'en', skip_callback: str = 'skip_step') -> InlineKeyboardMarkup:
    """
    Build inline keyboard with Skip and Cancel buttons.

    Used for text input steps in habit edit flow.

    Args:
        language: Language code for translating buttons
        skip_callback: Callback data for the Skip button

    Returns:
        InlineKeyboardMarkup with Skip and Cancel buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data=skip_callback
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_cancel_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard with Cancel button for reward flows."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_reward_type_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard for selecting reward type (virtual or real only)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text=msg('BUTTON_REWARD_TYPE_VIRTUAL', language),
                callback_data="reward_type_virtual"
            ),
            InlineKeyboardButton(
                text=msg('BUTTON_REWARD_TYPE_REAL', language),
                callback_data="reward_type_real"
            )
        ],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_reward_weight_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard with quick weight options for reward creation."""
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for idx, weight in enumerate(range(10, 101, 10), start=1):
        row.append(InlineKeyboardButton(
            text=str(weight),
            callback_data=f"reward_weight_{weight}"
        ))
        if idx % 3 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )
    ])

    return InlineKeyboardMarkup(keyboard)



def build_reward_pieces_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard for pieces required with quick option for non-accumulative rewards."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_PIECES_NOT_ACCUMULATIVE', language),
            callback_data="reward_pieces_1"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_recurring_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard for recurring reward selection (Yes/No)."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_RECURRING_YES', language),
            callback_data="reward_recurring_yes"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_RECURRING_NO', language),
            callback_data="reward_recurring_no"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_recurring_keyboard(
    *,
    current_is_recurring: bool | None = None,
    language: str = 'en',
) -> InlineKeyboardMarkup:
    """Build inline keyboard for recurring selection during reward edit (with Skip/Cancel)."""
    yes_text = msg('BUTTON_RECURRING_YES', language)
    no_text = msg('BUTTON_RECURRING_NO', language)
    if current_is_recurring is True:
        yes_text = f"✓ {yes_text}"
    elif current_is_recurring is False:
        no_text = f"✓ {no_text}"

    keyboard = [
        [InlineKeyboardButton(
            text=yes_text,
            callback_data="reward_recurring_yes"
        )],
        [InlineKeyboardButton(
            text=no_text,
            callback_data="reward_recurring_no"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data="reward_edit_recurring_skip"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_piece_value_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard for optional piece value with skip/cancel buttons."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data="reward_value_skip"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_reward_confirmation_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard for confirming reward creation."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_CONFIRM', language),
            callback_data="reward_confirm_save"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_EDIT_REWARD', language),
            callback_data="reward_confirm_edit"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_reward_post_create_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """Build inline keyboard shown after reward creation."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_ADD_ANOTHER_REWARD', language),
            callback_data="reward_add_another"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_BACK_TO_REWARDS', language),
            callback_data="reward_back_to_rewards"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_habit_confirmation_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for habit confirmation (Yes/No/Cancel).

    Args:
        language: Language code for translating Cancel button

    Returns:
        InlineKeyboardMarkup with Yes/No/Cancel buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_YES', language),
            callback_data="confirm_yes"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_NO', language),
            callback_data="confirm_no"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_start_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for the main start menu.

    Layout:
    [Habit Done]
    [Habits, Rewards]
    [Streaks, Settings]
    [Help, Close]
    """
    keyboard = [
        [InlineKeyboardButton(text=msg('BUTTON_HABIT_DONE', language), callback_data="menu_habit_done")],
        [
            InlineKeyboardButton(text=msg('BUTTON_HABITS', language), callback_data="menu_habits"),
            InlineKeyboardButton(text=msg('BUTTON_REWARDS', language), callback_data="menu_rewards")
        ],
        [
            InlineKeyboardButton(text=msg('BUTTON_ADD_HABIT', language), callback_data="menu_habits_add"),
            InlineKeyboardButton(text=msg('BUTTON_LIST_REWARDS', language), callback_data="menu_rewards_list")
        ],
        [
            InlineKeyboardButton(text=msg('BUTTON_STREAKS', language), callback_data="menu_streaks"),
            InlineKeyboardButton(text=msg('BUTTON_SETTINGS', language), callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton(text=msg('BUTTON_HELP', language), callback_data="menu_help"),
            InlineKeyboardButton(text=msg('MENU_CLOSE', language), callback_data="menu_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_habits_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for the habits submenu.
    """
    keyboard = [
        [InlineKeyboardButton(text=msg('BUTTON_ADD_HABIT', language), callback_data="menu_habits_add")],
        [InlineKeyboardButton(text=msg('BUTTON_EDIT_HABIT', language), callback_data="menu_habits_edit")],
        [InlineKeyboardButton(text=msg('BUTTON_REMOVE_HABIT', language), callback_data="menu_habits_remove")],
        [InlineKeyboardButton(text=msg('BUTTON_REVERT_HABIT', language), callback_data="menu_habits_revert")],
        [InlineKeyboardButton(text=msg('BUTTON_HABIT_DONE_DATE', language), callback_data="menu_habit_done_date")],
        [InlineKeyboardButton(text=msg('MENU_BACK', language), callback_data="menu_back_start")]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_rewards_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for the rewards submenu.
    """
    keyboard = [
        [InlineKeyboardButton(text=msg('BUTTON_ADD_REWARD', language), callback_data="menu_rewards_add")],
        [InlineKeyboardButton(text=msg('BUTTON_EDIT_REWARD_MENU', language), callback_data="menu_rewards_edit")],
        [InlineKeyboardButton(text=msg('BUTTON_TOGGLE_REWARD', language), callback_data="menu_reward_toggle")],
        [InlineKeyboardButton(text=msg('BUTTON_LIST_REWARDS', language), callback_data="menu_rewards_list")],
        [InlineKeyboardButton(text=msg('BUTTON_MY_REWARDS', language), callback_data="menu_rewards_my")],
        [InlineKeyboardButton(text=msg('BUTTON_CLAIM_REWARD', language), callback_data="menu_rewards_claim")],
        [InlineKeyboardButton(text=msg('MENU_BACK', language), callback_data="menu_back_start")]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_rewards_for_edit_keyboard(
    rewards: list[Reward],
    language: str = "en",
) -> InlineKeyboardMarkup:
    """Build inline keyboard for selecting a reward to edit."""
    keyboard: list[list[InlineKeyboardButton]] = []

    for reward in rewards:
        keyboard.append([
            InlineKeyboardButton(
                text=reward.name,
                callback_data=f"edit_reward_{reward.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="reward_edit_back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_rewards_for_toggle_keyboard(
    rewards: list[Reward],
    language: str = "en",
) -> InlineKeyboardMarkup:
    """Build inline keyboard for selecting a reward to activate/deactivate.

    Shows ALL rewards (both active and inactive) with status indicators.
    Format: "{status_emoji} {name} ({recurring_indicator})"
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    for reward in rewards:
        # Status emoji: ✅ for active, ❌ for inactive
        status_emoji = "✅" if reward.active else "❌"

        # Recurring indicator: 🔄 for recurring, 🔒 for non-recurring
        recurring_emoji = "🔄" if reward.is_recurring else "🔒"

        # Format: "✅ Reward Name (🔄)"
        display_text = f"{status_emoji} {reward.name} ({recurring_emoji})"

        keyboard.append([
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"toggle_reward_{reward.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="reward_toggle_back"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_reward_skip_cancel_keyboard(
    language: str = "en",
    skip_callback: str = "reward_edit_skip",
) -> InlineKeyboardMarkup:
    """Build inline keyboard with Skip and Cancel buttons for reward edit flow."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data=skip_callback
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_type_keyboard(
    current_type: str | None = None,
    language: str = "en",
) -> InlineKeyboardMarkup:
    """Build type selection keyboard for reward edit flow (virtual or real only, with Skip/Cancel)."""
    def _label(type_key: str, base_key: str) -> str:
        text = msg(base_key, language)
        return f"✓ {text}" if current_type == type_key else text

    keyboard = [
        [
            InlineKeyboardButton(
                text=_label("virtual", "BUTTON_REWARD_TYPE_VIRTUAL"),
                callback_data="edit_reward_type_virtual"
            ),
            InlineKeyboardButton(
                text=_label("real", "BUTTON_REWARD_TYPE_REAL"),
                callback_data="edit_reward_type_real"
            )
        ],
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data="edit_reward_type_skip"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_weight_keyboard(
    current_weight: float | None = None,
    language: str = "en",
) -> InlineKeyboardMarkup:
    """Build weight selection keyboard for reward edit flow (with Skip/Cancel)."""
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    # Quick options 10..100 (like create flow)
    for idx, weight in enumerate(range(10, 101, 10), start=1):
        is_current = False
        if current_weight is not None:
            try:
                is_current = float(current_weight) == float(weight)
            except Exception:
                is_current = False
        text = f"✓ {weight}" if is_current else str(weight)
        row.append(InlineKeyboardButton(text=text, callback_data=f"edit_reward_weight_{weight}"))
        if idx % 3 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text=msg('BUTTON_SKIP', language), callback_data="edit_reward_weight_skip")
    ])
    keyboard.append([
        InlineKeyboardButton(text=msg('MENU_CANCEL', language), callback_data="cancel_reward_flow")
    ])

    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_pieces_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    """Build pieces selection keyboard for reward edit flow (quick 1 + Skip/Cancel)."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_PIECES_NOT_ACCUMULATIVE', language),
            callback_data="edit_reward_pieces_1"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data="edit_reward_pieces_skip"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_piece_value_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    """Build piece value keyboard for reward edit flow (Skip/Clear/Cancel)."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_SKIP', language),
            callback_data="edit_reward_value_skip"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_CLEAR', language),
            callback_data="edit_reward_value_clear"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_reward_edit_confirm_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    """Build confirmation keyboard for reward edit flow."""
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_YES', language),
            callback_data="reward_edit_confirm_yes"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_NO', language),
            callback_data="reward_edit_confirm_no"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_reward_flow"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)



def build_remove_confirmation_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for remove confirmation with Back.
    """
    keyboard = [
        [InlineKeyboardButton(text=msg('BUTTON_YES', language), callback_data="confirm_yes")],
        [InlineKeyboardButton(text=msg('BUTTON_NO', language), callback_data="confirm_no")],
        [InlineKeyboardButton(text=msg('MENU_BACK', language), callback_data="remove_back_to_list")]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_no_habits_to_edit_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard for when no habits exist to edit.

    Offers option to add a new habit or go back to habits menu.

    Args:
        language: User's language preference

    Returns:
        InlineKeyboardMarkup with Add Habit and Back buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_ADD_HABIT', language),
            callback_data="edit_add_habit"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="edit_back"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)



def build_back_to_menu_keyboard(language: str = 'en') -> InlineKeyboardMarkup:
    """
    Build inline keyboard with only a Back button to return to main menu.

    This keyboard is used for command outputs (help, streaks, etc.) to allow
    users to navigate back to the start menu by editing the message in-place.

    Args:
        language: User's language preference

    Returns:
        InlineKeyboardMarkup with single Back button
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_grace_days_keyboard(
    current_grace_days: int | None = None, 
    language: str = 'en',
    skip_callback: str | None = None
) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for grace days selection (0, 1, 2, 3).

    Args:
        current_grace_days: Current grace days value (will be highlighted with ✓)
        language: Language code for translating Cancel button
        skip_callback: If provided, adds a Skip button with this callback data

    Returns:
        InlineKeyboardMarkup with grace days buttons
    """
    keyboard = []

    # Create buttons for grace days (0-3)
    row = []
    for days in range(0, 4):
        # Highlight current value with checkmark
        button_text = f"✓ {days}" if current_grace_days == days else str(days)
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"grace_days_{days}"
        )
        row.append(button)

    keyboard.append(row)

    # Add Skip button if requested
    if skip_callback:
        keyboard.append([
            InlineKeyboardButton(
                text=msg('BUTTON_SKIP', language),
                callback_data=skip_callback
            )
        ])

    # Add Cancel button
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_exempt_days_keyboard(
    current_exempt_days: list[int] | None = None, 
    language: str = 'en',
    skip_callback: str | None = None
) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for exempt days selection (None, Weekends, Custom).

    Args:
        current_exempt_days: Current exempt days list (will be highlighted with ✓)
        language: Language code for translating Cancel button
        skip_callback: If provided, adds a Skip button with this callback data

    Returns:
        InlineKeyboardMarkup with exempt days buttons
    """
    keyboard = []

    # Determine if current setting is None (empty list), Weekends (6,7), or Custom
    current_is_none = not current_exempt_days or len(current_exempt_days) == 0
    current_is_weekends = current_exempt_days and sorted(current_exempt_days) == [6, 7]

    # None option
    button_text = f"✓ {msg('BUTTON_EXEMPT_NONE', language)}" if current_is_none else msg('BUTTON_EXEMPT_NONE', language)
    keyboard.append([
        InlineKeyboardButton(
            text=button_text,
            callback_data="exempt_days_none"
        )
    ])

    # Weekends option (Saturday=6, Sunday=7)
    button_text = f"✓ {msg('BUTTON_EXEMPT_WEEKENDS', language)}" if current_is_weekends else msg('BUTTON_EXEMPT_WEEKENDS', language)
    keyboard.append([
        InlineKeyboardButton(
            text=button_text,
            callback_data="exempt_days_weekends"
        )
    ])

    # Add Skip button if requested
    if skip_callback:
        keyboard.append([
            InlineKeyboardButton(
                text=msg('BUTTON_SKIP', language),
                callback_data=skip_callback
            )
        ])

    # Add Cancel button
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_CANCEL', language),
            callback_data="cancel_habit_flow"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_completion_date_options_keyboard(
    habit_id: int | str,
    language: str = 'en'
) -> InlineKeyboardMarkup:
    """Build keyboard with Today/Yesterday/Select Date options.

    Args:
        habit_id: Habit primary key
        language: Language code for translating button text

    Returns:
        InlineKeyboardMarkup with date selection options
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_TODAY', language),
            callback_data=f"habit_{habit_id}_today"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_YESTERDAY', language),
            callback_data=f"habit_{habit_id}_yesterday"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_SELECT_DATE', language),
            callback_data=f"backdate_habit_{habit_id}"
        )],
        [InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="menu_back"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_date_picker_keyboard(
    habit_id: int | str,
    completed_dates: list,  # list[date]
    language: str = 'en'
) -> InlineKeyboardMarkup:
    """Build 8-day date picker showing which dates are already completed.

    Args:
        habit_id: Habit primary key
        completed_dates: List of dates that already have completions
        language: Language code for translating Back button

    Returns:
        InlineKeyboardMarkup with 8-day calendar (today + 7 days back) and back button
    """
    from datetime import date, timedelta

    keyboard = []
    today = date.today()

    # Build 8 days (today and 7 days back)
    dates = [today - timedelta(days=i) for i in range(8)]
    dates.reverse()  # Oldest to newest

    # Create rows of 4 buttons each
    row = []
    for target_date in dates:
        # Check if this date already has a completion
        is_completed = target_date in completed_dates

        # Format button text
        day_month = target_date.strftime("%b %d")  # e.g., "Nov 24"

        if is_completed:
            # Already completed - show checkmark, make it disabled/informational
            button_text = f"{day_month} ✓"
            callback_data = f"backdate_date_completed_{habit_id}_{target_date.isoformat()}"
        else:
            # Available for logging
            button_text = day_month
            callback_data = f"backdate_date_{habit_id}_{target_date.isoformat()}"

        button = InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        )
        row.append(button)

        # Create rows of 4 buttons
        if len(row) == 4:
            keyboard.append(row)
            row = []

    # Add remaining buttons
    if row:
        keyboard.append(row)

    # Add Back button
    keyboard.append([
        InlineKeyboardButton(
            text=msg('MENU_BACK', language),
            callback_data="backdate_cancel"
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_backdate_confirmation_keyboard(
    habit_id: int | str,
    target_date,  # date
    language: str = 'en'
) -> InlineKeyboardMarkup:
    """Build confirmation keyboard for backdated completion.

    Args:
        habit_id: Habit primary key
        target_date: The date to backdate to
        language: Language code for translating buttons

    Returns:
        InlineKeyboardMarkup with Confirm/Cancel buttons
    """
    keyboard = [
        [InlineKeyboardButton(
            text=msg('BUTTON_YES', language),
            callback_data=f"backdate_confirm_{habit_id}_{target_date.isoformat()}"
        )],
        [InlineKeyboardButton(
            text=msg('BUTTON_NO', language),
            callback_data="backdate_cancel"
        )]
    ]
    return InlineKeyboardMarkup(keyboard)
