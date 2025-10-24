# Scripts Directory

This directory contains utility scripts for managing the Telegram bot webhook configuration.

## Available Scripts

### 1. `set_webhook.py` - Webhook Configuration Manager

A comprehensive Python script for managing Telegram webhook settings.

#### Basic Usage

```bash
# Set webhook (uses TELEGRAM_WEBHOOK_URL from .env)
uv run python scripts/set_webhook.py

# Show current webhook information
uv run python scripts/set_webhook.py --info

# Delete webhook (switch to polling mode)
uv run python scripts/set_webhook.py --delete

# Set webhook and drop pending updates
uv run python scripts/set_webhook.py --drop-pending

# Delete webhook and drop pending updates
uv run python scripts/set_webhook.py --delete --drop-pending
```

#### Features

- ✅ Validates configuration before making changes
- ✅ Shows current webhook status
- ✅ Provides detailed error messages
- ✅ Supports dropping pending updates
- ✅ Color-coded output for easy reading
- ✅ Safe URL validation (HTTPS check, path validation)

#### Example Output

```
============================================================
🤖 TELEGRAM WEBHOOK MANAGER
============================================================
Project: habit_reward
============================================================

Current mode: Polling (no webhook set)

============================================================
🔧 SETTING WEBHOOK
============================================================
Webhook URL: https://abc123.ngrok-free.app/webhook/telegram
============================================================

✅ Webhook set successfully!

============================================================
📊 CURRENT WEBHOOK INFO
============================================================
URL: https://abc123.ngrok-free.app/webhook/telegram
Status: ✅ Webhook is SET
Pending updates: 0
Max connections: 40
IP address: 123.45.67.89
============================================================
```

---

### 2. `start_webhook_dev.sh` - Interactive Webhook Setup

An interactive bash script that guides you through the complete webhook development setup process.

#### Usage

```bash
# Run the interactive setup
./scripts/start_webhook_dev.sh
```

#### What It Does

1. **Validates Environment**
   - Checks for `.env` file
   - Verifies `TELEGRAM_BOT_TOKEN` is set
   - Confirms ngrok is installed
   - Ensures dependencies are installed

2. **Guides ngrok Setup**
   - Prompts you to start ngrok in a new terminal
   - Auto-detects ngrok URL from ngrok API
   - Falls back to manual input if auto-detection fails

3. **Updates Configuration**
   - Automatically updates `TELEGRAM_WEBHOOK_URL` in `.env`
   - Adds ngrok domain to `ALLOWED_HOSTS`
   - Preserves other environment variables

4. **Starts Server**
   - Guides you to start the Django ASGI server
   - Tests server connectivity
   - Provides clear command instructions

5. **Sets Webhook**
   - Automatically runs `set_webhook.py`
   - Shows webhook configuration status
   - Provides monitoring and testing tips

#### Features

- 🎨 Color-coded output (green for success, red for errors, yellow for warnings)
- 🤖 Automatic ngrok URL detection via ngrok API
- ⚙️ Automatic `.env` file updates
- ✅ Validation at each step
- 📝 Clear instructions for each terminal window
- 🔍 Server connectivity testing

#### Example Session

```bash
$ ./scripts/start_webhook_dev.sh

==========================================
🚀 Webhook Development Environment Setup
==========================================
✅ Configuration file found
✅ ngrok is installed
✅ Dependencies are ready

==========================================
📋 Next Steps:
==========================================

This script will guide you through the webhook setup process.
You'll need to run commands in SEPARATE terminal windows.

STEP 1: Start ngrok tunnel
----------------------------------------
Open a NEW terminal window and run:

    ngrok http 8000

Press ENTER when ngrok is running...
[User presses ENTER]

✅ Ngrok URL: https://abc123.ngrok-free.app
✅ .env file updated

STEP 2: Start Django ASGI server
----------------------------------------
Open ANOTHER NEW terminal window and run:

    cd /Users/erzhan/Data/PROJ/habit_reward
    uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload

Press ENTER when the server is running...
[User presses ENTER]

✅ Server is running

STEP 3: Set Telegram webhook
----------------------------------------
[Runs set_webhook.py automatically]

==========================================
🎉 Webhook setup complete!
==========================================

Your webhook is now configured:
  URL: https://abc123.ngrok-free.app/webhook/telegram

📊 Monitor your webhook:
  ngrok web interface: http://127.0.0.1:4040
  Server logs: Check the uvicorn terminal

🧪 Test your bot:
  1. Open Telegram and send /start to your bot
  2. Watch the server logs for incoming requests
  3. Check ngrok interface for request details

Happy coding! 🚀
```

---

### 3. `test_webhook.py` - Webhook Endpoint Tester

A utility script to verify that your webhook endpoint is accessible and responding correctly.

#### Usage

```bash
# Test localhost endpoint
uv run python scripts/test_webhook.py

# Test specific URL (e.g., ngrok)
uv run python scripts/test_webhook.py https://abc123.ngrok-free.app

# The script automatically detects and tests ngrok if running
```

#### What It Tests

