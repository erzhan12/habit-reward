"""Language detection and management utilities."""

import logging
from telegram import Update

from src.config import settings
from src.airtable.repositories import user_repository

logger = logging.getLogger(__name__)


def get_user_language(telegram_id: str) -> str:
    """
    Get user's preferred language from database.

    Args:
        telegram_id: Telegram user ID

    Returns:
        Language code (e.g., 'en', 'ru', 'kk'), defaults to config default if user not found
    """
    user = user_repository.get_by_telegram_id(telegram_id)
    if user and user.language:
        # Normalize and validate
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
    """
    Get language for message display using fallback chain.

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
    # Try to get from user database
    user = user_repository.get_by_telegram_id(telegram_id)
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


def set_user_language(telegram_id: str, language_code: str) -> bool:
    """
    Update user's language preference.

    Args:
        telegram_id: Telegram user ID
        language_code: New language code (e.g., 'en', 'ru', 'kk')

    Returns:
        True if successfully updated, False otherwise
    """
    user = user_repository.get_by_telegram_id(telegram_id)
    if not user:
        return False

    # Normalize and validate language code
    lang = language_code.lower()[:2]
    if lang not in settings.supported_languages:
        return False

    # Update user language
    try:
        user_repository.update(user.id, {"language": lang})
        return True
    except Exception as e:
        logger.error(f"Failed to update language for user {telegram_id}: {e}")
        return False
