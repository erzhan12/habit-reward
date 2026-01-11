# 🚀 Deployment Guide - Start Here!

## Choose Your Guide

### 📚 Complete Step-by-Step Guide (Recommended for First-Time Deployment)
**File:** [`docs/DEPLOYMENT_STEP_BY_STEP.md`](docs/DEPLOYMENT_STEP_BY_STEP.md)

**Perfect for:**
- First-time deployment
- Creating Digital Ocean account from scratch
- Never deployed to VPS before
- Want detailed explanations at every step

**What's included:**
- Creating Digital Ocean account
- VPS setup from zero
- Domain configuration
- Telegram bot creation
- Complete deployment process
- SSL certificate setup
- Testing and verification

**Time:** 60-90 minutes
**Difficulty:** Beginner-friendly with screenshots and explanations

---

### ✅ Quick Checklist (Print and Follow)
**File:** [`docs/DEPLOYMENT_CHECKLIST_SIMPLE.md`](docs/DEPLOYMENT_CHECKLIST_SIMPLE.md)

**Perfect for:**
- Quick reference while deploying
- Checking off completed steps
- Ensuring nothing is missed
- Printing out for offline use

**What's included:**
- 10-phase checklist
- Fill-in-the-blank info sheet
- Quick command reference
- Completion tracking

---

### 📖 Visual Guide (Understand the System)
**File:** [`docs/DEPLOYMENT_VISUAL_GUIDE.md`](docs/DEPLOYMENT_VISUAL_GUIDE.md)

**Perfect for:**
- Understanding how everything connects
- Visual learners
- System architecture overview
- Troubleshooting concepts

**What's included:**
- Architecture diagrams
- Data flow visualizations
- Timeline breakdown
- Cost breakdown
- Security layers explained

---

