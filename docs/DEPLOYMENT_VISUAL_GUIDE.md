# Visual Deployment Guide

## Complete System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────┘

  You (Developer)
       │
       │ 1. Write Code
       ▼
  Local Machine
  ├── Edit files
  ├── Test locally (./deployment/scripts/local-test.sh)
  └── Commit & Push
       │
       │ 2. git push origin main
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           GITHUB                                     │
│                                                                      │
│  Repository                                                          │
│  ├── Code                                                            │
│  ├── /deployment folder                                              │
│  │   ├── docker/                                                     │
│  │   ├── nginx/                                                      │
│  │   └── scripts/                                                    │
│  └── Secrets (15-18 environment variables)                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │               GITHUB ACTIONS (CI/CD)                       │    │
│  │                                                            │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │    │
│  │  │  TEST    │→ │  BUILD   │→ │  DEPLOY  │→ │  VERIFY  │  │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │    │
│  │  Run pytest   Build Docker  SSH to VPS   Check health   │    │
│  │  & linting    Push to GHCR  Run deploy   Test webhook   │    │
│  │  (2 min)      (5 min)        (3 min)      (30 sec)      │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             │                                       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              │ 3. SSH & Deploy
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    DIGITAL OCEAN VPS                                 │
│                  (Your Server: $6/month)                             │
│                                                                      │
│  IP: 123.456.789.012                                                 │
│  Domain: yourdomain.com → points to this IP                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              DOCKER COMPOSE ENVIRONMENT                    │    │
│  │                                                            │    │
│  │  ┌──────────────────────────────────────────────────┐     │    │
│  │  │           Nginx Container                        │     │    │
│  │  │  • Reverse Proxy                                 │     │    │
│  │  │  • SSL/TLS (Let's Encrypt)                       │     │    │
│  │  │  • Port 80 → 443 redirect                        │     │    │
│  │  │  • Serves static files                           │     │    │
│  │  └────┬─────────────────────────────────────────────┘     │    │
│  │       │ Forwards requests to                              │    │
│  │       ▼                                                    │    │
│  │  ┌──────────────────────────────────────────────────┐     │    │
│  │  │       Web Container (Django + Bot)               │     │    │
│  │  │  • Django 5.0+ ASGI Application                  │     │    │
│  │  │  • Telegram Bot (python-telegram-bot)            │     │    │
│  │  │  • Uvicorn server (port 8000)                    │     │    │
│  │  │  • Handles:                                      │     │    │
│  │  │    - /admin/ (Django admin)                      │     │    │
│  │  │    - /webhook/telegram (bot updates)             │     │    │
│  │  │    - Static files via whitenoise                 │     │    │
│  │  └────┬─────────────────────────────────────────────┘     │    │
│  │       │ Connects to                                       │    │
│  │       ▼                                                    │    │
│  │  ┌──────────────────────────────────────────────────┐     │    │
│  │  │     PostgreSQL Container                         │     │    │
│  │  │  • PostgreSQL 16                                 │     │    │
│  │  │  • Database: habit_reward                        │     │    │
│  │  │  • Tables: users, habits, rewards, logs          │     │    │
│  │  │  • Persistent volume (data survives restarts)    │     │    │
│  │  └──────────────────────────────────────────────────┘     │    │
│  │                                                            │    │
│  │  ┌──────────────────────────────────────────────────┐     │    │
│  │  │         Certbot Container                        │     │    │
│  │  │  • Manages SSL certificates                      │     │    │
│  │  │  • Auto-renewal every 12 hours                   │     │    │
│  │  │  • Let's Encrypt (free SSL)                      │     │    │
│  │  └──────────────────────────────────────────────────┘     │    │
│  │                                                            │    │
│  │  Persistent Volumes:                                       │    │
│  │  • postgres_data (database files)                          │    │
│  │  • bot_data (conversation state)                           │    │
│  │  • static_files (CSS, JS, images)                          │    │
│  │  • certbot_data (SSL certificates)                         │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Firewall (UFW):                                                     │
│  • Port 22 (SSH) ✓                                                   │
│  • Port 80 (HTTP) ✓                                                  │
│  • Port 443 (HTTPS) ✓                                                │
│  • All other ports blocked ✗                                         │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              │ 4. HTTPS Traffic
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      TELEGRAM SERVERS                                │
│                                                                      │
│  When user interacts with bot:                                      │
│  1. User sends message in Telegram                                  │
│  2. Telegram servers receive message                                │
│  3. Telegram sends HTTPS POST to:                                   │
│     https://yourdomain.com/webhook/telegram                         │
│  4. Your server processes and responds                              │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Telegram Users  │
                    │  Using Your Bot  │
                    └──────────────────┘
```

---

## Data Flow: User Sends "/start" Command

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STEP-BY-STEP FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

User (on phone)
  │
  │ Types: /start
  ▼
Telegram App
  │
  │ Sends message to
  ▼
Telegram Servers
  │
  │ POST request with JSON payload:
  │ {
  │   "message": {
  │     "text": "/start",
  │     "from": { "id": 123456, "first_name": "John" }
  │   }
  │ }
  ▼
HTTPS → yourdomain.com:443
  │
  │ SSL/TLS Handshake
  ▼
Nginx Container
  │
  │ 1. Verifies SSL certificate
  │ 2. Decrypts HTTPS
  │ 3. Checks nginx.conf rules
  │ 4. Proxies to backend
  ▼
Web Container (port 8000)
  │
  │ Django ASGI Application
  │ └── URL Router: /webhook/telegram
  │     └── webhook_handler.py
  │         └── TelegramWebhookHandler
  ▼
Telegram Bot Handler
  │
  │ 1. Parses JSON update
  │ 2. Identifies /start command
  │ 3. Loads command_handlers.py
  │ 4. Executes start_command()
  ▼
Business Logic
  │
  │ 1. Check if user exists in database
  │ 2. Create user if new
  │    └── SQL: INSERT INTO core_user ...
  │ 3. Load user preferences
  │ 4. Build welcome message
  │ 5. Build keyboard buttons
  ▼
Database (PostgreSQL)
  │
  │ Query/Insert operations
  │ Returns user data
  ▼
Response Preparation
  │
  │ Format message:
  │ "Welcome John! 👋
  │  Ready to track habits?"
  │
  │ Attach keyboard:
  │ [Add Habit] [My Habits]
  │ [Stats]     [Settings]
  ▼
Send to Telegram
  │
  │ API Call via python-telegram-bot:
  │ bot.send_message(
  │   chat_id=123456,
  │   text="Welcome...",
  │   reply_markup=keyboard
  │ )
  ▼
Telegram Servers
  │
  │ Deliver message
  ▼
User's Phone
  │
  │ Shows welcome message
  │ Shows keyboard buttons
  ▼
User sees response! ✅

Total time: ~100-300ms
```

---

## Deployment Timeline

```
Time: 0 min ──────────────────────────────────────────→ 90 min

├─ Phase 1: Digital Ocean Account (10 min)
│  └─ Create account, verify email, add payment
│
├─ Phase 2: Create VPS (15 min)
│  └─ Choose plan, add SSH key, create droplet
│
├─ Phase 3: Server Setup (20 min)
│  ├─ Install Docker
│  ├─ Install Docker Compose
│  ├─ Create deploy user
│  ├─ Configure firewall
│  └─ Generate SSH keys
│
├─ Phase 4: Domain Setup (10 min)
│  └─ Configure DNS A records
│  └─ ⏰ Wait for propagation (5-60 min, can do other tasks)
│
├─ Phase 5: Telegram Bot (5 min)
│  └─ Create bot with @BotFather
│
├─ Phase 6: GitHub Setup (15 min)
│  ├─ Generate secrets
│  ├─ Add 15-18 repository secrets
│  └─ Enable Actions
│
├─ Phase 7: Deploy (20 min)
│  ├─ Update nginx config
│  ├─ Push to GitHub
│  └─ ⏰ Wait for GitHub Actions (~10-15 min)
│
├─ Phase 8: SSL Certificate (10 min)
│  └─ Run certbot, configure HTTPS
│
├─ Phase 9: Verification (10 min)
│  ├─ Test Django admin
│  └─ Test Telegram bot
│
└─ Phase 10: Backups (10 min)
   └─ Configure automated backups

   DONE! 🎉
```

---

## Cost Breakdown

```
┌────────────────────────────────────────────────────────────┐
│                    MONTHLY COSTS                           │
└────────────────────────────────────────────────────────────┘

Digital Ocean Droplet (1GB)          $6.00/month
  ├─ 1 CPU
  ├─ 1GB RAM
  ├─ 25GB SSD
  ├─ 1TB Transfer
  └─ Free: Monitoring, Firewall, Backups (manual)

Domain Name (optional)               ~$1.00/month ($12/year)
  └─ Or use free: duckdns.org         $0.00/month

SSL Certificate (Let's Encrypt)      $0.00/month (FREE!)

Total: $6-7/month

┌────────────────────────────────────────────────────────────┐
│                    ONE-TIME COSTS                          │
└────────────────────────────────────────────────────────────┘

Domain Registration                  $10-15 (one-time, yearly)
  └─ Or use free subdomain            $0

Setup Time (your time)               90 minutes (one-time)

Total one-time: $0-15

┌────────────────────────────────────────────────────────────┐
│                  WAYS TO REDUCE COSTS                      │
└────────────────────────────────────────────────────────────┘

1. Use Digital Ocean $200 credit → 33 months FREE
2. Use free subdomain (duckdns.org) → Save $12/year
3. Optimize droplet after launch → Possibly downgrade

Minimum viable: $0/month for first 33 months with credits!
```

---

## System Requirements

```
┌─────────────────────────────────────────────────────────────┐
│                  MINIMUM REQUIREMENTS                       │
└─────────────────────────────────────────────────────────────┘

VPS:
  • 1 CPU core
  • 1GB RAM (512MB might work but not recommended)
  • 10GB disk space
  • Ubuntu 22.04 or similar Linux

Local Machine:
  • Any OS (Mac, Windows, Linux)
  • Git installed
  • SSH client (built-in on Mac/Linux)
  • Text editor

Knowledge:
  • Basic command line
  • Git basics (commit, push)
  • Basic understanding of environment variables
  • Patience! 😊

┌─────────────────────────────────────────────────────────────┐
│                 RECOMMENDED SETUP                           │
└─────────────────────────────────────────────────────────────┘

VPS:
  • 1-2 CPU cores
  • 2GB RAM (for better performance)
  • 25GB SSD
  • Backups enabled

For 100+ daily active users:
  • 2 CPU cores
  • 4GB RAM
  • 50GB SSD
  • Consider CDN for static files
```

---

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY STACK                           │
└─────────────────────────────────────────────────────────────┘

Layer 1: Firewall (UFW)
  └─ Only ports 22, 80, 443 open
  └─ All other ports blocked

Layer 2: SSH Keys
  └─ No password authentication
  └─ Only authorized keys can connect

Layer 3: SSL/TLS (HTTPS)
  └─ All traffic encrypted
  └─ Valid certificates from Let's Encrypt

Layer 4: Docker Isolation
  └─ Each service in separate container
  └─ Non-root users
  └─ Resource limits

Layer 5: Django Security
  └─ SECRET_KEY (50+ random chars)
  └─ DEBUG=False in production
  └─ CSRF protection
  └─ XSS protection headers

Layer 6: Database
  └─ Not exposed to internet
  └─ Strong password
  └─ Only accessible from web container

Layer 7: Environment Variables
  └─ Secrets in .env (not in code)
  └─ GitHub Secrets (encrypted)
  └─ Never committed to git

Layer 8: Regular Updates
  └─ Automatic security updates
  └─ Container image updates
  └─ Dependency updates
```

---

## What Happens When...

### When you push code to GitHub:

```
1. GitHub receives push
2. Triggers workflow (.github/workflows/deploy.yml)
3. Runs tests
4. Builds Docker image
5. Pushes image to GitHub Container Registry
6. SSHs to your VPS
7. Pulls new image
8. Stops old containers
9. Starts new containers
10. Verifies deployment
11. ✅ Done! (or ❌ reports error)
```

### When a user sends a message:

```
1. User types in Telegram
2. Telegram servers receive
3. POST to your webhook
4. Nginx receives HTTPS request
5. Forwards to Django
6. Django routes to webhook handler
7. Bot processes message
8. Database operations (if needed)
9. Bot sends response
10. Telegram delivers to user
```

### When server restarts:

```
1. Docker containers stop
2. Data persists in volumes
3. Server reboots
4. Docker starts automatically
5. Containers restart in order:
   a. Database first
   b. Web waits for database
   c. Nginx waits for web
   d. Certbot starts
6. Health checks verify all services
7. Bot is back online ✅
```

### When SSL certificate expires:

```
1. Certbot checks certificates (every 12h)
2. If <30 days until expiry:
   a. Requests renewal from Let's Encrypt
   b. Receives new certificate
   c. Reloads nginx
3. ✅ Automatic renewal, no downtime
```

---

## Monitoring Dashboard (what to track)

```
Daily Checks:
  [ ] Bot responding? → Send /start
  [ ] Admin panel? → https://yourdomain.com/admin/
  [ ] SSL valid? → Check browser lock icon

Weekly Checks:
  [ ] Disk space → ssh + df -h (should have >50% free)
  [ ] Memory usage → free -h
  [ ] Container status → docker-compose ps
  [ ] Error logs → docker-compose logs | grep ERROR

Monthly Checks:
  [ ] Backups exist → ls ~/backups/
  [ ] Test backup restore
  [ ] Security updates → apt update && apt upgrade
  [ ] Review user growth
  [ ] Check costs
```

---

## Quick Reference: File Locations

```
On Your VPS:
/home/deploy/habit_reward_bot/
├── docker/
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── nginx/
│   └── conf.d/habit_reward.conf
├── scripts/
│   └── deploy.sh
├── .env (YOUR SECRETS - NEVER COMMIT!)
└── (GitHub Actions copies deployment/ here)

Docker Volumes (data):
/var/lib/docker/volumes/
├── habit_reward_postgres_data/
├── habit_reward_bot_data/
├── habit_reward_static_files/
└── habit_reward_certbot_data/

SSL Certificates:
/var/lib/docker/volumes/certbot_data/_data/live/yourdomain.com/
├── fullchain.pem
└── privkey.pem

Backups:
/home/deploy/backups/
├── backup_20250108_020000.sql.gz
├── backup_20250107_020000.sql.gz
└── ...
```

---

**Need help?** See:
- Complete guide: `/docs/DEPLOYMENT_STEP_BY_STEP.md`
- Quick checklist: `/docs/DEPLOYMENT_CHECKLIST_SIMPLE.md`
- Commands: `/docs/DEPLOYMENT_QUICK_REFERENCE.md`
