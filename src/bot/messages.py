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

    # Usage/Help Messages
    HELP_CLAIM_REWARD_USAGE = "Usage: /claim_reward <reward_name>\nExample: /claim_reward Coffee at favorite cafe"
    HELP_HABIT_SELECTION = "Which habit did you complete? 🎯\n\nSelect from the list below:"
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
    BUTTON_LIST_REWARDS = "📄 List Rewards"
    BUTTON_MY_REWARDS = "📊 My Rewards"
    BUTTON_CLAIM_REWARD = "🎯 Claim Reward"
    BUTTON_YES = "✅ Yes"
    BUTTON_NO = "❌ No"

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
    FORMAT_STREAK = "🔥 <b>Streak:</b> {streak_count} days"
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
    HELP_ADD_HABIT_CONFIRM = "Review your new habit:\n<b>Name:</b> {name}\n<b>Weight:</b> {weight}\n<b>Category:</b> {category}\n\nCreate this habit?"
    SUCCESS_HABIT_CREATED = "✅ Habit '<b>{name}</b>' created successfully!"
    HELP_HABIT_CREATED_NEXT = "🧩 <b>Your habits:</b>"
    ERROR_HABIT_NAME_TOO_LONG = "❌ Habit name is too long (max 100 characters)."
    ERROR_HABIT_NAME_EMPTY = "❌ Habit name cannot be empty."
    ERROR_WEIGHT_INVALID = "❌ Invalid weight. Please select a value between 1-100."
    HELP_EDIT_HABIT_SELECT = "Select a habit to edit:"
    HELP_EDIT_HABIT_NAME_PROMPT = "Current name: <b>{current_name}</b>\n\nEnter new name:"
    HELP_EDIT_HABIT_WEIGHT_PROMPT = "Current weight: <b>{current_weight}</b>\n\nSelect new weight:"
    HELP_EDIT_HABIT_CATEGORY_PROMPT = "Current category: <b>{current_category}</b>\n\nSelect new category:"
    HELP_EDIT_HABIT_CONFIRM = "Review changes:\n<b>Name:</b> {old_name} → {new_name}\n<b>Weight:</b> {old_weight} → {new_weight}\n<b>Category:</b> {old_category} → {new_category}\n\nSave changes?"
    SUCCESS_HABIT_UPDATED = "✅ Habit '<b>{name}</b>' updated successfully!"
    HELP_REMOVE_HABIT_SELECT = "Select a habit to remove:"
    HELP_REMOVE_HABIT_CONFIRM = "Are you sure you want to remove '<b>{name}</b>'?\n\n⚠️ This will deactivate the habit. Your history will be preserved."
    SUCCESS_HABIT_REMOVED = "✅ Habit '<b>{name}</b>' removed successfully."
    ERROR_NO_HABITS_TO_EDIT = "❌ You don't have any habits to edit."
    ERROR_NO_HABITS_TO_EDIT_PROMPT = "❌ You don't have any habits to edit.\n\nWould you like to add a new habit?"
    ERROR_NO_HABITS_TO_REMOVE = "❌ You don't have any habits to remove."
    INFO_HABIT_CANCEL = "❌ Habit operation cancelled."

    # Reward Management Messages
    HELP_ADD_REWARD_NAME_PROMPT = "Please enter a name for your new reward:"
    ERROR_REWARD_NAME_EMPTY = "❌ Reward name cannot be empty."
    ERROR_REWARD_NAME_TOO_LONG = "❌ Reward name is too long (max 255 characters)."
    ERROR_REWARD_NAME_EXISTS = "❌ A reward with this name already exists. Please choose a different name."
    HELP_ADD_REWARD_TYPE_PROMPT = "Select a reward type:"
    BUTTON_REWARD_TYPE_VIRTUAL = "🖥 Virtual"
    BUTTON_REWARD_TYPE_REAL = "🎁 Real"
    BUTTON_REWARD_TYPE_NONE = "🚫 None"
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
        "<b>Piece Value:</b> {piece_value}\n\n"
        "Create this reward?"
    )
    SUCCESS_REWARD_CREATED = "✅ Reward '<b>{name}</b>' created successfully!"
    INFO_REWARD_CANCEL = "❌ Reward creation cancelled."
    BUTTON_ADD_ANOTHER_REWARD = "➕ Add Another Reward"
    BUTTON_BACK_TO_REWARDS = "🎁 Back to Rewards"
    BUTTON_SKIP = "⏭ Skip"
    BUTTON_CONFIRM = "✅ Create Reward"
    BUTTON_EDIT_REWARD = "✏️ Edit Details"
    BUTTON_PIECES_NOT_ACCUMULATIVE = "1 (Not accumulative)"
    TEXT_NOT_SET = "Not set"
    KEYWORD_SKIP = "skip"

    # Settings Menu
    SETTINGS_MENU = "⚙️ <b>Settings</b>\n\nSelect an option:"
    SETTINGS_SELECT_LANGUAGE = "🌐 Select Language"
    SETTINGS_BACK = "← Back to Settings"

    # Language Selection
    LANGUAGE_SELECTION_MENU = "🌐 <b>Select Language</b>\n\nChoose your preferred language:"

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
            'BUTTON_LIST_REWARDS': "📄 Список наград",
            'BUTTON_MY_REWARDS': "📊 Мои награды",
            'BUTTON_CLAIM_REWARD': "🎯 Получить награду",
            'BUTTON_YES': "✅ Да",
            'BUTTON_NO': "❌ Нет",

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
            'FORMAT_STREAK': "🔥 <b>Серия:</b> {streak_count} дней",
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
            'HELP_ADD_HABIT_CONFIRM': "Проверьте вашу новую привычку:\n<b>Название:</b> {name}\n<b>Вес:</b> {weight}\n<b>Категория:</b> {category}\n\nСоздать эту привычку?",
            'SUCCESS_HABIT_CREATED': "✅ Привычка '<b>{name}</b>' успешно создана!",
            'HELP_HABIT_CREATED_NEXT': "🧩 <b>Ваши привычки:</b>",
            'ERROR_HABIT_NAME_TOO_LONG': "❌ Название привычки слишком длинное (макс. 100 символов).",
            'ERROR_HABIT_NAME_EMPTY': "❌ Название привычки не может быть пустым.",
            'ERROR_WEIGHT_INVALID': "❌ Неверный вес. Выберите значение от 1 до 100.",
            'HELP_EDIT_HABIT_SELECT': "Выберите привычку для редактирования:",
            'HELP_EDIT_HABIT_NAME_PROMPT': "Текущее название: <b>{current_name}</b>\n\nВведите новое название:",
            'HELP_EDIT_HABIT_WEIGHT_PROMPT': "Текущий вес: <b>{current_weight}</b>\n\nВыберите новый вес:",
            'HELP_EDIT_HABIT_CATEGORY_PROMPT': "Текущая категория: <b>{current_category}</b>\n\nВыберите новую категорию:",
            'HELP_EDIT_HABIT_CONFIRM': "Проверьте изменения:\n<b>Название:</b> {old_name} → {new_name}\n<b>Вес:</b> {old_weight} → {new_weight}\n<b>Категория:</b> {old_category} → {new_category}\n\nСохранить изменения?",
            'SUCCESS_HABIT_UPDATED': "✅ Привычка '<b>{name}</b>' успешно обновлена!",
            'HELP_REMOVE_HABIT_SELECT': "Выберите привычку для удаления:",
            'HELP_REMOVE_HABIT_CONFIRM': "Вы уверены, что хотите удалить '<b>{name}</b>'?\n\n⚠️ Это деактивирует привычку. Ваша история будет сохранена.",
            'SUCCESS_HABIT_REMOVED': "✅ Привычка '<b>{name}</b>' успешно удалена.",
            'ERROR_NO_HABITS_TO_EDIT': "❌ У вас нет привычек для редактирования.",
            'ERROR_NO_HABITS_TO_EDIT_PROMPT': "❌ У вас нет привычек для редактирования.\n\nХотите добавить новую привычку?",
            'ERROR_NO_HABITS_TO_REMOVE': "❌ У вас нет привычек для удаления.",
            'INFO_HABIT_CANCEL': "❌ Операция с привычкой отменена.",

            # Reward Management Messages
            'HELP_ADD_REWARD_NAME_PROMPT': "Введите название новой награды:",
            'ERROR_REWARD_NAME_EMPTY': "❌ Название награды не может быть пустым.",
            'ERROR_REWARD_NAME_TOO_LONG': "❌ Название награды слишком длинное (максимум 255 символов).",
            'ERROR_REWARD_NAME_EXISTS': "❌ Награда с таким названием уже существует. Пожалуйста, выберите другое название.",
            'HELP_ADD_REWARD_TYPE_PROMPT': "Выберите тип награды:",
            'BUTTON_REWARD_TYPE_VIRTUAL': "🖥 Виртуальная",
            'BUTTON_REWARD_TYPE_REAL': "🎁 Реальная",
            'BUTTON_REWARD_TYPE_NONE': "🚫 Без награды",
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
                "<b>Ценность части:</b> {piece_value}\n\n"
                "Создать эту награду?"
            ),
            'SUCCESS_REWARD_CREATED': "✅ Награда '<b>{name}</b>' успешно создана!",
            'INFO_REWARD_CANCEL': "❌ Создание награды отменено.",
            'BUTTON_ADD_ANOTHER_REWARD': "➕ Добавить ещё награду",
            'BUTTON_BACK_TO_REWARDS': "🎁 Назад к наградам",
            'BUTTON_SKIP': "⏭ Пропустить",
            'BUTTON_CONFIRM': "✅ Создать награду",
            'BUTTON_EDIT_REWARD': "✏️ Изменить данные",
            'BUTTON_PIECES_NOT_ACCUMULATIVE': "1 (Без накопления)",
            'TEXT_NOT_SET': "Не указано",
            'KEYWORD_SKIP': "пропустить",

            # Settings Menu
            'SETTINGS_MENU': "⚙️ <b>Настройки</b>\n\nВыберите опцию:",
            'SETTINGS_SELECT_LANGUAGE': "🌐 Выбрать язык",
            'SETTINGS_BACK': "← Назад в настройки",

            # Language Selection
            'LANGUAGE_SELECTION_MENU': "🌐 <b>Выбрать язык</b>\n\nВыберите предпочитаемый язык:",
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
            'BUTTON_LIST_REWARDS': "📄 Марапаттар тізімі",
            'BUTTON_MY_REWARDS': "📊 Менің марапаттарым",
            'BUTTON_CLAIM_REWARD': "🎯 Марапат алу",
            'BUTTON_YES': "✅ Иә",
            'BUTTON_NO': "❌ Жоқ",

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
            'FORMAT_STREAK': "🔥 <b>Серия:</b> {streak_count} күн",
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
            'HELP_ADD_HABIT_CONFIRM': "Жаңа әдетіңізді тексеріңіз:\n<b>Аты:</b> {name}\n<b>Салмақ:</b> {weight}\n<b>Санат:</b> {category}\n\nОсы әдетті жасау керек пе?",
            'SUCCESS_HABIT_CREATED': "✅ '<b>{name}</b>' әдеті сәтті жасалды!",
            'HELP_HABIT_CREATED_NEXT': "🧩 <b>Сіздің әдеттеріңіз:</b>",
            'ERROR_HABIT_NAME_TOO_LONG': "❌ Әдет атауы тым ұзын (макс. 100 таңба).",
            'ERROR_HABIT_NAME_EMPTY': "❌ Әдет атауы бос болуы мүмкін емес.",
            'ERROR_WEIGHT_INVALID': "❌ Қате салмақ. 1-ден 100-ге дейін мән таңдаңыз.",
            'HELP_EDIT_HABIT_SELECT': "Өңдеу үшін әдетті таңдаңыз:",
            'HELP_EDIT_HABIT_NAME_PROMPT': "Ағымдағы аты: <b>{current_name}</b>\n\nЖаңа атын енгізіңіз:",
            'HELP_EDIT_HABIT_WEIGHT_PROMPT': "Ағымдағы салмақ: <b>{current_weight}</b>\n\nЖаңа салмақты таңдаңыз:",
            'HELP_EDIT_HABIT_CATEGORY_PROMPT': "Ағымдағы санат: <b>{current_category}</b>\n\nЖаңа санатты таңдаңыз:",
            'HELP_EDIT_HABIT_CONFIRM': "Өзгерістерді тексеріңіз:\n<b>Аты:</b> {old_name} → {new_name}\n<b>Салмақ:</b> {old_weight} → {new_weight}\n<b>Санат:</b> {old_category} → {new_category}\n\nӨзгерістерді сақтау керек пе?",
            'SUCCESS_HABIT_UPDATED': "✅ '<b>{name}</b>' әдеті сәтті жаңартылды!",
            'HELP_REMOVE_HABIT_SELECT': "Жою үшін әдетті таңдаңыз:",
            'HELP_REMOVE_HABIT_CONFIRM': "Сіз '<b>{name}</b>' жоюға сенімдісіз бе?\n\n⚠️ Бұл әдетті белсенсіз етеді. Тарихыңыз сақталады.",
            'SUCCESS_HABIT_REMOVED': "✅ '<b>{name}</b>' әдеті сәтті жойылды.",
            'ERROR_NO_HABITS_TO_EDIT': "❌ Өңдеуге әдеттеріңіз жоқ.",
            'ERROR_NO_HABITS_TO_EDIT_PROMPT': "❌ Өңдеуге әдеттеріңіз жоқ.\n\nЖаңа әдет қосқыңыз келе ме?",
            'ERROR_NO_HABITS_TO_REMOVE': "❌ Жоюға әдеттеріңіз жоқ.",
            'INFO_HABIT_CANCEL': "❌ Әдет операциясы болдырылмады.",

            # Reward Management Messages
            'HELP_ADD_REWARD_NAME_PROMPT': "Жаңа сыйлықтың атауын енгізіңіз:",
            'ERROR_REWARD_NAME_EMPTY': "❌ Сыйлық атауы бос болмауы тиіс.",
            'ERROR_REWARD_NAME_TOO_LONG': "❌ Сыйлық атауы тым ұзын (ең көбі 255 таңба).",
            'ERROR_REWARD_NAME_EXISTS': "❌ Бұл атаумен сыйлық бар. Басқа атауды таңдаңыз.",
            'HELP_ADD_REWARD_TYPE_PROMPT': "Сыйлық түрін таңдаңыз:",
            'BUTTON_REWARD_TYPE_VIRTUAL': "🖥 Виртуалды",
            'BUTTON_REWARD_TYPE_REAL': "🎁 Нақты",
            'BUTTON_REWARD_TYPE_NONE': "🚫 Сыйлық жоқ",
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
                "<b>Бөлік құны:</b> {piece_value}\n\n"
                "Бұл сыйлықты жасаймыз ба?"
            ),
            'SUCCESS_REWARD_CREATED': "✅ '<b>{name}</b>' сыйлығы сәтті құрылды!",
            'INFO_REWARD_CANCEL': "❌ Сыйлық жасау тоқтатылды.",
            'BUTTON_ADD_ANOTHER_REWARD': "➕ Тағы бір сыйлық қосу",
            'BUTTON_BACK_TO_REWARDS': "🎁 Сыйлықтар мәзіріне оралу",
            'BUTTON_SKIP': "⏭ Өткізу",
            'BUTTON_CONFIRM': "✅ Сыйлық жасау",
            'BUTTON_EDIT_REWARD': "✏️ Мәліметтерді түзету",
            'BUTTON_PIECES_NOT_ACCUMULATIVE': "1 (Жинақсыз)",
            'TEXT_NOT_SET': "Көрсетілмеген",
            'KEYWORD_SKIP': "өткізу",

            # Settings Menu
            'SETTINGS_MENU': "⚙️ <b>Параметрлер</b>\n\nОпцияны таңдаңыз:",
            'SETTINGS_SELECT_LANGUAGE': "🌐 Тілді таңдау",
            'SETTINGS_BACK': "← Параметрлерге оралу",

            # Language Selection
            'LANGUAGE_SELECTION_MENU': "🌐 <b>Тілді таңдау</b>\n\nҚалаған тіліңізді таңдаңыз:",
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
