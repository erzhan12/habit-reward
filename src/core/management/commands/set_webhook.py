"""Django management command to set Telegram webhook URL."""

import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
import telegram


class Command(BaseCommand):
    """Set Telegram webhook URL for production deployment."""

    help = 'Set Telegram webhook URL for bot'

    async def set_webhook_async(self):
        """Async method to set webhook."""
        bot = telegram.Bot(settings.TELEGRAM_BOT_TOKEN)
        webhook_url = settings.TELEGRAM_WEBHOOK_URL

        if not webhook_url:
            self.stdout.write(self.style.ERROR(
                '❌ TELEGRAM_WEBHOOK_URL not set in settings'
            ))
            self.stdout.write(self.style.WARNING(
                'Set TELEGRAM_WEBHOOK_URL in your .env file (e.g., https://yourdomain.com/webhook/telegram)'
            ))
            return

        self.stdout.write(f'Setting webhook to: {webhook_url}')

        # Set webhook
        await bot.set_webhook(url=webhook_url)

        # Verify
        webhook_info = await bot.get_webhook_info()
        self.stdout.write(self.style.SUCCESS(f'✅ Webhook set: {webhook_info.url}'))
        self.stdout.write(f'Pending updates: {webhook_info.pending_update_count}')

        if webhook_info.last_error_message:
            self.stdout.write(self.style.WARNING(
                f'⚠️ Last error: {webhook_info.last_error_message}'
            ))

    def handle(self, *args, **options):
        """Handle the command."""
        asyncio.run(self.set_webhook_async())
