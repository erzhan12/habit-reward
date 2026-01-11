# Deployment Directory Structure

All deployment-related files have been organized into the `/deployment` directory for better project organization.

## New Structure

```
habit_reward/
├── deployment/                          # All deployment files
│   ├── docker/                          # Docker configuration
│   │   ├── Dockerfile                   # Application container
│   │   ├── .dockerignore                # Build exclusions
│   │   ├── docker-compose.yml           # Caddy + app (production)
│   │   └── .env.production              # Example production env file
│   │
│   ├── caddy/                           # Reverse proxy (recommended)
│   │   └── Caddyfile                    # Automatic HTTPS + proxy rules
│   │
│   ├── scripts/                         # Deployment scripts
│   │   ├── entrypoint.sh                # Container startup
│   │   ├── deploy-caddy.sh              # Manual server deployment
│   │   └── local-test.sh                # Local testing
│   │
│   └── README.md                        # Deployment docs
│
├── .github/
│   └── workflows/
│       └── deploy-caddy.yml             # CI/CD (Caddy + SQLite)
│
├── docs/
│   ├── DEPLOYMENT.md                    # Complete guide
│   ├── QUICK_START.md                   # Quick setup
│   ├── DEPLOYMENT_QUICK_REFERENCE.md    # Command reference
│   └── WEBHOOK_QUICK_START.md           # Webhook guide
│
├── .env.example                         # Environment template
├── DEPLOYMENT_CHECKLIST.md              # Verification checklist
├── DEPLOYMENT_SUMMARY.md                # Architecture overview
└── DEPLOYMENT_STRUCTURE.md              # This file
```

## What Changed

### Files Moved

1. **Docker files** → `/deployment/docker/`
   - `Dockerfile` → `/deployment/docker/Dockerfile`
   - `.dockerignore` → `/deployment/docker/.dockerignore`
   - `docker-compose.yml` → `/deployment/docker/docker-compose.yml`

2. **Caddy files** → `/deployment/caddy/`
   - `Caddyfile` → `/deployment/caddy/Caddyfile`

3. **Scripts** → `/deployment/scripts/`
   - `entrypoint.sh` → `/deployment/scripts/entrypoint.sh`
   - `deploy-caddy.sh` → `/deployment/scripts/deploy-caddy.sh`
   - `local-test.sh` → `/deployment/scripts/local-test.sh`

### Files Updated

1. **`/deployment/docker/Dockerfile`**
   - Updated entrypoint path: `deployment/scripts/entrypoint.sh`

2. **`/deployment/docker/docker-compose.yml`**
   - Updated build context: `../../` (project root)
   - Updated Dockerfile path: `deployment/docker/Dockerfile`
   - Uses Caddy for HTTPS
   - Persists SQLite DB at `/app/data/db.sqlite3`

3. **`/.github/workflows/deploy-caddy.yml`**
   - Updated Dockerfile path: `./deployment/docker/Dockerfile`
   - Copies `deployment/` to the server
   - Deploys via `docker/docker-compose.yml`
   - Updated docker-compose paths in verification

4. **`/deployment/scripts/deploy-caddy.sh`**
   - Pulls the `web` image and restarts `web` + `caddy`

5. **`/deployment/scripts/local-test.sh`**
   - Added `cd "$(dirname "$0")/../docker"` to change to docker directory
   - Updated docker-compose commands to use explicit file path

### Files Created

1. **`/deployment/README.md`**
   - Complete guide to deployment directory
   - File descriptions
   - Common commands
   - Troubleshooting

2. **`/DEPLOYMENT_STRUCTURE.md`** (this file)
   - Documents the new structure
   - Migration notes

## Quick Commands (Updated)

### Local Testing

```bash
# From project root
./deployment/scripts/local-test.sh

# OR manually from deployment/docker directory
cd deployment/docker
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### Production Deployment

**VPS Setup:**
```bash
# On your VPS, the structure will be:
/home/deploy/habit_reward_bot/
├── docker/
│   ├── docker-compose.yml
│   ├── data/                # SQLite database lives here
│   └── staticfiles/         # Collected static assets
├── caddy/
│   └── Caddyfile
├── scripts/
│   └── deploy-caddy.sh
└── .env

# Run deployment
cd /home/deploy/habit_reward_bot
./scripts/deploy-caddy.sh
```

**GitHub Actions:**
```bash
# Just push to main - GitHub Actions handles the rest
git push origin main
```

### Common Docker Commands

```bash
# Navigate to docker directory first
cd deployment/docker

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Django management
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Benefits of New Structure

### 1. **Better Organization**
- All deployment files in one place
- Easier to find and maintain
- Clear separation of concerns

### 2. **Cleaner Project Root**
- Less clutter in root directory
- Easier to navigate codebase
- Professional project structure

### 3. **Easier Deployment**
- Single directory to copy to VPS
- `scp -r deployment/*` copies everything
- Self-contained deployment configuration

### 4. **Better Documentation**
- `/deployment/README.md` for deployment-specific docs
- Main `/README.md` stays focused on application
- Easy reference for deployment team

### 5. **Scalability**
- Easy to add more deployment configurations
- Can add staging, development variants
- Environment-specific configs organized

## Migration Notes

### For Existing Deployments

If you have an existing deployment, re-copy the `deployment/` directory and re-run `./scripts/deploy-caddy.sh`.

3. **Or simpler - re-copy everything:**
   ```bash
   # GitHub Actions will copy the new structure automatically
   # Just trigger a new deployment
   git push origin main
   ```

### For New Deployments

Just follow the normal deployment process - all paths are already correct!

## Compatibility

### GitHub Actions
✅ **Fully compatible** - workflow updated to use new paths

### Docker Compose
✅ **Fully compatible** - build context and paths updated

### Scripts
✅ **Fully compatible** - all scripts updated

### Documentation
✅ **Fully compatible** - notes added to reference new structure

## Need Help?

See these guides:
- `/deployment/README.md` - Deployment directory guide
- `/docs/DEPLOYMENT.md` - Complete deployment guide
- `/docs/QUICK_START.md` - Quick setup (30 min)
- `/docs/DEPLOYMENT_QUICK_REFERENCE.md` - Command reference

---

**Structure Version:** 2.0.0
**Last Updated:** 2025-11-08
**Status:** ✅ Fully Migrated
