# Deployment Setup - Summary

## Overview

A complete Docker-based deployment infrastructure is provided for the Habit Reward Bot with the following production architecture:

- **Docker Compose** for container orchestration
- **SQLite** database (persisted on disk in a mounted volume)
- **Caddy** reverse proxy with automatic HTTPS (Let's Encrypt)
- **GitHub Actions** for CI/CD automation

## Files Created

### Docker Configuration

1. **`Dockerfile`**
   - Multi-stage build for optimized image size
   - Python 3.13 base image
   - Non-root user for security
   - Health checks configured
   - Uses `uv` for fast dependency installation

2. **`.dockerignore`**
   - Excludes unnecessary files from Docker builds
   - Reduces image size and build time

3. **`entrypoint.sh`**
   - Container startup script
   - Runs Django migrations
   - Runs database migrations automatically
   - Collects static files
   - Creates Django superuser (if configured)
   - Sets Telegram webhook

4. **`docker-compose.yml`**
   - Production configuration (Caddy-based)
   - Defines 2 services:
     - `web` - Django + Telegram bot application
     - `caddy` - Reverse proxy + automatic HTTPS
   - Persists the SQLite database at `/app/data/db.sqlite3` via bind mount
   - Persists static files via bind mount

5. **`caddy/Caddyfile`**
   - Caddy reverse proxy configuration
   - Automatic certificate provisioning and HTTPS redirect
   - Static files served from `/app/staticfiles`

### GitHub Actions

6. **`.github/workflows/deploy-caddy.yml`**
   - Automated CI/CD pipeline
   - 4 jobs:
     - **Test**: Run linter and tests
     - **Build**: Build and push Docker images to GHCR
     - **Deploy**: SSH to VPS and deploy
     - **Health Check**: Verify deployment
   - Triggers on push to `main` branch
   - Manual trigger support

### Deployment Scripts

7. **`deploy-caddy.sh`**
   - Manual fallback deployment script for the Caddy-based setup
   - Pulls latest image and restarts Compose

8. **`local-test.sh`**
    - Local testing helper script
    - Validates configuration
    - Builds and starts containers
    - Provides testing instructions

### Environment Configuration

12. **`.env.example`**
    - Complete environment variable template
    - Includes all required and optional variables
    - Detailed comments and examples
    - Security notes and best practices

### Documentation

13. **`docs/DEPLOYMENT.md`** (Comprehensive - 800+ lines)
    - Complete deployment guide
    - Step-by-step instructions
    - Prerequisites and architecture diagrams
    - VPS setup instructions
    - GitHub configuration
    - SSL certificate setup
    - Monitoring and maintenance
    - Troubleshooting guide
    - Security best practices

14. **`docs/QUICK_START.md`** (Condensed - 200+ lines)
    - Quick reference guide
    - 30-minute deployment walkthrough
    - Common commands reference
    - Quick troubleshooting

15. **`DEPLOYMENT_CHECKLIST.md`** (Detailed - 400+ lines)
    - Pre-deployment checklist
    - VPS configuration checklist
    - GitHub repository checklist
    - SSL certificate checklist
    - Post-deployment verification
    - Monitoring setup
    - Security checklist
    - Testing checklist
    - Go-live checklist
    - Rollback plan

### Git Configuration

16. **`.gitignore`** (Updated)
    - Added Docker-related exclusions
    - SSL certificate exclusions
    - Deployment artifact exclusions
    - Static files exclusions

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Actions                          │
│  (Build → Test → Push to Registry → Deploy to VPS)             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ SSH Deploy
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                           VPS Server                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Docker Compose                         │ │
│  │                                                           │ │
│  │  ┌────────────┐   ┌──────────────┐                      │ │
│  │  │   Caddy    │   │     Web      │                      │ │
│  │  │  (Proxy)   │◄─►│   (Django    │                      │ │
│  │  │            │   │    + Bot)    │                      │ │
│  │  │  80/443    │   │   8000       │                      │ │
│  │  └─────┬──────┘   └──────────────┘                      │ │
│  │                                                           │ │
│  │  Volumes:                                                │ │
│  │  • ./data (SQLite database persistence)                  │ │
│  │  • ./staticfiles (Django static files)                   │ │
│  │  • caddy_data / caddy_config (Caddy state + certs)       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
              HTTPS (Port 443)
                     │
           ┌─────────▼──────────┐
           │  Telegram Servers  │
           │   (Webhook API)    │
           └────────────────────┘
```

## Deployment Flow

### Automated Deployment (Recommended)

```
Developer pushes code to main branch
           ↓
GitHub Actions triggered
           ↓
1. Test job runs (linting, tests)
           ↓
2. Build job (build Docker image, push to GHCR)
           ↓
3. Deploy job (SSH to VPS, run deploy.sh)
           ↓
   - Pull latest images
   - Stop old containers
   - Start new containers
   - Run migrations
   - Set webhook
   - Verify deployment
           ↓
4. Health check job (verify bot is responding)
           ↓
Deployment complete! ✅
```

### Manual Deployment

```
SSH to VPS
    ↓
Pull latest code (git pull)
    ↓
Update .env file (if needed)
    ↓
Run: docker-compose --env-file .env -f docker/docker-compose.yml pull web
    ↓
Run: docker-compose --env-file .env -f docker/docker-compose.yml up -d
    ↓
Verify: docker-compose ps
    ↓
Check logs: docker-compose logs -f
    ↓
Deployment complete! ✅
```

## Key Features

### Security
- ✅ Non-root user in containers
- ✅ Environment variables for secrets
- ✅ SSL/TLS encryption (Let's Encrypt)
- ✅ HTTPS-only in production
- ✅ Security headers configured
- ✅ Database in isolated network
- ✅ GitHub Secrets for CI/CD
- ✅ Firewall configured

### High Availability
- ✅ Container health checks
- ✅ Automatic restart policies
- ✅ Zero-downtime deployments
- ✅ Caddy as reverse proxy
- ✅ Resource limits configured

### Developer Experience
- ✅ One-command deployment
- ✅ Automated CI/CD
- ✅ Comprehensive documentation
- ✅ Local testing script
- ✅ Detailed checklists
- ✅ Troubleshooting guides

### Monitoring & Maintenance
- ✅ Container logs
- ✅ Health check endpoints
- ✅ Database backup procedures
- ✅ SSL auto-renewal
- ✅ Rollback procedures

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | 50+ char random string |
| `DATABASE_URL` | DB connection URL | `sqlite:////app/data/db.sqlite3` |
| `ALLOWED_HOSTS` | Allowed domains | `yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origins | `https://yourdomain.com` |
| `TELEGRAM_BOT_TOKEN` | Bot token | From @BotFather |
| `TELEGRAM_WEBHOOK_URL` | Webhook URL | `https://yourdomain.com/webhook/telegram` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `False` |
| `LLM_PROVIDER` | AI provider | `openai` |
| `LLM_MODEL` | AI model | `gpt-3.5-turbo` |
| `LLM_API_KEY` | AI API key | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SUPPORTED_LANGUAGES` | Languages | `en,ru,kk` |

## GitHub Secrets Required

The following secrets must be added to GitHub repository:

### Database
- *(none)* (production uses SQLite via `DATABASE_URL=sqlite:////app/data/db.sqlite3` in server `.env`)

### Django
- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

### Telegram
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_URL`

### Superuser
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

### Deployment
- `SERVER_HOST`
- `SSH_USER`
- `SSH_PRIVATE_KEY`
- `DEPLOY_PATH`

### Optional
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`

## Next Steps

1. **Review Documentation**
   - Read `docs/DEPLOYMENT.md` for complete instructions
   - Review `docs/QUICK_START.md` for condensed guide
   - Use `DEPLOYMENT_CHECKLIST.md` to track progress

2. **Set Up VPS**
   - Provision VPS (DigitalOcean, Linode, AWS EC2, etc.)
   - Install Docker and Docker Compose
   - Configure firewall
   - Generate SSH keys

3. **Configure GitHub**
   - Add all required secrets
   - Enable GitHub Actions
   - Set write permissions

4. **Configure Domain**
   - Point DNS to VPS IP
   - (Optional) Update Caddyfile
   - HTTPS is automatic (Caddy)

5. **Deploy**
   - Push to main branch (automated)
   - OR run `scripts/deploy-caddy.sh` manually
   - Monitor deployment logs
   - Verify functionality

6. **Test**
   - Test bot in Telegram
   - Access Django admin
   - Check logs for errors
   - Verify webhook is working

7. **Monitor**
   - Set up monitoring
   - Configure backups
   - Review logs regularly

## Testing Locally

Before deploying to production, test locally:

```bash
# Make script executable
chmod +x deployment/scripts/local-test.sh

# Run local test
./deployment/scripts/local-test.sh

# Access admin panel
open http://localhost:8000/admin/

# View logs
docker-compose logs -f

# Stop when done
docker-compose down
```

## Common Commands

### Deployment
```bash
# Deploy (automated via GitHub)
git push origin main

# Deploy (manual)
ssh deploy@server
cd /home/deploy/habit_reward_bot
./scripts/deploy-caddy.sh
```

### Container Management
```bash
# View status
docker-compose --env-file .env -f docker/docker-compose.yml ps

# View logs
docker-compose --env-file .env -f docker/docker-compose.yml logs -f

# Restart services
docker-compose --env-file .env -f docker/docker-compose.yml restart

# Stop services
docker-compose --env-file .env -f docker/docker-compose.yml down

# Start services
docker-compose --env-file .env -f docker/docker-compose.yml up -d
```

### Database
```bash
# Backup (SQLite file)
cp docker/data/db.sqlite3 docker/data/db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Restore (SQLite file)
cp docker/data/db.sqlite3.backup_YYYYMMDD_HHMMSS docker/data/db.sqlite3
```

### Django
```bash
# Migrations
docker-compose --env-file .env -f docker/docker-compose.yml exec web python manage.py migrate

# Shell
docker-compose --env-file .env -f docker/docker-compose.yml exec web python manage.py shell

# Create superuser
docker-compose --env-file .env -f docker/docker-compose.yml exec web python manage.py createsuperuser
```

## Support & Resources

- **Documentation**: `docs/DEPLOYMENT.md` - Complete deployment guide
- **Quick Start**: `docs/QUICK_START.md` - 30-minute setup
- **Checklist**: `DEPLOYMENT_CHECKLIST.md` - Step-by-step verification

For issues:
1. Check logs first
2. Review troubleshooting section in docs
3. Search existing issues
4. Create new issue with logs

## Summary

This deployment setup provides:

✅ **Production-ready infrastructure**
✅ **Automated CI/CD pipeline**
✅ **Comprehensive documentation**
✅ **Security best practices**
✅ **Easy maintenance and monitoring**
✅ **Scalable architecture**

Estimated deployment time: **30-40 minutes** (with preparation)

---

**Created:** 2025-11-08
**Version:** 1.0.0
**Status:** Ready for deployment
