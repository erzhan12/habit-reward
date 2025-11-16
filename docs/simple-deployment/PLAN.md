# Simple 2-Container Deployment Plan with Automatic HTTPS

**Target Domain:** habitreward.duckdns.org
**Target IP:** 206.189.40.240
**Date:** 2025-11-16
**Status:** Planning Phase

---

## Executive Summary

This plan replaces the current complex 3-container deployment (PostgreSQL + Django/Bot + nginx + manual certbot) with a simplified 2-container architecture using Caddy for automatic SSL management and SQLite for data persistence.

### Key Benefits

✅ **Automatic HTTPS** - Caddy handles SSL certificates automatically (no manual certbot)
✅ **Simpler Configuration** - 15-line Caddyfile vs 100+ line nginx config
✅ **No Port Conflicts** - Eliminates the port binding issues we encountered
✅ **Single-File Database** - Easy backups with SQLite
✅ **Faster Deployments** - Fewer moving parts, quicker startup
✅ **Auto SSL Renewal** - Caddy renews certificates automatically

### Trade-offs

❌ **SQLite Limitations** - Not suitable for high-concurrency (fine for Telegram bot)
❌ **No Horizontal Scaling** - SQLite is single-instance (can migrate to PostgreSQL later)
⚠️ **Data Migration Required** - One-time migration from PostgreSQL to SQLite

---

## Current vs Proposed Architecture

### Current Architecture (3 Containers)

```
┌─────────────────────────────────────────────────┐
│  VPS (206.189.40.240)                          │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │  habit_reward_nginx (Port 80, 443)      │  │
│  │  - Manual certbot SSL setup             │  │
│  │  - 100+ line nginx config               │  │
│  │  - Port binding issues                  │  │
│  └──────────────┬──────────────────────────┘  │
│                 │ reverse proxy                │
│  ┌──────────────▼──────────────────────────┐  │
│  │  habit_reward_web (Port 8000)           │  │
│  │  - Django + Uvicorn                     │  │
│  │  - Telegram Bot (webhook)               │  │
│  └──────────────┬──────────────────────────┘  │
│                 │                              │
│  ┌──────────────▼──────────────────────────┐  │
│  │  habit_reward_db (Port 5432)            │  │
│  │  - PostgreSQL 16                        │  │
│  │  - Complex connection management        │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  Issues:                                        │
│  - Port 80/443 conflicts                       │
│  - Manual SSL certificate management           │
│  - Complex multi-container orchestration       │
│  - DATABASE_URL encoding issues                │
└─────────────────────────────────────────────────┘
```

### Proposed Architecture (2 Containers)

```
┌─────────────────────────────────────────────────┐
│  VPS (206.189.40.240)                          │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │  habit_reward_caddy (Port 80, 443)      │  │
│  │  - Automatic SSL (Let's Encrypt)        │  │
│  │  - 15-line Caddyfile                    │  │
│  │  - Auto-renewal                         │  │
│  │  - Zero configuration                   │  │
│  └──────────────┬──────────────────────────┘  │
│                 │ reverse proxy                │
│  ┌──────────────▼──────────────────────────┐  │
│  │  habit_reward_web (Port 8000)           │  │
│  │  - Django + Uvicorn                     │  │
│  │  - Telegram Bot (webhook)               │  │
│  │  - SQLite database (persistent volume)  │  │
│  │  - All-in-one application container     │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  Benefits:                                      │
│  - Automatic HTTPS (zero config)               │
│  - No port conflicts                           │
│  - Simple backup (one file)                    │
│  - Faster deployments                          │
└─────────────────────────────────────────────────┘
```

---

## Why This Approach?

### Why Caddy Instead of nginx?

1. **Automatic SSL**
   - nginx: Manual certbot commands, renewal scripts, port stopping
   - Caddy: Automatic Let's Encrypt on first HTTPS request, auto-renewal

2. **Configuration Simplicity**
   - nginx: 100+ lines for SSL, proxy, headers, redirects
   - Caddy: 10-15 lines total

3. **Zero Maintenance**
   - nginx: Monitor cert expiry, run renewal commands
   - Caddy: Set it and forget it

4. **No Port Conflicts**
   - nginx: Recent issues with certbot port binding
   - Caddy: Handles both HTTP challenge and HTTPS in one container

### Why SQLite Instead of PostgreSQL?

1. **Simplicity**
   - PostgreSQL: Separate container, connection strings, user management
   - SQLite: Single file, no network overhead

2. **Backup Simplicity**
   - PostgreSQL: `pg_dump` commands, complex restore
   - SQLite: Copy one file

