#!/usr/bin/env python
"""Quick fix script to add ngrok domain to ALLOWED_HOSTS.

This script helps resolve the Django DisallowedHost error when using ngrok.

Usage:
    python scripts/fix_allowed_hosts.py 74b6a10e97a5.ngrok-free.app
"""
import sys
from pathlib import Path

def fix_allowed_hosts(ngrok_domain):
    """Add ngrok domain to ALLOWED_HOSTS in .env file.

    Args:
        ngrok_domain (str): The ngrok domain to add (e.g., 'abc123.ngrok-free.app')
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'

    if not env_file.exists():
        print(f"❌ Error: .env file not found at {env_file}")
        print("\nCreate a .env file first with:")
        print("ALLOWED_HOSTS=localhost,127.0.0.1")
        return False

    # Clean the domain (remove https://, trailing slash, etc.)
    ngrok_domain = ngrok_domain.replace('https://', '').replace('http://', '')
    ngrok_domain = ngrok_domain.split('/')[0]  # Remove any path
    ngrok_domain = ngrok_domain.strip()

    print(f"🔧 Adding '{ngrok_domain}' to ALLOWED_HOSTS...")

    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()

    # Find and update ALLOWED_HOSTS line
    found = False
    updated_lines = []

    for line in lines:
        if line.strip().startswith('ALLOWED_HOSTS='):
            found = True
            # Extract current hosts
            current = line.split('=', 1)[1].strip()

            # Check if domain already in list
            if ngrok_domain in current:
                print(f"✅ '{ngrok_domain}' already in ALLOWED_HOSTS")
                return True

            # Add new domain
            if current:
                # Append to existing hosts
                new_value = f"{current},{ngrok_domain}"
            else:
                # First host
                new_value = ngrok_domain

            updated_lines.append(f"ALLOWED_HOSTS={new_value}\n")
            print(f"✅ Updated ALLOWED_HOSTS to: {new_value}")
        else:
            updated_lines.append(line)

    # If ALLOWED_HOSTS not found, add it
    if not found:
        default_hosts = f"localhost,127.0.0.1,{ngrok_domain}"
        updated_lines.append(f"\nALLOWED_HOSTS={default_hosts}\n")
        print(f"✅ Added ALLOWED_HOSTS: {default_hosts}")

    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)

    print("\n" + "="*60)
    print("✅ .env file updated successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Restart your Django server (Ctrl+C and restart uvicorn)")
    print("2. The webhook should now work correctly")
    print("\nTo restart server:")
    print("uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload")

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("❌ Error: No ngrok domain provided")
        print("\nUsage:")
        print("  python scripts/fix_allowed_hosts.py <ngrok-domain>")
        print("\nExamples:")
        print("  python scripts/fix_allowed_hosts.py 74b6a10e97a5.ngrok-free.app")
        print("  python scripts/fix_allowed_hosts.py https://74b6a10e97a5.ngrok-free.app")
        sys.exit(1)

    ngrok_domain = sys.argv[1]

    print("\n" + "="*60)
    print("🔧 ALLOWED_HOSTS FIX UTILITY")
    print("="*60 + "\n")

    success = fix_allowed_hosts(ngrok_domain)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
