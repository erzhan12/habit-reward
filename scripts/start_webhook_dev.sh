#!/bin/bash
# Quick start script for webhook development with ngrok
# This script helps set up the complete webhook development environment

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_msg $BLUE "=========================================="
print_msg $BLUE "🚀 Webhook Development Environment Setup"
print_msg $BLUE "=========================================="

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    print_msg $RED "❌ Error: .env file not found"
    print_msg $YELLOW "Please create a .env file with the following variables:"
    print_msg $YELLOW "  - TELEGRAM_BOT_TOKEN"
    print_msg $YELLOW "  - TELEGRAM_WEBHOOK_URL (will be set after ngrok starts)"
    exit 1
fi

# Check if TELEGRAM_BOT_TOKEN is set
if ! grep -q "TELEGRAM_BOT_TOKEN=.*[^=]" "$PROJECT_ROOT/.env" 2>/dev/null; then
    print_msg $RED "❌ Error: TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

print_msg $GREEN "✅ Configuration file found"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    print_msg $RED "❌ Error: ngrok is not installed"
    print_msg $YELLOW "Install ngrok:"
    print_msg $YELLOW "  macOS: brew install ngrok"
    print_msg $YELLOW "  Linux: Visit https://ngrok.com/download"
    exit 1
fi

print_msg $GREEN "✅ ngrok is installed"

# Check if uvicorn is available
if ! uv run python -c "import uvicorn" 2>/dev/null; then
    print_msg $YELLOW "⚠️ uvicorn not found, installing dependencies..."
    cd "$PROJECT_ROOT"
    uv sync
fi

print_msg $GREEN "✅ Dependencies are ready"

echo ""
print_msg $BLUE "=========================================="
print_msg $BLUE "📋 Next Steps:"
print_msg $BLUE "=========================================="
echo ""
print_msg $YELLOW "This script will guide you through the webhook setup process."
print_msg $YELLOW "You'll need to run commands in SEPARATE terminal windows."
echo ""

# Step 1: ngrok
print_msg $GREEN "STEP 1: Start ngrok tunnel"
print_msg $BLUE "----------------------------------------"
echo "Open a NEW terminal window and run:"
echo ""
print_msg $YELLOW "    ngrok http 8000"
echo ""
read -p "Press ENTER when ngrok is running..."

# Get ngrok URL
print_msg $BLUE "----------------------------------------"
echo "Getting ngrok URL from ngrok API..."
NGROK_URL=""
for i in {1..5}; do
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | grep -o 'https://[a-zA-Z0-9-]*\.ngrok[a-zA-Z0-9.-]*' | head -1 || echo "")
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    echo "Waiting for ngrok... (attempt $i/5)"
    sleep 2
done

if [ -z "$NGROK_URL" ]; then
    print_msg $RED "❌ Could not detect ngrok URL automatically"
    echo ""
    read -p "Please enter your ngrok HTTPS URL (e.g., https://abc123.ngrok-free.app): " NGROK_URL
    NGROK_URL=$(echo "$NGROK_URL" | tr -d '[:space:]')  # Remove whitespace
fi

print_msg $GREEN "✅ Ngrok URL: $NGROK_URL"

# Update .env file with NGROK_URL (single variable for both webhook URL and ALLOWED_HOSTS)
print_msg $BLUE "Updating .env with NGROK_URL..."

# Remove old ngrok-related variables if they exist
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' '/^TELEGRAM_WEBHOOK_URL=.*ngrok/d' "$PROJECT_ROOT/.env" 2>/dev/null || true
else
    # Linux
    sed -i '/^TELEGRAM_WEBHOOK_URL=.*ngrok/d' "$PROJECT_ROOT/.env" 2>/dev/null || true
fi

# Update or add NGROK_URL
if grep -q "^NGROK_URL=" "$PROJECT_ROOT/.env"; then
    # Update existing line
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^NGROK_URL=.*|NGROK_URL=$NGROK_URL|" "$PROJECT_ROOT/.env"
    else
        # Linux
        sed -i "s|^NGROK_URL=.*|NGROK_URL=$NGROK_URL|" "$PROJECT_ROOT/.env"
    fi
else
    # Add new line
    echo "NGROK_URL=$NGROK_URL" >> "$PROJECT_ROOT/.env"
fi

# Ensure ALLOWED_HOSTS has localhost and 127.0.0.1 (ngrok domain will be added automatically by settings.py)
if ! grep -q "^ALLOWED_HOSTS=" "$PROJECT_ROOT/.env"; then
    echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> "$PROJECT_ROOT/.env"
fi

WEBHOOK_URL="${NGROK_URL}/webhook/telegram"
print_msg $GREEN "✅ .env file updated with NGROK_URL"
print_msg $BLUE "   Webhook URL will be: $WEBHOOK_URL (derived automatically)"
print_msg $BLUE "   ALLOWED_HOSTS will include ngrok domain automatically"

echo ""
print_msg $GREEN "STEP 2: Start Django ASGI server"
print_msg $BLUE "----------------------------------------"
echo "Open ANOTHER NEW terminal window and run:"
echo ""
print_msg $YELLOW "    cd $PROJECT_ROOT"
print_msg $YELLOW "    uvicorn src.habit_reward_project.asgi:application --host 0.0.0.0 --port 8000 --reload"
echo ""
read -p "Press ENTER when the server is running..."

# Test if server is running
print_msg $BLUE "Testing server connection..."
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/webhook/telegram" | grep -q "400\|405"; then
    print_msg $GREEN "✅ Server is running"
else
    print_msg $YELLOW "⚠️ Server might not be running, but continuing..."
fi

echo ""
print_msg $GREEN "STEP 3: Set Telegram webhook"
print_msg $BLUE "----------------------------------------"
cd "$PROJECT_ROOT"
uv run python scripts/set_webhook.py

echo ""
print_msg $BLUE "=========================================="
print_msg $GREEN "🎉 Webhook setup complete!"
print_msg $BLUE "=========================================="
echo ""
print_msg $YELLOW "Your webhook is now configured:"
print_msg $BLUE "  NGROK_URL: $NGROK_URL"
print_msg $BLUE "  Webhook URL: $WEBHOOK_URL (derived from NGROK_URL)"
print_msg $BLUE "  ALLOWED_HOSTS: includes ngrok domain automatically"
echo ""
print_msg $YELLOW "📊 Monitor your webhook:"
print_msg $BLUE "  ngrok web interface: http://127.0.0.1:4040"
print_msg $BLUE "  Server logs: Check the uvicorn terminal"
echo ""
print_msg $YELLOW "🧪 Test your bot:"
print_msg $BLUE "  1. Open Telegram and send /start to your bot"
print_msg $BLUE "  2. Watch the server logs for incoming requests"
print_msg $BLUE "  3. Check ngrok interface for request details"
echo ""
print_msg $YELLOW "ℹ️ Useful commands:"
print_msg $BLUE "  Check webhook status: uv run python scripts/set_webhook.py --info"
print_msg $BLUE "  Delete webhook: uv run python scripts/set_webhook.py --delete"
echo ""
print_msg $GREEN "Happy coding! 🚀"
