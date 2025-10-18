#!/usr/bin/env python3
"""
Main CLI entry point for the Habit-Reward System.

This script provides a command-line interface to launch different components
of the habit-reward system.
"""

import sys
import subprocess
from pathlib import Path


def print_usage():
    """Print usage information."""
    print("Habit-Reward System CLI")
    print("Usage: python main.py <command>")
    print()
    print("Commands:")
    print("  bot        Start the Telegram bot")
    print("  dashboard  Start the Streamlit dashboard")
    print("  help       Show this help message")
    print()
    print("Examples:")
    print("  python main.py bot")
    print("  python main.py dashboard")


def run_bot():
    """Launch the Telegram bot."""
    print("🤖 Starting Telegram bot...")
    bot_script = Path(__file__).parent / "src" / "bot" / "main.py"
    try:
        subprocess.run([sys.executable, str(bot_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")


def run_dashboard():
    """Launch the Streamlit dashboard."""
    print("📊 Starting Streamlit dashboard...")
    dashboard_script = Path(__file__).parent / "src" / "dashboard" / "app.py"
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(dashboard_script)
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "bot":
        run_bot()
    elif command == "dashboard":
        run_dashboard()
    elif command in ["help", "-h", "--help"]:
        print_usage()
    else:
        print(f"❌ Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