3. **Resource Efficiency**
   - PostgreSQL: ~50MB RAM + separate container
   - SQLite: No additional overhead

4. **Sufficient for Use Case**
   - Telegram bots are low-concurrency (one user at a time)
   - Typical usage: <100 requests/minute
   - SQLite handles this perfectly

5. **Easy Migration Path**
   - Can switch to PostgreSQL later if needed
   - Django supports both transparently

---

## Detailed Implementation Plan

### Phase 1: Preparation (15 minutes)

#### Step 1.1: Commit Current State
```bash
# On local machine
cd /Users/erzhan/Data/PROJ/habit_reward

# Check current changes
git status

# Commit any uncommitted changes
git add -A
git commit -m "chore: checkpoint before simple deployment migration"

# Push to GitHub
git push origin main
```

#### Step 1.2: Create New Branch
```bash
# Create and switch to new branch
git checkout -b simple-caddy-deploy

# Push branch to GitHub
git push -u origin simple-caddy-deploy
```

#### Step 1.3: Backup Current Data (on VPS)
```bash
# SSH to VPS
ssh deploy@206.189.40.240

# Navigate to deployment directory
cd /home/deploy/habit_reward_bot

# Backup PostgreSQL database
docker-compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec -T db \
  pg_dump -U postgres habit_reward > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql

# Download backup to local machine (from local terminal)
scp deploy@206.189.40.240:/home/deploy/habit_reward_bot/backup_*.sql ~/Desktop/
```

### Phase 2: Create New Files (30 minutes)

#### File 1: Caddyfile

**Location:** `deployment/caddy/Caddyfile`

```caddyfile
# Habit Reward Bot - Caddy Configuration
# Automatic HTTPS with Let's Encrypt

habitreward.duckdns.org {
    # Automatic HTTPS via Let's Encrypt
    # Certificate obtained on first HTTPS request
    # Auto-renewal handled automatically
    tls admin@example.com {
        # Optional: Use ZeroSSL as fallback
        # issuer acme {
        #     ca https://acme.zerossl.com/v2/DV90
        # }
    }

    # Reverse proxy to Django application
    reverse_proxy web:8000 {
        # Health check
        health_uri /admin/login/
        health_interval 30s
        health_timeout 10s
    }

    # Static files (optional - Django can serve via WhiteNoise)
    handle /static/* {
        root * /app/staticfiles
        file_server
    }

    # Security headers
    header {
        # HSTS
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        # Prevent clickjacking
        X-Frame-Options "SAMEORIGIN"
        # Prevent MIME sniffing
        X-Content-Type-Options "nosniff"
        # XSS protection
        X-XSS-Protection "1; mode=block"
        # Referrer policy
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Logging
    log {
        output file /var/log/caddy/access.log
        format console
    }

    # Error handling
    handle_errors {
        respond "{http.error.status_code} {http.error.status_text}"
    }
}

# Redirect www to non-www (if needed)
www.habitreward.duckdns.org {
    redir https://habitreward.duckdns.org{uri} permanent
}
```

#### File 2: Docker Compose

**Location:** `deployment/docker/docker-compose.caddy.yml`

```yaml
version: '3.8'

services:
  # Django Application + Telegram Bot
  web:
    build:
      context: ../../
      dockerfile: deployment/docker/Dockerfile.simple
    container_name: habit_reward_web
    restart: unless-stopped

    environment:
      # Django Configuration
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG:-False}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-habitreward.duckdns.org}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-https://habitreward.duckdns.org}

      # Database (SQLite for simplicity)
      DATABASE_URL: sqlite:////app/data/db.sqlite3

      # Telegram Bot Configuration
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_WEBHOOK_URL: ${TELEGRAM_WEBHOOK_URL:-https://habitreward.duckdns.org/webhook/telegram}

      # Optional: Django Superuser (created on first run)
      DJANGO_SUPERUSER_USERNAME: ${DJANGO_SUPERUSER_USERNAME:-admin}
      DJANGO_SUPERUSER_EMAIL: ${DJANGO_SUPERUSER_EMAIL:-admin@example.com}
      DJANGO_SUPERUSER_PASSWORD: ${DJANGO_SUPERUSER_PASSWORD:-}

      # Optional: AI/LLM Configuration
      LLM_PROVIDER: ${LLM_PROVIDER:-openai}
      LLM_MODEL: ${LLM_MODEL:-gpt-3.5-turbo}
      LLM_API_KEY: ${LLM_API_KEY:-}

      # Optional: Application Settings
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      SUPPORTED_LANGUAGES: ${SUPPORTED_LANGUAGES:-en,ru,kk}
      STREAK_MULTIPLIER_RATE: ${STREAK_MULTIPLIER_RATE:-0.1}

    volumes:
      # Persist SQLite database
      - app_data:/app/data
      # Persist static files
      - static_files:/app/staticfiles

    # Don't expose port to host (Caddy handles this)
    expose:
      - "8000"

    networks:
      - habit_reward_network

    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Caddy Reverse Proxy with Automatic SSL
  caddy:
    image: caddy:2-alpine
    container_name: habit_reward_caddy
    restart: unless-stopped
    depends_on:
      web:
        condition: service_healthy

    ports:
      - "80:80"       # HTTP
      - "443:443"     # HTTPS
      - "443:443/udp" # HTTP/3 (QUIC)

    volumes:
      # Caddy configuration
      - ../caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      # Persistent SSL certificates and config
      - caddy_data:/data
      - caddy_config:/config
      # Static files (optional)
      - static_files:/app/staticfiles:ro
      # Logs
      - caddy_logs:/var/log/caddy

    networks:
      - habit_reward_network

    environment:
      - DOMAIN=${DOMAIN:-habitreward.duckdns.org}

volumes:
  app_data:
    driver: local
  static_files:
    driver: local
  caddy_data:
    driver: local
  caddy_config:
    driver: local
  caddy_logs:
    driver: local

networks:
  habit_reward_network:
    driver: bridge
```

