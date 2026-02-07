"""Telegram webhook handler for Django ASGI deployment."""

import json
import logging
from telegram import Update
from telegram.ext import Application, PicklePersistence
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize persistence for conversation state
persistence = PicklePersistence(filepath='telegram_bot_persistence.pkl')

# Initialize application (singleton) with persistence
application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).persistence(persistence).build()
_initialized = False


def setup_handlers_sync():
    """Synchronous handler setup (called from Django apps.py).

    This only registers handlers. The application will be initialized
    lazily on the first webhook request.
    """
    logger.info("🔧 Registering Telegram bot handlers...")

    # Import all handlers
    from telegram.ext import CommandHandler
    from src.bot.handlers.command_handlers import start_command, help_command
    from src.bot.handlers.habit_done_handler import habit_done_conversation
    from src.bot.handlers.habit_revert_handler import habit_revert_conversation
    from src.bot.handlers.backdate_handler import backdate_conversation
    from src.bot.handlers.habit_management_handler import (
        add_habit_conversation,
        edit_habit_conversation,
        remove_habit_conversation
    )
    from src.bot.handlers.reward_handlers import (
        list_rewards_command,
        my_rewards_command,
        claim_reward_conversation,
        add_reward_conversation,
        edit_reward_conversation,
        toggle_reward_conversation,
    )
    from src.bot.handlers.streak_handler import streaks_command
    from src.bot.handlers.settings_handler import settings_conversation
    from src.bot.handlers.menu_handler import get_menu_handlers

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add conversation handler for habit_done
    application.add_handler(habit_done_conversation)
    application.add_handler(habit_revert_conversation)
    application.add_handler(backdate_conversation)

    # Add habit management conversation handlers
    application.add_handler(add_habit_conversation)
    application.add_handler(edit_habit_conversation)
    application.add_handler(remove_habit_conversation)

    # Add reward handlers
    application.add_handler(CommandHandler("list_rewards", list_rewards_command))
    application.add_handler(CommandHandler("my_rewards", my_rewards_command))
    application.add_handler(claim_reward_conversation)
    application.add_handler(add_reward_conversation)
    application.add_handler(edit_reward_conversation)
    application.add_handler(toggle_reward_conversation)

    # Add streak handler
    application.add_handler(CommandHandler("streaks", streaks_command))

    # Add settings handler
    application.add_handler(settings_conversation)

    # Register menu callbacks in group 1 so they run alongside ConversationHandlers
    # (ConversationHandlers in group 0 end conversations; group 1 handles navigation)
    for handler in get_menu_handlers():
        application.add_handler(handler, group=1)

    # DEBUG: Add catch-all callback handler to log all callbacks
    from telegram.ext import CallbackQueryHandler
    async def debug_all_callbacks(update: Update, context):
        query = update.callback_query
        user_id = update.effective_user.id
        logger.debug(f"🟢 GLOBAL DEBUG: Callback received - user: {user_id}, data: {query.data}")
        # Don't answer, let other handlers process it
        return None

    # Add as lowest priority (catches what others miss)
    application.add_handler(CallbackQueryHandler(debug_all_callbacks), group=999)

    logger.info("✅ All Telegram handlers registered")


async def _ensure_initialized():
    """Ensure the application is initialized (lazy initialization).

    This is called on the first webhook request to initialize the
    Telegram Application in the running event loop.

    Note: We skip calling get_me() to avoid timeout on first webhook request.
    """
    global _initialized
    if not _initialized:
        logger.info("🔧 Initializing Telegram Application (lazy init)...")
        # Initialize the entire application (not just the bot)
        # In python-telegram-bot v20+, Application.initialize() is required for webhook mode
        await application.initialize()
        if application.job_queue:
            await application.job_queue.start()
            logger.info("✅ Job queue started")
        else:
            logger.warning("⚠️ JobQueue unavailable; scheduled jobs will not run")
        _initialized = True
        logger.info("✅ Telegram Application initialized")


@csrf_exempt
async def telegram_webhook(request):
    """Handle incoming Telegram webhook requests.

    This view processes webhook updates from Telegram when running in
    production mode with ASGI server (e.g., Uvicorn).

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse with 'ok' on success, HttpResponseBadRequest on error
    """
    if request.method != 'POST':
        logger.warning(f"⚠️ Received {request.method} request to webhook endpoint")
        return HttpResponseBadRequest('Only POST requests are allowed')

    try:
        # Ensure application is initialized (lazy init on first request)
        await _ensure_initialized()

        # Parse update from request body
        update_data = json.loads(request.body)
        logger.debug(f"📨 Received webhook update: {update_data.get('update_id', 'unknown')}")

        update = Update.de_json(update_data, application.bot)

        # Process update
        await application.process_update(update)

        return HttpResponse('ok')

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in webhook: {e}")
        return HttpResponseBadRequest(f'Invalid JSON: {e}')
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        return HttpResponseBadRequest(str(e))
