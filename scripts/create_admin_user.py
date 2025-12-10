#!/usr/bin/env python
"""Create admin superuser for Django admin panel.

This script creates a new Django superuser with all required fields
including telegram_id and name.

Usage:
    python scripts/create_admin_user.py
    python scripts/create_admin_user.py --username admin --telegram-id admin123 --name "Admin User"
    python scripts/create_admin_user.py --username admin --password mypass123
"""
import os
import sys
import argparse
import getpass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def create_admin_user(
    username='admin',
    telegram_id=None,
    name=None,
    email=None,
    password=None,
    interactive=True
):
    """Create a new admin superuser.

    Args:
        username (str): Username for the admin user
        telegram_id (str): Telegram ID (required, will prompt if not provided)
        name (str): Display name (required, will prompt if not provided)
        email (str): Email address (optional)
        password (str): Password (will prompt if not provided and interactive=True)
        interactive (bool): Whether to prompt for missing values

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"\n❌ User '{username}' already exists.")
        print("\nTo reset the password for this user, run:")
        print("  python scripts/reset_admin_password.py --username {username}")
        return False

    # Get telegram_id
    if telegram_id is None:
        if interactive:
            telegram_id = input("Enter Telegram ID (required): ").strip()
            if not telegram_id:
                print("❌ Telegram ID is required")
                return False
        else:
            print("❌ Telegram ID is required")
            return False

    # Check if telegram_id already exists
    if User.objects.filter(telegram_id=telegram_id).exists():
        print(f"\n❌ User with Telegram ID '{telegram_id}' already exists.")
        existing_user = User.objects.get(telegram_id=telegram_id)
        print(f"  Existing username: {existing_user.username}")
        return False

    # Get name
    if name is None:
        if interactive:
            name = input("Enter display name (required): ").strip()
            if not name:
                print("❌ Display name is required")
                return False
        else:
            print("❌ Display name is required")
            return False

    # Get email (optional)
    if email is None and interactive:
        email_input = input("Enter email address (optional, press Enter to skip): ").strip()
        email = email_input if email_input else None

    # Get password
    if password is None:
        if interactive:
            while True:
                password = getpass.getpass("Enter password: ")
                if not password:
                    print("❌ Password cannot be empty")
                    continue
                password_confirm = getpass.getpass("Confirm password: ")
                if password != password_confirm:
                    print("❌ Passwords do not match. Try again.")
                    continue
                break
        else:
            print("❌ Password is required in non-interactive mode")
            return False

    # Create the superuser
    try:
        user = User.objects.create_user(
            username=username,
            telegram_id=telegram_id,
            name=name,
            email=email or '',
            password=password,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        print(f"\n{'='*60}")
        print("✅ ADMIN USER CREATED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"Username: {user.username}")
        print(f"Telegram ID: {user.telegram_id}")
        print(f"Name: {user.name}")
        print(f"Email: {user.email or '(not set)'}")
        print(f"Staff: {'✓' if user.is_staff else '✗'}")
        print(f"Superuser: {'✓' if user.is_superuser else '✗'}")
        print(f"Active: {'✓' if user.is_active else '✗'}")
        print(f"{'='*60}")
        print("\nYou can now login to Django admin at:")
        print("  http://localhost:8000/admin/")
        print(f"\n  Username: {username}")
        print("  Password: (the password you just set)")
        print()
        return True
    except Exception as e:
        print(f"\n❌ Error creating user: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create admin superuser for Django admin panel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/create_admin_user.py
  python scripts/create_admin_user.py --username admin --telegram-id admin123 --name "Admin User"
  python scripts/create_admin_user.py --username admin --telegram-id admin123 --name "Admin User" --password mypass123
        """
    )

    parser.add_argument(
        '--username',
        default='admin',
        help='Username for the admin user (default: admin)'
    )

    parser.add_argument(
        '--telegram-id',
        help='Telegram ID (required, will prompt if not provided)'
    )

    parser.add_argument(
        '--name',
        help='Display name (required, will prompt if not provided)'
    )

    parser.add_argument(
        '--email',
        help='Email address (optional)'
    )

    parser.add_argument(
        '--password',
        help='Password (will prompt if not provided)'
    )

    args = parser.parse_args()

    # Create admin user
    interactive = args.password is None or args.telegram_id is None or args.name is None
    success = create_admin_user(
        username=args.username,
        telegram_id=args.telegram_id,
        name=args.name,
        email=args.email,
        password=args.password,
        interactive=interactive
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
