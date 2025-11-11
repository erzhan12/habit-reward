# Deployment Files

This directory contains all deployment-related configuration and scripts for the Habit Reward Bot.

## Directory Structure

```
deployment/
├── docker/                      # Docker configuration
│   ├── Dockerfile               # Main application container definition
│   ├── .dockerignore            # Build exclusions
│   ├── docker-compose.yml       # Development & base configuration
│   └── docker-compose.prod.yml  # Production overrides
│
├── nginx/                       # Reverse proxy configuration
│   ├── Dockerfile               # Nginx container definition
│   ├── nginx.conf               # Main nginx configuration
│   └── conf.d/
│       └── habit_reward.conf    # Site-specific configuration
│
├── scripts/                     # Deployment scripts
│   ├── entrypoint.sh            # Container startup script
│   ├── deploy.sh                # Server deployment automation
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
./scripts/deploy.sh
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
- Defines 4 services:
  - `db` - PostgreSQL 16 database
  - `web` - Django application + Telegram bot
  - `nginx` - Reverse proxy with SSL
  - `certbot` - SSL certificate management
- Configured volumes for data persistence
- Health checks for all services
- Network isolation

#### `docker/docker-compose.prod.yml`
- Production-specific overrides
- Uses pre-built images from GitHub Container Registry
- Resource limits (CPU/memory)
- Security hardening
- Database optimization

### Nginx Configuration

#### `nginx/nginx.conf`
- Performance optimizations (gzip, caching)
- Security headers
- Worker process configuration

#### `nginx/conf.d/habit_reward.conf`
- HTTP to HTTPS redirect
- SSL/TLS configuration
- Static file serving
- Webhook endpoint proxying
- Admin panel proxying

### Scripts

#### `scripts/entrypoint.sh`
Container startup script that:
- Waits for PostgreSQL to be ready
- Runs database migrations
- Collects static files
- Creates Django superuser (if configured)
- Sets Telegram webhook

#### `scripts/deploy.sh`
Server-side deployment script that:
- Pulls latest Docker images
- Performs zero-downtime deployment
- Validates deployment
- Checks webhook status
- Provides deployment status

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

# Start services (production)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

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

# Database shell
docker-compose exec db psql -U postgres habit_reward

# Backup database
docker-compose exec db pg_dump -U postgres habit_reward > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres habit_reward < backup.sql

# Check database size
docker-compose exec db psql -U postgres -d habit_reward -c "SELECT pg_size_pretty(pg_database_size('habit_reward'));"
```

## Environment Variables

All environment variables should be defined in a `.env` file in the deployment directory on the server.

See `/Users/erzhan/Data/PROJ/habit_reward/.env.example` for a complete list of required and optional variables.

**Required:**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL`

**Optional:**
- `DJANGO_SUPERUSER_*` (username, email, password)
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`
- `LOG_LEVEL`, `SUPPORTED_LANGUAGES`

## Ports

| Service | Port | Exposed | Description |
|---------|------|---------|-------------|
| Nginx | 80 | Yes | HTTP (redirects to HTTPS) |
| Nginx | 443 | Yes | HTTPS |
| Web | 8000 | No | Django app (internal) |
| PostgreSQL | 5432 | No | Database (internal) |

## Volumes

- `postgres_data` - PostgreSQL database persistence
- `bot_data` - Telegram bot conversation state
- `static_files` - Django static files
- `certbot_data` - SSL certificates
- `certbot_www` - Let's Encrypt challenge files

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