### 📝 Detailed Reference (Deep Dive)
**File:** [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

**Perfect for:**
- Advanced users
- Troubleshooting specific issues
- Understanding configuration options
- Security best practices

**What's included:**
- 800+ lines of detailed documentation
- Advanced configurations
- Comprehensive troubleshooting
- Rollback procedures
- Monitoring and maintenance

---

### 🎯 Quick Command Reference
**File:** [`docs/DEPLOYMENT_QUICK_REFERENCE.md`](docs/DEPLOYMENT_QUICK_REFERENCE.md)

**Perfect for:**
- Daily operations
- Common commands
- Quick lookups
- Copy-paste commands

**What's included:**
- Docker commands
- Database operations
- Deployment commands
- Monitoring commands

---

## Quick Decision Tree

```
┌─────────────────────────────────────────────────┐
│   Have you deployed to a VPS before?           │
└─────────────────┬───────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
       NO                 YES
         │                 │
         ▼                 ▼
    ┌─────────┐      ┌──────────┐
    │  START  │      │  START   │
    │  HERE:  │      │  HERE:   │
    │         │      │          │
    │ STEP-BY │      │ QUICK    │
    │  -STEP  │      │ START    │
    │  GUIDE  │      │ (30 min) │
    └─────────┘      └──────────┘
         │                 │
         │                 │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────┐
         │   DEPLOYING    │
         │                │
         │  Use checklist │
         │  to track      │
         │  progress      │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │  Need Help?    │
         │                │
         │  Visual Guide  │
         │  or Full Docs  │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │  DEPLOYED! 🎉  │
         │                │
         │ Daily ops:     │
         │ Quick Ref      │
         └────────────────┘
```

---

## Deployment Files Organization

All deployment files are in the `/deployment` directory:

```
deployment/
├── docker/                  # Docker configuration
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── docker-compose.yml
│   └── .env.production
│
├── caddy/                   # Reverse proxy (recommended)
│   └── Caddyfile
│
├── scripts/                 # Deployment scripts
│   ├── entrypoint.sh
│   ├── deploy-caddy.sh
│   └── local-test.sh
│
└── README.md               # Deployment folder guide
```

See [`deployment/README.md`](deployment/README.md) for details.

---

## Quick Start (30 minutes)

Already have:
- ✅ VPS with Ubuntu
- ✅ Docker installed
- ✅ Domain configured
- ✅ Telegram bot created

**Then you can deploy in 30 minutes:**

1. **Local setup:**
   ```bash
   # Review Caddyfile domain and proxy config (if needed)
   nano deployment/caddy/Caddyfile
   ```

2. **Add GitHub Secrets** (15 secrets - see [`.env.example`](.env.example))

3. **Deploy:**
   ```bash
   git add .
   git commit -m "feat: configure deployment"
   git push origin main
   ```

4. **SSL certificate**
   - Automatic: Caddy provisions and renews certificates automatically after the containers start.

5. **Test:**
   - Open: `https://yourdomain.com/admin/`
   - Telegram: Send `/start` to your bot

Done! 🎉

---

## Documentation Index

### Getting Started
1. [`DEPLOYMENT_STEP_BY_STEP.md`](docs/DEPLOYMENT_STEP_BY_STEP.md) - Complete guide from zero
2. [`DEPLOYMENT_CHECKLIST_SIMPLE.md`](docs/DEPLOYMENT_CHECKLIST_SIMPLE.md) - Printable checklist
3. [`QUICK_START.md`](docs/QUICK_START.md) - 30-minute deployment

### Understanding
4. [`DEPLOYMENT_VISUAL_GUIDE.md`](docs/DEPLOYMENT_VISUAL_GUIDE.md) - Diagrams and visualizations
5. [`DEPLOYMENT.md`](docs/DEPLOYMENT.md) - Comprehensive reference (800+ lines)
6. [`DEPLOYMENT_STRUCTURE.md`](DEPLOYMENT_STRUCTURE.md) - File organization

### Reference
7. [`DEPLOYMENT_QUICK_REFERENCE.md`](docs/DEPLOYMENT_QUICK_REFERENCE.md) - Command cheat sheet
8. [`DEPLOYMENT_SUMMARY.md`](DEPLOYMENT_SUMMARY.md) - Architecture overview
9. [`.env.example`](.env.example) - Environment variables template

### Deployment Folder
10. [`deployment/README.md`](deployment/README.md) - Deployment files guide

---

## What You Need Before Starting

### Required
- [ ] Computer (Mac, Windows, or Linux)
- [ ] Credit/debit card (for VPS - ~$6/month)
- [ ] Email address
- [ ] Telegram account
- [ ] GitHub account
- [ ] 90 minutes of time

### Optional
- [ ] Domain name (~$12/year) - or use free subdomain
- [ ] OpenAI API key (for AI habit classification)

---

## Cost Summary

| Item | Cost |
|------|------|
| VPS (Digital Ocean 1GB) | $6/month |
| Domain name (optional) | $12/year (~$1/month) |
| SSL Certificate | FREE (Let's Encrypt) |
| **Total** | **~$6-7/month** |

**Free options:**
- Get $200 Digital Ocean credit → 33 months FREE
- Use free subdomain (duckdns.org) → $0/month
- **Possible total:** $0 for first 33 months!

---

## Support & Help

### Common Issues
- **Can't SSH to VPS** → Check SSH key path
- **Domain not working** → Wait for DNS propagation (up to 24h)
- **SSL failed** → Ensure domain points to VPS, ports 80/443 open
- **Bot not responding** → Check webhook URL, verify HTTPS
- **Database error** → Check .env file, restart containers

### Where to Get Help
1. **Read troubleshooting** in [`DEPLOYMENT_STEP_BY_STEP.md`](docs/DEPLOYMENT_STEP_BY_STEP.md)
2. **Check logs:**
   ```bash
   ssh deploy@YOUR_IP
   cd /home/deploy/habit_reward_bot
   docker-compose --env-file .env -f docker/docker-compose.yml logs -f
   ```
3. **Review GitHub Actions** logs (if using automated deployment)
4. **Search documentation** - use Ctrl+F in the guides

---

## After Deployment

### Daily (1 minute)
- Check bot is responding

### Weekly (5 minutes)
- Check disk space: `df -h`
- Check logs: `docker-compose logs --tail=100`
- Verify backups exist

### Monthly (10 minutes)
- Update system: `apt update && apt upgrade -y`
- Review costs in Digital Ocean dashboard
- Check SSL certificate validity

### When Making Changes
1. Edit code locally
2. Test with: `./deployment/scripts/local-test.sh`
3. Commit changes
4. Push to GitHub: `git push origin main`
5. GitHub Actions auto-deploys
6. Verify in production

---

## Success Criteria

Your deployment is successful when:

✅ All containers running: `docker-compose ps` shows "Up"
✅ HTTPS working: `https://yourdomain.com` shows lock icon
✅ Admin accessible: `https://yourdomain.com/admin/` loads
✅ Bot responding: `/start` in Telegram gets response
✅ No errors in logs: `docker-compose logs` shows no red errors
✅ Database working: Can create habits, view rewards
✅ Webhook verified: Shows correct URL in Telegram

---

## Next Steps After Deployment

1. **Customize your bot**
   - Add more habits
   - Configure rewards
   - Customize messages

2. **Share with friends**
   - Get feedback
   - Find bugs early
   - Improve UX

3. **Monitor and maintain**
   - Set up uptime monitoring
   - Regular backups
   - Keep updated

4. **Scale if needed**
   - Upgrade VPS for more users
   - Add Redis caching
   - Optimize database

---

## Quick Comparison of Guides

| Guide | Time | Best For | Includes |
|-------|------|----------|----------|
| Step-by-Step | 90 min | First deployment | Everything from account creation |
| Quick Start | 30 min | Experienced users | Assumes VPS/domain ready |
| Checklist | N/A | All levels | Track progress |
| Visual Guide | 15 min | Understanding | Diagrams and architecture |
| Full Docs | N/A | Reference | Deep dive and troubleshooting |
| Quick Ref | N/A | Daily ops | Commands only |

---

## Recommended Learning Path

```
Day 1: Read Step-by-Step Guide → Deploy
Day 2: Read Visual Guide → Understand
Day 3: Read Full Docs → Deep dive
Day 4+: Use Quick Reference → Daily operations
```

---

**Ready to deploy?** Start with [`docs/DEPLOYMENT_STEP_BY_STEP.md`](docs/DEPLOYMENT_STEP_BY_STEP.md)

**Already deployed?** Use [`docs/DEPLOYMENT_QUICK_REFERENCE.md`](docs/DEPLOYMENT_QUICK_REFERENCE.md) for daily ops

**Need help?** Check [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) troubleshooting section

---

**Last Updated:** 2025-11-08
**Deployment Version:** 2.0.0
**Status:** ✅ Production Ready
