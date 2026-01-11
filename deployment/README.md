# Deployment Files

This directory contains all deployment-related configuration and scripts for the Habit Reward Bot.

## Directory Structure

```
deployment/
├── docker/                      # Docker configuration
│   ├── Dockerfile               # Main application container definition
│   ├── .dockerignore            # Build exclusions
│   ├── docker-compose.yml       # Production (web + caddy)
│   └── .env.production          # Example production environment file
│
├── caddy/                       # Reverse proxy (recommended)
│   └── Caddyfile                # Automatic HTTPS + proxy rules
│
├── scripts/                     # Deployment scripts
│   ├── entrypoint.sh            # Container startup script
│   ├── deploy-caddy.sh          # Manual deployment helper
│   └── local-test.sh            # Local testing helper
│
└── README.md                    # This file
```

## Quick Start

### Local Testing

```bash
# From project root
./deployment/scripts/local-test.sh

# Access admin panel
open http://localhost:8000/admin/
```

### Production Deployment

**Automated (via GitHub Actions):**
```bash
git push origin main  # Deployment happens automatically
```

**Manual (on VPS):**
```bash
cd /home/deploy/habit_reward_bot
./scripts/deploy-caddy.sh
```

## Files Overview

### Docker Configuration

#### `docker/Dockerfile`
- Multi-stage build for optimized image size
- Python 3.13 base image
- Non-root user for security
- Health checks configured
- Installs dependencies using `uv`

#### `docker/docker-compose.yml`
- Defines 2 services:
  - `web` - Django application + Telegram bot
  - `caddy` - Reverse proxy + automatic HTTPS
- Uses SQLite in production via `DATABASE_URL=sqlite:////app/data/db.sqlite3`
- Persists data via bind mounts:
  - `./data:/app/data` (SQLite DB)
  - `./staticfiles:/app/staticfiles` (static assets)
- Network isolation

#### `caddy/Caddyfile`
- HTTPS termination + proxy to `web`
- Serves static files from `/app/staticfiles`
- Manages certificates automatically

### Scripts

#### `scripts/entrypoint.sh`
Container startup script that:
- Runs database migrations
- Collects static files
- Creates Django superuser (if configured)
- Sets Telegram webhook

#### `scripts/deploy-caddy.sh`
Manual deployment script (fallback if GitHub Actions deployment fails) that:
- Pulls the latest app image
- Restarts the Compose stack

#### `scripts/local-test.sh`
Local testing helper that:
- Validates configuration
- Builds and starts containers
- Shows access points and useful commands

## Common Commands

### From Deployment Directory

```bash
cd deployment/docker

# Start services (development)
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Check status
docker-compose ps
```

### Django Management

```bash
cd deployment/docker

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Django shell
docker-compose exec web python manage.py shell

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Database Operations

```bash
cd deployment/docker

# Backup database (SQLite)
cp ./data/db.sqlite3 ./data/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Restore database (SQLite)
cp ./data/db.sqlite3.backup_YYYYMMDD_HHMMSS ./data/db.sqlite3
```

## Environment Variables

All environment variables should be defined in a `.env` file. The location depends on how you're running Docker Compose:

- **Production (on server):** `.env` file in the deployment directory (e.g., `/home/deploy/habit_reward_bot/.env`)
- **Local testing:** `.env` file in the project root (created automatically by `local-test.sh`)

**Note:** Docker Compose automatically loads `.env` files from the current directory. If you see warnings about missing variables, ensure:
1. The `.env` file exists in the correct location
2. You're running docker-compose from the directory containing the `.env` file, OR
3. Use `--env-file` flag to specify the `.env` file path

**Required variables:**
- `SECRET_KEY` (generate with: `python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DATABASE_URL` (production default: `sqlite:////app/data/db.sqlite3`)
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL`

**Optional variables:**
- `DJANGO_SUPERUSER_*` (username, email, password)
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`
- `LOG_LEVEL`, `SUPPORTED_LANGUAGES`

**Creating .env file:**
```bash
# On server (production)
cd /home/deploy/habit_reward_bot
# GitHub Actions creates this automatically, or create manually:
nano .env

# Locally (for testing)
cd /path/to/habit_reward
./deployment/scripts/local-test.sh  # Creates .env automatically
```

## Ports

| Service | Port | Exposed | Description |
|---------|------|---------|-------------|
| Caddy | 80 | Yes | HTTP (redirects to HTTPS) |
| Caddy | 443 | Yes | HTTPS |
| Web | 8000 | No | Django app (internal) |

## Volumes

- `./data` - SQLite database persistence (`db.sqlite3`)
- `./staticfiles` - Django static files
- `caddy_data` - Caddy-managed data (certificates)
- `caddy_config` - Caddy config state
- `caddy_logs` - Reverse proxy logs

## Documentation

For detailed deployment instructions, see:
- `/docs/DEPLOYMENT.md` - Complete deployment guide
- `/docs/QUICK_START.md` - 30-minute quick start
- `/DEPLOYMENT_CHECKLIST.md` - Verification checklist
- `/DEPLOYMENT_SUMMARY.md` - Architecture overview
- `/docs/DEPLOYMENT_QUICK_REFERENCE.md` - Command reference

## Troubleshooting

### Containers won't start
```bash
# Check logs
docker-compose logs

# Validate configuration
docker-compose config

# Check .env file
cat .env
```

### 502 Bad Gateway
```bash
# Check if web container is running
docker-compose ps web

# Check web logs
docker-compose logs web

# Restart web
docker-compose restart web
```

### Database connection error
```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

## Security Notes

- **Never commit `.env` files** - they contain secrets
- **Use strong passwords** - generate with `openssl rand -base64 32`
- **Keep system updated** - `apt update && apt upgrade`
- **Limit SSH access** - use SSH keys only
- **Enable firewall** - only allow necessary ports (22, 80, 443)
- **Monitor logs** - check for suspicious activity regularly

## Support

For issues or questions:
1. Check the troubleshooting section in `/docs/DEPLOYMENT.md`
2. Review container logs
3. Verify environment variables
4. Check GitHub Actions logs (for CI/CD issues)

---

**Last Updated:** 2025-11-08
**Version:** 1.0.0
