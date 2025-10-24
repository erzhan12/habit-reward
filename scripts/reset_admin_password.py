#!/usr/bin/env python
"""Reset admin password for Django admin panel.

This script helps reset or create admin user passwords for accessing
the Django admin interface.

Usage:
    python scripts/reset_admin_password.py
    python scripts/reset_admin_password.py --username admin
    python scripts/reset_admin_password.py --password mypassword123
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


def reset_password(username='admin', password=None, interactive=True):
    """Reset password for a user.

    Args:
        username (str): Username to reset password for
        password (str): New password (if None and interactive=True, will prompt)
        interactive (bool): Whether to prompt for password

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"\n❌ User '{username}' does not exist.")
        print("\nAvailable admin users:")
        admins = User.objects.filter(is_staff=True)
        if admins.exists():
            for admin in admins:
                print(f"  - {admin.username} (Telegram: {admin.telegram_id}, Superuser: {admin.is_superuser})")
        else:
            print("  No admin users found.")
        print("\nTo create a new superuser, run:")
        print("  python manage.py createsuperuser")
        return False

    print(f"\n{'='*60}")
    print(f"RESET PASSWORD FOR USER")
    print(f"{'='*60}")
    print(f"Username: {user.username}")
    print(f"Telegram ID: {user.telegram_id}")
    print(f"Name: {user.name}")
    print(f"Staff: {user.is_staff}")
    print(f"Superuser: {user.is_superuser}")
    print(f"{'='*60}\n")

    # Get password
    if password is None and interactive:
        while True:
            password = getpass.getpass("Enter new password: ")
            if not password:
                print("❌ Password cannot be empty")
                continue
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords do not match. Try again.")
                continue
            break
    elif password is None:
        print("❌ Password is required in non-interactive mode")
        return False

    # Set password
    user.set_password(password)
    user.save()

    print(f"\n✅ Password reset successfully for user '{username}'!")
    print(f"\nYou can now login to Django admin at:")
    print(f"  http://localhost:8000/admin/")
    print(f"\n  Username: {username}")
    print(f"  Password: (the password you just set)")
    print()

    return True


def list_admin_users():
    """List all admin/staff users."""
    print(f"\n{'='*60}")
    print("ADMIN USERS")
    print(f"{'='*60}")

    admins = User.objects.filter(is_staff=True)

    if not admins.exists():
        print("No admin users found.")
        print("\nTo create a new superuser, run:")
        print("  python manage.py createsuperuser")
        return

    for user in admins:
        print(f"\nUsername: {user.username}")
        print(f"  Telegram ID: {user.telegram_id}")
        print(f"  Name: {user.name}")
        print(f"  Staff: {'✓' if user.is_staff else '✗'}")
        print(f"  Superuser: {'✓' if user.is_superuser else '✗'}")
        print(f"  Active: {'✓' if user.is_active else '✗'}")
        print(f"  Has usable password: {'✓' if user.has_usable_password() else '✗'}")

    print(f"\n{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Reset admin password for Django admin panel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/reset_admin_password.py
  python scripts/reset_admin_password.py --username admin
  python scripts/reset_admin_password.py --list
  python scripts/reset_admin_password.py --username admin --password mypass123
        """
    )

    parser.add_argument(
        '--username',
        default='admin',
        help='Username to reset password for (default: admin)'
    )

    parser.add_argument(
        '--password',
        help='New password (will prompt if not provided)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all admin users'
    )

    args = parser.parse_args()

    if args.list:
        list_admin_users()
        sys.exit(0)

    # Reset password
    interactive = args.password is None
    success = reset_password(
        username=args.username,
        password=args.password,
        interactive=interactive
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
