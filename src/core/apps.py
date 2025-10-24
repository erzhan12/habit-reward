"""Django app configuration for core app."""

import asyncio
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """Configuration for core app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.core'
    verbose_name = 'Habit Reward Core'

    def ready(self):
        """Initialize Telegram bot handlers when Django starts.

        This method is called once when Django initializes the app.
        We use it to register all Telegram bot handlers for webhook mode.
        """
        # Only setup handlers if webhook mode is configured
        from django.conf import settings

        if not settings.TELEGRAM_WEBHOOK_URL:
            # Skip handler setup in polling mode (development)
            logger.info("ℹ️ TELEGRAM_WEBHOOK_URL not set - skipping webhook handler setup")
            logger.info("ℹ️ Use polling mode for development: python src/bot/main.py")
            return

        try:
            # Import setup_handlers function
            from src.bot.webhook_handler import setup_handlers_sync

            # Run setup synchronously (handlers will be initialized on first request)
            logger.info("🔧 Initializing Telegram webhook handlers...")
            setup_handlers_sync()
            logger.info("✅ Telegram webhook handlers initialized successfully")

        except ImportError as e:
            logger.warning(f"⚠️ Could not import webhook handler: {e}")
            logger.warning("This is expected if webhook_handler.py doesn't exist yet")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram handlers: {e}", exc_info=True)
            # Don't raise - allow Django to start even if handler setup fails
            # This prevents the entire app from crashing due to bot configuration issues
