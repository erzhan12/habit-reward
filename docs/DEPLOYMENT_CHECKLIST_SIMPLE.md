# Deployment Checklist - Quick Reference

Print this page and check off each step as you complete it!

## ☐ Phase 1: Digital Ocean Setup (10 min)
- [X] Create Digital Ocean account at https://www.digitalocean.com/
- [X] Verify email
- [X] Add payment method
- [X] (Optional) Apply $200 credit code

## ☐ Phase 2: Create VPS (15 min)
- [X] Click "Create" → "Droplets"
- [X] Choose region (closest to you)
- [X] Choose Ubuntu 22.04 LTS x64
- [X] Choose $6/month plan (1GB RAM)
- [X] Generate SSH key: `ssh-keygen -t ed25519 -C "do-habit-bot"`
- [X] Add SSH key to Digital Ocean
- [X] Create droplet
- [X] **Write down IP address:** ___________________
- [X] Connect: `ssh -i ~/.ssh/do_habit_bot root@YOUR_IP`
- [X] Update: `apt update && apt upgrade -y`
- [X] Reboot if needed: `reboot`

## ☐ Phase 3: Install Software (20 min)
- [X] Install Docker (see full guide for commands)
- [X] Verify: `docker --version`
- [X] Install Docker Compose
- [X] Verify: `docker-compose --version`
- [X] Create deploy user: `adduser deploy`
- [X] Add to docker group: `usermod -aG docker deploy`
- [X] Add to sudo group: `usermod -aG sudo deploy`
- [X] Copy SSH keys to deploy user
- [X] Test deploy user login
- [X] Configure firewall: `ufw allow 22,80,443/tcp && ufw enable`
- [X] Create directory: `mkdir -p /home/deploy/habit_reward_bot`
- [X] Generate GitHub Actions key: `ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""`
- [X] **Copy private key** (for GitHub Secrets)

## ☐ Phase 4: Domain Setup (10 min)
- [X] Buy domain OR use free subdomain (duckdns.org)
- [X] **Write down domain:** habitreward.org
- [X] Add A record: `@` → Your VPS IP
- [X] Add A record: `www` → Your VPS IP
- [X] Wait for DNS propagation (5-60 min)
- [X] Test: `ping yourdomain.com`

## ☐ Phase 5: Telegram Bot (5 min)
- [X] Open Telegram, find @BotFather
- [X] Send `/newbot`
- [X] Enter bot name
- [X] Enter bot username (must end with 'bot')
- [X] **Copy bot token:** ___________________
- [X] Keep token secret!

## ☐ Phase 6: GitHub Setup (15 min)

### Generate Secrets
- [X] Generate Django secret: `python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [X] Generate DB password: `openssl rand -base64 32`
- [X] Generate admin password (strong password)

### Add to GitHub
Go to Settings → Secrets and variables → Actions → New repository secret

- [X] `POSTGRES_DB` = `habit_reward`
- [X] `POSTGRES_USER` = `postgres`
- [X] `POSTGRES_PASSWORD` = (generated password)
- [X] `DJANGO_SECRET_KEY` = (generated secret key)
- [X] `ALLOWED_HOSTS` = `yourdomain.com,www.yourdomain.com`
- [X] `CSRF_TRUSTED_ORIGINS` = `https://yourdomain.com,https://www.yourdomain.com`
- [X] `TELEGRAM_BOT_TOKEN` = (from BotFather)
- [X] `TELEGRAM_WEBHOOK_URL` = `https://yourdomain.com/webhook/telegram`
- [X] `DJANGO_SUPERUSER_USERNAME` = `admin`
- [X] `DJANGO_SUPERUSER_EMAIL` = (your email)
- [X] `DJANGO_SUPERUSER_PASSWORD` = (strong password)
- [X] `SERVER_HOST` = (your VPS IP)
- [X] `SSH_USER` = `deploy`
- [X] `SSH_PRIVATE_KEY` = (paste entire private key from Phase 3)
- [X] `DEPLOY_PATH` = `/home/deploy/habit_reward_bot`
- [X] Enable GitHub Actions: Settings → Actions → Allow all

## ☐ Phase 7: Deploy (20 min)
- [X] Update nginx config: Replace `example.com` with your domain
- [X] Commit: `git add . && git commit -m "feat: configure domain"`
- [X] Push: `git push origin main`
- [X] Watch GitHub Actions (should take ~10-15 min)
- [ ] All checks green ✅

## ☐ Phase 8: SSL Certificate (10 min)
- [X] SSH to VPS: `ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP`
- [X] Navigate: `cd /home/deploy/habit_reward_bot/docker`
- [X] Verify DNS: `ping yourdomain.com`
- [X] Stop nginx: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx`
- [X] Get certificate: (see full guide for certbot command)
- [X] Start nginx: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml start nginx`
- [X] Test HTTPS: Open `https://yourdomain.com` (should show lock icon)

## ☐ Phase 9: Verify (10 min)
- [X] Check containers: `docker-compose ps` (all should show "Up")
- [X] Check logs: `docker-compose logs web` (no errors)
- [X] Access admin: `https://yourdomain.com/admin/`
- [ ] Login with superuser credentials
- [ ] Open Telegram, find your bot
- [ ] Send `/start` to bot
- [ ] Bot responds!

## ☐ Phase 10: Backups (10 min)
- [ ] Create backup script (see full guide)
- [ ] Make executable: `chmod +x ~/backup_db.sh`
- [ ] Schedule cron: `crontab -e`
- [ ] Add daily backup at 2 AM
- [ ] Set up uptime monitoring (uptimerobot.com)

---

## Quick Info Sheet

Fill this out as you go:

| Item | Value |
|------|-------|
| VPS IP Address | _________________ |
| Domain Name | _________________ |
| Telegram Bot Token | _________________ |
| Django Admin Username | _________________ |
| Django Admin Password | _________________ |
| Database Password | _________________ |

**Keep this information secure!** 🔒

---

## Quick Commands Reference

**SSH to VPS:**
```bash
ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
```

**Check containers:**
```bash
cd /home/deploy/habit_reward_bot/docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

**View logs:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

**Restart bot:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

**Backup database:**
```bash
~/backup_db.sh
```

**Deploy updates:**
```bash
# On local machine:
git add .
git commit -m "update: description"
git push origin main
# GitHub Actions will auto-deploy!
```

---

## Completion Status

Total Phases: 10
Estimated Time: 60-90 minutes
Monthly Cost: $6-7

**Status:** ☐ Not Started | ☐ In Progress | ☐ Completed ✅

**Deployment Date:** _______________

**Notes:**
```


```

---

**Need help?** See `/docs/DEPLOYMENT_STEP_BY_STEP.md` for detailed instructions.
