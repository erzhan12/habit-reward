# Habit Reward Bot - Deployment Guide

> **Note:** All deployment files are located in the `/deployment` directory:
> - Docker configs: `/deployment/docker/`
> - Nginx configs: `/deployment/nginx/`
> - Scripts: `/deployment/scripts/`
> - See `/deployment/README.md` for details

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Initial VPS Setup](#initial-vps-setup)
5. [GitHub Repository Setup](#github-repository-setup)
6. [SSL Certificate Setup](#ssl-certificate-setup)
7. [Deployment Process](#deployment-process)
8. [Post-Deployment Configuration](#post-deployment-configuration)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide provides step-by-step instructions to deploy the Habit Reward Telegram Bot to a production environment using:

- **Docker Compose** for container orchestration
- **PostgreSQL** database in a separate container
- **Nginx** as reverse proxy with SSL/TLS
- **GitHub Actions** for CI/CD automation
- **Let's Encrypt** for free SSL certificates

**Deployment Flow:**
```
Push to GitHub (main) → GitHub Actions → Build Docker Image →
Push to Registry → SSH to VPS → Pull & Deploy → Verify
```

---

## Prerequisites

### Required Services & Accounts

1. **VPS/Cloud Server**
   - Minimum specs: 1 CPU, 2GB RAM, 20GB storage
   - Ubuntu 22.04 LTS or similar Linux distribution
   - Root or sudo access
   - Static IP address

2. **Domain Name**
   - A registered domain pointed to your VPS IP
   - DNS A record: `yourdomain.com` → `VPS_IP_ADDRESS`
   - DNS A record: `www.yourdomain.com` → `VPS_IP_ADDRESS` (optional)

3. **Telegram Bot**
   - Bot token from [@BotFather](https://t.me/BotFather)
   - Bot should be created and ready to use

4. **GitHub Account**
   - Repository for your code
   - GitHub Actions enabled (free for public repos)

5. **Optional: AI Provider**
   - OpenAI API key (for habit classification)
   - Or Anthropic API key

### Required Tools (on your local machine)

- Git
- SSH client
- Text editor

---

## Architecture

### Container Architecture

```
┌─────────────────────────────────────────────────────────┐
│                       VPS Server                        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │               Docker Network                     │  │
│  │                                                  │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────┐   │  │
│  │  │  Nginx  │  │   Web    │  │  PostgreSQL  │   │  │
│  │  │ (Proxy) │←→│ (Django  │←→│   Database   │   │  │
│  │  │         │  │   + Bot) │  │              │   │  │
│  │  └────┬────┘  └──────────┘  └──────────────┘   │  │
│  │       │                                          │  │
│  └───────┼──────────────────────────────────────────┘  │
│          │                                             │
└──────────┼─────────────────────────────────────────────┘
           │
     ┌─────┴─────┐
     │  Internet │
     │ (Port 443)│
     └───────────┘
```

### Data Persistence

- **PostgreSQL Data**: Docker volume `postgres_data`
- **Bot Persistence**: Docker volume `bot_data` (conversation state)
- **Static Files**: Docker volume `static_files`
- **SSL Certificates**: Docker volume `certbot_data`

---

## Initial VPS Setup

### Step 1: Connect to Your VPS

```bash
ssh root@YOUR_VPS_IP
```

### Step 2: Update System

```bash
apt update && apt upgrade -y
```

### Step 3: Install Docker

```bash
# Install required packages
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify installation
docker --version
```

### Step 4: Install Docker Compose

```bash
# Download Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Step 5: Create Deployment User (Recommended)

```bash
# Create deploy user
adduser deploy

# Add to docker group
usermod -aG docker deploy

# Grant sudo privileges (if needed)
usermod -aG sudo deploy

# Switch to deploy user
su - deploy
```

### Step 6: Create Deployment Directory

```bash
mkdir -p /home/deploy/habit_reward_bot
cd /home/deploy/habit_reward_bot
```

### Step 7: Configure Firewall

```bash
# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### Step 8: Generate SSH Key for GitHub Actions

```bash
# On your VPS, generate SSH key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions -N ""

# Display public key (add this to ~/.ssh/authorized_keys)
cat ~/.ssh/github_actions.pub

# Add public key to authorized_keys
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# Display private key (add this to GitHub Secrets)
cat ~/.ssh/github_actions
```

**Save the private key** - you'll add it to GitHub Secrets later.

---

## GitHub Repository Setup

### Step 1: Configure Repository Secrets

Go to your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

#### Database Secrets
```
POSTGRES_DB=habit_reward
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generate-strong-password>
```

#### Django Secrets
```
DJANGO_SECRET_KEY=<generate-with-python>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

To generate `DJANGO_SECRET_KEY`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Telegram Secrets
```
TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram
```

#### Superuser Secrets
```
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
DJANGO_SUPERUSER_PASSWORD=<generate-strong-password>
```

#### Optional: LLM Secrets
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=<your-openai-api-key>
```

#### Deployment Secrets
```
SERVER_HOST=<your-vps-ip-or-domain>
SSH_USER=deploy
SSH_PRIVATE_KEY=<paste-private-key-from-step-8>
DEPLOY_PATH=/home/deploy/habit_reward_bot
```

#### GitHub Token (automatic)
The `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### Step 2: Enable GitHub Actions

1. Go to **Settings → Actions → General**
2. Under "Actions permissions", select **Allow all actions and reusable workflows**
3. Under "Workflow permissions", select **Read and write permissions**
4. Click **Save**

### Step 3: Enable GitHub Container Registry

1. Go to **Settings → Packages**
2. Make sure package visibility is set appropriately (public or private)
3. No additional setup needed - GitHub Actions will automatically push images

---

## SSL Certificate Setup

### Option 1: Initial Setup with Self-Signed Certificate (Testing)

If you want to test the deployment before getting a real SSL certificate:

```bash
# On your VPS
cd /home/deploy/habit_reward_bot
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=yourdomain.com"
```

Then update `nginx/conf.d/habit_reward.conf` to point to these files.

### Option 2: Let's Encrypt (Production)

After initial deployment, get a real SSL certificate:

```bash
# On your VPS, run certbot in the certbot container
cd /home/deploy/habit_reward_bot

# Stop nginx temporarily
docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx

# Run certbot to obtain certificate
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly \
  --standalone \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com \
  -d www.yourdomain.com

# Update nginx config to use the certificate
# Edit nginx/conf.d/habit_reward.conf and replace 'example.com' with 'yourdomain.com'

# Start nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml start nginx
```

**Note:** The nginx config file has a placeholder `example.com` - you must replace it with your actual domain before running certbot.

---

## Deployment Process

### Method 1: Automated Deployment (Recommended)

Once everything is set up, deployment is automatic:

1. **Commit and push to main branch:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin main
   ```

2. **Monitor GitHub Actions:**
   - Go to **Actions** tab in your GitHub repository
   - Watch the workflow progress
   - Check for any errors

3. **Verify deployment:**
   - SSH to your VPS
   - Check container status:
     ```bash
     cd /home/deploy/habit_reward_bot
     docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
     ```

### Method 2: Manual Deployment

If you need to deploy manually:

1. **SSH to your VPS:**
   ```bash
   ssh deploy@YOUR_VPS_IP
   cd /home/deploy/habit_reward_bot
   ```

2. **Clone or pull repository:**
   ```bash
   # First time
   git clone https://github.com/YOUR_USERNAME/habit_reward.git .

   # Updates
   git pull origin main
   ```

3. **Create .env file:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your actual values
   ```

4. **Update nginx config:**
   ```bash
   nano nginx/conf.d/habit_reward.conf
   # Replace 'example.com' with your actual domain
   ```

5. **Build and start containers:**
   ```bash
   # For production
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

   # View logs
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
   ```

---

## Post-Deployment Configuration

### Step 1: Verify Containers Are Running

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                    STATUS    PORTS
habit_reward_web        Up        8000/tcp
habit_reward_db         Up        5432/tcp
habit_reward_nginx      Up        0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
habit_reward_certbot    Up
```

### Step 2: Check Application Logs

```bash
# All containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs

# Specific container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs db
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs nginx
```

### Step 3: Verify Database Migrations

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py showmigrations
```

All migrations should show `[X]` indicating they've been applied.

### Step 4: Access Django Admin

1. Open browser: `https://yourdomain.com/admin/`
2. Login with superuser credentials (from GitHub Secrets)
3. Verify you can see the admin panel

### Step 5: Test Telegram Bot

1. Open Telegram and find your bot
2. Send `/start` command
3. Verify bot responds

### Step 6: Verify Webhook

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
import asyncio
from telegram import Bot

async def check_webhook():
    bot = Bot('YOUR_BOT_TOKEN')
    info = await bot.get_webhook_info()
    print(f'Webhook URL: {info.url}')
    print(f'Pending updates: {info.pending_update_count}')

asyncio.run(check_webhook())
"
```

---

## Monitoring & Maintenance

### Daily Monitoring

**View Logs:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=100
```

**Check Container Health:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker stats
```

**Database Size:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db psql -U postgres -d habit_reward -c "SELECT pg_size_pretty(pg_database_size('habit_reward'));"
```

### Backup Database

**Create Backup:**
```bash
# Create backup
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db pg_dump -U postgres habit_reward > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_*.sql

# Copy to safe location
scp backup_*.sql.gz user@backup-server:/backups/
```

**Restore from Backup:**
```bash
# Stop web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop web

# Restore database
gunzip backup_20240101_120000.sql.gz
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db psql -U postgres habit_reward < backup_20240101_120000.sql

# Start web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml start web
```

### Update Application

**Automated (via GitHub Actions):**
Just push to main branch - GitHub Actions handles everything.

**Manual Update:**
```bash
cd /home/deploy/habit_reward_bot
git pull origin main
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Renew SSL Certificates

Certificates auto-renew via the certbot container. To manually renew:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec certbot certbot renew
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

---

## Troubleshooting

### Issue: Containers Won't Start

**Solution:**
```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs

# Check .env file
cat .env

# Verify syntax
docker-compose -f docker-compose.yml -f docker-compose.prod.yml config
```

### Issue: Database Connection Failed

**Solution:**
```bash
# Check database container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs db

# Verify database is running
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT version();"

# Check DATABASE_URL in .env
grep DATABASE_URL .env
```

### Issue: Nginx 502 Bad Gateway

**Solution:**
```bash
# Check if web container is running
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps web

# Check web logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs web

# Check nginx logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs nginx

# Restart web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### Issue: SSL Certificate Error

**Solution:**
```bash
# Check certificate files
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx ls -la /etc/letsencrypt/live/yourdomain.com/

# Verify nginx config
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -t

# Obtain new certificate
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly --standalone -d yourdomain.com
```

### Issue: Telegram Webhook Not Working

**Solution:**
```bash
# Check webhook URL
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
import asyncio
from telegram import Bot
async def check():
    bot = Bot('$TELEGRAM_BOT_TOKEN')
    info = await bot.get_webhook_info()
    print(info)
asyncio.run(check())
"

# Manually set webhook
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
import asyncio
from telegram import Bot
async def set_webhook():
    bot = Bot('$TELEGRAM_BOT_TOKEN')
    await bot.set_webhook('$TELEGRAM_WEBHOOK_URL')
    print('Webhook set')
asyncio.run(set_webhook())
"

# Check HTTPS is working
curl -I https://yourdomain.com/webhook/telegram
```

### Issue: Out of Disk Space

**Solution:**
```bash
# Check disk usage
df -h

# Remove unused Docker images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove old logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --no-log-prefix | tail -n 1000 > recent.log
# Then manually clean log files
```

---

## Rollback Procedures

### Rollback to Previous Image

```bash
# List available images
docker images

# Stop containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Edit docker-compose.prod.yml to use previous image tag
nano docker-compose.prod.yml
# Change IMAGE_TAG to previous version

# Start containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Rollback Database Migration

```bash
# List migrations
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py showmigrations

# Rollback to specific migration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate core 0001_initial

# Restart web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

---

## Security Best Practices

1. **Never commit .env file** - it contains secrets
2. **Use strong passwords** - generate with: `openssl rand -base64 32`
3. **Keep system updated** - `apt update && apt upgrade`
4. **Limit SSH access** - use SSH keys, disable password auth
5. **Enable firewall** - only allow necessary ports
6. **Regular backups** - automate database backups
7. **Monitor logs** - check for suspicious activity
8. **Rotate secrets** - periodically change passwords and keys

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## Support

If you encounter issues not covered in this guide:

1. Check application logs
2. Review GitHub Actions workflow logs
3. Search for similar issues in the repository
4. Create a new issue with:
   - Detailed description
   - Error messages
   - Logs (redact sensitive info)
   - Steps to reproduce

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
