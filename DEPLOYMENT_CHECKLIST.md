# Deployment Checklist

Use this checklist to ensure you complete all deployment steps correctly.

## Pre-Deployment Checklist

### Local Setup
- [ ] All code changes committed and pushed to GitHub
- [ ] All tests passing locally
- [ ] `.env.example` updated with all required variables
- [ ] Deployment documentation reviewed

### VPS/Server Setup
- [ ] VPS provisioned (1 CPU, 2GB RAM minimum)
- [ ] Ubuntu 22.04 LTS or similar installed
- [ ] Root/sudo access confirmed
- [ ] Static IP address assigned
- [ ] SSH access working

### Domain & DNS
- [ ] Domain registered
- [ ] DNS A record: `yourdomain.com` → VPS IP
- [ ] DNS A record: `www.yourdomain.com` → VPS IP (optional)
- [ ] DNS propagation completed (check with `dig yourdomain.com`)

### Telegram Bot
- [ ] Bot created via @BotFather
- [ ] Bot token obtained
- [ ] Bot username configured

### GitHub
- [ ] Repository created/exists
- [ ] GitHub Actions enabled
- [ ] Write permissions enabled for Actions

### Optional Services
- [ ] OpenAI/Anthropic API key obtained (if using AI features)

---

## VPS Configuration Checklist

### System Updates
- [ ] System packages updated: `apt update && apt upgrade -y`
- [ ] Reboot if kernel updated

### Docker Installation
- [ ] Docker installed and verified: `docker --version`
- [ ] Docker service running: `systemctl status docker`
- [ ] Docker Compose installed: `docker-compose --version`

### User Setup
- [ ] Deploy user created: `adduser deploy`
- [ ] User added to docker group: `usermod -aG docker deploy`
- [ ] User can run docker without sudo

### Firewall Configuration
- [ ] UFW installed
- [ ] Port 22 (SSH) allowed
- [ ] Port 80 (HTTP) allowed
- [ ] Port 443 (HTTPS) allowed
- [ ] UFW enabled and active
- [ ] Firewall status verified: `ufw status`

### SSH Keys
- [ ] SSH key pair generated for GitHub Actions
- [ ] Public key added to `~/.ssh/authorized_keys`
- [ ] Private key saved securely
- [ ] SSH access tested with new key

### Deployment Directory
- [ ] Directory created: `/home/deploy/habit_reward_bot`
- [ ] Proper ownership set: `chown deploy:deploy`
- [ ] Directory accessible

---

## GitHub Repository Checklist

### Secrets Configuration
All secrets added to: **Settings → Secrets and variables → Actions**

#### Database Secrets
- [ ] `POSTGRES_DB`
- [ ] `POSTGRES_USER`
- [ ] `POSTGRES_PASSWORD` (strong, random)

#### Django Secrets
- [ ] `DJANGO_SECRET_KEY` (generated, 50+ chars)
- [ ] `ALLOWED_HOSTS` (your domain)
- [ ] `CSRF_TRUSTED_ORIGINS` (https URLs)

