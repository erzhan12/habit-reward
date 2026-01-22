# Telegram Webhook Quick Start Guide

A condensed guide for developers already familiar with webhooks and ngrok.

## TL;DR

```bash
# Automated setup (recommended)
./scripts/start_webhook_dev.sh

# Manual setup
# Terminal 1: make ngrok (or ngrok http 8000)
# Terminal 2: make api (or uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload)
# Terminal 3: uv run python scripts/set_webhook.py
```

---

## Prerequisites

- ngrok installed and authenticated
- `.env` file with `TELEGRAM_BOT_TOKEN` set
- Dependencies installed (`uv sync`)

---

## Automated Setup

The easiest way to get started:

```bash
./scripts/start_webhook_dev.sh
```

This interactive script will:
1. Validate your environment
2. Guide you to start ngrok
3. Auto-detect ngrok URL
4. Update `.env` file
5. Guide you to start the server
6. Set the webhook

---

## Manual Setup

### 1. Start ngrok

```bash
make ngrok
```

Or directly:
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

### 2. Update .env

```bash
TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app/webhook/telegram
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
```

### 3. Start Django Server

```bash
make api
```

Or directly:
```bash
uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload
```

### 4. Set Webhook

```bash
uv run python scripts/set_webhook.py
```

---

## Useful Commands

```bash
# Check webhook status
uv run python scripts/set_webhook.py --info

# Delete webhook (switch to polling)
uv run python scripts/set_webhook.py --delete

# Set webhook and clear pending updates
uv run python scripts/set_webhook.py --drop-pending

# Monitor requests
open http://127.0.0.1:4040  # ngrok web interface
```

---

## Testing

1. Send `/start` to your bot in Telegram
2. Watch logs in uvicorn terminal
3. Check ngrok interface at http://127.0.0.1:4040
4. Verify webhook info: `uv run python scripts/set_webhook.py --info`

---

## When ngrok URL Changes

ngrok free tier assigns new URLs on restart. When this happens:

```bash
# Quick fix (re-run automated setup)
./scripts/start_webhook_dev.sh

# Or manually
# 1. Update TELEGRAM_WEBHOOK_URL and ALLOWED_HOSTS in .env
# 2. Restart uvicorn
# 3. uv run python scripts/set_webhook.py
```

---

## Switch to Polling Mode

```bash
# Delete webhook
uv run python scripts/set_webhook.py --delete

# Run in polling mode
uv run python src/bot/main.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Check ngrok, server, and webhook are all running |
| 403 Forbidden | Webhook handler has `@csrf_exempt`, check Django settings |
| URL changed | Re-run setup or update `.env` and reset webhook |
| Pending updates stuck | Use `--drop-pending` flag when setting webhook |

---

## Architecture

```
Telegram → ngrok (HTTPS) → localhost:8000 → Django ASGI → webhook_handler.py
```

### Key Files

- `src/bot/webhook_handler.py` - Handles POST requests from Telegram
- `src/habit_reward_project/urls.py` - Routes `/webhook/telegram`
- `src/bot/main.py` - Polling mode (alternative to webhooks)
- `scripts/set_webhook.py` - Webhook management tool
- `scripts/start_webhook_dev.sh` - Automated setup script

---

## Full Documentation

For detailed explanations, troubleshooting, and production deployment:

📖 [Complete Webhook Guide](./TELEGRAM_WEBHOOK_NGROK_GUIDE.md)

📖 [Scripts Documentation](../scripts/README.md)
