#!/bin/bash
# ============================================================================
# Habit Reward Bot - Deployment Script
# ============================================================================
# This script is executed on the VPS server via SSH from GitHub Actions
# It pulls the latest Docker images and restarts the containers

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ensure_port_available() {
    local port="$1"
    local retries="${2:-5}"
    local delay="${3:-3}"

    echo -e "${YELLOW}Ensuring port ${port} is free...${NC}"

    for attempt in $(seq 1 "$retries"); do
        local pids
        pids=$(sudo lsof -i :"$port" -t 2>/dev/null || true)

        if [ -z "$pids" ]; then
            echo -e "${GREEN}Port ${port} is available${NC}"
            return 0
        fi

        echo -e "${YELLOW}Port ${port} is in use (attempt ${attempt}/${retries}).${NC}"
        sudo lsof -i :"$port" || true

        if sudo systemctl is-active --quiet nginx 2>/dev/null; then
            echo -e "${YELLOW}Stopping system nginx service...${NC}"
            sudo systemctl stop nginx
            sudo systemctl disable nginx || true
        fi

        if sudo systemctl is-active --quiet apache2 2>/dev/null; then
            echo -e "${YELLOW}Stopping apache2 service...${NC}"
            sudo systemctl stop apache2
            sudo systemctl disable apache2 || true
        fi

        echo -e "${YELLOW}Force freeing port ${port}...${NC}"
        sudo fuser -k "${port}/tcp" >/dev/null 2>&1 || true

        sleep "$delay"
    done

    echo -e "${RED}Failed to free port ${port} after ${retries} attempts${NC}"
    exit 1
}

load_env_file() {
    local env_file="$1"

    while IFS= read -r raw_line || [ -n "$raw_line" ]; do
        raw_line="${raw_line%$'\r'}"

        local trimmed="${raw_line#"${raw_line%%[![:space:]]*}"}"
        [[ -z "$trimmed" ]] && continue
        [[ "${trimmed:0:1}" == "#" ]] && continue
        [[ "$raw_line" != *=* ]] && continue

        local key="${raw_line%%=*}"
        local value="${raw_line#*=}"

        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        [[ -z "$key" ]] && continue

        value="${value#"${value%%[![:space:]]*}"}"

        export "${key}=${value}"
    done < "$env_file"
}

# Configuration
DEPLOY_PATH="${DEPLOY_PATH:-/home/deploy/habit_reward_bot}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
DOCKER_IMAGE_NAME="${DOCKER_IMAGE_NAME:-habit_reward_bot}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Habit Reward Bot - Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Navigate to deployment directory
echo -e "${YELLOW}Navigating to deployment directory...${NC}"
cd "$DEPLOY_PATH" || {
    echo -e "${RED}Error: Deployment directory not found: $DEPLOY_PATH${NC}"
    exit 1
}

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env file based on .env.example${NC}"
    exit 1
fi

# Load environment variables without triggering shell expansion on secrets
echo -e "${YELLOW}Loading environment variables...${NC}"
load_env_file ".env"

# Login to GitHub Container Registry (if credentials provided)
if [ -n "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}Logging in to GitHub Container Registry...${NC}"
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
fi

# Pull latest code from repository (if git repo exists)
if [ -d .git ]; then
    echo -e "${YELLOW}Pulling latest code from repository...${NC}"
    git pull origin main || {
        echo -e "${YELLOW}Warning: Could not pull latest code (continuing anyway)${NC}"
    }
fi

# Pull latest Docker image for web service (skip nginx as it's built locally)
echo -e "${YELLOW}Pulling latest Docker image for web service...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml pull web || {
    echo -e "${YELLOW}Warning: Could not pull web image (will build locally)${NC}"
}

# Check for port conflicts and stop conflicting services
echo -e "${YELLOW}Checking for port conflicts...${NC}"
ensure_port_available 80 3 2
ensure_port_available 443 3 2

# Stop and remove old containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down || true

# Wait for Docker to fully release network namespaces and port bindings
echo -e "${YELLOW}Waiting for Docker to release ports (5 seconds)...${NC}"
sleep 5

# Ensure ports are still free before bringing containers back up (docker-proxy can linger briefly)
ensure_port_available 80 10 3
ensure_port_available 443 10 3

# Remove old, unused images to free up space
echo -e "${YELLOW}Cleaning up old Docker images...${NC}"
docker image prune -f || true

# Build nginx image locally (since it's not in a registry)
echo -e "${YELLOW}Building nginx image...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml build nginx

# Start new containers (web will use pulled image if available, nginx uses built image)
echo -e "${YELLOW}Starting new containers...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check container status
echo -e "${YELLOW}Checking container status...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps

# Show logs (last 50 lines)
echo -e "${YELLOW}Recent logs from web container:${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs --tail=50 web

# Verify deployment
echo -e "${YELLOW}Verifying deployment...${NC}"

# Check if web container is running
WEB_RUNNING=$(docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps -q web)
if [ -z "$WEB_RUNNING" ]; then
    echo -e "${RED}Error: Web container is not running!${NC}"
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs web
    exit 1
fi

# Check if database container is running
DB_RUNNING=$(docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps -q db)
if [ -z "$DB_RUNNING" ]; then
    echo -e "${RED}Error: Database container is not running!${NC}"
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs db
    exit 1
fi

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec -T web python manage.py check --database default || {
    echo -e "${RED}Error: Database connection failed!${NC}"
    exit 1
}

# Check webhook status (if configured)
if [ -n "$TELEGRAM_WEBHOOK_URL" ]; then
    echo -e "${YELLOW}Verifying Telegram webhook...${NC}"
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec -T web python -c "
import asyncio
from telegram import Bot

async def check_webhook():
    bot = Bot('$TELEGRAM_BOT_TOKEN')
    webhook_info = await bot.get_webhook_info()
    print(f'Webhook URL: {webhook_info.url}')
    print(f'Pending updates: {webhook_info.pending_update_count}')
    if webhook_info.url != '$TELEGRAM_WEBHOOK_URL':
        print('WARNING: Webhook URL mismatch!')
        return False
    return True

result = asyncio.run(check_webhook())
exit(0 if result else 1)
" || {
        echo -e "${YELLOW}Warning: Webhook verification failed (this might be normal during initial setup)${NC}"
    }
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Web container: Running${NC}"
echo -e "${GREEN}Database container: Running${NC}"
echo -e "${YELLOW}Monitor logs with: docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f${NC}"
echo -e "${YELLOW}Stop services with: docker-compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down${NC}"

exit 0
