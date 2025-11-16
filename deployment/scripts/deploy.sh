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

    # Test if port is actually available by trying to bind to it
    test_port_available() {
        # Use timeout and nc to test if port is available (no sudo needed)
        if command -v timeout >/dev/null 2>&1 && command -v nc >/dev/null 2>&1; then
            timeout 1 bash -c "echo > /dev/tcp/127.0.0.1/${port}" 2>/dev/null && return 1 || return 0
        fi
        # Fallback: try to use ss without sudo (works for checking listening ports)
        if command -v ss >/dev/null 2>&1; then
            ss -tln 2>/dev/null | grep -q ":${port} " && return 1 || return 0
        fi
        # Last resort: assume port might be in use
        return 1
    }

    for attempt in $(seq 1 "$retries"); do
        local port_in_use=false
        local cleanup_needed=false

        # First, check Docker containers (no sudo needed)
        local containers_with_port
        containers_with_port=$(docker ps -a --format "{{.ID}} {{.Names}} {{.Ports}}" 2>/dev/null | grep -E ":${port}->|:${port}/|0.0.0.0:${port}:" || true)
        if [ -n "$containers_with_port" ]; then
            port_in_use=true
            cleanup_needed=true
            echo -e "${YELLOW}Found Docker containers with port ${port} mappings (attempt ${attempt}/${retries}):${NC}"
            echo "$containers_with_port"
            # Extract container IDs and remove them
            echo "$containers_with_port" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
            sleep 2
        fi

        # Check for docker-proxy processes holding the port (no sudo needed for detection)
        local docker_proxy_pids
        docker_proxy_pids=$(pgrep -f "docker-proxy.*-proto tcp -host-ip 0.0.0.0 -host-port ${port}" 2>/dev/null || true)
        if [ -z "$docker_proxy_pids" ]; then
            # Try alternative pattern (different Docker versions use different formats)
            docker_proxy_pids=$(pgrep -f "docker-proxy.*:${port}" 2>/dev/null || true)
        fi
        if [ -n "$docker_proxy_pids" ]; then
            port_in_use=true
            cleanup_needed=true
            echo -e "${YELLOW}Found docker-proxy processes holding port ${port}:${NC}"
            ps aux | grep -E "docker-proxy.*:${port}|docker-proxy.*-host-port ${port}" | grep -v grep || true
            echo -e "${YELLOW}Killing docker-proxy processes...${NC}"
            # Try without sudo first (if user is in docker group)
            echo "$docker_proxy_pids" | xargs -r kill -9 2>/dev/null || {
                # If that fails, try with sudo (but don't fail if sudo doesn't work)
                echo "$docker_proxy_pids" | xargs -r sudo kill -9 2>/dev/null || true
            }
            sleep 2
        fi

        # Check using ss without sudo (works for checking listening ports)
        if command -v ss >/dev/null 2>&1; then
            local ss_output
            ss_output=$(ss -tln 2>/dev/null | grep ":${port} " || true)
            if [ -n "$ss_output" ]; then
                port_in_use=true
                echo -e "${YELLOW}Port ${port} is in use (ss detected):${NC}"
                echo "$ss_output"
            fi
        fi

        # Try sudo commands but don't fail if they don't work
        if command -v sudo >/dev/null 2>&1; then
            # Check using lsof with sudo (but handle failures gracefully)
            local pids
            pids=$(sudo -n lsof -i :"$port" -t 2>/dev/null || true)
            if [ -n "$pids" ]; then
                port_in_use=true
                echo -e "${YELLOW}Port ${port} is in use (lsof detected):${NC}"
                sudo -n lsof -i :"$port" 2>/dev/null || true
            fi

            # Stop system services (with sudo, but handle failures)
            if sudo -n systemctl is-active --quiet nginx 2>/dev/null; then
                port_in_use=true
                cleanup_needed=true
                echo -e "${YELLOW}Stopping system nginx service...${NC}"
                sudo -n systemctl stop nginx 2>/dev/null || true
                sudo -n systemctl disable nginx 2>/dev/null || true
            fi

            if sudo -n systemctl is-active --quiet apache2 2>/dev/null; then
                port_in_use=true
                cleanup_needed=true
                echo -e "${YELLOW}Stopping apache2 service...${NC}"
                sudo -n systemctl stop apache2 2>/dev/null || true
                sudo -n systemctl disable apache2 2>/dev/null || true
            fi

            # Try to kill processes holding the port
            if [ "$cleanup_needed" = true ]; then
                echo -e "${YELLOW}Force freeing port ${port}...${NC}"
                sudo -n fuser -k "${port}/tcp" 2>/dev/null || true
            fi
        fi

        # Wait a bit for cleanup to take effect
        if [ "$cleanup_needed" = true ]; then
            sleep "$delay"
        fi

        # Test if port is actually available now
        if test_port_available; then
            echo -e "${GREEN}Port ${port} is available${NC}"
            return 0
        else
            if [ "$attempt" -lt "$retries" ]; then
                echo -e "${YELLOW}Port ${port} still appears to be in use, retrying...${NC}"
                sleep "$delay"
            fi
        fi
    done

    # Final check - try to see what's using the port
    echo -e "${RED}Failed to free port ${port} after ${retries} attempts${NC}"
    echo -e "${YELLOW}Final port status:${NC}"
    
    # Check without sudo first
    if command -v ss >/dev/null 2>&1; then
        ss -tln 2>/dev/null | grep ":${port} " || true
    fi
    
    docker ps -a --format "{{.Names}} {{.Ports}}" 2>/dev/null | grep -E ":${port}" || true
    
    # Try with sudo if available
    if command -v sudo >/dev/null 2>&1; then
        sudo -n lsof -i :"$port" 2>/dev/null || true
    fi
    
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