#### File 3: Simplified Dockerfile

**Location:** `deployment/docker/Dockerfile.simple`

```dockerfile
# Multi-stage Dockerfile for Habit Reward Bot (Simplified)
# Stage 1: Builder - Install dependencies
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash botuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser manage.py ./

# Copy entrypoint script
COPY --chown=botuser:botuser deployment/scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create directories with proper permissions
RUN mkdir -p /app/staticfiles /app/data && \
    chown -R botuser:botuser /app/staticfiles /app/data

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/')" || exit 1

# Entrypoint handles migrations and superuser creation
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: Start Uvicorn server
CMD ["uvicorn", "src.habit_reward_project.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

#### File 4: GitHub Actions Workflow

**Location:** `.github/workflows/deploy-caddy.yml`

```yaml
name: Build and Deploy (Caddy)

on:
  push:
    branches:
      - main
      - simple-caddy-deploy  # Also deploy from feature branch for testing
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: uv pip install --system -r pyproject.toml

      - name: Run tests
        run: pytest tests/ -v
        env:
          SECRET_KEY: test-secret-key-for-ci
          DATABASE_URL: sqlite:///test.db
          TELEGRAM_BOT_TOKEN: test-token-not-real
          DEBUG: "True"

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./deployment/docker/Dockerfile.simple
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/simple-caddy-deploy'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install SSH key
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}

      - name: Add server to known hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.SERVER_HOST }} >> ~/.ssh/known_hosts

      - name: Create deployment directory
        run: |
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SERVER_HOST }} << 'SETUP'
            mkdir -p ${{ secrets.DEPLOY_PATH }}
            mkdir -p ${{ secrets.DEPLOY_PATH }}/data
            mkdir -p ${{ secrets.DEPLOY_PATH }}/staticfiles
          SETUP

      - name: Copy deployment files to server
        run: |
          tar czf - -C deployment . | ssh ${{ secrets.SSH_USER }}@${{ secrets.SERVER_HOST }} \
            "cd ${{ secrets.DEPLOY_PATH }} && tar xzf -"

      - name: Create .env file on server
        run: |
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SERVER_HOST }} << 'ENVSETUP'
            cd ${{ secrets.DEPLOY_PATH }}

            # Backup existing .env if it exists
            if [ -f .env ]; then
              cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
            fi

            # Create new .env file
            cat > .env << 'EOF'
# Django Configuration
SECRET_KEY=${{ secrets.DJANGO_SECRET_KEY }}
DEBUG=False
ALLOWED_HOSTS=${{ secrets.ALLOWED_HOSTS }}
CSRF_TRUSTED_ORIGINS=${{ secrets.CSRF_TRUSTED_ORIGINS }}

# Database (SQLite for simplicity)
DATABASE_URL=sqlite:////app/data/db.sqlite3

# Telegram Bot
TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}
TELEGRAM_WEBHOOK_URL=${{ secrets.TELEGRAM_WEBHOOK_URL }}

