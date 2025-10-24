# Comprehensive Guide: Setting Up Telegram Webhooks with ngrok

This guide will walk you through setting up Telegram webhooks for local development using ngrok.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Understanding Polling vs Webhooks](#understanding-polling-vs-webhooks)
3. [Project Architecture](#project-architecture)
4. [Setting Up ngrok](#setting-up-ngrok)
5. [Configuring the Bot](#configuring-the-bot)
6. [Running the Webhook Server](#running-the-webhook-server)
7. [Setting the Telegram Webhook](#setting-the-telegram-webhook)
8. [Testing the Setup](#testing-the-setup)
9. [Troubleshooting](#troubleshooting)
10. [Switching Back to Polling](#switching-back-to-polling)

---

## Prerequisites

Before starting, ensure you have:

- Python 3.13+ installed
- A Telegram bot token (from [@BotFather](https://t.me/botfather))
- ngrok account and installation
- Project dependencies installed (`uv sync`)
- Environment variables configured in `.env` file

---

## Understanding Polling vs Webhooks

### Polling Mode (Development)
- Bot actively requests updates from Telegram servers
- Simple to set up, no external URL needed
- Uses `application.run_polling()` method
- File: `src/bot/main.py:181`
- Command: `uv run python src/bot/main.py`

### Webhook Mode (Production/Testing)
- Telegram sends updates to your server via HTTP POST
- Requires publicly accessible HTTPS URL
- More efficient for production
- Uses Django ASGI server with webhook handler
- File: `src/bot/webhook_handler.py`
- Command: `uvicorn src.habit_reward_project.asgi:application`

---

## Project Architecture

### Key Files

1. **`src/bot/main.py`**
   - Contains polling mode implementation
   - Defines `/start` and `/help` commands
   - Used for local development without webhooks

2. **`src/bot/webhook_handler.py`**
   - Django view that handles incoming webhook POST requests
   - Processes Telegram updates asynchronously
   - CSRF exempt for Telegram requests
   - Endpoint: `/webhook/telegram`

3. **`src/habit_reward_project/urls.py`**
   - URL routing configuration
   - Maps `/webhook/telegram` to webhook handler

4. **`src/habit_reward_project/asgi.py`**
   - ASGI application entry point
   - Used by uvicorn to serve the Django app

5. **`src/habit_reward_project/settings.py`**
   - Configuration settings
   - Environment variable management
   - TELEGRAM_BOT_TOKEN (line 149)
   - TELEGRAM_WEBHOOK_URL (line 150)

---

## Setting Up ngrok

### Step 1: Install ngrok

**macOS (via Homebrew):**
```bash
brew install ngrok
```

**Linux/WSL:**
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok
```

**Manual Download:**
Visit [ngrok.com/download](https://ngrok.com/download)

### Step 2: Authenticate ngrok

1. Sign up at [ngrok.com](https://ngrok.com)
2. Get your authtoken from the dashboard
3. Configure ngrok:

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

### Step 3: Start ngrok Tunnel

Open a **new terminal window** and run:

```bash
ngrok http 8000
```

You should see output like:
```
ngrok

Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123def456.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Important:** Copy the `https://` URL (e.g., `https://abc123def456.ngrok-free.app`)

### Step 4: Keep ngrok Running

Leave this terminal window open while developing. The ngrok tunnel must stay active to receive webhooks.

---

## Configuring the Bot

### Step 1: Update Environment Variables

Edit your `.env` file:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_actual_bot_token_from_botfather

# Webhook URL (use your ngrok URL + webhook path)
TELEGRAM_WEBHOOK_URL=https://abc123def456.ngrok-free.app/webhook/telegram

# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,abc123def456.ngrok-free.app

# Database (SQLite for development)
DATABASE_URL=sqlite:///db.sqlite3
```

**Critical Notes:**
- Replace `abc123def456.ngrok-free.app` with YOUR actual ngrok domain
- Add your ngrok domain to `ALLOWED_HOSTS`
- The webhook path must be `/webhook/telegram` (configured in `urls.py:9`)

### Step 2: Verify Django Settings

The `settings.py` file automatically loads these variables:

```python
# From settings.py:149-150
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='test_token')
TELEGRAM_WEBHOOK_URL = env('TELEGRAM_WEBHOOK_URL', default=None)

# From settings.py:32
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '[::1]'])
```

---

## Running the Webhook Server

### Step 1: Activate Virtual Environment (if not already)

```bash
source .venv/bin/activate
# or if using uv:
# uv automatically manages the venv
```

### Step 2: Run Database Migrations (if needed)

```bash
uv run python manage.py migrate
```

### Step 3: Start the ASGI Server

Open a **new terminal window** (keeping ngrok running) and run:

```bash
uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload
```

**Command Breakdown:**
- `uvicorn` - ASGI server for async Python apps
- `src.habit_reward_project.asgi:application` - path to ASGI app
- `--host 0.0.0.0` - listen on all interfaces
- `--port 8000` - use port 8000 (must match ngrok)
- `--reload` - auto-reload on code changes (development only)

You should see:
```
INFO:     Will watch for changes in these directories: ['/Users/erzhan/Data/PROJ/habit_reward']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Setting the Telegram Webhook

### Method 1: Using curl (Recommended)

```bash
curl -F "url=https://abc123def456.ngrok-free.app/webhook/telegram" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

**Replace:**
- `abc123def456.ngrok-free.app` with your ngrok domain
- `<YOUR_BOT_TOKEN>` with your actual bot token

**Expected Response:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### Method 2: Using Browser

Open in your browser:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://abc123def456.ngrok-free.app/webhook/telegram
```

### Method 3: Using Python Script

Create `scripts/set_webhook.py`:

```python
#!/usr/bin/env python
"""Script to set Telegram webhook."""
import os
import sys
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

def set_webhook():
    """Set Telegram webhook using bot token and webhook URL from settings."""
    token = settings.TELEGRAM_BOT_TOKEN
    webhook_url = settings.TELEGRAM_WEBHOOK_URL

    if not webhook_url:
        print("❌ ERROR: TELEGRAM_WEBHOOK_URL not set in .env file")
        return False

    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    print(f"🔧 Setting webhook to: {webhook_url}")
    response = requests.post(api_url, data={'url': webhook_url})

    result = response.json()

    if result.get('ok'):
        print("✅ Webhook set successfully!")
        print(f"   URL: {webhook_url}")
        return True
    else:
        print(f"❌ Failed to set webhook: {result.get('description')}")
        return False

def get_webhook_info():
    """Get current webhook information."""
    token = settings.TELEGRAM_BOT_TOKEN
    api_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"

    response = requests.get(api_url)
    info = response.json()

    if info.get('ok'):
        result = info['result']
        print("\n📊 Current Webhook Info:")
        print(f"   URL: {result.get('url', 'Not set')}")
        print(f"   Pending updates: {result.get('pending_update_count', 0)}")
        if result.get('last_error_message'):
            print(f"   ⚠️ Last error: {result['last_error_message']}")
            print(f"      At: {result.get('last_error_date')}")

if __name__ == '__main__':
    if set_webhook():
        get_webhook_info()
```

Run it:
```bash
uv run python scripts/set_webhook.py
```

### Verify Webhook is Set

Check webhook status:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

**Expected Response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123def456.ngrok-free.app/webhook/telegram",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40,
    "ip_address": "xxx.xxx.xxx.xxx"
  }
}
```

---

## Testing the Setup

### Step 1: Open Telegram

Open your bot in Telegram and send `/start`

### Step 2: Monitor Logs

You should see activity in **three places**:

**1. Uvicorn Server Logs:**
```
INFO:     123.45.67.89:12345 - "POST /webhook/telegram HTTP/1.1" 200 OK
```

**2. Django Application Logs:**
```
INFO 2025-10-24 12:34:56,789 src.bot.webhook_handler 📨 Received webhook update: 123456789
INFO 2025-10-24 12:34:56,790 src.bot.main 📨 Received /start command from user 123456789 (@username)
INFO 2025-10-24 12:34:56,791 src.bot.main ✅ Sending start menu to user 123456789 in language: en
```

**3. ngrok Web Interface:**

Visit http://127.0.0.1:4040 in your browser to see:
- All incoming requests
- Request/response details
- Request body (the Telegram update JSON)

### Step 3: Test Bot Commands

Try these commands in Telegram:
- `/start` - Should show the start menu
- `/help` - Should show help message
- Try marking a habit as done
- Try viewing rewards

### Step 4: Check for Errors

If something doesn't work:

1. Check uvicorn logs for errors
2. Check ngrok web interface for request details
3. Verify webhook is still set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
4. Check Django logs for exceptions

---

## Troubleshooting

### Problem: Bot Not Responding

**Check 1: Is ngrok running?**
```bash
# In ngrok terminal, you should see:
# Forwarding https://xyz.ngrok-free.app -> http://localhost:8000
```

**Check 2: Is uvicorn running?**
```bash
# Should see:
# INFO: Uvicorn running on http://0.0.0.0:8000
```

**Check 3: Is webhook set correctly?**
```bash
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
# Should show your ngrok URL
```

**Check 4: Test endpoint manually**
```bash
# Should return 400 (we need POST, not GET)
curl https://abc123def456.ngrok-free.app/webhook/telegram
```

### Problem: 403 Forbidden / CSRF Error

**Solution:** The webhook handler is decorated with `@csrf_exempt` (line 71 in webhook_handler.py), but verify:

1. Handler has `@csrf_exempt` decorator
2. Django is using correct settings
3. Telegram's IP is not blocked

### Problem: ngrok URL Changed

**ngrok free tier generates new URLs on restart**

When ngrok restarts:
1. Note the new URL from ngrok output
2. Update `.env` with new `TELEGRAM_WEBHOOK_URL`
3. Update `ALLOWED_HOSTS` with new domain
4. Restart uvicorn server
5. Reset webhook using new URL

**To get consistent URLs:**
- Upgrade to ngrok paid plan for reserved domains
- Or use a VPS/cloud server with static IP

### Problem: Updates Not Received

**Check pending updates:**
```bash
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

If `pending_update_count` > 0, Telegram is trying to send updates but failing.

**Clear pending updates:**
```bash
# Delete webhook (switches back to polling mode temporarily)
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true

# Set webhook again
curl -F "url=https://YOUR_NGROK_URL/webhook/telegram" \
     https://api.telegram.org/bot<TOKEN>/setWebhook
```

### Problem: "Connection Refused" in Webhook Info

This means Telegram cannot reach your server.

**Checklist:**
- [ ] ngrok is running
- [ ] Forwarding URL matches webhook URL
- [ ] uvicorn is running on port 8000
- [ ] Firewall not blocking port 8000
- [ ] Using HTTPS in webhook URL (not HTTP)

### Problem: Handlers Not Working

**If specific commands fail:**

1. Check handler registration in `webhook_handler.py:17-68`
2. Verify handlers are imported correctly
3. Check application logs for exceptions
4. Test in polling mode to isolate webhook issues

---

## Switching Back to Polling

### Step 1: Delete Webhook

```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook
```

### Step 2: Stop Uvicorn Server

Press `CTRL+C` in the uvicorn terminal

### Step 3: Stop ngrok

Press `CTRL+C` in the ngrok terminal

### Step 4: Run Polling Mode

```bash
uv run python src/bot/main.py
```

You should see:
```
🤖 Running bot in POLLING mode (development)
ℹ️ For production, use: uvicorn src.habit_reward_project.asgi:application
```

---

## Best Practices

### Development Workflow

1. **Use polling for rapid development**
   - Faster iteration
   - No webhook setup needed
   - Easier debugging

2. **Use webhooks to test production behavior**
   - Test webhook handling
   - Verify ASGI server setup
   - Practice deployment workflow

### Production Deployment

For production, instead of ngrok use:

1. **Cloud hosting** (Railway, Render, DigitalOcean, AWS)
2. **Static domain name**
3. **Proper HTTPS certificate**
4. **Environment variables for configuration**
5. **Database migration strategy**
6. **Logging and monitoring**

### Security Notes

- Never commit `.env` file to git
- Use strong `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Use environment-specific settings
- Restrict `ALLOWED_HOSTS` in production
- Monitor webhook errors in Telegram API

---

## Quick Reference

### Start Webhook Mode

```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Terminal 2: Start Django server
uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Set webhook
curl -F "url=https://YOUR_NGROK_URL/webhook/telegram" \
     https://api.telegram.org/bot<TOKEN>/setWebhook
```

### Start Polling Mode

```bash
# Single terminal
uv run python src/bot/main.py
```

### Useful Commands

```bash
# Get webhook info
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Delete webhook
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook

# Get bot info
curl https://api.telegram.org/bot<TOKEN>/getMe

# View ngrok requests
open http://127.0.0.1:4040
```

---

## Additional Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [ngrok Documentation](https://ngrok.com/docs)
- [Django ASGI Documentation](https://docs.djangoproject.com/en/stable/howto/deployment/asgi/)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)

---

## Need Help?

If you encounter issues not covered in this guide:

1. Check the application logs for detailed error messages
2. Visit the ngrok web interface at http://127.0.0.1:4040
3. Review the Telegram Bot API error descriptions
4. Verify all environment variables are set correctly
5. Test the endpoint manually with curl

Good luck with your webhook setup!