# Set ENV_FILE path for docker-compose commands
ENV_FILE="$(pwd)/.env"

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
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml pull web || {
    echo -e "${YELLOW}Warning: Could not pull web image (will build locally)${NC}"
}

# Check for port conflicts and stop conflicting services
echo -e "${YELLOW}Checking for port conflicts...${NC}"
ensure_port_available 80 3 2
ensure_port_available 443 3 2

# Stop and remove old containers (including networks to release ports)
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down --remove-orphans || true

# Force remove any containers that might still be running (by name pattern)
echo -e "${YELLOW}Cleaning up any remaining containers...${NC}"
# Get container names from docker-compose to ensure we catch all
COMPOSE_PROJECT_NAME=$(docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config --services 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "habit_reward")
docker ps -a --filter "name=${COMPOSE_PROJECT_NAME}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
# Also check for containers with our specific names
for container_name in habit_reward_nginx habit_reward_web habit_reward_db; do
    docker ps -a --filter "name=^${container_name}$" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done

# Force remove any containers using ports 80 or 443
echo -e "${YELLOW}Removing any containers using ports 80/443...${NC}"
for port in 80 443; do
    containers=$(docker ps -a --format "{{.ID}} {{.Names}} {{.Ports}}" 2>/dev/null | grep -E ":${port}->|:${port}/|0.0.0.0:${port}:" | awk '{print $1}' || true)
    if [ -n "$containers" ]; then
        echo "$containers" | xargs -r docker rm -f 2>/dev/null || true
    fi
done

# Wait for Docker to fully release network namespaces and port bindings
echo -e "${YELLOW}Waiting for Docker to release ports (10 seconds)...${NC}"
sleep 10

# Kill any remaining docker-proxy processes (they can linger)
echo -e "${YELLOW}Checking for lingering docker-proxy processes...${NC}"
for port in 80 443; do
    proxy_pids=$(pgrep -f "docker-proxy.*:${port}" 2>/dev/null || true)
    if [ -n "$proxy_pids" ]; then
        echo -e "${YELLOW}Found docker-proxy for port ${port}, killing...${NC}"
        echo "$proxy_pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
    fi
done

# Ensure ports are still free before bringing containers back up (docker-proxy can linger briefly)
ensure_port_available 80 10 3
ensure_port_available 443 10 3

# Remove old, unused images to free up space
echo -e "${YELLOW}Cleaning up old Docker images...${NC}"
docker image prune -f || true

# Build nginx image locally (since it's not in a registry)
echo -e "${YELLOW}Building nginx image...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml build nginx

# Final port check right before starting containers (critical!)
echo -e "${YELLOW}Final port check before starting containers...${NC}"
ensure_port_available 80 5 2
ensure_port_available 443 5 2

# Additional verification: Try to test port binding with Docker
echo -e "${YELLOW}Verifying ports are available for Docker...${NC}"
# Check if any Docker containers are still using these ports
for port in 80 443; do
    if docker ps --format "{{.Ports}}" 2>/dev/null | grep -q ":${port}->"; then
        echo -e "${RED}ERROR: Port ${port} is still bound by a Docker container!${NC}"
        docker ps --format "{{.Names}} {{.Ports}}" 2>/dev/null | grep ":${port}" || true
        echo -e "${YELLOW}Attempting to remove containers...${NC}"
        docker ps -a --format "{{.ID}} {{.Names}} {{.Ports}}" 2>/dev/null | grep ":${port}" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
        sleep 3
        ensure_port_available "$port" 3 2
    fi
done

# Start new containers (web will use pulled image if available, nginx uses built image)
echo -e "${YELLOW}Starting new containers...${NC}"
# Start containers one by one to catch port conflicts early
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d db web || {
    echo -e "${RED}Failed to start db/web containers${NC}"
    docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
    exit 1
}

# Small delay before starting nginx to ensure other containers are up
sleep 2

# Start nginx last (since it needs ports 80/443)
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d nginx || {
    echo -e "${RED}Failed to start nginx container - checking port status...${NC}"
    ensure_port_available 80 3 1
    ensure_port_available 443 3 1
    echo -e "${YELLOW}Retrying nginx startup...${NC}"
    docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d nginx || {
        echo -e "${RED}Failed to start nginx after retry${NC}"
        docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
        docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs nginx
        exit 1
    }
}

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check container status
echo -e "${YELLOW}Checking container status...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps

# Show logs (last 50 lines)
echo -e "${YELLOW}Recent logs from web container:${NC}"
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs --tail=50 web

# Verify deployment
echo -e "${YELLOW}Verifying deployment...${NC}"

# Check if web container is running
WEB_RUNNING=$(docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps -q web)
if [ -z "$WEB_RUNNING" ]; then
    echo -e "${RED}Error: Web container is not running!${NC}"
    docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs web
    exit 1
fi

# Check if database container is running
DB_RUNNING=$(docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps -q db)
if [ -z "$DB_RUNNING" ]; then
    echo -e "${RED}Error: Database container is not running!${NC}"
    docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs db
    exit 1
fi

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec -T web python manage.py check --database default || {
    echo -e "${RED}Error: Database connection failed!${NC}"
    exit 1
}

# Check webhook status (if configured)
if [ -n "$TELEGRAM_WEBHOOK_URL" ]; then
    echo -e "${YELLOW}Verifying Telegram webhook...${NC}"
    docker-compose --env-file "$ENV_FILE" -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec -T web python -c "
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
echo -e "${YELLOW}Monitor logs with: docker-compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f${NC}"
echo -e "${YELLOW}Stop services with: docker-compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down${NC}"

exit 0