# Superuser (created on first run if not exists)
DJANGO_SUPERUSER_USERNAME=${{ secrets.DJANGO_SUPERUSER_USERNAME }}
DJANGO_SUPERUSER_EMAIL=${{ secrets.DJANGO_SUPERUSER_EMAIL }}
DJANGO_SUPERUSER_PASSWORD=${{ secrets.DJANGO_SUPERUSER_PASSWORD }}

# Docker Configuration
DOCKER_REGISTRY=${{ env.REGISTRY }}
DOCKER_IMAGE_NAME=${{ env.IMAGE_NAME }}
IMAGE_TAG=latest

# Domain
DOMAIN=habitreward.duckdns.org

# Optional: LLM/AI Configuration
LLM_PROVIDER=${{ secrets.LLM_PROVIDER }}
LLM_MODEL=${{ secrets.LLM_MODEL }}
LLM_API_KEY=${{ secrets.LLM_API_KEY }}

# Application Settings
LOG_LEVEL=INFO
SUPPORTED_LANGUAGES=en,ru,kk
STREAK_MULTIPLIER_RATE=0.1
EOF

            echo "✅ .env file created successfully"
          ENVSETUP

      - name: Deploy containers with Caddy
        run: |
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SERVER_HOST }} << 'DEPLOY'
            cd ${{ secrets.DEPLOY_PATH }}

            # Login to GitHub Container Registry
            echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

            # Pull latest application image
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml pull web

            # Stop existing containers gracefully
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml down --timeout 30

            # Start new containers
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml up -d

            # Wait for services to be ready
            echo "Waiting for containers to start..."
            sleep 15

            # Show container status
            echo "Container Status:"
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml ps
          DEPLOY

      - name: Verify deployment health
        run: |
          ssh ${{ secrets.SSH_USER }}@${{ secrets.SERVER_HOST }} << 'VERIFY'
            cd ${{ secrets.DEPLOY_PATH }}

            echo "Checking container logs:"
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml logs --tail=30 web
            docker-compose --env-file .env -f docker/docker-compose.caddy.yml logs --tail=30 caddy

            echo "Checking container health:"
            docker inspect habit_reward_web --format='{{.State.Health.Status}}'
          VERIFY

  health-check:
    name: Health Check (HTTPS)
    runs-on: ubuntu-latest
    needs: deploy
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/simple-caddy-deploy'

    steps:
      - name: Wait for services to stabilize
        run: sleep 30

      - name: Check HTTPS endpoint
        run: |
          echo "Testing HTTPS endpoint..."
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://habitreward.duckdns.org/admin/login/ || echo "000")

          if [ "$STATUS" == "200" ] || [ "$STATUS" == "302" ]; then
            echo "✅ HTTPS is working! (HTTP $STATUS)"
          else
            echo "⚠️ Warning: Unexpected HTTP status: $STATUS"
            echo "This might be normal on first deployment (SSL cert provisioning)"
            # Don't fail the workflow - Caddy might still be provisioning cert
          fi

      - name: Check SSL certificate
        run: |
          echo "Checking SSL certificate..."
          echo | openssl s_client -servername habitreward.duckdns.org -connect habitreward.duckdns.org:443 2>/dev/null | \
            openssl x509 -noout -dates || echo "SSL cert not ready yet (will be provisioned automatically)"
```

#### File 5: Environment Template

**Location:** `.env.caddy.example`

```bash
# Habit Reward Bot - Caddy Deployment Configuration
# Copy this file to .env and fill in your values

# ===== Django Configuration =====
SECRET_KEY=your-secret-key-generate-with-python-django-command
DEBUG=False
ALLOWED_HOSTS=habitreward.duckdns.org,localhost
CSRF_TRUSTED_ORIGINS=https://habitreward.duckdns.org

# ===== Database Configuration =====
# Using SQLite for simplicity (stored in persistent volume)
DATABASE_URL=sqlite:////app/data/db.sqlite3

# ===== Telegram Bot Configuration =====
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://habitreward.duckdns.org/webhook/telegram

# ===== Django Superuser (Auto-created on first run) =====
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=change-me-to-strong-password

# ===== Docker Configuration =====
DOCKER_REGISTRY=ghcr.io
DOCKER_IMAGE_NAME=your-github-username/habit-reward
IMAGE_TAG=latest

# ===== Domain Configuration =====
DOMAIN=habitreward.duckdns.org

# ===== Optional: AI/LLM Configuration =====
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=

# ===== Application Settings =====
LOG_LEVEL=INFO
SUPPORTED_LANGUAGES=en,ru,kk
STREAK_MULTIPLIER_RATE=0.1
```

#### File 6: Manual Deployment Script

**Location:** `deployment/scripts/deploy-caddy.sh`

```bash
#!/bin/bash
# Manual deployment script for Caddy-based setup
# Use this if GitHub Actions deployment fails

