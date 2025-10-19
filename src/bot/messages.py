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
    INFO_MULTIPLE_HABITS = "I also detected: {other_habits}. Use /habit_done to log those separately."
    INFO_NO_REWARDS_TO_CLAIM = "You have no rewards ready to claim yet. Keep logging habits to earn rewards!"

    # Usage/Help Messages
    HELP_CLAIM_REWARD_USAGE = "Usage: /claim_reward <reward_name>\nExample: /claim_reward Coffee at favorite cafe"
    HELP_HABIT_SELECTION = "Which habit did you complete? 🎯\n\nSelect from the list below:"
    HELP_CUSTOM_TEXT = "Please type what habit you completed:"
    HELP_SELECT_REWARD_TO_CLAIM = "🎁 <b>Select a reward to claim:</b>"

    # Success Messages
    SUCCESS_HABIT_COMPLETED = "✅ <b>Habit completed:</b> {habit_name}"
    SUCCESS_REWARD_CLAIMED = "✅ Reward claimed: <b>{reward_name}</b>\nStatus: {status}\n\nCongratulations! 🎉"
    SUCCESS_STATUS_UPDATED = "✅ Reward status updated: <b>{reward_name}</b>\nNew status: {status}"
    SUCCESS_REWARD_CLAIMED_HEADER = "✅ <b>Reward claimed:</b> {reward_name}"

    # Headers/Titles
    HEADER_REWARD_PROGRESS = "🎁 <b>Your Reward Progress:</b>\n"
    HEADER_STREAKS = "🔥 <b>Your Current Streaks:</b>\n"
    HEADER_REWARDS_LIST = "🎁 <b>Available Rewards:</b>\n"
    HEADER_HABIT_LOGS = "📋 <b>Recent Habit Completions:</b>\n"
    HEADER_UPDATED_REWARD_PROGRESS = "\n📊 <b>Your updated reward progress:</b>"

    # Welcome/Help Messages
    HELP_START_MESSAGE = """🎯 <b>Welcome to Habit Reward System!</b>

Track your habits and earn rewards!

<b>Available commands:</b>
/habit_done - Log a completed habit
/streaks - View your current streaks
/list_rewards - See all available rewards
/my_rewards - Check your reward progress
/claim_reward - Claim an achieved reward
/settings - Change language and preferences
/help - Show this help message"""

    HELP_COMMAND_MESSAGE = """🎯 <b>Habit Reward System Help</b>

<b>Core Commands:</b>
/habit_done - Log a habit completion and earn rewards
/streaks - View your current streaks for all habits

<b>Reward Commands:</b>
/list_rewards - List all available rewards
/my_rewards - View your cumulative reward progress
/claim_reward - Mark an achieved reward as completed

<b>Settings:</b>
/settings - Change language and preferences

<b>How it works:</b>
1. Complete a habit using /habit_done
2. Build streaks by completing habits daily
3. Earn reward pieces (cumulative rewards)
4. Claim rewards when you have enough pieces

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
            'INFO_MULTIPLE_HABITS': "Также обнаружены: {other_habits}. Используйте /habit_done для их регистрации.",
            'INFO_NO_REWARDS_TO_CLAIM': "У вас пока нет наград для получения. Продолжайте регистрировать привычки, чтобы заработать награды!",

            # Usage/Help Messages
            'HELP_CLAIM_REWARD_USAGE': "Использование: /claim_reward <название_награды>\nПример: /claim_reward Кофе в любимом кафе",
            'HELP_HABIT_SELECTION': "Какую привычку вы выполнили? 🎯\n\nВыберите из списка ниже:",
            'HELP_CUSTOM_TEXT': "Напишите, какую привычку вы выполнили:",
            'HELP_SELECT_REWARD_TO_CLAIM': "🎁 <b>Выберите награду для получения:</b>",

            # Success Messages
            'SUCCESS_HABIT_COMPLETED': "✅ <b>Привычка выполнена:</b> {habit_name}",
            'SUCCESS_REWARD_CLAIMED': "✅ Награда получена: <b>{reward_name}</b>\nСтатус: {status}\n\nПоздравляем! 🎉",
            'SUCCESS_STATUS_UPDATED': "✅ Статус награды обновлён: <b>{reward_name}</b>\nНовый статус: {status}",
            'SUCCESS_REWARD_CLAIMED_HEADER': "✅ <b>Награда получена:</b> {reward_name}",

            # Headers/Titles
            'HEADER_REWARD_PROGRESS': "🎁 <b>Ваш прогресс по наградам:</b>\n",
            'HEADER_STREAKS': "🔥 <b>Ваши текущие серии:</b>\n",
            'HEADER_REWARDS_LIST': "🎁 <b>Доступные награды:</b>\n",
            'HEADER_HABIT_LOGS': "📋 <b>Недавние выполнения привычек:</b>\n",
            'HEADER_UPDATED_REWARD_PROGRESS': "\n📊 <b>Ваш обновлённый прогресс по наградам:</b>",

            # Welcome/Help Messages
            'HELP_START_MESSAGE': """🎯 <b>Добро пожаловать в систему наград за привычки!</b>

Отслеживайте привычки и получайте награды!

