"""Centralized message management with multi-lingual support.

This module provides a Django-compatible approach to message management that will
allow easy migration to Django's gettext i18n framework in the future.
"""

from src.config import settings


class Messages:
    """Message constants with multi-lingual support."""

    # Error Messages - User Validation
    ERROR_USER_NOT_FOUND = "❌ User not found. Please contact admin to register."
    ERROR_USER_INACTIVE = "❌ Your account is not active. Please contact admin."

    # Error Messages - Entity Not Found
    ERROR_NO_HABITS = "No active habits found. Please add habits first."
    ERROR_NO_HABITS_LOGGED = "No habits logged yet. Use /habit_done to start building your streaks!"
    ERROR_HABIT_NOT_FOUND = "Habit not found. Please try again."
    ERROR_NO_LOG_TO_REVERT = "No habit completion found to revert."
    ERROR_REWARD_NOT_FOUND = "Reward '{reward_name}' not found."
    ERROR_NO_MATCH_HABIT = "I couldn't match your text to any known habit. Please select from the list using /habit_done again."

    # Error Messages - Validation
    ERROR_INVALID_STATUS = "Invalid status. Use: pending, achieved, or completed"
    ERROR_GENERAL = "Error: {error}"

    # Info Messages
    INFO_NO_REWARD_PROGRESS = "No reward progress yet. Keep completing habits!"
    INFO_NO_REWARD = "❌ No reward this time - keep going!"
    INFO_REWARD_ACTIONABLE = "⏳ <b>Reward achieved!</b> You can claim it now!"
    INFO_FEATURE_COMING_SOON = "🎁 <b>Add New Reward</b>\n\nThis feature will guide you through creating a new reward.\nFor now, please add rewards directly in Airtable.\n\nComing soon: conversational reward creation!"
    INFO_CANCELLED = "Habit logging cancelled."
    INFO_CANCELLED_REVERT = "Revert cancelled."
    INFO_MULTIPLE_HABITS = "I also detected: {other_habits}. Use /habit_done to log those separately."
    INFO_NO_REWARDS_TO_CLAIM = "You have no rewards ready to claim yet. Keep logging habits to earn rewards!"
    INFO_ALL_HABITS_COMPLETED = "🎉 All active habits are already completed for today. Check back tomorrow!"

    # Auth Code (external API login) Messages
    AUTH_CODE_LOGIN_CODE = "🔐 <b>Login Code:</b> <code>{code}</code>"
    AUTH_CODE_DEVICE = "📱 Device: {device}"
    AUTH_CODE_EXPIRES = "⏱ Expires in 5 minutes"
    AUTH_CODE_WARNING_1 = "⚠️ If you didn't request this code, ignore this message."
    AUTH_CODE_WARNING_2 = "Someone may be trying to access your account."

    # Usage/Help Messages
    HELP_CLAIM_REWARD_USAGE = "Usage: /claim_reward <reward_name>\nExample: /claim_reward Coffee at favorite cafe"
    HELP_HABIT_SELECTION = "Which habit did you complete? 🎯\n\nSelect from the list below:"
    HELP_SIMPLE_HABIT_SELECTION = "Which habit did you complete today? 🎯"
    HELP_CUSTOM_TEXT = "Please type what habit you completed:"
    HELP_REVERT_HABIT_SELECTION = "Which habit completion would you like to revert?"
    HELP_SELECT_REWARD_TO_CLAIM = "🎁 <b>Select a reward to claim:</b>"

    # Success Messages
    SUCCESS_HABIT_COMPLETED = "✅ <b>Habit completed:</b> {habit_name}"
    SUCCESS_REWARD_CLAIMED = "✅ Reward claimed: <b>{reward_name}</b>\nStatus: {status}\n\nCongratulations! 🎉"
    SUCCESS_STATUS_UPDATED = "✅ Reward status updated: <b>{reward_name}</b>\nNew status: {status}"
    SUCCESS_HABIT_REVERTED = "✅ <b>Habit completion reverted:</b> {habit_name}"
    SUCCESS_REWARD_REVERTED = "Reward progress rolled back: {reward_name} ({pieces_earned}/{pieces_required})"
    SUCCESS_REWARD_CLAIMED_HEADER = "✅ <b>Reward claimed:</b> {reward_name}"

    # Headers/Titles
    HEADER_REWARD_PROGRESS = "🎁 <b>Your Reward Progress:</b>\n"
    HEADER_STREAKS = "🔥 <b>Your Current Streaks:</b>\n"
    HEADER_REWARDS_LIST = "🎁 <b>Available Rewards:</b>\n"
    HEADER_HABIT_LOGS = "📋 <b>Recent Habit Completions:</b>\n"
    HEADER_UPDATED_REWARD_PROGRESS = "\n📊 <b>Your updated reward progress:</b>"

    # Start/Menu Titles and Buttons
    START_MENU_TITLE = "🏠 <b>Main Menu</b>\nSelect an option:"
    HABITS_MENU_TITLE = "🧩 <b>Habits</b>\nChoose an action:"
    REWARDS_MENU_TITLE = "🎁 <b>Rewards</b>\nChoose an action:"
    MENU_BACK = "« Back"
    MENU_CANCEL = "✖ Cancel"
    MENU_CLOSE = "✖ Close"
    MENU_CLOSED = "Menu closed. Use /start to open again."
    BUTTON_HABIT_DONE = "✅ Habit Done"
    BUTTON_HABIT_DONE_DATE = "📅 Habit Done for Date"
    BUTTON_HABITS = "🧩 Habits"
    BUTTON_REWARDS = "🎁 Rewards"
    BUTTON_STREAKS = "🔥 Streaks"
    BUTTON_SETTINGS = "⚙️ Settings"
    BUTTON_HELP = "❓ Help"
    BUTTON_ADD_HABIT = "➕ Add Habit"
    BUTTON_EDIT_HABIT = "✏️ Edit Habit"
    BUTTON_REMOVE_HABIT = "🗑 Remove Habit"
    BUTTON_REVERT_HABIT = "↩️ Revert Habit"
    BUTTON_ADD_REWARD = "➕ Add Reward"
    BUTTON_EDIT_REWARD_MENU = "✏️ Edit Reward"
    BUTTON_TOGGLE_REWARD = "🔄 Activate/Deactivate Reward"
    BUTTON_LIST_REWARDS = "📄 List Rewards"
    BUTTON_MY_REWARDS = "📊 My Rewards"
    BUTTON_CLAIM_REWARD = "🎯 Claim Reward"
    BUTTON_YES = "✅ Yes"
    BUTTON_NO = "❌ No"
    BUTTON_EXEMPT_NONE = "None"
    BUTTON_EXEMPT_WEEKENDS = "Weekends (Sat/Sun)"

    # Welcome/Help Messages
    HELP_START_MESSAGE = """🎯 <b>Welcome to Habit Reward System!</b>

Track your habits and earn rewards!

<b>Available commands:</b>
/habit_done - Log a completed habit
/add_habit - Create a new habit
/edit_habit - Modify an existing habit
/remove_habit - Remove a habit
/streaks - View your current streaks
/list_rewards - See all available rewards
/my_rewards - Check your reward progress
/claim_reward - Claim an achieved reward
/revert_habit - Revert the last completion of a habit
/settings - Change language and preferences
/help - Show this help message"""

    HELP_COMMAND_MESSAGE = """🎯 <b>Habit Reward System Help</b>

<b>Core Commands:</b>
/habit_done - Log a habit completion and earn rewards
/backdate - Log habits for past dates (up to 7 days back)
/streaks - View your current streaks for all habits

<b>Habit Management:</b>
/add_habit - Create a new habit
/edit_habit - Modify an existing habit
/remove_habit - Remove a habit (soft delete)

<b>Reward Commands:</b>
/list_rewards - List all available rewards
/my_rewards - View your cumulative reward progress
/claim_reward - Mark an achieved reward as completed
/revert_habit - Revert the last completion of a habit

<b>Settings:</b>
/settings - Change language and preferences

<b>How it works:</b>
1. Create habits using /add_habit or manage existing ones
2. Complete habits using /habit_done
3. Build streaks by completing habits daily
4. Earn reward pieces (cumulative rewards)
5. Claim rewards when you have enough pieces

Your streak multiplier increases your chances of getting rewards!"""

    # Formatter Messages
    FORMAT_STREAK = "<b>Streak:</b> {streak_count} days"
    FORMAT_REWARD = "🎁 <b>Reward:</b> {reward_name}"
    FORMAT_PROGRESS = "📊 Progress: {progress_bar} {pieces_earned}/{pieces_required}"
    FORMAT_STATUS = "Status: {status}"
    FORMAT_READY_TO_CLAIM = "⏳ <b>Ready to claim!</b>"
    FORMAT_NO_REWARDS_YET = "No rewards configured yet."
    FORMAT_NO_STREAKS = "No habits logged yet. Start building your streaks!"
    FORMAT_NO_LOGS = "No habit logs found."

    # Habit Management Messages
    HELP_ADD_HABIT_NAME_PROMPT = "Please enter the name for your new habit:"
    HELP_ADD_HABIT_WEIGHT_PROMPT = "Select the weight for this habit (1-100). Weight affects reward chances:"
    HELP_ADD_HABIT_CATEGORY_PROMPT = "Select a category for this habit:"
    HELP_ADD_HABIT_GRACE_DAYS_PROMPT = "How many grace days for this habit?\n\n<b>Grace days</b> allow you to skip days without breaking your streak.\n\nExample: With 1 grace day, you can miss one day and still maintain your streak."
    HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT = "Select days that don't count against your streak:\n\n<b>Exempt days</b> are days of the week (like weekends) that won't break your streak if you don't complete the habit."
    HELP_EXEMPT_DAYS_OR_MANUAL = "\n\n• Select an option below OR\n• <b>Type numbers manually</b> (e.g., <code>2, 4</code> for Tue/Thu)"
    HELP_EXEMPT_DAYS_MANUAL_ENTRY = (
        "<b>Enter exempt days as numbers separated by commas.</b>\n\n"
        "1 = Monday\n2 = Tuesday\n3 = Wednesday\n4 = Thursday\n"
        "5 = Friday\n6 = Saturday\n7 = Sunday\n\n"
        "Example: <code>2, 4</code> for Tuesday and Thursday."
    )
    ERROR_EXEMPT_DAYS_INVALID_FORMAT = (
        "⚠️ <b>Invalid format.</b>\n"
        "Please enter numbers 1-7 separated by commas (1=Mon, 7=Sun).\n"
        "Example: <code>2, 4</code> for Tuesday and Thursday."
    )
    HELP_ADD_HABIT_CONFIRM = "Review your new habit:\n<b>Name:</b> {name}\n<b>Weight:</b> {weight}\n<b>Grace Days:</b> {grace_days}\n<b>Exempt Days:</b> {exempt_days}\n\nCreate this habit?"
    SUCCESS_HABIT_CREATED = "✅ Habit '<b>{name}</b>' created successfully!"
    HELP_HABIT_CREATED_NEXT = "🧩 <b>Your habits:</b>"
    ERROR_HABIT_NAME_TOO_LONG = "❌ Habit name is too long (max 100 characters)."
    ERROR_HABIT_NAME_EMPTY = "❌ Habit name cannot be empty."
    ERROR_HABIT_NAME_EXISTS = "❌ You already have a habit named '<b>{name}</b>'.\n\nPlease choose a different name:"
    ERROR_WEIGHT_INVALID = "❌ Invalid weight. Please select a value between 1-100."
    HELP_EDIT_HABIT_SELECT = "Select a habit to edit:"
    HELP_EDIT_HABIT_NAME_PROMPT = "Current name: <b>{current_name}</b>\n\nEnter new name:"
    HELP_EDIT_HABIT_WEIGHT_PROMPT = "Current weight: <b>{current_weight}</b>\n\nSelect new weight:"
    HELP_EDIT_HABIT_CATEGORY_PROMPT = "Current category: <b>{current_category}</b>\n\nSelect new category:"
    HELP_EDIT_HABIT_GRACE_DAYS_PROMPT = "Current grace days: <b>{current_grace_days}</b>\n\nSelect new grace days:"
    HELP_EDIT_HABIT_EXEMPT_DAYS_PROMPT = "Current exempt days: <b>{current_exempt_days}</b>\n\nSelect new exempt days:"
    HELP_EDIT_HABIT_CONFIRM = "Review changes:\n<b>Name:</b> {old_name} → {new_name}\n<b>Weight:</b> {old_weight} → {new_weight}\n<b>Grace Days:</b> {old_grace_days} → {new_grace_days}\n<b>Exempt Days:</b> {old_exempt_days} → {new_exempt_days}\n\nSave changes?"
    SUCCESS_HABIT_UPDATED = "✅ Habit '<b>{name}</b>' updated successfully!"
    HELP_REMOVE_HABIT_SELECT = "Select a habit to remove:"
    HELP_REMOVE_HABIT_CONFIRM = "Are you sure you want to remove '<b>{name}</b>'?\n\n⚠️ This will deactivate the habit. Your history will be preserved."
    SUCCESS_HABIT_REMOVED = "✅ Habit '<b>{name}</b>' removed successfully."
    ERROR_NO_HABITS_TO_EDIT = "❌ You don't have any habits to edit."
    ERROR_NO_HABITS_TO_EDIT_PROMPT = "❌ You don't have any habits to edit.\n\nWould you like to add a new habit?"
    ERROR_NO_HABITS_TO_REMOVE = "❌ You don't have any habits to remove."
    INFO_HABIT_CANCEL = "❌ Habit operation cancelled."

    # Backdate Messages
    HELP_BACKDATE_SELECT_HABIT = "📅 Which habit would you like to log for a past date?"
    HELP_BACKDATE_SELECT_DATE = "📆 Select the date you completed <b>{habit_name}</b>:\n\n✓ = already logged"
    HELP_BACKDATE_CONFIRM = "Log <b>{habit_name}</b> for <b>{date}</b>?"
    HELP_SELECT_COMPLETION_DATE = "When did you complete <b>{habit_name}</b>?"
    SUCCESS_BACKDATE_COMPLETED = "✅ <b>Habit logged:</b> {habit_name}\n📅 <b>Date:</b> {date}"
    ERROR_BACKDATE_DUPLICATE = "❌ You already logged <b>{habit_name}</b> on {date}."
    ERROR_BACKDATE_TOO_OLD = "❌ Cannot backdate more than 7 days."
    ERROR_BACKDATE_FUTURE = "❌ Cannot log habits for future dates."
    ERROR_BACKDATE_BEFORE_CREATED = "❌ Cannot backdate before habit was created ({date})."
    BUTTON_TODAY = "✅ Today"
    BUTTON_YESTERDAY = "📅 Yesterday"
    BUTTON_SELECT_DATE = "📆 Select Different Date"

    # Reward Management Messages
    HELP_ADD_REWARD_NAME_PROMPT = "Please enter a name for your new reward:"
    ERROR_REWARD_NAME_EMPTY = "❌ Reward name cannot be empty."
    ERROR_REWARD_NAME_TOO_LONG = "❌ Reward name is too long (max 255 characters)."
    ERROR_REWARD_NAME_EXISTS = "❌ A reward with this name already exists. Please choose a different name."
    HELP_ADD_REWARD_TYPE_PROMPT = "Select a reward type:"
    BUTTON_REWARD_TYPE_VIRTUAL = "🖥 Virtual"
    BUTTON_REWARD_TYPE_REAL = "🎁 Real"
    HELP_ADD_REWARD_WEIGHT_PROMPT = "Enter the weight for this reward (higher is more likely) or pick a quick option below:"
    ERROR_REWARD_WEIGHT_INVALID = "❌ Invalid weight. Enter a number between {min} and {max}."
    HELP_ADD_REWARD_PIECES_PROMPT = "Enter how many pieces are required to claim this reward:"
    ERROR_REWARD_PIECES_INVALID = "❌ Pieces required must be a whole number greater than 0."
    HELP_ADD_REWARD_PIECE_VALUE_PROMPT = "Enter the value of each piece (e.g., 0.50) or tap Skip if it has no monetary value:"
    ERROR_REWARD_PIECE_VALUE_INVALID = "❌ Piece value must be a non-negative number."
    HELP_ADD_REWARD_CONFIRM = (
        "Review your new reward:\n"
        "<b>Name:</b> {name}\n"
        "<b>Type:</b> {type_label}\n"
        "<b>Weight:</b> {weight}\n"
        "<b>Pieces Required:</b> {pieces}\n"
        "<b>Recurring:</b> {recurring}\n\n"
        "Create this reward?"
    )
    SUCCESS_REWARD_CREATED = "✅ Reward '<b>{name}</b>' created successfully!"
    INFO_REWARD_CANCEL = "❌ Reward creation cancelled."
    BUTTON_ADD_ANOTHER_REWARD = "➕ Add Another Reward"
    BUTTON_BACK_TO_REWARDS = "🎁 Back to Rewards"
    BUTTON_SKIP = "⏭ Skip"
    BUTTON_CLEAR = "🧹 Clear"
    BUTTON_CONFIRM = "✅ Create Reward"
    BUTTON_EDIT_REWARD = "✏️ Edit Details"
    BUTTON_PIECES_NOT_ACCUMULATIVE = "1 (Not accumulative)"
    TEXT_NOT_SET = "Not set"
    KEYWORD_SKIP = "skip"

    HELP_EDIT_REWARD_SELECT = "Select a reward to edit:"
    ERROR_NO_REWARDS_TO_EDIT = "❌ You don't have any rewards to edit."
    HELP_EDIT_REWARD_NAME_PROMPT = "Current name: <b>{current_name}</b>\n\nEnter new name:"
    HELP_EDIT_REWARD_TYPE_PROMPT = "Current type: <b>{current_type}</b>\n\nSelect new type:"
    HELP_EDIT_REWARD_WEIGHT_PROMPT = "Current weight: <b>{current_weight}</b>\n\nSelect a new weight (or type one):"
    HELP_EDIT_REWARD_PIECES_PROMPT = "Current pieces required: <b>{current_pieces}</b>\n\nEnter new pieces required:"
    HELP_EDIT_REWARD_PIECE_VALUE_PROMPT = (
        "Current piece value: <b>{current_value}</b>\n\n"
        "Enter new piece value, tap Clear to remove it, or Skip to keep current:"
    )
    HELP_EDIT_REWARD_CONFIRM = (
        "Review changes:\n"
        "<b>Name:</b> {old_name} → {new_name}\n"
        "<b>Type:</b> {old_type} → {new_type}\n"
        "<b>Weight:</b> {old_weight} → {new_weight}\n"
        "<b>Pieces Required:</b> {old_pieces} → {new_pieces}\n"
        "<b>Recurring:</b> {old_recurring} → {new_recurring}\n\n"
        "Save changes?"
    )
    SUCCESS_REWARD_UPDATED = "✅ Reward '<b>{name}</b>' updated successfully!"
    INFO_REWARD_EDIT_CANCEL = "❌ Reward editing cancelled."

    # Recurring Reward Messages
    HELP_ADD_REWARD_RECURRING_PROMPT = "Is this reward recurring (can be claimed multiple times)?"
    HELP_EDIT_REWARD_RECURRING_PROMPT = "Is this reward recurring? Current: <b>{current_value}</b>"
    BUTTON_RECURRING_YES = "🔄 Yes (can claim multiple times)"
    BUTTON_RECURRING_NO = "🔒 No (one-time only)"

    # Toggle Reward Active/Inactive Messages
    HELP_TOGGLE_REWARD_SELECT = "Select a reward to activate/deactivate:"
    SUCCESS_REWARD_ACTIVATED = "✅ Reward '<b>{name}</b>' is now active"
    SUCCESS_REWARD_DEACTIVATED = "❌ Reward '<b>{name}</b>' is now inactive"
    ERROR_NO_REWARDS_TO_TOGGLE = "You don't have any rewards to manage."
    INFO_REWARD_NON_RECURRING_DEACTIVATED = "This reward is non-recurring and has been deactivated. You can reactivate it manually from the Rewards menu if needed."

    # Reward Status Labels
    LABEL_REWARD_ACTIVE = "✅ Active"
    LABEL_REWARD_INACTIVE = "❌ Inactive"
    LABEL_REWARD_NON_RECURRING = "🔒 One-time"
    LABEL_REWARD_RECURRING = "🔄 Recurring"

    # Settings Menu
    SETTINGS_MENU = "⚙️ <b>Settings</b>\n\nSelect an option:"
    SETTINGS_SELECT_LANGUAGE = "🌐 Select Language"
    SETTINGS_API_KEYS = "🔑 API Keys"
    SETTINGS_NO_REWARD_PROB = "🎲 No Reward Probability"
    SETTINGS_BACK = "← Back to Settings"

    # No Reward Probability Settings
    NO_REWARD_PROB_MENU = "🎲 <b>No Reward Probability</b>\n\nCurrent: <b>{current}%</b>\n\nChoose a preset or enter a custom value (0.01-99.99):"
    NO_REWARD_PROB_CUSTOM = "✏️ Custom"
    NO_REWARD_PROB_ENTER_CUSTOM = "📝 <b>Enter custom probability</b>\n\nEnter a value between 0.01 and 99.99:"
    NO_REWARD_PROB_UPDATED = "✅ No reward probability updated to <b>{value}%</b>"
    NO_REWARD_PROB_INVALID = "❌ Invalid value. Please enter a number between 0.01 and 99.99."

    # Language Selection
    LANGUAGE_SELECTION_MENU = "🌐 <b>Select Language</b>\n\nChoose your preferred language:"

    # API Key Management
    API_KEY_MENU = "🔑 <b>API Keys</b>\n\nManage your API keys for external integrations (fitness apps, automations, etc.):"
    API_KEY_CREATE = "➕ Create New Key"
    API_KEY_LIST = "📋 List Keys"
    API_KEY_REVOKE = "❌ Revoke Key"
    API_KEY_ENTER_NAME = "📝 <b>Enter a name for your API key</b>\n\nExample: Fitness App, iOS Shortcut"
    API_KEY_CREATED = """✅ <b>API Key Created!</b>

<b>Name:</b> {name}
<b>Key:</b> <code>{key}</code>

⚠️ <b>IMPORTANT:</b> Copy this key now! You won't be able to see it again.

Use this key in your app with the header:
<code>X-API-Key: {key}</code>"""
    API_KEY_NAME_EXISTS = "❌ An API key with name '{name}' already exists. Please choose a different name."
    API_KEY_NAME_TOO_LONG = "❌ Key name is too long. Maximum 100 characters."
    API_KEY_NAME_EMPTY = "❌ Key name cannot be empty. Please enter a name."
    API_KEY_LIST_HEADER = "🔑 <b>Your API Keys:</b>\n"
    API_KEY_LIST_EMPTY = "📭 You don't have any API keys yet.\n\nCreate one to connect your apps!"
    API_KEY_CREATED_AT = "Created"
    API_KEY_LAST_USED = "Last used"
    API_KEY_NEVER_USED = "Never"
    API_KEY_SELECT_TO_REVOKE = "🔑 <b>Select a key to revoke:</b>"
    API_KEY_REVOKED = "✅ API key '<b>{name}</b>' has been revoked."
    API_KEY_REVOKE_FAILED = "❌ Failed to revoke API key. Please try again."
    BACK_TO_SETTINGS = "← Back to Settings"
    BACK = "← Back"

    # Translations dictionary for Phase 1
    _TRANSLATIONS = {
        'ru': {
            # Error Messages - User Validation
            'ERROR_USER_NOT_FOUND': "❌ Пользователь не найден. Обратитесь к администратору для регистрации.",
            'ERROR_USER_INACTIVE': "❌ Ваш аккаунт не активен. Обратитесь к администратору.",

            # Error Messages - Entity Not Found
            'ERROR_NO_HABITS': "Активные привычки не найдены. Сначала добавьте привычки.",
            'ERROR_NO_HABITS_LOGGED': "Привычки ещё не зарегистрированы. Используйте /habit_done для начала!",
            'ERROR_HABIT_NOT_FOUND': "Привычка не найдена. Попробуйте ещё раз.",
            'ERROR_NO_LOG_TO_REVERT': "Не найдено завершение привычки для отмены.",
            'ERROR_REWARD_NOT_FOUND': "Награда '{reward_name}' не найдена.",
            'ERROR_NO_MATCH_HABIT': "Не удалось сопоставить ваш текст с известной привычкой. Выберите из списка, используя /habit_done.",

            # Error Messages - Validation
            'ERROR_INVALID_STATUS': "Неверный статус. Используйте: pending, achieved или completed",
            'ERROR_GENERAL': "Ошибка: {error}",

            # Info Messages
            'INFO_NO_REWARD_PROGRESS': "Прогресс по наградам отсутствует. Продолжайте выполнять привычки!",
            'INFO_NO_REWARD': "❌ В этот раз награды нет - продолжайте!",
            'INFO_REWARD_ACTIONABLE': "⏳ <b>Награда достигнута!</b> Вы можете забрать её сейчас!",
            'INFO_FEATURE_COMING_SOON': "🎁 <b>Добавить новую награду</b>\n\nЭта функция проведёт вас через создание новой награды.\nПока что добавляйте награды в Airtable.\n\nСкоро: создание наград через бота!",
            'INFO_CANCELLED': "Регистрация привычки отменена.",
            'INFO_CANCELLED_REVERT': "Отмена операции отмены привычки.",
            'INFO_MULTIPLE_HABITS': "Также обнаружены: {other_habits}. Используйте /habit_done для их регистрации.",
            'INFO_NO_REWARDS_TO_CLAIM': "У вас пока нет наград для получения. Продолжайте регистрировать привычки, чтобы заработать награды!",
            'INFO_ALL_HABITS_COMPLETED': "🎉 Все активные привычки уже выполнены сегодня. Возвращайтесь завтра!",

            # Usage/Help Messages
            'HELP_CLAIM_REWARD_USAGE': "Использование: /claim_reward <название_награды>\nПример: /claim_reward Кофе в любимом кафе",
            'HELP_HABIT_SELECTION': "Какую привычку вы выполнили? 🎯\n\nВыберите из списка ниже:",
            'HELP_SIMPLE_HABIT_SELECTION': "Какую привычку вы выполнили сегодня? 🎯",
            'HELP_CUSTOM_TEXT': "Напишите, какую привычку вы выполнили:",
            'HELP_REVERT_HABIT_SELECTION': "Какое завершение привычки вы хотите отменить?",
            'HELP_SELECT_REWARD_TO_CLAIM': "🎁 <b>Выберите награду для получения:</b>",

            # Success Messages
            'SUCCESS_HABIT_COMPLETED': "✅ <b>Привычка выполнена:</b> {habit_name}",
            'SUCCESS_REWARD_CLAIMED': "✅ Награда получена: <b>{reward_name}</b>\nСтатус: {status}\n\nПоздравляем! 🎉",
            'SUCCESS_STATUS_UPDATED': "✅ Статус награды обновлён: <b>{reward_name}</b>\nНовый статус: {status}",
            'SUCCESS_HABIT_REVERTED': "✅ <b>Отмена завершения привычки:</b> {habit_name}",
            'SUCCESS_REWARD_REVERTED': "Прогресс по награде возвращён: {reward_name} ({pieces_earned}/{pieces_required})",
            'SUCCESS_REWARD_CLAIMED_HEADER': "✅ <b>Награда получена:</b> {reward_name}",

            # Headers/Titles
            'HEADER_REWARD_PROGRESS': "🎁 <b>Ваш прогресс по наградам:</b>\n",
            'HEADER_STREAKS': "🔥 <b>Ваши текущие серии:</b>\n",
            'HEADER_REWARDS_LIST': "🎁 <b>Доступные награды:</b>\n",
            'HEADER_HABIT_LOGS': "📋 <b>Недавние выполнения привычек:</b>\n",
            'HEADER_UPDATED_REWARD_PROGRESS': "\n📊 <b>Ваш обновлённый прогресс по наградам:</b>",

            # Start/Menu Titles and Buttons
            'START_MENU_TITLE': "🏠 <b>Главное меню</b>\nВыберите действие:",
            'HABITS_MENU_TITLE': "🧩 <b>Привычки</b>\nВыберите действие:",
            'REWARDS_MENU_TITLE': "🎁 <b>Награды</b>\nВыберите действие:",
            'MENU_BACK': "« Назад",
            'MENU_CANCEL': "✖ Отмена",
            'MENU_CLOSE': "✖ Закрыть",
            'MENU_CLOSED': "Меню закрыто. Используйте /start чтобы открыть снова.",
            'BUTTON_HABIT_DONE': "✅ Отметить привычку",
            'BUTTON_HABIT_DONE_DATE': "📅 Отметить за дату",
            'BUTTON_HABITS': "🧩 Привычки",
            'BUTTON_REWARDS': "🎁 Награды",
            'BUTTON_STREAKS': "🔥 Серии",
            'BUTTON_SETTINGS': "⚙️ Настройки",
            'BUTTON_HELP': "❓ Помощь",
            'BUTTON_ADD_HABIT': "➕ Добавить привычку",
            'BUTTON_EDIT_HABIT': "✏️ Изменить привычку",
            'BUTTON_REMOVE_HABИТ': "🗑 Удалить привычку",
            'BUTTON_REVERT_HABIT': "↩️ Отменить выполнение",
            'BUTTON_ADD_REWARD': "➕ Добавить награду",
            'BUTTON_EDIT_REWARD_MENU': "✏️ Изменить награду",
            'BUTTON_TOGGLE_REWARD': "🔄 Активировать/Деактивировать награду",
            'BUTTON_LIST_REWARDS': "📄 Список наград",
            'BUTTON_MY_REWARDS': "📊 Мои награды",
            'BUTTON_CLAIM_REWARD': "🎯 Получить награду",
            'BUTTON_YES': "✅ Да",
            'BUTTON_NO': "❌ Нет",
            'BUTTON_EXEMPT_NONE': "Нет",
            'BUTTON_EXEMPT_WEEKENDS': "Выходные (Сб/Вс)",

            # Welcome/Help Messages
            'HELP_START_MESSAGE': """🎯 <b>Добро пожаловать в систему наград за привычки!</b>

Отслеживайте привычки и получайте награды!

<b>Доступные команды:</b>
/habit_done - Зарегистрировать выполненную привычку
/add_habit - Создать новую привычку
/edit_habit - Изменить существующую привычку
/remove_habit - Удалить привычку
/streaks - Посмотреть текущие серии
/list_rewards - Посмотреть все доступные награды
/my_rewards - Проверить прогресс по наградам
/claim_reward - Забрать достигнутую награду
/revert_habit - Отменить последнее выполнение привычки
/settings - Изменить язык и настройки
/help - Показать это сообщение помощи""",

            'HELP_COMMAND_MESSAGE': """🎯 <b>Помощь по системе наград за привычки</b>

<b>Основные команды:</b>
/habit_done - Зарегистрировать выполнение привычки и получить награды
/backdate - Записать привычки за прошедшие дни (до 7 дней назад)
/streaks - Посмотреть текущие серии для всех привычек

<b>Управление привычками:</b>
/add_habit - Создать новую привычку
/edit_habit - Изменить существующую привычку
/remove_habit - Удалить привычку (мягкое удаление)

<b>Команды наград:</b>
/list_rewards - Показать все доступные награды
/my_rewards - Посмотреть накопленный прогресс по наградам
/claim_reward - Отметить достигнутую награду как завершённую
/revert_habit - Отменить последнее выполнение привычки

<b>Настройки:</b>
/settings - Изменить язык и настройки

<b>Как это работает:</b>
1. Создавайте привычки через /add_habit или управляйте существующими
2. Выполняйте привычки через /habit_done
3. Создавайте серии, выполняя привычки ежедневно
4. Зарабатывайте части наград (накопительные награды)
5. Забирайте награды, когда наберёте достаточно частей

Множитель серий увеличивает шансы получения наград!""",

            # Formatter Messages
            'FORMAT_STREAK': "<b>Серия:</b> {streak_count} дней",
            'FORMAT_REWARD': "🎁 <b>Награда:</b> {reward_name}",
            'FORMAT_PROGRESS': "📊 Прогресс: {progress_bar} {pieces_earned}/{pieces_required}",
            'FORMAT_STATUS': "Статус: {status}",
            'FORMAT_READY_TO_CLAIM': "⏳ <b>Готово к получению!</b>",
            'FORMAT_NO_REWARDS_YET': "Награды ещё не настроены.",
            'FORMAT_NO_STREAKS': "Привычки ещё не зарегистрированы. Начните создавать серии!",
            'FORMAT_NO_LOGS': "Записи о привычках не найдены.",

            # Habit Management Messages
            'HELP_ADD_HABIT_NAME_PROMPT': "Введите название для новой привычки:",
            'HELP_ADD_HABIT_WEIGHT_PROMPT': "Выберите вес для этой привычки (1-100). Вес влияет на шансы получения наград:",
            'HELP_ADD_HABIT_CATEGORY_PROMPT': "Выберите категорию для этой привычки:",
            'HELP_ADD_HABIT_GRACE_DAYS_PROMPT': "Сколько дней отсрочки (grace days) для этой привычки?\n\n<b>Дни отсрочки</b> позволяют пропускать дни без потери серии.\n\nПример: С 1 днём отсрочки вы можете пропустить один день и сохранить серию.",
            'HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT': "Выберите дни, которые не учитываются в серии:\n\n<b>Исключённые дни</b> — это дни недели (например, выходные), которые не прервут вашу серию, если вы не выполните привычку.",
            'HELP_EXEMPT_DAYS_OR_MANUAL': "\n\n• Выберите опцию ниже ИЛИ\n• <b>Введите номера вручную</b> (напр., <code>2, 4</code> для Вт/Чт)",
            'HELP_EXEMPT_DAYS_MANUAL_ENTRY': (
                "<b>Введите исключённые дни цифрами через запятую.</b>\n\n"
                "1 = Понедельник\n2 = Вторник\n3 = Среда\n4 = Четверг\n"
                "5 = Пятница\n6 = Суббота\n7 = Воскресенье\n\n"
                "Пример: <code>2, 4</code> для вторника и четверга."
            ),
            'ERROR_EXEMPT_DAYS_INVALID_FORMAT': (
                "⚠️ <b>Неверный формат.</b>\n"
                "Пожалуйста, введите цифры 1-7 через запятую (1=Пн, 7=Вс).\n"
                "Пример: <code>2, 4</code>"
            ),
            'HELP_ADD_HABIT_CONFIRM': "Проверьте вашу новую привычку:\n<b>Название:</b> {name}\n<b>Вес:</b> {weight}\n<b>Дни отсрочки:</b> {grace_days}\n<b>Исключённые дни:</b> {exempt_days}\n\nСоздать эту привычку?",
            'SUCCESS_HABIT_CREATED': "✅ Привычка '<b>{name}</b>' успешно создана!",
            'HELP_HABIT_CREATED_NEXT': "🧩 <b>Ваши привычки:</b>",
            'ERROR_HABIT_NAME_TOO_LONG': "❌ Название привычки слишком длинное (макс. 100 символов).",
            'ERROR_HABIT_NAME_EMPTY': "❌ Название привычки не может быть пустым.",
            'ERROR_WEIGHT_INVALID': "❌ Неверный вес. Выберите значение от 1 до 100.",
            'HELP_EDIT_HABIT_SELECT': "Выберите привычку для редактирования:",
            'HELP_EDIT_HABIT_NAME_PROMPT': "Текущее название: <b>{current_name}</b>\n\nВведите новое название:",
            'HELP_EDIT_HABIT_WEIGHT_PROMPT': "Текущий вес: <b>{current_weight}</b>\n\nВыберите новый вес:",
            'HELP_EDIT_HABIT_CATEGORY_PROMPT': "Текущая категория: <b>{current_category}</b>\n\nВыберите новую категорию:",
            'HELP_EDIT_HABIT_GRACE_DAYS_PROMPT': "Текущие дни отсрочки: <b>{current_grace_days}</b>\n\nВыберите новые дни отсрочки:",
            'HELP_EDIT_HABIT_EXEMPT_DAYS_PROMPT': "Текущие исключённые дни: <b>{current_exempt_days}</b>\n\nВыберите новые исключённые дни:",
            'HELP_EDIT_HABIT_CONFIRM': "Проверьте изменения:\n<b>Название:</b> {old_name} → {new_name}\n<b>Вес:</b> {old_weight} → {new_weight}\n<b>Дни отсрочки:</b> {old_grace_days} → {new_grace_days}\n<b>Исключённые дни:</b> {old_exempt_days} → {new_exempt_days}\n\nСохранить изменения?",
            'SUCCESS_HABIT_UPDATED': "✅ Привычка '<b>{name}</b>' успешно обновлена!",
            'HELP_REMOVE_HABIT_SELECT': "Выберите привычку для удаления:",
            'HELP_REMOVE_HABIT_CONFIRM': "Вы уверены, что хотите удалить '<b>{name}</b>'?\n\n⚠️ Это деактивирует привычку. Ваша история будет сохранена.",
            'SUCCESS_HABIT_REMOVED': "✅ Привычка '<b>{name}</b>' успешно удалена.",
            'ERROR_NO_HABITS_TO_EDIT': "❌ У вас нет привычек для редактирования.",
            'ERROR_NO_HABITS_TO_EDIT_PROMPT': "❌ У вас нет привычек для редактирования.\n\nХотите добавить новую привычку?",
            'ERROR_NO_HABITS_TO_REMOVE': "❌ У вас нет привычек для удаления.",
            'INFO_HABIT_CANCEL': "❌ Операция с привычкой отменена.",

            # Backdate Messages
            'HELP_BACKDATE_SELECT_HABIT': "📅 Какую привычку вы хотите записать за прошлую дату?",
            'HELP_BACKDATE_SELECT_DATE': "📆 Выберите дату, когда вы выполнили <b>{habit_name}</b>:\n\n✓ = уже записано",
            'HELP_BACKDATE_CONFIRM': "Записать <b>{habit_name}</b> на <b>{date}</b>?",
            'HELP_SELECT_COMPLETION_DATE': "Когда вы выполнили <b>{habit_name}</b>?",
            'SUCCESS_BACKDATE_COMPLETED': "✅ <b>Привычка записана:</b> {habit_name}\n📅 <b>Дата:</b> {date}",
            'ERROR_BACKDATE_DUPLICATE': "❌ Вы уже записали <b>{habit_name}</b> на {date}.",
            'ERROR_BACKDATE_TOO_OLD': "❌ Нельзя записать дату старше 7 дней.",
            'ERROR_BACKDATE_FUTURE': "❌ Нельзя записывать привычки на будущие даты.",
            'ERROR_BACKDATE_BEFORE_CREATED': "❌ Нельзя записать дату раньше создания привычки ({date}).",
            'BUTTON_TODAY': "✅ Сегодня",
            'BUTTON_YESTERDAY': "📅 Вчера",
            'BUTTON_SELECT_DATE': "📆 Выбрать другую дату",

            # Reward Management Messages
            'HELP_ADD_REWARD_NAME_PROMPT': "Введите название новой награды:",
            'ERROR_REWARD_NAME_EMPTY': "❌ Название награды не может быть пустым.",
            'ERROR_REWARD_NAME_TOO_LONG': "❌ Название награды слишком длинное (максимум 255 символов).",
            'ERROR_REWARD_NAME_EXISTS': "❌ Награда с таким названием уже существует. Пожалуйста, выберите другое название.",
            'HELP_ADD_REWARD_TYPE_PROMPT': "Выберите тип награды:",
            'BUTTON_REWARD_TYPE_VIRTUAL': "🖥 Виртуальная",
            'BUTTON_REWARD_TYPE_REAL': "🎁 Реальная",
            'HELP_ADD_REWARD_WEIGHT_PROMPT': "Введите вес награды (чем выше, тем больше шанс) или выберите вариант ниже:",
            'ERROR_REWARD_WEIGHT_INVALID': "❌ Неверный вес. Введите число от {min} до {max}.",
            'HELP_ADD_REWARD_PIECES_PROMPT': "Введите сколько частей нужно для получения награды:",
            'ERROR_REWARD_PIECES_INVALID': "❌ Количество частей должно быть целым числом больше 0.",
            'HELP_ADD_REWARD_PIECE_VALUE_PROMPT': "Введите ценность одной части (например, 0.50) или нажмите «Пропустить», если ценности нет:",
            'ERROR_REWARD_PIECE_VALUE_INVALID': "❌ Ценность части должна быть неотрицательным числом.",
            'HELP_ADD_REWARD_CONFIRM': (
                "Проверьте новую награду:\n"
                "<b>Название:</b> {name}\n"
                "<b>Тип:</b> {type_label}\n"
                "<b>Вес:</b> {weight}\n"
                "<b>Количество частей:</b> {pieces}\n"
                "<b>Повторяющаяся:</b> {recurring}\n\n"
                "Создать эту награду?"
            ),
            'SUCCESS_REWARD_CREATED': "✅ Награда '<b>{name}</b>' успешно создана!",
            'INFO_REWARD_CANCEL': "❌ Создание награды отменено.",
            'BUTTON_ADD_ANOTHER_REWARD': "➕ Добавить ещё награду",
            'BUTTON_BACK_TO_REWARDS': "🎁 Назад к наградам",
            'BUTTON_SKIP': "⏭ Пропустить",
            'BUTTON_CLEAR': "🧹 Очистить",
            'BUTTON_CONFIRM': "✅ Создать награду",
            'BUTTON_EDIT_REWARD': "✏️ Изменить данные",
            'BUTTON_PIECES_NOT_ACCUMULATIVE': "1 (Без накопления)",
            'TEXT_NOT_SET': "Не указано",
            'KEYWORD_SKIP': "пропустить",

            'HELP_EDIT_REWARD_SELECT': "Выберите награду для редактирования:",
            'ERROR_NO_REWARDS_TO_EDIT': "❌ У вас нет наград для редактирования.",
            'HELP_EDIT_REWARD_NAME_PROMPT': "Текущее название: <b>{current_name}</b>\n\nВведите новое название:",
            'HELP_EDIT_REWARD_TYPE_PROMPT': "Текущий тип: <b>{current_type}</b>\n\nВыберите новый тип:",
            'HELP_EDIT_REWARD_WEIGHT_PROMPT': "Текущий вес: <b>{current_weight}</b>\n\nВыберите новый вес (или введите вручную):",
            'HELP_EDIT_REWARD_PIECES_PROMPT': "Текущее количество частей: <b>{current_pieces}</b>\n\nВведите новое количество частей:",
            'HELP_EDIT_REWARD_PIECE_VALUE_PROMPT': (
                "Текущая ценность части: <b>{current_value}</b>\n\n"
                "Введите новую ценность, нажмите «Очистить» чтобы убрать её, или «Пропустить» чтобы оставить:"
            ),
            'HELP_EDIT_REWARD_CONFIRM': (
                "Проверьте изменения:\n"
                "<b>Название:</b> {old_name} → {new_name}\n"
                "<b>Тип:</b> {old_type} → {new_type}\n"
                "<b>Вес:</b> {old_weight} → {new_weight}\n"
                "<b>Количество частей:</b> {old_pieces} → {new_pieces}\n"
                "<b>Повторяющаяся:</b> {old_recurring} → {new_recurring}\n\n"
                "Сохранить изменения?"
            ),
            'SUCCESS_REWARD_UPDATED': "✅ Награда '<b>{name}</b>' успешно обновлена!",
            'INFO_REWARD_EDIT_CANCEL': "❌ Редактирование награды отменено.",

            # Recurring Reward Messages
            'HELP_ADD_REWARD_RECURRING_PROMPT': "Награда повторяющаяся (можно получить несколько раз)?",
            'HELP_EDIT_REWARD_RECURRING_PROMPT': "Награда повторяющаяся? Текущее: <b>{current_value}</b>",
            'BUTTON_RECURRING_YES': "🔄 Да (можно получить несколько раз)",
            'BUTTON_RECURRING_NO': "🔒 Нет (только один раз)",

            # Toggle Reward Active/Inactive Messages
            'HELP_TOGGLE_REWARD_SELECT': "Выберите награду для активации/деактивации:",
            'SUCCESS_REWARD_ACTIVATED': "✅ Награда '<b>{name}</b>' теперь активна",
            'SUCCESS_REWARD_DEACTIVATED': "❌ Награда '<b>{name}</b>' теперь неактивна",
            'ERROR_NO_REWARDS_TO_TOGGLE': "У вас нет наград для управления.",
            'INFO_REWARD_NON_RECURRING_DEACTIVATED': "Эта награда неповторяющаяся и была деактивирована. Вы можете активировать её вручную из меню Наград при необходимости.",

            # Reward Status Labels
            'LABEL_REWARD_ACTIVE': "✅ Активна",
            'LABEL_REWARD_INACTIVE': "❌ Неактивна",
            'LABEL_REWARD_NON_RECURRING': "🔒 Одноразовая",
            'LABEL_REWARD_RECURRING': "🔄 Повторяющаяся",

            # Settings Menu
            'SETTINGS_MENU': "⚙️ <b>Настройки</b>\n\nВыберите опцию:",
            'SETTINGS_SELECT_LANGUAGE': "🌐 Выбрать язык",
            'SETTINGS_API_KEYS': "🔑 API-ключи",
            'SETTINGS_NO_REWARD_PROB': "🎲 Вероятность без награды",
            'SETTINGS_BACK': "← Назад в настройки",

            # No Reward Probability Settings
            'NO_REWARD_PROB_MENU': "🎲 <b>Вероятность без награды</b>\n\nТекущее значение: <b>{current}%</b>\n\nВыберите пресет или введите своё значение (0.01-99.99):",
            'NO_REWARD_PROB_CUSTOM': "✏️ Своё значение",
            'NO_REWARD_PROB_ENTER_CUSTOM': "📝 <b>Введите вероятность</b>\n\nВведите значение от 0.01 до 99.99:",
            'NO_REWARD_PROB_UPDATED': "✅ Вероятность без награды обновлена: <b>{value}%</b>",
            'NO_REWARD_PROB_INVALID': "❌ Неверное значение. Введите число от 0.01 до 99.99.",

            # Language Selection
            'LANGUAGE_SELECTION_MENU': "🌐 <b>Выбрать язык</b>\n\nВыберите предпочитаемый язык:",

            # API Key Management
            'API_KEY_MENU': "🔑 <b>API-ключи</b>\n\nУправляйте ключами для внешних интеграций (фитнес-приложения, автоматизации и т.д.):",
            'API_KEY_CREATE': "➕ Создать ключ",
            'API_KEY_LIST': "📋 Список ключей",
            'API_KEY_REVOKE': "❌ Отозвать ключ",
            'API_KEY_ENTER_NAME': "📝 <b>Введите название API-ключа</b>\n\nПример: Фитнес-приложение, iOS Shortcut",
            'API_KEY_CREATED': """✅ <b>API-ключ создан!</b>

<b>Название:</b> {name}
<b>Ключ:</b> <code>{key}</code>

⚠️ <b>ВАЖНО:</b> Скопируйте ключ сейчас! Вы не сможете увидеть его снова.

Используйте этот ключ в вашем приложении с заголовком:
<code>X-API-Key: {key}</code>""",
            'API_KEY_NAME_EXISTS': "❌ API-ключ с названием '{name}' уже существует. Выберите другое название.",
            'API_KEY_NAME_TOO_LONG': "❌ Название ключа слишком длинное. Максимум 100 символов.",
            'API_KEY_NAME_EMPTY': "❌ Название ключа не может быть пустым. Введите название.",
            'API_KEY_LIST_HEADER': "🔑 <b>Ваши API-ключи:</b>\n",
            'API_KEY_LIST_EMPTY': "📭 У вас пока нет API-ключей.\n\nСоздайте один для подключения ваших приложений!",
            'API_KEY_CREATED_AT': "Создан",
            'API_KEY_LAST_USED': "Последнее использование",
            'API_KEY_NEVER_USED': "Никогда",
            'API_KEY_SELECT_TO_REVOKE': "🔑 <b>Выберите ключ для отзыва:</b>",
            'API_KEY_REVOKED': "✅ API-ключ '<b>{name}</b>' отозван.",
            'API_KEY_REVOKE_FAILED': "❌ Не удалось отозвать API-ключ. Попробуйте снова.",
            'BACK_TO_SETTINGS': "← Назад в настройки",
            'BACK': "← Назад",
        },
        'kk': {
            # Error Messages - User Validation
            'ERROR_USER_NOT_FOUND': "❌ Пайдаланушы табылмады. Тіркелу үшін әкімшіге хабарласыңыз.",
            'ERROR_USER_INACTIVE': "❌ Сіздің аккаунтыңыз белсенді емес. Әкімшіге хабарласыңыз.",

            # Error Messages - Entity Not Found
            'ERROR_NO_HABITS': "Белсенді әдеттер табылмады. Алдымен әдеттер қосыңыз.",
            'ERROR_NO_HABITS_LOGGED': "Әдеттер әлі тіркелмеген. Бастау үшін /habit_done пайдаланыңыз!",
            'ERROR_HABIT_NOT_FOUND': "Әдет табылмады. Қайталап көріңіз.",
            'ERROR_NO_LOG_TO_REVERT': "Қайтаруға арналған әдет орындау табылмады.",
            'ERROR_REWARD_NOT_FOUND': "'{reward_name}' сыйлығы табылмады.",
            'ERROR_NO_MATCH_HABIT': "Мәтініңізді белгілі әдетпен сәйкестендіру мүмкін болмады. /habit_done арқылы тізімнен таңдаңыз.",

            # Error Messages - Validation
            'ERROR_INVALID_STATUS': "Қате статус. Мыналарды пайдаланыңыз: pending, achieved немесе completed",
            'ERROR_GENERAL': "Қате: {error}",

            # Info Messages
            'INFO_NO_REWARD_PROGRESS': "Сыйлық бойынша прогресс жоқ. Әдеттерді орындауды жалғастырыңыз!",
            'INFO_NO_REWARD': "❌ Бұл жолы сыйлық жоқ - жалғастырыңыз!",
            'INFO_REWARD_ACTIONABLE': "⏳ <b>Сыйлық қол жеткізілді!</b> Оны қазір алуға болады!",
            'INFO_FEATURE_COMING_SOON': "🎁 <b>Жаңа сыйлық қосу</b>\n\nБұл функция жаңа сыйлық жасауға жетелейді.\nҚазірше Airtable арқылы сыйлықтар қосыңыз.\n\nЖақында: бот арқылы сыйлықтар жасау!",
            'INFO_CANCELLED': "Әдетті тіркеу болдырылмады.",
            'INFO_CANCELLED_REVERT': "Қайтару тоқтатылды.",
            'INFO_MULTIPLE_HABITS': "Сондай-ақ табылды: {other_habits}. Оларды тіркеу үшін /habit_done пайдаланыңыз.",
            'INFO_NO_REWARDS_TO_CLAIM': "Әлі алуға дайын сыйлықтарыңыз жоқ. Сыйлықтар табу үшін әдеттерді тіркеуді жалғастырыңыз!",
            'INFO_ALL_HABITS_COMPLETED': "🎉 Бүгін барлық белсенді әдеттер орындалды. Ертең қайта келіңіз!",

            # Usage/Help Messages
            'HELP_CLAIM_REWARD_USAGE': "Пайдалану: /claim_reward <сыйлық_аты>\nМысал: /claim_reward Сүйікті кафеде кофе",
            'HELP_HABIT_SELECTION': "Қандай әдетті орындадыңыз? 🎯\n\nТөмендегі тізімнен таңдаңыз:",
            'HELP_SIMPLE_HABIT_SELECTION': "Бүгін қай әдетті орындадыңыз? 🎯",
            'HELP_CUSTOM_TEXT': "Қандай әдетті орындағаныңызды жазыңыз:",
            'HELP_REVERT_HABIT_SELECTION': "Қай әдет орындалуын қайтарғыңыз келеді?",
            'HELP_SELECT_REWARD_TO_CLAIM': "🎁 <b>Алатын сыйлықты таңдаңыз:</b>",

            # Success Messages
            'SUCCESS_HABIT_COMPLETED': "✅ <b>Әдет орындалды:</b> {habit_name}",
            'SUCCESS_REWARD_CLAIMED': "✅ Сыйлық алынды: <b>{reward_name}</b>\nСтатус: {status}\n\nКұттықтаймыз! 🎉",
            'SUCCESS_STATUS_UPDATED': "✅ Сыйлық статусы жаңартылды: <b>{reward_name}</b>\nЖаңа статус: {status}",
            'SUCCESS_HABIT_REVERTED': "✅ <b>Әдет орындалуы қайтарылды:</b> {habit_name}",
            'SUCCESS_REWARD_REVERTED': "Сыйлық прогресі де қайтарылды: {reward_name} ({pieces_earned}/{pieces_required})",
            'SUCCESS_REWARD_CLAIMED_HEADER': "✅ <b>Сыйлық алынды:</b> {reward_name}",

            # Headers/Titles
            'HEADER_REWARD_PROGRESS': "🎁 <b>Сіздің сыйлық бойынша прогресс:</b>\n",
            'HEADER_STREAKS': "🔥 <b>Сіздің ағымдағы сериялар:</b>\n",
            'HEADER_REWARDS_LIST': "🎁 <b>Қолжетімді сыйлықтар:</b>\n",
            'HEADER_HABIT_LOGS': "📋 <b>Соңғы орындалған әдеттер:</b>\n",
            'HEADER_UPDATED_REWARD_PROGRESS': "\n📊 <b>Сіздің жаңартылған сыйлық прогресі:</b>",

            # Start/Menu Titles and Buttons
            'START_MENU_TITLE': "🏠 <b>Басты мәзір</b>\nӘрекетті таңдаңыз:",
            'HABITS_MENU_TITLE': "🧩 <b>Әдеттер</b>\nӘрекетті таңдаңыз:",
            'REWARDS_MENU_TITLE': "🎁 <b>Сыйлықтар</b>\nӘрекетті таңдаңыз:",
            'MENU_BACK': "« Артқа",
            'MENU_CANCEL': "✖ Болдырмау",
            'MENU_CLOSE': "✖ Жабу",
            'MENU_CLOSED': "Мәзір жабылды. Қайта ашу үшін /start пайдаланыңыз.",
            'BUTTON_HABIT_DONE': "✅ Әдет аяқталды",
            'BUTTON_HABIT_DONE_DATE': "📅 Күнге белгілеу",
            'BUTTON_HABITS': "🧩 Әдеттер",
            'BUTTON_REWARDS': "🎁 Марапаттар",
            'BUTTON_STREAKS': "🔥 Сериялар",
            'BUTTON_SETTINGS': "⚙️ Параметрлер",
            'BUTTON_HELP': "❓ Көмек",
            'BUTTON_ADD_HABIT': "➕ Әдет қосу",
            'BUTTON_EDIT_HABIT': "✏️ Әдетті өңдеу",
            'BUTTON_REMOVE_HABIT': "🗑 Әдетті жою",
            'BUTTON_REVERT_HABIT': "↩️ Әдетті қайтару",
            'BUTTON_ADD_REWARD': "➕ Марапат қосу",
            'BUTTON_EDIT_REWARD_MENU': "✏️ Марапатты өңдеу",
            'BUTTON_TOGGLE_REWARD': "🔄 Марапатты іске қосу/өшіру",
            'BUTTON_LIST_REWARDS': "📄 Марапаттар тізімі",
            'BUTTON_MY_REWARDS': "📊 Менің марапаттарым",
            'BUTTON_CLAIM_REWARD': "🎯 Марапат алу",
            'BUTTON_YES': "✅ Иә",
            'BUTTON_NO': "❌ Жоқ",
            'BUTTON_EXEMPT_NONE': "Жоқ",
            'BUTTON_EXEMPT_WEEKENDS': "Демалыс (Сн/Жк)",

            # Welcome/Help Messages
            'HELP_START_MESSAGE': """🎯 <b>Әдеттер үшін сыйлықтар жүйесіне қош келдіңіз!</b>

Әдеттерді қадағалаңыз және сыйлықтар алыңыз!

<b>Қолжетімді команdalар:</b>
/habit_done - Орындалған әдетті тіркеу
/add_habit - Жаңа әдет жасау
/edit_habit - Қолданыстағы әдетті өзгерту
/remove_habit - Әдетті жою
/streaks - Ағымдағы сериялар көру
/list_rewards - Барлық қолжетімді сыйлықтарды көру
/my_rewards - Сыйлықтар бойынша прогресті тексеру
/claim_reward - Қол жеткізілген сыйлықты алу
/revert_habit - Соңғы әдет орындалуын қайтару
/settings - Тілді және параметрлерді өзгерту
/help - Осы анықтаманы көрсету""",

            'HELP_COMMAND_MESSAGE': """🎯 <b>Әдеттер үшін сыйлықтар жүйесі бойынша анықтама</b>

<b>Негізгі командалар:</b>
/habit_done - Әдет орындауды тіркеу және сыйлықтар алу
/backdate - Өткен күндер үшін әдеттерді жазу (7 күнге дейін)
/streaks - Барлық әдеттер үшін ағымдағы сериялар көру

<b>Әдеттерді басқару:</b>
/add_habit - Жаңа әдет жасау
/edit_habit - Қолданыстағы әдетті өзгерту
/remove_habit - Әдетті жою (жұмсақ жою)

<b>Сыйлықтар командалары:</b>
/list_rewards - Барлық қолжетімді сыйлықтарды көрсету
/my_rewards - Жинақталған сыйлық прогресін көру
/claim_reward - Қол жеткізілген сыйлықты аяқталған деп белгілеу
/revert_habit - Соңғы әдет орындалуын қайтару

<b>Параметрлер:</b>
/settings - Тілді және параметрлерді өзгерту

<b>Бұл қалай жұмысістейді:</b>
1. /add_habit арқылы әдеттер жасаңыз немесе қолданыстағыларды басқарыңыз
2. /habit_done арқылы әдеттерді орындаңыз
3. Әдеттерді күн сайын орындау арқылы сериялар жасаңыз
4. Сыйлық бөліктерін жинаңыз (жинақталатын сыйлықтар)
5. Жеткілікті бөліктер жинағанда сыйлықтарды алыңыз

Сериялар көбейткіші сыйлық алу мүмкіндігін арттырады!""",

            # Formatter Messages
            'FORMAT_STREAK': "<b>Серия:</b> {streak_count} күн",
            'FORMAT_REWARD': "🎁 <b>Сыйлық:</b> {reward_name}",
            'FORMAT_PROGRESS': "📊 Прогресс: {progress_bar} {pieces_earned}/{pieces_required}",
            'FORMAT_STATUS': "Статус: {status}",
            'FORMAT_READY_TO_CLAIM': "⏳ <b>Алуға дайын!</b>",
            'FORMAT_NO_REWARDS_YET': "Сыйлықтар әлі конфигурацияланбаған.",
            'FORMAT_NO_STREAKS': "Әдеттер әлі тіркелмеген. Сериялар жасауды бастаңыз!",
            'FORMAT_NO_LOGS': "Әдеттер туралы жазбалар табылмады.",

            # Habit Management Messages
            'HELP_ADD_HABIT_NAME_PROMPT': "Жаңа әдеттің атын енгізіңіз:",
            'HELP_ADD_HABIT_WEIGHT_PROMPT': "Осы әдет үшін салмақты таңдаңыз (1-100). Салмақ сыйлық мүмкіндігіне әсер етеді:",
            'HELP_ADD_HABIT_CATEGORY_PROMPT': "Осы әдет үшін санатты таңдаңыз:",
            'HELP_ADD_HABIT_GRACE_DAYS_PROMPT': "Бұл әдет үшін қанша күн шегерім (grace days) керек?\n\n<b>Шегерім күндері</b> серияны үзбей күндерді өткізіп жіберуге мүмкіндік береді.\n\nМысалы: 1 шегерім күнімен сіз бір күнді өткізіп жіберіп, серияны сақтай аласыз.",
            'HELP_ADD_HABIT_EXEMPT_DAYS_PROMPT': "Серияға әсер етпейтін күндерді таңдаңыз:\n\n<b>Ерекше күндер</b> — бұл әдетті орындамасаңыз да серияңызды үзбейтін апта күндері (мысалы, демалыс күндері).",
            'HELP_EXEMPT_DAYS_OR_MANUAL': "\n\n• Төмендегі опцияны таңдаңыз НЕМЕСЕ\n• <b>Нөмірлерді қолмен енгізіңіз</b> (мыс., сей/бей үшін <code>2, 4</code>)",
            'HELP_EXEMPT_DAYS_MANUAL_ENTRY': (
                "<b>Ерекше күндерді сандармен үтір арқылы енгізіңіз.</b>\n\n"
                "1 = Дүйсенбі\n2 = Сейсенбі\n3 = Сәрсенбі\n4 = Бейсенбі\n"
                "5 = Жұма\n6 = Сенбі\n7 = Жексенбі\n\n"
                "Мысалы: сейсенбі мен бейсенбі үшін <code>2, 4</code>."
            ),
            'ERROR_EXEMPT_DAYS_INVALID_FORMAT': (
                "⚠️ <b>Қате формат.</b>\n"
                "Сандарды 1-7 аралығында үтір арқылы енгізіңіз (1=Дүй, 7=Жек).\n"
                "Мысалы: <code>2, 4</code>"
            ),
            'HELP_ADD_HABIT_CONFIRM': "Жаңа әдетіңізді тексеріңіз:\n<b>Аты:</b> {name}\n<b>Салмақ:</b> {weight}\n<b>Шегерім күндері:</b> {grace_days}\n<b>Ерекше күндер:</b> {exempt_days}\n\nОсы әдетті жасау керек пе?",
            'SUCCESS_HABIT_CREATED': "✅ '<b>{name}</b>' әдеті сәтті жасалды!",
            'HELP_HABIT_CREATED_NEXT': "🧩 <b>Сіздің әдеттеріңіз:</b>",
            'ERROR_HABIT_NAME_TOO_LONG': "❌ Әдет атауы тым ұзын (макс. 100 таңба).",
            'ERROR_HABIT_NAME_EMPTY': "❌ Әдет атауы бос болуы мүмкін емес.",
            'ERROR_HABIT_NAME_EXISTS': "❌ Сізде '<b>{name}</b>' атты әдет бар.\n\nБасқа атау таңдаңыз:",
            'ERROR_WEIGHT_INVALID': "❌ Қате салмақ. 1-ден 100-ге дейін мән таңдаңыз.",
            'HELP_EDIT_HABIT_SELECT': "Өңдеу үшін әдетті таңдаңыз:",
            'HELP_EDIT_HABIT_NAME_PROMPT': "Ағымдағы аты: <b>{current_name}</b>\n\nЖаңа атын енгізіңіз:",
            'HELP_EDIT_HABIT_WEIGHT_PROMPT': "Ағымдағы салмақ: <b>{current_weight}</b>\n\nЖаңа салмақты таңдаңыз:",
            'HELP_EDIT_HABIT_CATEGORY_PROMPT': "Ағымдағы санат: <b>{current_category}</b>\n\nЖаңа санатты таңдаңыз:",
            'HELP_EDIT_HABIT_GRACE_DAYS_PROMPT': "Ағымдағы шегерім күндері: <b>{current_grace_days}</b>\n\nЖаңа шегерім күндерін таңдаңыз:",
            'HELP_EDIT_HABIT_EXEMPT_DAYS_PROMPT': "Ағымдағы ерекше күндер: <b>{current_exempt_days}</b>\n\nЖаңа ерекше күндерді таңдаңыз:",
            'HELP_EDIT_HABIT_CONFIRM': "Өзгерістерді тексеріңіз:\n<b>Аты:</b> {old_name} → {new_name}\n<b>Салмақ:</b> {old_weight} → {new_weight}\n<b>Шегерім күндері:</b> {old_grace_days} → {new_grace_days}\n<b>Ерекше күндер:</b> {old_exempt_days} → {new_exempt_days}\n\nӨзгерістерді сақтау керек пе?",
            'SUCCESS_HABIT_UPDATED': "✅ '<b>{name}</b>' әдеті сәтті жаңартылды!",
            'HELP_REMOVE_HABIT_SELECT': "Жою үшін әдетті таңдаңыз:",
            'HELP_REMOVE_HABIT_CONFIRM': "Сіз '<b>{name}</b>' жоюға сенімдісіз бе?\n\n⚠️ Бұл әдетті белсенсіз етеді. Тарихыңыз сақталады.",
            'SUCCESS_HABIT_REMOVED': "✅ '<b>{name}</b>' әдеті сәтті жойылды.",
            'ERROR_NO_HABITS_TO_EDIT': "❌ Өңдеуге әдеттеріңіз жоқ.",
            'ERROR_NO_HABITS_TO_EDIT_PROMPT': "❌ Өңдеуге әдеттеріңіз жоқ.\n\nЖаңа әдет қосқыңыз келе ме?",
            'ERROR_NO_HABITS_TO_REMOVE': "❌ Жоюға әдеттеріңіз жоқ.",
            'INFO_HABIT_CANCEL': "❌ Әдет операциясы болдырылмады.",

            # Backdate Messages
            'HELP_BACKDATE_SELECT_HABIT': "📅 Өткен күнге қай әдетті жазғыңыз келеді?",
            'HELP_BACKDATE_SELECT_DATE': "📆 <b>{habit_name}</b> орындаған күніңізді таңдаңыз:\n\n✓ = жазылған",
            'HELP_BACKDATE_CONFIRM': "<b>{habit_name}</b> әдетін <b>{date}</b> күніне жазу керек пе?",
            'HELP_SELECT_COMPLETION_DATE': "<b>{habit_name}</b> қашан орындадыңыз?",
            'SUCCESS_BACKDATE_COMPLETED': "✅ <b>Әдет жазылды:</b> {habit_name}\n📅 <b>Күні:</b> {date}",
            'ERROR_BACKDATE_DUPLICATE': "❌ Сіз <b>{habit_name}</b> әдетін {date} күніне жазып қойдыңыз.",
            'ERROR_BACKDATE_TOO_OLD': "❌ 7 күннен көп кешіктіруге болмайды.",
            'ERROR_BACKDATE_FUTURE': "❌ Болашақ күндерге әдет жазуға болмайды.",
            'ERROR_BACKDATE_BEFORE_CREATED': "❌ Әдет жасалғанға дейінгі күнге жазуға болмайды ({date}).",
            'BUTTON_TODAY': "✅ Бүгін",
            'BUTTON_YESTERDAY': "📅 Кеше",
            'BUTTON_SELECT_DATE': "📆 Басқа күнді таңдау",

            # Reward Management Messages
            'HELP_ADD_REWARD_NAME_PROMPT': "Жаңа сыйлықтың атауын енгізіңіз:",
            'ERROR_REWARD_NAME_EMPTY': "❌ Сыйлық атауы бос болмауы тиіс.",
            'ERROR_REWARD_NAME_TOO_LONG': "❌ Сыйлық атауы тым ұзын (ең көбі 255 таңба).",
            'ERROR_REWARD_NAME_EXISTS': "❌ Бұл атаумен сыйлық бар. Басқа атауды таңдаңыз.",
            'HELP_ADD_REWARD_TYPE_PROMPT': "Сыйлық түрін таңдаңыз:",
            'BUTTON_REWARD_TYPE_VIRTUAL': "🖥 Виртуалды",
            'BUTTON_REWARD_TYPE_REAL': "🎁 Нақты",
            'HELP_ADD_REWARD_WEIGHT_PROMPT': "Сыйлық салмағын енгізіңіз (үлкен салмақ — жоғары мүмкіндік) немесе төменнен таңдаңыз:",
            'ERROR_REWARD_WEIGHT_INVALID': "❌ Дұрыс емес салмақ. {min} мен {max} аралығындағы сан енгізіңіз.",
            'HELP_ADD_REWARD_PIECES_PROMPT': "Сыйлық алу үшін қанша бөлік керек екенін енгізіңіз:",
            'ERROR_REWARD_PIECES_INVALID': "❌ Бөліктер саны 0-ден үлкен бүтін сан болуы тиіс.",
            'HELP_ADD_REWARD_PIECE_VALUE_PROMPT': "Әр бөліктің құнын енгізіңіз (мысалы, 0.50) немесе құны жоқ болса «Өткізу» түймесін басыңыз:",
            'ERROR_REWARD_PIECE_VALUE_INVALID': "❌ Бөлік құны теріс емес сан болуы тиіс.",
            'HELP_ADD_REWARD_CONFIRM': (
                "Жаңа сыйлықты тексеріңіз:\n"
                "<b>Атауы:</b> {name}\n"
                "<b>Түрі:</b> {type_label}\n"
                "<b>Салмағы:</b> {weight}\n"
                "<b>Қажет бөліктер:</b> {pieces}\n"
                "<b>Қайталанатын:</b> {recurring}\n\n"
                "Бұл сыйлықты жасаймыз ба?"
            ),
            'SUCCESS_REWARD_CREATED': "✅ '<b>{name}</b>' сыйлығы сәтті құрылды!",
            'INFO_REWARD_CANCEL': "❌ Сыйлық жасау тоқтатылды.",
            'BUTTON_ADD_ANOTHER_REWARD': "➕ Тағы бір сыйлық қосу",
            'BUTTON_BACK_TO_REWARDS': "🎁 Сыйлықтар мәзіріне оралу",
            'BUTTON_SKIP': "⏭ Өткізу",
            'BUTTON_CLEAR': "🧹 Тазарту",
            'BUTTON_CONFIRM': "✅ Сыйлық жасау",
            'BUTTON_EDIT_REWARD': "✏️ Мәліметтерді түзету",
            'BUTTON_PIECES_NOT_ACCUMULATIVE': "1 (Жинақсыз)",
            'TEXT_NOT_SET': "Көрсетілмеген",
            'KEYWORD_SKIP': "өткізу",

            'HELP_EDIT_REWARD_SELECT': "Өңдеу үшін марапатты таңдаңыз:",
            'ERROR_NO_REWARDS_TO_EDIT': "❌ Өңдеуге марапаттарыңыз жоқ.",
            'HELP_EDIT_REWARD_NAME_PROMPT': "Ағымдағы атауы: <b>{current_name}</b>\n\nЖаңа атауын енгізіңіз:",
            'HELP_EDIT_REWARD_TYPE_PROMPT': "Ағымдағы түрі: <b>{current_type}</b>\n\nЖаңа түрін таңдаңыз:",
            'HELP_EDIT_REWARD_WEIGHT_PROMPT': "Ағымдағы салмағы: <b>{current_weight}</b>\n\nЖаңа салмақты таңдаңыз (немесе енгізіңіз):",
            'HELP_EDIT_REWARD_PIECES_PROMPT': "Ағымдағы қажет бөліктер: <b>{current_pieces}</b>\n\nЖаңа қажет бөліктер санын енгізіңіз:",
            'HELP_EDIT_REWARD_PIECE_VALUE_PROMPT': (
                "Ағымдағы бөлік құны: <b>{current_value}</b>\n\n"
                "Жаңа құнды енгізіңіз, алып тастау үшін «Тазарту», сақтау үшін «Өткізу» басыңыз:"
            ),
            'HELP_EDIT_REWARD_CONFIRM': (
                "Өзгерістерді тексеріңіз:\n"
                "<b>Атауы:</b> {old_name} → {new_name}\n"
                "<b>Түрі:</b> {old_type} → {new_type}\n"
                "<b>Салмағы:</b> {old_weight} → {new_weight}\n"
                "<b>Қажет бөліктер:</b> {old_pieces} → {new_pieces}\n"
                "<b>Қайталанатын:</b> {old_recurring} → {new_recurring}\n\n"
                "Өзгерістерді сақтау керек пе?"
            ),
            'SUCCESS_REWARD_UPDATED': "✅ '<b>{name}</b>' марапаты сәтті жаңартылды!",
            'INFO_REWARD_EDIT_CANCEL': "❌ Марапатты өңдеу тоқтатылды.",

            # Recurring Reward Messages
            'HELP_ADD_REWARD_RECURRING_PROMPT': "Сыйлық қайталанатын (бірнеше рет алуға бола ма)?",
            'HELP_EDIT_REWARD_RECURRING_PROMPT': "Сыйлық қайталанатын ба? Ағымдағы: <b>{current_value}</b>",
            'BUTTON_RECURRING_YES': "🔄 Иә (бірнеше рет алуға болады)",
            'BUTTON_RECURRING_NO': "🔒 Жоқ (тек бір рет)",

            # Toggle Reward Active/Inactive Messages
            'HELP_TOGGLE_REWARD_SELECT': "Іске қосу/өшіру үшін сыйлықты таңдаңыз:",
            'SUCCESS_REWARD_ACTIVATED': "✅ '<b>{name}</b>' сыйлығы енді белсенді",
            'SUCCESS_REWARD_DEACTIVATED': "❌ '<b>{name}</b>' сыйлығы енді белсенді емес",
            'ERROR_NO_REWARDS_TO_TOGGLE': "Басқаруға сыйлықтарыңыз жоқ.",
            'INFO_REWARD_NON_RECURRING_DEACTIVATED': "Бұл сыйлық қайталанбайтын және өшірілді. Қажет болса, Сыйлықтар мәзірінен қолмен іске қосуға болады.",

            # Reward Status Labels
            'LABEL_REWARD_ACTIVE': "✅ Белсенді",
            'LABEL_REWARD_INACTIVE': "❌ Белсенді емес",
            'LABEL_REWARD_NON_RECURRING': "🔒 Бір реттік",
            'LABEL_REWARD_RECURRING': "🔄 Қайталанатын",

            # Settings Menu
            'SETTINGS_MENU': "⚙️ <b>Параметрлер</b>\n\nОпцияны таңдаңыз:",
            'SETTINGS_SELECT_LANGUAGE': "🌐 Тілді таңдау",
            'SETTINGS_API_KEYS': "🔑 API кілттері",
            'SETTINGS_NO_REWARD_PROB': "🎲 Сыйлықсыз ықтималдық",
            'SETTINGS_BACK': "← Параметрлерге оралу",

            # No Reward Probability Settings
            'NO_REWARD_PROB_MENU': "🎲 <b>Сыйлықсыз ықтималдық</b>\n\nАғымдағы мән: <b>{current}%</b>\n\nПресетті таңдаңыз немесе өз мәніңізді енгізіңіз (0.01-99.99):",
            'NO_REWARD_PROB_CUSTOM': "✏️ Өз мәні",
            'NO_REWARD_PROB_ENTER_CUSTOM': "📝 <b>Ықтималдықты енгізіңіз</b>\n\n0.01-ден 99.99-ға дейін мән енгізіңіз:",
            'NO_REWARD_PROB_UPDATED': "✅ Сыйлықсыз ықтималдық жаңартылды: <b>{value}%</b>",
            'NO_REWARD_PROB_INVALID': "❌ Қате мән. 0.01-ден 99.99-ға дейін сан енгізіңіз.",

            # Language Selection
            'LANGUAGE_SELECTION_MENU': "🌐 <b>Тілді таңдау</b>\n\nҚалаған тіліңізді таңдаңыз:",

            # API Key Management
            'API_KEY_MENU': "🔑 <b>API кілттері</b>\n\nСыртқы интеграциялар үшін кілттерді басқарыңыз (фитнес қосымшалары, автоматтандыру және т.б.):",
            'API_KEY_CREATE': "➕ Жаңа кілт жасау",
            'API_KEY_LIST': "📋 Кілттер тізімі",
            'API_KEY_REVOKE': "❌ Кілтті қайтарып алу",
            'API_KEY_ENTER_NAME': "📝 <b>API кілтінің атауын енгізіңіз</b>\n\nМысалы: Фитнес қосымшасы, iOS Shortcut",
            'API_KEY_CREATED': """✅ <b>API кілті жасалды!</b>

<b>Атауы:</b> {name}
<b>Кілт:</b> <code>{key}</code>

⚠️ <b>МАҢЫЗДЫ:</b> Кілтті қазір көшіріңіз! Сіз оны қайта көре алмайсыз.

Бұл кілтті қосымшаңызда келесі тақырыппен пайдаланыңыз:
<code>X-API-Key: {key}</code>""",
            'API_KEY_NAME_EXISTS': "❌ '{name}' атауымен API кілті бар. Басқа атау таңдаңыз.",
            'API_KEY_NAME_TOO_LONG': "❌ Кілт атауы тым ұзын. Максимум 100 таңба.",
            'API_KEY_NAME_EMPTY': "❌ Кілт атауы бос болмауы керек. Атауды енгізіңіз.",
            'API_KEY_LIST_HEADER': "🔑 <b>Сіздің API кілттеріңіз:</b>\n",
            'API_KEY_LIST_EMPTY': "📭 Сізде API кілттері жоқ.\n\nҚосымшаларыңызды қосу үшін біреуін жасаңыз!",
            'API_KEY_CREATED_AT': "Жасалған",
            'API_KEY_LAST_USED': "Соңғы қолданылған",
            'API_KEY_NEVER_USED': "Ешқашан",
            'API_KEY_SELECT_TO_REVOKE': "🔑 <b>Қайтарып алу үшін кілтті таңдаңыз:</b>",
            'API_KEY_REVOKED': "✅ '<b>{name}</b>' API кілті қайтарып алынды.",
            'API_KEY_REVOKE_FAILED': "❌ API кілтін қайтарып алу сәтсіз аяқталды. Қайталап көріңіз.",
            'BACK_TO_SETTINGS': "← Параметрлерге оралу",
            'BACK': "← Артқа",
        }
    }

    @classmethod
    def get(cls, key: str, lang: str = 'en', **kwargs) -> str:
        """
        Get translated message by key.

        Args:
            key: Message constant name (e.g., 'ERROR_USER_NOT_FOUND')
            lang: Language code (e.g., 'en', 'ru', 'kk')
            **kwargs: Format arguments for string interpolation

        Returns:
            Translated and formatted message string
        """
        # Normalize language code
        lang = lang.lower()[:2]

        # Check if language is supported
        if lang not in settings.supported_languages:
            lang = settings.default_language

        # Get message from translations or fallback to English default
        if lang != 'en' and lang in cls._TRANSLATIONS:
            message = cls._TRANSLATIONS[lang].get(key)
            if message:
                return message.format(**kwargs) if kwargs else message

        # Fallback to English (class attribute)
        message = getattr(cls, key, f"[Missing message: {key}]")
        return message.format(**kwargs) if kwargs else message


def msg(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Convenience function for getting translated messages.

    Args:
        key: Message constant name
        lang: Language code
        **kwargs: Format arguments

    Returns:
        Translated message string

    Example:
        msg('ERROR_USER_NOT_FOUND', 'ru')
        msg('ERROR_REWARD_NOT_FOUND', 'en', reward_name='Coffee')
    """
    return Messages.get(key, lang, **kwargs)