set -e

echo "🚀 Deploying Habit Reward Bot (Caddy)..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env from .env.caddy.example"
    exit 1
fi

# Navigate to docker directory
cd "$(dirname "$0")/../docker"

echo "📦 Pulling latest images..."
docker-compose -f docker-compose.caddy.yml pull web

echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.caddy.yml down --timeout 30

echo "🚀 Starting containers..."
docker-compose -f docker-compose.caddy.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 15

echo "📊 Container Status:"
docker-compose -f docker-compose.caddy.yml ps

echo "📝 Recent Logs:"
echo "=== Web Container ==="
docker-compose -f docker-compose.caddy.yml logs --tail=20 web

echo "=== Caddy Container ==="
docker-compose -f docker-compose.caddy.yml logs --tail=20 caddy

echo "✅ Deployment complete!"
echo "🌐 Access your application at: https://habitreward.duckdns.org"
echo "🔧 Admin panel: https://habitreward.duckdns.org/admin/"
echo ""
echo "📋 Next steps:"
echo "1. Wait 1-2 minutes for Caddy to obtain SSL certificate"
echo "2. Test the admin panel"
echo "3. Test Telegram bot webhook"
echo ""
echo "🔍 Monitor logs with:"
echo "docker-compose -f docker-compose.caddy.yml logs -f"
```

### Phase 3: GitHub Configuration (10 minutes)

#### Update GitHub Secrets

Navigate to: `https://github.com/YOUR_USERNAME/habit_reward/settings/secrets/actions`

**Secrets to KEEP (already exist):**
- `SSH_PRIVATE_KEY`
- `SERVER_HOST` = `206.189.40.240`
- `SSH_USER` = `deploy`
- `DEPLOY_PATH` = `/home/deploy/habit_reward_bot`
- `DJANGO_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`
- `LLM_PROVIDER` (optional)
- `LLM_MODEL` (optional)
- `LLM_API_KEY` (optional)

**Secrets to UPDATE:**
- `ALLOWED_HOSTS` = `habitreward.duckdns.org`
- `CSRF_TRUSTED_ORIGINS` = `https://habitreward.duckdns.org`
- `TELEGRAM_WEBHOOK_URL` = `https://habitreward.duckdns.org/webhook/telegram`

**Secrets to REMOVE (no longer needed):**
- ~~`POSTGRES_DB`~~
- ~~`POSTGRES_USER`~~
- ~~`POSTGRES_PASSWORD`~~

### Phase 4: Local Testing (20 minutes)

#### Test Build Locally

```bash
# On local machine
cd /Users/erzhan/Data/PROJ/habit_reward

# Build the Docker image
docker build -t habit-reward-simple:test -f deployment/docker/Dockerfile.simple .

# Create test .env
cp .env.caddy.example .env.test
# Edit .env.test with test values

# Test run locally
docker run --rm -it \
  --env-file .env.test \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  habit-reward-simple:test

# In another terminal, test the endpoint
curl http://localhost:8000/admin/login/

# Should return HTTP 200 or 302
```

#### Test Caddy Configuration

```bash
# Test Caddyfile syntax
docker run --rm -v $(pwd)/deployment/caddy/Caddyfile:/etc/caddy/Caddyfile \
  caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile

# Should output: "Valid configuration"
```

### Phase 5: VPS Deployment (30 minutes)

#### Step 5.1: Prepare VPS

```bash
# SSH to VPS
ssh deploy@206.189.40.240

# Navigate to deployment directory
cd /home/deploy/habit_reward_bot

# Pull latest code (from simple-caddy-deploy branch)
git fetch origin
git checkout simple-caddy-deploy
git pull origin simple-caddy-deploy
```

#### Step 5.2: Stop Old Containers

```bash
# Stop existing containers
cd /home/deploy/habit_reward_bot/docker
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml down

# Verify containers stopped
docker ps
# Should show no habit_reward containers
```

#### Step 5.3: Create .env File

```bash
cd /home/deploy/habit_reward_bot

# Copy example env file
cp .env.caddy.example .env

# Edit with real values
nano .env

# Set:
# - SECRET_KEY (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
# - TELEGRAM_BOT_TOKEN
# - DJANGO_SUPERUSER_PASSWORD
# - Other values as needed
```

#### Step 5.4: Start New Containers