1. **GET Request Test**
   - Verifies endpoint rejects GET requests (should return 400/405)
   - Confirms endpoint is accessible

2. **Invalid JSON Test**
   - Sends malformed JSON data
   - Verifies proper error handling (should return 400)

3. **Valid Update Test**
   - Sends a minimal valid Telegram update structure
   - Verifies endpoint accepts properly formatted updates (should return 200)

4. **ngrok Detection**
   - Automatically detects ngrok tunnel via ngrok API
   - Tests both localhost and ngrok endpoints

#### Features

- 🧪 Three-stage testing (GET, invalid POST, valid POST)
- 🔍 Auto-detects ngrok tunnel
- ✅ Clear pass/fail indicators
- 📊 Response preview for debugging
- 🚀 No dependencies beyond requests library

#### Example Output

```
============================================================
🤖 TELEGRAM WEBHOOK ENDPOINT TESTER
============================================================

Testing localhost (default)

============================================================
🧪 WEBHOOK ENDPOINT TEST
============================================================
Testing: http://localhost:8000/webhook/telegram
============================================================

Test 1: GET request (should return 400 or 405)
------------------------------------------------------------
✅ PASS - Got expected 400 response
   Response: Only POST requests are allowed

Test 2: POST request with invalid JSON (should return 400)
------------------------------------------------------------
✅ PASS - Got expected 400 response
   Response: Invalid JSON: Expecting value: line 1 column 1 (char 0)

Test 3: POST request with minimal valid Telegram update structure
------------------------------------------------------------
✅ PASS - Got 200 OK response
   Response: ok
   Note: Bot will process this update if user exists in DB

============================================================
✅ WEBHOOK ENDPOINT TESTS COMPLETE
============================================================

Attempting to detect ngrok tunnel...
------------------------------------------------------------
✅ Found ngrok tunnel: https://abc123.ngrok-free.app

Testing ngrok tunnel...
[Tests repeated for ngrok URL]
```

#### When to Use

- ✅ After starting the webhook server
- ✅ After setting up ngrok
- ✅ Before setting the Telegram webhook
- ✅ When troubleshooting connection issues
- ✅ To verify endpoint is publicly accessible

---

## Quick Reference Commands

### Development Workflow

```bash
# Option 1: Automated setup (recommended for first-time setup)
./scripts/start_webhook_dev.sh

# Option 2: Manual setup
# Terminal 1:
ngrok http 8000

# Terminal 2:
uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload

# Terminal 3:
uv run python scripts/set_webhook.py
```

### Check Webhook Status

```bash
# Using script
uv run python scripts/set_webhook.py --info

# Using curl
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

### Switch to Polling Mode

```bash
# Delete webhook
uv run python scripts/set_webhook.py --delete

# Run polling mode
uv run python src/bot/main.py
```

### When ngrok URL Changes

When you restart ngrok, you get a new URL. To update:

```bash
# Option 1: Run the automated setup again
./scripts/start_webhook_dev.sh

# Option 2: Manual update
# 1. Update TELEGRAM_WEBHOOK_URL in .env with new ngrok URL
# 2. Update ALLOWED_HOSTS in .env with new ngrok domain
# 3. Restart uvicorn server
# 4. Run: uv run python scripts/set_webhook.py
```

---

## Troubleshooting

### Script Permission Denied

```bash
chmod +x scripts/set_webhook.py
chmod +x scripts/start_webhook_dev.sh
```

### ngrok Not Found

**macOS:**
```bash
brew install ngrok
```

**Linux:**
```bash
# Visit https://ngrok.com/download for installation instructions
```

### Cannot Detect ngrok URL

The script tries to auto-detect the ngrok URL from the ngrok API. If this fails:

1. Make sure ngrok is running on port 8000
2. Check ngrok web interface: http://127.0.0.1:4040
3. Manually enter the URL when prompted
4. Or update `.env` manually and run `set_webhook.py`

### Webhook Set But Bot Not Responding

1. Check server is running: `curl http://localhost:8000/webhook/telegram`
2. Check ngrok tunnel: visit http://127.0.0.1:4040
3. Check webhook info: `uv run python scripts/set_webhook.py --info`
4. Check server logs in uvicorn terminal
5. Try deleting and re-setting webhook with `--drop-pending` flag

---

## Environment Variables Required

These must be set in your `.env` file:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Auto-set by start_webhook_dev.sh (or set manually)
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook/telegram
ALLOWED_HOSTS=localhost,127.0.0.1,your-ngrok-domain.ngrok-free.app
```

---

## See Also

- [Full Webhook Guide](../docs/TELEGRAM_WEBHOOK_NGROK_GUIDE.md) - Comprehensive documentation
- [Telegram Bot API](https://core.telegram.org/bots/api) - Official API documentation
- [ngrok Documentation](https://ngrok.com/docs) - ngrok usage and features

---

## Contributing

If you create additional utility scripts, please:

1. Add them to this directory
2. Make them executable (`chmod +x`)
3. Document them in this README
4. Follow the existing code style and conventions
