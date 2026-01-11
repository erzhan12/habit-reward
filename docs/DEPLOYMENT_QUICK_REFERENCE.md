# Deployment Quick Reference

## File Structure

```
habit_reward/
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml      # Production (web + caddy)
│   │   └── .env.production         # Example production env file
│   ├── caddy/
│   │   └── Caddyfile               # Reverse proxy + automatic HTTPS
│   └── scripts/
│       ├── entrypoint.sh
│       ├── deploy-caddy.sh
│       └── local-test.sh
│
├── .github/workflows/deploy-caddy.yml
├── .env.example
└── docs/
    ├── DEPLOYMENT.md
    ├── DEPLOYMENT_STEP_BY_STEP.md
    ├── DEPLOYMENT_CHECKLIST_SIMPLE.md
    └── DEPLOYMENT_VISUAL_GUIDE.md
```

## Quick Commands

### Local Development
```bash
# Test locally
./deployment/scripts/local-test.sh

# Or manually
cd deployment/docker
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### Production Deployment
```bash
# Automated (push to GitHub)
git push origin main

# Manual (on VPS)
cd /home/deploy/habit_reward_bot
./scripts/deploy-caddy.sh
```

### Container Management
```bash
# Run from the deployment directory on the VPS
alias dc='docker-compose --env-file .env -f docker/docker-compose.yml'

# View status
dc ps

# View logs
dc logs -f

# Restart
dc restart

# Stop
dc down

# Start
dc up -d
```

### Database Operations
```bash
# SQLite database is a file persisted at: docker/data/db.sqlite3

# Backup (on VPS)
cp docker/data/db.sqlite3 docker/data/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Restore (on VPS)
cp docker/data/db.sqlite3.backup_YYYYMMDD_HHMMSS docker/data/db.sqlite3
```

### Django Management
```bash
# Migrations
dc exec web python manage.py migrate

# Create superuser
dc exec web python manage.py createsuperuser

# Django shell
dc exec web python manage.py shell

# Collect static files
dc exec web python manage.py collectstatic --noinput
```

### Telegram Bot
```bash
# Check webhook
dc exec web python -c "
import asyncio
from telegram import Bot
async def check():
    bot = Bot('YOUR_TOKEN')
    info = await bot.get_webhook_info()
    print(f'URL: {info.url}')
    print(f'Pending: {info.pending_update_count}')
asyncio.run(check())
"

# Set webhook manually
dc exec web python -c "
import asyncio
from telegram import Bot
async def set_webhook():
    bot = Bot('YOUR_TOKEN')
    await bot.set_webhook('YOUR_WEBHOOK_URL')
    print('Webhook set')
asyncio.run(set_webhook())
"

# Delete webhook (for testing)
dc exec web python -c "
import asyncio
from telegram import Bot
async def delete():
    bot = Bot('YOUR_TOKEN')
    await bot.delete_webhook()
    print('Webhook deleted')
asyncio.run(delete())
"
```

### SSL Certificate
```bash
# Automatic: Caddy provisions and renews certificates.
# To debug HTTPS issues:
dc logs -f caddy
```

### Monitoring
```bash
# Container stats
docker stats

# Disk usage
df -h
docker system df

# Clean up
docker image prune -f
docker volume prune -f
docker system prune -f
```

## Environment Variables Reference

### Required
```bash
SECRET_KEY=<django-secret-key>
DATABASE_URL=sqlite:////app/data/db.sqlite3
ALLOWED_HOSTS=yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram
```

### Optional
```bash
DEBUG=False
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=<password>
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=<api-key>
LOG_LEVEL=INFO
SUPPORTED_LANGUAGES=en,ru,kk
```

## GitHub Secrets Reference

Add these to: **Settings → Secrets and variables → Actions**

| Secret Name | Example Value |
|-------------|---------------|
| `DJANGO_SECRET_KEY` | `django-secret-key-50-chars` |
| `ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://yourdomain.com` |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABC...` |
| `TELEGRAM_WEBHOOK_URL` | `https://yourdomain.com/webhook/telegram` |
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_EMAIL` | `admin@yourdomain.com` |
| `DJANGO_SUPERUSER_PASSWORD` | `admin_password_here` |
| `SERVER_HOST` | `123.45.67.89` |
| `SSH_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_PATH` | `/home/deploy/habit_reward_bot` |
| `LLM_PROVIDER` | `openai` (optional) |
| `LLM_MODEL` | `gpt-3.5-turbo` (optional) |
| `LLM_API_KEY` | `sk-...` (optional) |

## Port Reference

| Service | Port | Exposed | Description |
|---------|------|---------|-------------|
| Caddy | 80 | Yes | HTTP (redirects to HTTPS) |
| Caddy | 443 | Yes | HTTPS |
| Web | 8000 | No | Django app (internal) |

## Troubleshooting Quick Fixes

### Container won't start
```bash
dc logs <service_name>
dc restart <service_name>
dc config  # Validate configuration
```

### 502 Bad Gateway
```bash
dc logs caddy
dc logs web
dc restart web
```

### Database connection error
```bash
grep DATABASE_URL .env
ls -la docker/data/db.sqlite3
dc restart web
```

### Webhook not working
```bash
# Check HTTPS is working
curl -I https://yourdomain.com/webhook/telegram

# Check reverse proxy logs
dc logs caddy

# Restart web
dc restart web
```

### Out of disk space
```bash
df -h
docker system df
docker system prune -f
docker volume prune -f  # CAREFUL: removes unused volumes
```

## Rollback Procedure

```bash
# 1. Stop current containers
dc down

# 2. Change image tag in .env
nano .env
# Change IMAGE_TAG=latest to IMAGE_TAG=<previous-version-or-sha-tag>

# 3. Pull and start
dc pull web
dc up -d

# 4. Verify
dc ps
dc logs -f
```

## Health Check URLs

| Check | URL | Expected |
|-------|-----|----------|
| Admin | `https://yourdomain.com/admin/` | Login page |
| Webhook | `https://yourdomain.com/webhook/telegram` | 405 Method Not Allowed (GET) |
| SSL | `https://yourdomain.com` | Valid certificate |

## One-Line Deployment

```bash
# Complete deployment in one command
git add . && git commit -m "deploy: update" && git push origin main
```

## Emergency Contacts

- **Logs Location**: `/var/lib/docker/volumes/`
- **Backup Location**: Define in your backup script
- **SSL Certs**: `/etc/letsencrypt/live/yourdomain.com/`

---

**Need Help?**
- Full Guide: `docs/DEPLOYMENT.md`
- Quick Start: `docs/QUICK_START.md`
- Checklist: `DEPLOYMENT_CHECKLIST.md`