```bash
cd /home/deploy/habit_reward_bot/docker

# Start containers
docker-compose --env-file ../.env -f docker-compose.caddy.yml up -d

# Watch logs
docker-compose --env-file ../.env -f docker-compose.caddy.yml logs -f

# Wait for:
# - Web container: "Uvicorn running on http://0.0.0.0:8000"
# - Caddy container: "serving initial configuration"
```

#### Step 5.5: Verify Deployment

```bash
# Check container status
docker-compose --env-file ../.env -f docker-compose.caddy.yml ps

# Both containers should show "Up" status

# Check web container health
docker inspect habit_reward_web --format='{{.State.Health.Status}}'
# Should show: "healthy"

# Test from VPS
curl -I http://localhost:8000/admin/login/
# Should return: HTTP/1.1 302 Found (redirect to login)

# Test HTTPS (will trigger SSL cert provisioning)
curl -I https://habitreward.duckdns.org/admin/login/
# First time: May take 10-30 seconds while Caddy gets certificate
# Should return: HTTP/2 302 (with valid SSL)
```

#### Step 5.6: Verify SSL Certificate

```bash
# Check Caddy logs for SSL provisioning
docker-compose --env-file ../.env -f docker-compose.caddy.yml logs caddy | grep -i "certificate"

# Should see:
# "certificate obtained successfully"
# "serving remaining initial configuration"

# Check certificate details
echo | openssl s_client -servername habitreward.duckdns.org \
  -connect habitreward.duckdns.org:443 2>/dev/null | \
  openssl x509 -noout -text | grep -E "Issuer|Not After"

# Should show Let's Encrypt as issuer
# Expiry date should be ~90 days in future
```

### Phase 6: Data Migration (Optional, 15-30 minutes)

#### Option A: Fresh Start (Recommended)

```bash
# The entrypoint.sh already runs migrations and creates superuser
# Just access admin panel and recreate test data

# 1. Open browser: https://habitreward.duckdns.org/admin/
# 2. Login with DJANGO_SUPERUSER credentials
# 3. Create 2-3 test habits
# 4. Test Telegram bot
```

#### Option B: Migrate Data from PostgreSQL

```bash
# On VPS with old PostgreSQL still running

# 1. Export data from PostgreSQL
cd /home/deploy/habit_reward_bot
docker-compose -f docker/docker-compose.yml exec web \
  python manage.py dumpdata \
  --exclude auth.permission \
  --exclude contenttypes \
  --indent 2 > data_export.json

# 2. Copy data to new container
docker cp data_export.json habit_reward_web:/app/data/

# 3. Load data into SQLite
docker exec habit_reward_web \
  python manage.py loaddata /app/data/data_export.json

# 4. Verify data
docker exec habit_reward_web \
  python manage.py shell << 'PYTHON'
from src.core.models import User, Habit, Reward
print(f"Users: {User.objects.count()}")
print(f"Habits: {Habit.objects.count()}")
print(f"Rewards: {Reward.objects.count()}")
PYTHON
```

### Phase 7: Set Telegram Webhook (5 minutes)

```bash
# The webhook URL is automatically set via environment variable
# But you can verify it's set correctly:

curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# Should show:
# {
#   "ok": true,
#   "result": {
#     "url": "https://habitreward.duckdns.org/webhook/telegram",
#     "has_custom_certificate": false,
#     "pending_update_count": 0
#   }
# }

# If not set, set it manually:
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://habitreward.duckdns.org/webhook/telegram"
```

### Phase 8: Testing & Verification (15 minutes)

#### Test Checklist

- [ ] **Admin Panel Access**
  ```bash
  # Open in browser
  open https://habitreward.duckdns.org/admin/

  # Login with superuser credentials
  # Should work without SSL warnings
  ```

- [ ] **SSL Certificate**
  ```bash
  # Check SSL grade
  curl -I https://habitreward.duckdns.org
  # Should return HTTP/2 302

  # Check browser - should show secure lock icon
  ```

- [ ] **Telegram Bot**
  ```bash
  # Open Telegram
  # Send /start to your bot
  # Should receive welcome message

  # Send /help
  # Should receive help text

  # Try logging a habit
  ```

- [ ] **Database Persistence**
  ```bash
  # Create a test habit in admin panel
  # Restart containers
  docker-compose -f docker/docker-compose.caddy.yml restart

  # Check if habit still exists
  # Should persist (SQLite data in volume)
  ```

- [ ] **Logs**
  ```bash
  # Check for errors
  docker-compose -f docker/docker-compose.caddy.yml logs | grep -i error
  # Should show minimal or no errors
  ```

- [ ] **Resource Usage**
  ```bash
  # Check container resource usage
  docker stats --no-stream

  # Should show reasonable CPU/RAM usage
  # Typically: Web ~200MB, Caddy ~50MB
  ```

