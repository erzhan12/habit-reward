"""Navigation stack management for unified menu navigation.

This module provides functions to track navigation history, enabling seamless
back button navigation between menu screens by editing messages in-place.
"""

import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def push_navigation(context: ContextTypes.DEFAULT_TYPE, message_id: int, menu_type: str, lang: str) -> None:
    """
    Push a new navigation state onto the stack.

    Args:
        context: Telegram context object
        message_id: ID of the current menu message
        menu_type: Type of menu ('start', 'habits', 'rewards')
        lang: User's language preference
    """
    if 'navigation_stack' not in context.user_data:
        context.user_data['navigation_stack'] = []

    context.user_data['navigation_stack'].append({
        'message_id': message_id,
        'menu_type': menu_type,
        'lang': lang
    })
    context.user_data['last_language'] = lang

    logger.info(f"🔝 Pushed navigation: {menu_type} (message_id: {message_id}, lang: {lang})")


def pop_navigation(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Pop the current navigation state and return the previous one.

    Args:
        context: Telegram context object

    Returns:
        Previous navigation state dict, or default 'start' state if stack is empty
    """
    if 'navigation_stack' not in context.user_data:
        context.user_data['navigation_stack'] = []

    stack = context.user_data['navigation_stack']

    # Pop current state if exists
    if stack:
        current = stack.pop()
        logger.info(f"⬇️ Popped navigation: {current['menu_type']}")

    # Return previous state or default to start
    if stack:
        prev = stack[-1]
        logger.info(f"↩️ Returning to: {prev['menu_type']}")
        return prev
    else:
        logger.info(f"↩️ Stack empty, returning to start menu")
        last_lang = context.user_data.get('last_language', 'en')
        return {'menu_type': 'start', 'lang': last_lang}


def get_current_navigation(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """
    Get the current navigation state without modifying the stack.

    Args:
        context: Telegram context object

    Returns:
        Current navigation state dict, or None if stack is empty
    """
    if 'navigation_stack' not in context.user_data:
        return None

    stack = context.user_data['navigation_stack']
    return stack[-1] if stack else None


def clear_navigation(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Clear the entire navigation stack.

    Args:
        context: Telegram context object
    """
    context.user_data['navigation_stack'] = []
    logger.info(f"🧹 Cleared navigation stack")


def update_navigation_language(context: ContextTypes.DEFAULT_TYPE, new_lang: str) -> None:
    """Update stored navigation states to reflect a new language preference."""
    stack = context.user_data.get('navigation_stack')
    if stack:
        for state in stack:
            state['lang'] = new_lang
    context.user_data['last_language'] = new_lang
    logger.info("🔁 Updated navigation stack language to %s", new_lang)