#### Telegram Secrets
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `TELEGRAM_WEBHOOK_URL` (https://yourdomain.com/webhook/telegram)

#### Superuser Secrets
- [ ] `DJANGO_SUPERUSER_USERNAME`
- [ ] `DJANGO_SUPERUSER_EMAIL`
- [ ] `DJANGO_SUPERUSER_PASSWORD` (strong, random)

#### Deployment Secrets
- [ ] `SERVER_HOST` (VPS IP or domain)
- [ ] `SSH_USER` (usually 'deploy')
- [ ] `SSH_PRIVATE_KEY` (from VPS setup)
- [ ] `DEPLOY_PATH` (/home/deploy/habit_reward_bot)

#### Optional Secrets
- [ ] `LLM_PROVIDER` (if using AI)
- [ ] `LLM_MODEL` (if using AI)
- [ ] `LLM_API_KEY` (if using AI)

### GitHub Actions Configuration
- [ ] Actions enabled in repository settings
- [ ] Workflow permissions set to "Read and write"
- [ ] All actions and reusable workflows allowed

### Files Verified
- [ ] `Dockerfile` exists and is valid
- [ ] `docker-compose.yml` exists
- [ ] `docker-compose.prod.yml` exists
- [ ] `.dockerignore` exists
- [ ] `entrypoint.sh` exists and is executable
- [ ] `deploy.sh` exists and is executable
- [ ] `.env.example` exists and is complete
- [ ] `.github/workflows/deploy.yml` exists
- [ ] `nginx/Dockerfile` exists
- [ ] `nginx/nginx.conf` exists
- [ ] `nginx/conf.d/habit_reward.conf` exists
- [ ] Domain replaced in nginx config (not 'example.com')

---

## Initial Deployment Checklist

### Automated Deployment (via GitHub Actions)
- [ ] All changes committed: `git commit -am "feat: deployment setup"`
- [ ] Changes pushed to main: `git push origin main`
- [ ] GitHub Actions workflow triggered
- [ ] Workflow running (check Actions tab)
- [ ] Build job passed
- [ ] Test job passed (or skipped if no tests)
- [ ] Deploy job in progress
- [ ] No errors in workflow logs

### Manual Deployment (if not using GitHub Actions)
- [ ] Repository cloned to VPS
- [ ] `.env` file created from `.env.example`
- [ ] All environment variables filled in `.env`
- [ ] Nginx config updated with actual domain
- [ ] Docker images built
- [ ] Containers started

---

## SSL Certificate Checklist

### Let's Encrypt Setup
- [ ] Nginx container stopped temporarily
- [ ] Certbot container run successfully
- [ ] Certificate obtained for domain
- [ ] Certificate files exist in `/etc/letsencrypt/live/yourdomain.com/`
- [ ] Nginx config points to correct certificate paths
- [ ] Nginx container restarted
- [ ] HTTPS working (test: `curl -I https://yourdomain.com`)

### Certificate Auto-Renewal
- [ ] Certbot container running in background
- [ ] Auto-renewal configured (via docker-compose)
- [ ] Renewal tested: `docker-compose exec certbot certbot renew --dry-run`

---

## Post-Deployment Verification

### Container Health
- [ ] All containers running: `docker-compose ps`
- [ ] No containers in "Exit" or "Restarting" state
- [ ] Web container healthy
- [ ] Database container healthy
- [ ] Nginx container healthy
- [ ] Certbot container healthy

### Application Health
- [ ] Django admin accessible: `https://yourdomain.com/admin/`
- [ ] Admin login working
- [ ] No 500/502 errors
- [ ] Static files loading correctly
- [ ] Database migrations applied: `docker-compose exec web python manage.py showmigrations`

### Telegram Bot
- [ ] Bot responds to `/start`
- [ ] Bot responds to `/help`
- [ ] Webhook URL set correctly
- [ ] Webhook info verified:
  ```bash
  docker-compose exec web python -c "
  import asyncio
  from telegram import Bot
  async def check():
      bot = Bot('TOKEN')
      info = await bot.get_webhook_info()
      print(f'URL: {info.url}')
      print(f'Pending: {info.pending_update_count}')
  asyncio.run(check())
  "
  ```
- [ ] No pending updates accumulating

### Database
- [ ] Database accessible
- [ ] Migrations applied
- [ ] Superuser created
- [ ] Can login to admin panel
- [ ] Data persisting across restarts

### HTTPS/SSL
- [ ] HTTPS working: `https://yourdomain.com`
- [ ] No SSL warnings in browser
- [ ] HTTP redirects to HTTPS
- [ ] Certificate valid and not expired
- [ ] SSL Labs test: A or A+ rating (optional)

### Logs
- [ ] No critical errors in web logs
- [ ] No errors in database logs
- [ ] No errors in nginx logs
- [ ] Application logging working

---

## Monitoring Setup (Recommended)

### Application Monitoring
- [ ] Log rotation configured
- [ ] Disk space monitoring set up
- [ ] Container resource monitoring (CPU, RAM)
- [ ] Uptime monitoring configured (e.g., Uptime Robot)

### Backup Configuration
- [ ] Database backup script created
- [ ] Backup schedule configured (daily recommended)
- [ ] Backup storage location configured
- [ ] Backup restoration tested

### Alerting
- [ ] Email alerts for container failures (optional)
- [ ] Disk space alerts configured
- [ ] SSL expiration alerts (Let's Encrypt auto-renews, but good to monitor)

---

## Security Checklist

### Server Security
- [ ] SSH password authentication disabled (key-only)
- [ ] Root login disabled
- [ ] Only necessary ports open (22, 80, 443)
- [ ] Fail2ban installed and configured (optional but recommended)
- [ ] Automatic security updates enabled

### Application Security
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (50+ characters, random)
- [ ] Strong database password
- [ ] Strong superuser password
- [ ] All secrets in GitHub Secrets (not in code)
- [ ] `.env` file not committed to git
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] `CSRF_TRUSTED_ORIGINS` properly configured

### Docker Security
- [ ] Containers running as non-root user
- [ ] Resource limits set (CPU, memory)
- [ ] Unnecessary privileges removed
- [ ] Images from trusted sources only

---

## Testing Checklist

### Functionality Testing
- [ ] Create new habit via bot
- [ ] Mark habit as done
- [ ] View habits list
- [ ] Edit habit
- [ ] Delete habit
- [ ] View rewards
- [ ] Claim reward (if applicable)
- [ ] View stats/streaks
- [ ] All menu buttons working
- [ ] All callback handlers working

### Load Testing (Optional)
- [ ] Bot handles multiple concurrent users
- [ ] Database performs well under load
- [ ] No memory leaks after extended use

### Disaster Recovery Testing
- [ ] Container restart: `docker-compose restart`
- [ ] Full system restart: `docker-compose down && docker-compose up -d`
- [ ] Database backup and restore tested
- [ ] Rollback procedure tested

---

## Documentation Checklist

- [ ] README.md updated with deployment info
- [ ] DEPLOYMENT.md reviewed and accurate
- [ ] QUICK_START.md reviewed
- [ ] Environment variables documented in .env.example
- [ ] Architecture diagram available (optional)
- [ ] Runbook created for common operations

---

## Go-Live Checklist

### Final Verification
- [ ] All above checklists completed
- [ ] All tests passing
- [ ] No critical issues in logs
- [ ] Performance acceptable
- [ ] Backup working
- [ ] Monitoring active

### Communication
- [ ] Team notified of deployment
- [ ] Users informed (if applicable)
- [ ] Support team briefed
- [ ] Documentation shared

### Post-Go-Live
- [ ] Monitor logs for first 24 hours
- [ ] Check for unusual activity
- [ ] Verify backups running
- [ ] Address any issues immediately

---

## Rollback Plan

If something goes wrong:

- [ ] Rollback procedure documented
- [ ] Previous version available
- [ ] Database backup available
- [ ] Can execute rollback in < 10 minutes

### Rollback Steps
1. [ ] Stop current containers
2. [ ] Restore previous Docker image
3. [ ] Restore database backup (if needed)
4. [ ] Start containers
5. [ ] Verify functionality
6. [ ] Investigate and fix issue

---

## Success Criteria

Deployment is successful when:

- ✅ All containers running healthy
- ✅ HTTPS working with valid certificate
- ✅ Bot responding to commands
- ✅ Admin panel accessible
- ✅ Database persisting data
- ✅ No errors in logs
- ✅ GitHub Actions deploying automatically
- ✅ Backups configured and working

---

## Notes

Use this space for deployment-specific notes:

- Date deployed:
- Deployed by:
- Server IP:
- Domain:
- Issues encountered:
- Resolution:

---

**Checklist Version:** 1.0.0
**Last Updated:** 2025-11-08