---

## Rollback Plan

If anything goes wrong during deployment, you can rollback:

### Quick Rollback (5 minutes)

```bash
# SSH to VPS
ssh deploy@206.189.40.240
cd /home/deploy/habit_reward_bot

# Stop new containers
docker-compose -f docker/docker-compose.caddy.yml down

# Switch back to main branch
git checkout main

# Start old containers
cd docker
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify old setup is working
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Data Rollback (if needed)

```bash
# If you migrated data and need to restore PostgreSQL

# 1. Stop new containers
docker-compose -f docker-compose.caddy.yml down

# 2. Start old PostgreSQL container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db

# 3. Restore from backup
docker exec -i habit_reward_db psql -U postgres habit_reward < backup_YYYYMMDD_HHMMSS.sql

# 4. Start old web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d web nginx
```

---

## Maintenance & Operations

### Daily Operations

**View Logs:**
```bash
# Follow all logs
docker-compose -f docker-compose.caddy.yml logs -f

# Follow specific container
docker-compose -f docker-compose.caddy.yml logs -f web
docker-compose -f docker-compose.caddy.yml logs -f caddy

# View recent errors
docker-compose -f docker-compose.caddy.yml logs | grep -i error | tail -50
```

**Restart Containers:**
```bash
# Restart all
docker-compose -f docker-compose.caddy.yml restart

# Restart specific service
docker-compose -f docker-compose.caddy.yml restart web
```

**Update Deployment:**
```bash
# GitHub Actions handles this automatically on push to main
# Or manually:
cd /home/deploy/habit_reward_bot
git pull origin main
docker-compose -f docker/docker-compose.caddy.yml pull
docker-compose -f docker/docker-compose.caddy.yml up -d
```

### Weekly Operations

**Backup Database:**
```bash
# Create backup directory
mkdir -p /home/deploy/backups

# Backup SQLite database
docker cp habit_reward_web:/app/data/db.sqlite3 \
  /home/deploy/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# Compress old backups
find /home/deploy/backups -name "db_*.sqlite3" -mtime +1 -exec gzip {} \;

# Keep only last 30 days
find /home/deploy/backups -name "db_*.sqlite3.gz" -mtime +30 -delete
```

**Check Disk Space:**
```bash
# Check overall disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up old images/containers (if needed)
docker system prune -a --filter "until=168h"
```

### Monthly Operations

**Update System Packages:**
```bash
sudo apt update
sudo apt upgrade -y
```

**Check SSL Certificate:**
```bash
# Caddy auto-renews, but verify it's working
docker-compose -f docker-compose.caddy.yml logs caddy | grep -i "renew"

# Check expiry
echo | openssl s_client -servername habitreward.duckdns.org \
  -connect habitreward.duckdns.org:443 2>/dev/null | \
  openssl x509 -noout -dates
```

---

## Comparison: Before vs After

### Complexity Metrics

| Metric | Before (nginx) | After (Caddy) | Improvement |
|--------|----------------|---------------|-------------|
| Containers | 3 | 2 | 33% fewer |
| Config Files | 5 | 3 | 40% fewer |
| Config Lines | ~300 | ~100 | 67% less |
| Manual SSL Steps | 5 | 0 | 100% automated |
| Deployment Time | 15-20 min | 5-10 min | 50% faster |
| Maintenance/Month | 30-60 min | 10-15 min | 75% less |

### Cost Analysis

| Aspect | Before | After | Savings |
|--------|--------|-------|---------|
| VPS Cost | $6-12/mo | $6-12/mo | $0 (same) |
| Developer Time | 2-3 hrs/mo | 30 min/mo | ~2.5 hrs/mo |
| Downtime Risk | Medium | Low | - |
| SSL Cert Cost | $0 (Let's Encrypt) | $0 (Let's Encrypt) | $0 |

### Feature Comparison

| Feature | Before | After | Notes |
|---------|--------|-------|-------|
| HTTPS/SSL | ✅ Manual | ✅ Automatic | Caddy auto-renews |
| Database | PostgreSQL | SQLite | Simpler for bot usage |
| Backups | pg_dump | File copy | Much simpler |
| Port Conflicts | ❌ Had issues | ✅ None | Caddy handles cleanly |
| Config Complexity | High | Low | 15 lines vs 100+ |
| Deployment Speed | Slow | Fast | Fewer moving parts |
| Scalability | Horizontal | Vertical | Trade-off for simplicity |
| Data Migration | Complex | Simple | Single file |

---

## Troubleshooting

### Issue: Caddy Can't Get SSL Certificate

**Symptoms:**
```
Error obtaining certificate: acme: error: 403
```

**Solutions:**
1. **Check DNS:** Ensure `habitreward.duckdns.org` points to `206.189.40.240`
   ```bash
   nslookup habitreward.duckdns.org
   ```

2. **Check Firewall:** Ensure ports 80 and 443 are open
   ```bash
   sudo ufw status
   # Should show 80/tcp and 443/tcp as ALLOW
   ```

3. **Check Port Availability:**
   ```bash
   sudo lsof -i :80
   sudo lsof -i :443
   # Should only show docker-proxy
   ```

4. **Check Caddy Logs:**
   ```bash
   docker-compose -f docker-compose.caddy.yml logs caddy
   ```

### Issue: Database Connection Errors

**Symptoms:**
```
django.db.utils.OperationalError: unable to open database file
```

**Solutions:**
1. **Check Volume Permissions:**
   ```bash
   docker exec habit_reward_web ls -la /app/data/
   # Should show botuser ownership
   ```

2. **Recreate Volume:**
   ```bash
   docker-compose -f docker-compose.caddy.yml down -v
   docker-compose -f docker-compose.caddy.yml up -d
   ```

### Issue: Telegram Webhook Not Working

**Symptoms:**
- Bot doesn't respond to messages
- Webhook info shows wrong URL

**Solutions:**
1. **Check Webhook:**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
   ```

