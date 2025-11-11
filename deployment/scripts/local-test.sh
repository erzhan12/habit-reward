#!/bin/bash
# ============================================================================
# Habit Reward Bot - Local Testing Script
# ============================================================================
# This script helps you test the Docker deployment locally before deploying
# to production

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Habit Reward Bot - Local Testing${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your local settings${NC}"
    echo -e "${YELLOW}Minimum required:${NC}"
    echo -e "${YELLOW}  - TELEGRAM_BOT_TOKEN${NC}"
    echo -e "${YELLOW}  - SECRET_KEY (generate with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\")${NC}"
    echo ""
    read -p "Press enter after editing .env file..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running!${NC}"
    echo -e "${YELLOW}Please start Docker and try again.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed!${NC}"
    exit 1
fi

# Store project root path and .env file location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Change to deployment/docker directory
cd "$SCRIPT_DIR/../docker"

echo -e "${YELLOW}Validating docker-compose configuration...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker-compose.yml config > /dev/null
echo -e "${GREEN}✓ Configuration valid${NC}"

echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker-compose.yml build

echo -e "${YELLOW}Starting containers...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker-compose.yml up -d

echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

echo -e "${YELLOW}Checking container status...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker-compose.yml ps

echo -e "${YELLOW}Checking logs...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker-compose.yml logs --tail=50

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Local test environment is running!${NC}"
echo -e "${GREEN}========================================${NC}"

echo ""
echo -e "${GREEN}Access points:${NC}"
echo -e "  Admin panel: http://localhost:8000/admin/"
echo -e "  Webhook endpoint: http://localhost:8000/webhook/telegram"
echo ""
echo -e "${YELLOW}Useful commands (run from deployment/docker directory):${NC}"
echo -e "  View logs:        docker-compose --env-file ../../.env logs -f"
echo -e "  Restart:          docker-compose --env-file ../../.env restart"
echo -e "  Stop:             docker-compose --env-file ../../.env down"
echo -e "  Django shell:     docker-compose --env-file ../../.env exec web python manage.py shell"
echo -e "  Database shell:   docker-compose --env-file ../../.env exec db psql -U postgres -d habit_reward"
echo ""
echo -e "${YELLOW}Test your bot:${NC}"
echo -e "  1. The bot will run in POLLING mode (no webhook needed for local testing)"
echo -e "  2. Open Telegram and send /start to your bot"
echo -e "  3. Check logs: docker-compose --env-file ../../.env logs -f web"
echo ""
echo -e "${GREEN}Happy testing!${NC}"