<b>Доступные команды:</b>
/habit_done - Зарегистрировать выполненную привычку
/streaks - Посмотреть текущие серии
/list_rewards - Посмотреть все доступные награды
/my_rewards - Проверить прогресс по наградам
/claim_reward - Забрать достигнутую награду
/settings - Изменить язык и настройки
/help - Показать это сообщение помощи""",

            'HELP_COMMAND_MESSAGE': """🎯 <b>Помощь по системе наград за привычки</b>

<b>Основные команды:</b>
/habit_done - Зарегистрировать выполнение привычки и получить награды
/streaks - Посмотреть текущие серии для всех привычек

<b>Команды наград:</b>
/list_rewards - Показать все доступные награды
/my_rewards - Посмотреть накопленный прогресс по наградам
/claim_reward - Отметить достигнутую награду как завершённую

<b>Настройки:</b>
/settings - Изменить язык и настройки

<b>Как это работает:</b>
1. Выполняйте привычки через /habit_done
2. Создавайте серии, выполняя привычки ежедневно
3. Зарабатывайте части наград (накопительные награды)
4. Забирайте награды, когда наберёте достаточно частей

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
            'INFO_MULTIPLE_HABITS': "Сондай-ақ табылды: {other_habits}. Оларды тіркеу үшін /habit_done пайдаланыңыз.",
            'INFO_NO_REWARDS_TO_CLAIM': "Әлі алуға дайын сыйлықтарыңыз жоқ. Сыйлықтар табу үшін әдеттерді тіркеуді жалғастырыңыз!",

            # Usage/Help Messages
            'HELP_CLAIM_REWARD_USAGE': "Пайдалану: /claim_reward <сыйлық_аты>\nМысал: /claim_reward Сүйікті кафеде кофе",
            'HELP_HABIT_SELECTION': "Қандай әдетті орындадыңыз? 🎯\n\nТөмендегі тізімнен таңдаңыз:",
            'HELP_CUSTOM_TEXT': "Қандай әдетті орындағаныңызды жазыңыз:",
            'HELP_SELECT_REWARD_TO_CLAIM': "🎁 <b>Алатын сыйлықты таңдаңыз:</b>",

            # Success Messages
            'SUCCESS_HABIT_COMPLETED': "✅ <b>Әдет орындалды:</b> {habit_name}",
            'SUCCESS_REWARD_CLAIMED': "✅ Сыйлық алынды: <b>{reward_name}</b>\nСтатус: {status}\n\nКұттықтаймыз! 🎉",
            'SUCCESS_STATUS_UPDATED': "✅ Сыйлық статусы жаңартылды: <b>{reward_name}</b>\nЖаңа статус: {status}",
            'SUCCESS_REWARD_CLAIMED_HEADER': "✅ <b>Сыйлық алынды:</b> {reward_name}",

            # Headers/Titles
            'HEADER_REWARD_PROGRESS': "🎁 <b>Сіздің сыйлық бойынша прогресс:</b>\n",
            'HEADER_STREAKS': "🔥 <b>Сіздің ағымдағы сериялар:</b>\n",
            'HEADER_REWARDS_LIST': "🎁 <b>Қолжетімді сыйлықтар:</b>\n",
            'HEADER_HABIT_LOGS': "📋 <b>Соңғы орындалған әдеттер:</b>\n",
            'HEADER_UPDATED_REWARD_PROGRESS': "\n📊 <b>Сіздің жаңартылған сыйлық прогресі:</b>",

            # Welcome/Help Messages
            'HELP_START_MESSAGE': """🎯 <b>Әдеттер үшін сыйлықтар жүйесіне қош келдіңіз!</b>

Әдеттерді қадағалаңыз және сыйлықтар алыңыз!

<b>Қолжетімді команdalар:</b>
/habit_done - Орындалған әдетті тіркеу
/streaks - Ағымдағы сериялар көру
/list_rewards - Барлық қолжетімді сыйлықтарды көру
/my_rewards - Сыйлықтар бойынша прогресті тексеру
/claim_reward - Қол жеткізілген сыйлықты алу
/settings - Тілді және параметрлерді өзгерту
/help - Осы анықтаманы көрсету""",

            'HELP_COMMAND_MESSAGE': """🎯 <b>Әдеттер үшін сыйлықтар жүйесі бойынша анықтама</b>

<b>Негізгі командалар:</b>
/habit_done - Әдет орындауды тіркеу және сыйлықтар алу
/streaks - Барлық әдеттер үшін ағымдағы сериялар көру

<b>Сыйлықтар командалары:</b>
/list_rewards - Барлық қолжетімді сыйлықтарды көрсету
/my_rewards - Жинақталған сыйлық прогресін көру
/claim_reward - Қол жеткізілген сыйлықты аяқталған деп белгілеу

<b>Параметрлер:</b>
/settings - Тілді және параметрлерді өзгерту

<b>Бұл қалай жұмысістейді:</b>
1. /habit_done арқылы әдеттерді орындаңыз
2. Әдеттерді күн сайын орындау арқылы сериялар жасаңыз
3. Сыйлық бөліктерін жинаңыз (жинақталатын сыйлықтар)
4. Жеткілікті бөліктер жинағанда сыйлықтарды алыңыз

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