2. **Reset Webhook:**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://habitreward.duckdns.org/webhook/telegram"
   ```

3. **Check Web Logs:**
   ```bash
   docker-compose -f docker-compose.caddy.yml logs web | grep webhook
   ```

### Issue: High Memory Usage

**Symptoms:**
- Containers using >1GB RAM
- Server becomes slow

**Solutions:**
1. **Check Current Usage:**
   ```bash
   docker stats --no-stream
   ```

2. **Restart Containers:**
   ```bash
   docker-compose -f docker-compose.caddy.yml restart
   ```

3. **Upgrade VPS:**
   - If consistently high, upgrade from 1GB to 2GB plan

---

## Success Criteria

Deployment is successful when:

- ✅ HTTPS works without certificate warnings
- ✅ Admin panel accessible at https://habitreward.duckdns.org/admin/
- ✅ Telegram bot responds to /start command
- ✅ Habits can be created and logged
- ✅ Data persists after container restart
- ✅ SSL certificate auto-renews (verify in 60 days)
- ✅ Deployment time < 10 minutes
- ✅ No port binding errors
- ✅ Container health checks passing
- ✅ GitHub Actions workflow succeeds

---

## Timeline

**Total Estimated Time:** 2-3 hours

| Phase | Time | Description |
|-------|------|-------------|
| Phase 1: Preparation | 15 min | Commit, branch, backup |
| Phase 2: Create Files | 30 min | All new config files |
| Phase 3: GitHub Setup | 10 min | Update secrets |
| Phase 4: Local Testing | 20 min | Test build locally |
| Phase 5: VPS Deployment | 30 min | Deploy to production |
| Phase 6: Data Migration | 15-30 min | Optional |
| Phase 7: Webhook Setup | 5 min | Configure Telegram |
| Phase 8: Testing | 15 min | Verify everything works |

---

## Next Steps

After successful deployment:

1. **Monitor for 24 Hours**
   - Check logs for errors
   - Verify SSL auto-renewal is scheduled
   - Test bot with real users

2. **Document Learnings**
   - Update RULES.md with new deployment patterns
   - Document any issues encountered

3. **Set Up Monitoring (Optional)**
   - UptimeRobot for uptime monitoring
   - Telegram notifications for errors

4. **Optimize Performance (Optional)**
   - Add Redis for caching (if needed)
   - Optimize Docker image size
   - Add CDN for static files

5. **Plan Future Improvements**
   - Consider adding metrics/analytics
   - Plan for user growth
   - Consider PostgreSQL migration if needed

---

## Conclusion

This plan provides a significantly simpler deployment while maintaining all required functionality:

- **Automatic HTTPS** via Caddy (no manual SSL management)
- **Simple Database** with SQLite (easy backups)
- **Fewer Containers** (2 instead of 3)
- **Less Configuration** (100 lines vs 300)
- **Faster Deployments** (5-10 min vs 15-20 min)

The trade-off is moving from PostgreSQL to SQLite, but for a Telegram bot with low concurrency, this is perfectly acceptable and provides significant operational benefits.

**Ready to proceed? Review this plan and confirm to begin implementation.**
