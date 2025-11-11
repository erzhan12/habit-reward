"""Language detection and management utilities."""

import logging
from telegram import Update
from asgiref.sync import async_to_sync

from src.config import settings
from src.core.repositories import user_repository as default_user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)


def _resolve_user_repository():
    """Return user repository, honoring patches on src.bot.main."""

    try:
        from src.bot import main as bot_main  # Local import avoids circular dependency
    except ModuleNotFoundError:
        return default_user_repository

    return getattr(bot_main, "user_repository", default_user_repository)


def get_user_language(telegram_id: str) -> str:
    """Fetch the persisted language for synchronous callers."""
    repo = _resolve_user_repository()
    user = async_to_sync(repo.get_by_telegram_id)(telegram_id)
    if user and user.language:
        lang = user.language.lower()[:2]
        if lang in settings.supported_languages:
            return lang
    return settings.default_language


def detect_language_from_telegram(update: Update) -> str:
    """
    Detect language from Telegram user settings.

    Args:
        update: Telegram Update object

    Returns:
        Language code detected from Telegram, or default language
    """
    if update and update.effective_user:
        telegram_lang = update.effective_user.language_code
        if telegram_lang:
            # Normalize to 2-letter lowercase code
            lang = telegram_lang.lower()[:2]
            # Check if supported
            if lang in settings.supported_languages:
                return lang
    return settings.default_language


def get_message_language(telegram_id: str, update: Update | None = None) -> str:
    """Synchronous helper that mirrors async language detection."""
    repo = _resolve_user_repository()
    user = async_to_sync(repo.get_by_telegram_id)(telegram_id)
    if user and user.language:
        lang = user.language.lower()[:2]
        if lang in settings.supported_languages:
            return lang

    if update:
        telegram_lang = detect_language_from_telegram(update)
        if telegram_lang != settings.default_language:
            return telegram_lang

    return settings.default_language


async def get_message_language_async(telegram_id: str, update: Update | None = None) -> str:
    """
    Async version: Get language for message display using fallback chain.

    Fallback order:
    1. User's saved language preference in database
    2. Telegram user's language setting (if update provided)
    3. System default language

    Args:
        telegram_id: Telegram user ID
        update: Optional Telegram Update object

    Returns:
        Language code to use for messages
    """
    # Try to get from user database (async)
    repo = _resolve_user_repository()
    user = await maybe_await(repo.get_by_telegram_id(telegram_id))
    if user and user.language:
        lang = user.language.lower()[:2]
        if lang in settings.supported_languages:
            return lang

    # Try to detect from Telegram
    if update:
        telegram_lang = detect_language_from_telegram(update)
        if telegram_lang != settings.default_language:
            return telegram_lang

    # Fallback to default
    return settings.default_language


async def set_user_language(telegram_id: str, language_code: str) -> bool:
    """Persist the user's preferred language.

    Args:
        telegram_id: Telegram user ID
        language_code: Desired 2-letter language code (en, ru, kk)

    Returns:
        True if the update succeeds, False otherwise.
    """
    repo = _resolve_user_repository()
    user = await maybe_await(repo.get_by_telegram_id(telegram_id))
    if not user:
        logger.warning("Attempted to set language for unknown user %s", telegram_id)
        return False

    # Normalize and validate language code
    lang = language_code.lower()[:2]
    if lang not in settings.supported_languages:
        logger.warning(
            "Unsupported language '%s' provided for user %s", language_code, telegram_id
        )
        return False

    if user.language == lang:
        logger.info("Language for user %s already set to %s", telegram_id, lang)
        return True

    try:
        await maybe_await(repo.update(user.id, {"language": lang}))
        logger.info("Updated language for user %s to %s", telegram_id, lang)
        return True
    except Exception as exc:
        logger.error("Failed to update language for user %s: %s", telegram_id, exc)
        return False
