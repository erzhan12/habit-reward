# Deployment Directory Structure

All deployment-related files have been organized into the `/deployment` directory for better project organization.

## New Structure

```
habit_reward/
├── deployment/                          # All deployment files
│   ├── docker/                          # Docker configuration
│   │   ├── Dockerfile                   # Application container
│   │   ├── .dockerignore                # Build exclusions
│   │   ├── docker-compose.yml           # Base configuration
│   │   └── docker-compose.prod.yml      # Production overrides
│   │
│   ├── nginx/                           # Reverse proxy
│   │   ├── Dockerfile                   # Nginx container
│   │   ├── nginx.conf                   # Main config
│   │   └── conf.d/
│   │       └── habit_reward.conf        # Site config
│   │
│   ├── scripts/                         # Deployment scripts
│   │   ├── entrypoint.sh                # Container startup
│   │   ├── deploy.sh                    # Server deployment
│   │   └── local-test.sh                # Local testing
│   │
│   └── README.md                        # Deployment docs
│
├── .github/
│   └── workflows/
│       └── deploy.yml                   # CI/CD (updated paths)
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
   - `docker-compose.prod.yml` → `/deployment/docker/docker-compose.prod.yml`

2. **Nginx files** → `/deployment/nginx/`
   - `nginx/*` → `/deployment/nginx/*`

3. **Scripts** → `/deployment/scripts/`
   - `entrypoint.sh` → `/deployment/scripts/entrypoint.sh`
   - `deploy.sh` → `/deployment/scripts/deploy.sh`
   - `local-test.sh` → `/deployment/scripts/local-test.sh`

### Files Updated

1. **`/deployment/docker/Dockerfile`**
   - Updated entrypoint path: `deployment/scripts/entrypoint.sh`

2. **`/deployment/docker/docker-compose.yml`**
   - Updated build context: `../../` (project root)
   - Updated Dockerfile path: `deployment/docker/Dockerfile`
   - Updated nginx context: `../nginx`
   - Updated nginx volume paths: `../nginx/`

3. **`/.github/workflows/deploy.yml`**
   - Updated Dockerfile path: `./deployment/docker/Dockerfile`
   - Updated SCP command: `scp -r deployment/*`
   - Updated deploy script: `./scripts/deploy.sh`
   - Updated docker-compose paths in verification

4. **`/deployment/scripts/deploy.sh`**
   - Updated all docker-compose commands: `-f docker/docker-compose.yml -f docker/docker-compose.prod.yml`

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
│   └── docker-compose.prod.yml
├── nginx/
│   ├── nginx.conf
│   └── conf.d/habit_reward.conf
├── scripts/
│   └── deploy.sh
└── .env

# Run deployment
cd /home/deploy/habit_reward_bot
./scripts/deploy.sh
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

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Django management
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Database
docker-compose exec db psql -U postgres habit_reward
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

If you have already deployed with the old structure:

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **On VPS, reorganize files:**
   ```bash
   cd /home/deploy/habit_reward_bot

   # Create new structure
   mkdir -p docker nginx scripts

   # Move files
   mv docker-compose.yml docker/
   mv docker-compose.prod.yml docker/
   mv Dockerfile docker/
   mv .dockerignore docker/
   mv nginx/* nginx/  # if nginx dir exists
   mv deploy.sh scripts/
   mv entrypoint.sh scripts/

   # Update docker-compose commands in deploy.sh
   # (or re-copy from repository)
   ```

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
