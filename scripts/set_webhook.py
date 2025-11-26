#!/usr/bin/env python
"""Script to set Telegram webhook.

This script sets the Telegram webhook URL for the bot using the configuration
from the .env file. It also provides webhook status information.

Usage:
    python scripts/set_webhook.py              # Set webhook
    python scripts/set_webhook.py --delete     # Delete webhook
    python scripts/set_webhook.py --info       # Show webhook info only
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
import django
django.setup()

from django.conf import settings
import requests


def get_webhook_info():
    """Get current webhook information from Telegram.

    Returns:
        dict: Webhook information from Telegram API
    """
    token = settings.TELEGRAM_BOT_TOKEN
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        info = response.json()

        if info.get('ok'):
            return info['result']
        else:
            print(f"❌ Failed to get webhook info: {info.get('description')}")
            return None
    except requests.RequestException as e:
        print(f"❌ Network error getting webhook info: {e}")
        return None


def display_webhook_info(info):
    """Display webhook information in a formatted way.

    Args:
        info (dict): Webhook information from Telegram API
    """
    if not info:
        return

    print("\n" + "=" * 60)
    print("📊 CURRENT WEBHOOK INFO")
    print("=" * 60)

    url = info.get('url', '')
    if url:
        print(f"URL: {url}")
        print("Status: ✅ Webhook is SET")
    else:
        print("URL: (not set)")
        print("Status: ⚠️ No webhook configured (using polling mode)")

    print(f"Pending updates: {info.get('pending_update_count', 0)}")
    print(f"Max connections: {info.get('max_connections', 'N/A')}")

    if info.get('ip_address'):
        print(f"IP address: {info.get('ip_address')}")

    if info.get('last_error_date'):
        print("\n⚠️ LAST ERROR:")
        print(f"   Message: {info.get('last_error_message', 'Unknown')}")
        print(f"   Date: {info.get('last_error_date')}")

    if info.get('last_synchronization_error_date'):
        print("\n⚠️ LAST SYNC ERROR:")
        print(f"   Date: {info.get('last_synchronization_error_date')}")

    print("=" * 60 + "\n")


def set_webhook(drop_pending_updates=False):
    """Set Telegram webhook using bot token and webhook URL from settings.

    Args:
        drop_pending_updates (bool): Whether to drop pending updates when setting webhook

    Returns:
        bool: True if webhook was set successfully, False otherwise
    """
    token = settings.TELEGRAM_BOT_TOKEN
    webhook_url = settings.TELEGRAM_WEBHOOK_URL

    # Validate configuration
    if not webhook_url:
        print("\n❌ ERROR: TELEGRAM_WEBHOOK_URL not set in .env file")
        print("\nTo set webhook, add this to your .env file:")
        print("TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook/telegram")
        print("\nExample:")
        print("TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app/webhook/telegram")
        return False

    if not webhook_url.startswith('https://'):
        print("\n❌ ERROR: Webhook URL must use HTTPS")
        print(f"Current URL: {webhook_url}")
        return False

    if '/webhook/telegram' not in webhook_url:
        print("\n⚠️ WARNING: Webhook URL should end with /webhook/telegram")
        print(f"Current URL: {webhook_url}")
        print("\nExpected format: https://your-domain.com/webhook/telegram")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            return False

    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    data = {'url': webhook_url}
    if drop_pending_updates:
        data['drop_pending_updates'] = True

    print("\n" + "=" * 60)
    print("🔧 SETTING WEBHOOK")
    print("=" * 60)
    print(f"Webhook URL: {webhook_url}")
    if drop_pending_updates:
        print("Drop pending updates: Yes")
    print("=" * 60)

    try:
        response = requests.post(api_url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get('ok'):
            print("\n✅ Webhook set successfully!\n")
            return True
        else:
            print(f"\n❌ Failed to set webhook: {result.get('description')}\n")
            return False
    except requests.RequestException as e:
        print(f"\n❌ Network error setting webhook: {e}\n")
        return False


def delete_webhook(drop_pending_updates=False):
    """Delete the current webhook (switches bot to polling mode).

    Args:
        drop_pending_updates (bool): Whether to drop pending updates when deleting webhook

    Returns:
        bool: True if webhook was deleted successfully, False otherwise
    """
    token = settings.TELEGRAM_BOT_TOKEN
    api_url = f"https://api.telegram.org/bot{token}/deleteWebhook"

    data = {}
    if drop_pending_updates:
        data['drop_pending_updates'] = True

    print("\n" + "=" * 60)
    print("🗑️ DELETING WEBHOOK")
    print("=" * 60)
    if drop_pending_updates:
        print("Drop pending updates: Yes")
    print("This will switch the bot to polling mode.")
    print("=" * 60)

    try:
        response = requests.post(api_url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get('ok'):
            print("\n✅ Webhook deleted successfully!\n")
            print("Bot is now in polling mode.")
            print("To use the bot, run: uv run python src/bot/main.py\n")
            return True
        else:
            print(f"\n❌ Failed to delete webhook: {result.get('description')}\n")
            return False
    except requests.RequestException as e:
        print(f"\n❌ Network error deleting webhook: {e}\n")
        return False


def validate_configuration():
    """Validate that required configuration is present.

    Returns:
        bool: True if configuration is valid, False otherwise
    """
    issues = []

    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'test_token':
        issues.append("TELEGRAM_BOT_TOKEN is not set or using default test value")

    if issues:
        print("\n❌ CONFIGURATION ISSUES:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nPlease check your .env file and ensure all required variables are set.\n")
        return False

    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Manage Telegram webhook configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/set_webhook.py                    # Set webhook
  python scripts/set_webhook.py --info             # Show webhook info
  python scripts/set_webhook.py --delete           # Delete webhook
  python scripts/set_webhook.py --drop-pending     # Set webhook and drop pending updates
  python scripts/set_webhook.py --delete --drop-pending  # Delete and drop pending
        """
    )

    parser.add_argument(
        '--info',
        action='store_true',
        help='Show current webhook information only (no changes)'
    )

    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete the webhook (switch to polling mode)'
    )

    parser.add_argument(
        '--drop-pending',
        action='store_true',
        help='Drop pending updates when setting/deleting webhook'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🤖 TELEGRAM WEBHOOK MANAGER")
    print("=" * 60)
    print(f"Project: {settings.BASE_DIR.name}")
    print("=" * 60 + "\n")

    # Validate configuration
    if not validate_configuration():
        sys.exit(1)

    # Get and display current webhook info
    current_info = get_webhook_info()

    # If --info flag, just show info and exit
    if args.info:
        display_webhook_info(current_info)
        sys.exit(0)

    # Show current state before making changes
    if current_info:
        current_url = current_info.get('url', '')
        if current_url:
            print(f"Current webhook: {current_url}")
        else:
            print("Current mode: Polling (no webhook set)")
        print()

    # Perform action
    success = False
    if args.delete:
        success = delete_webhook(drop_pending_updates=args.drop_pending)
    else:
        success = set_webhook(drop_pending_updates=args.drop_pending)

    # Show updated webhook info
    if success:
        updated_info = get_webhook_info()
        display_webhook_info(updated_info)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
