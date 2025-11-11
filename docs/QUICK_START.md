# Habit Reward Bot - Quick Start Deployment Guide

This is a condensed version of the full deployment guide. For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Prerequisites Checklist

- [ ] VPS with Ubuntu 22.04+ (1 CPU, 2GB RAM minimum)
- [ ] Domain name pointed to VPS IP
- [ ] Telegram bot token from @BotFather
- [ ] GitHub repository with code
- [ ] Email for SSL certificates

## 1. VPS Setup (5 minutes)

```bash
# Connect to VPS
ssh root@YOUR_VPS_IP

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create deploy user
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Generate SSH key for GitHub Actions
su - deploy
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions -N ""
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/github_actions  # Copy this to GitHub Secrets

# Create deployment directory
mkdir -p /home/deploy/habit_reward_bot
cd /home/deploy/habit_reward_bot
```

## 2. GitHub Repository Setup (10 minutes)

### Add Repository Secrets

Go to: **Settings → Secrets and variables → Actions → New repository secret**

**Required Secrets:**

```bash
# Database
POSTGRES_DB=habit_reward
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-random-password>

# Django (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_SECRET_KEY=<generated-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Telegram
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram

# Superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
DJANGO_SUPERUSER_PASSWORD=<strong-random-password>

# Deployment
SERVER_HOST=<your-vps-ip>
SSH_USER=deploy
SSH_PRIVATE_KEY=<paste-private-key-from-step-1>
DEPLOY_PATH=/home/deploy/habit_reward_bot
```

**Optional Secrets:**
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=<your-api-key>
```

### Enable GitHub Actions

1. **Settings → Actions → General**
2. Select "Allow all actions and reusable workflows"
3. Select "Read and write permissions"
4. Click Save

## 3. Initial Deployment (15 minutes)

### Option A: Automated Deployment (Recommended)

```bash
# On your local machine
git add .
git commit -m "feat: add deployment configuration"
git push origin main

# Monitor at: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

### Option B: Manual Deployment

```bash
# On VPS as deploy user
cd /home/deploy/habit_reward_bot

# Clone repository
git clone https://github.com/YOUR_USERNAME/habit_reward.git .

# Create .env file
cp .env.example .env
nano .env  # Fill in your values

# Update nginx config with your domain
nano nginx/conf.d/habit_reward.conf
# Replace 'example.com' with 'yourdomain.com'

# Start containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 4. SSL Certificate Setup (5 minutes)

```bash
# On VPS
cd /home/deploy/habit_reward_bot

# Stop nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx

# Obtain certificate
docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly \
  --standalone \
  --email admin@yourdomain.com \
  --agree-tos \
  -d yourdomain.com

# Start nginx
docker-compose -f docker-compose.yml -f docker-compose.prod.yml start nginx
```

## 5. Verification (2 minutes)

```bash
# Check containers are running
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f --tail=50

# Test bot in Telegram
# Send /start to your bot

# Access admin panel
# Open: https://yourdomain.com/admin/
```

## Common Commands

### View Logs
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Restart Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

### Stop Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Start Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Backup Database
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec db pg_dump -U postgres habit_reward > backup.sql
```

### Access Django Shell
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py shell
```

### Run Migrations
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

## Troubleshooting

### Bot Not Responding
```bash
# Check webhook
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
import asyncio
from telegram import Bot
async def check():
    bot = Bot('YOUR_TOKEN')
    info = await bot.get_webhook_info()
    print(info)
asyncio.run(check())
"

# Reset webhook
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### 502 Bad Gateway
```bash
# Check web container
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### Database Connection Error
```bash
# Check database
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs db
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart db
```

## Next Steps

After successful deployment:

1. **Test bot functionality** - Try all commands
2. **Monitor logs** - Watch for errors
3. **Set up monitoring** - Consider tools like Uptime Robot
4. **Configure backups** - Automate database backups
5. **Review security** - Ensure all secrets are set correctly

## Support

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

For issues:
- Check logs first
- Review GitHub Actions workflow
- Search existing issues
- Create new issue with logs

---

**Estimated Total Time:** 30-40 minutes
