# Complete Step-by-Step Deployment Guide
## From Digital Ocean Account to Running Bot

**Estimated Total Time:** 60-90 minutes
**Cost:** ~$6-12/month for VPS

---

## Phase 1: Digital Ocean Account Setup (10 minutes)

### Step 1.1: Create Digital Ocean Account

1. **Go to Digital Ocean website:**
   - Open browser: https://www.digitalocean.com/
   - Click "Sign Up" button (top right)

2. **Register your account:**
   - Enter your email address
   - Create a strong password
   - Click "Sign Up with Email"
   - Or use "Continue with Google/GitHub" for faster signup

3. **Verify your email:**
   - Check your email inbox
   - Click the verification link from Digital Ocean
   - You'll be redirected to complete your profile

4. **Add payment method:**
   - Digital Ocean requires payment info even for free credits
   - Choose: Credit Card or PayPal
   - **Credit Card option:**
     - Enter card number, expiry, CVV
     - Enter billing address
     - Click "Add Payment Method"
   - **Note:** You won't be charged until you exceed free credits

5. **Get free credits (optional but recommended):**
   - Use referral links for $200 free credit (60 days)
   - Search "Digital Ocean $200 credit" or ask friends
   - Or just proceed with regular $6/month pricing

6. **Complete profile:**
   - Choose account type: "Personal" or "Business"
   - Select your use case: "Deploy an application"
   - Click "Continue"

✅ **Checkpoint:** You should now see the Digital Ocean dashboard

---

## Phase 2: Create and Configure VPS (Droplet) (15 minutes)

### Step 2.1: Create a Droplet

1. **Start droplet creation:**
   - From dashboard, click "Create" → "Droplets" (green button, top right)
   - Or go to: https://cloud.digitalocean.com/droplets/new

2. **Choose region:**
   - Select closest to your users for best performance
   - Recommended: New York, San Francisco, Amsterdam, Singapore
   - **Choose:** Any datacenter in your preferred region
   - Example: "New York 1" or "San Francisco 3"

3. **Choose operating system:**
   - Click "OS" tab (should be selected by default)
   - **Select:** Ubuntu 22.04 (LTS) x64
   - This is the recommended, stable version

4. **Choose droplet size:**
   - Click "Droplet Type" → "Basic"
   - Click "CPU options" → "Regular" (not Premium)
   - **Select pricing plan:**
     - **Recommended:** $6/month (1GB RAM, 1 CPU, 25GB SSD)
     - **Alternative:** $12/month (2GB RAM, 1 CPU, 50GB SSD) - for more traffic
   - Click on the plan box to select it

5. **Choose authentication method:**
   - **IMPORTANT:** Choose "SSH keys" (NOT "Password")
   - Click "New SSH Key" button

6. **Generate and add SSH key:**

   **On Mac/Linux:**
   ```bash
   # Open Terminal and run:
   ssh-keygen -t ed25519 -C "digitalocean-habit-bot" -f ~/.ssh/do_habit_bot

   # When prompted:
   # - Enter file location: Press ENTER (use default)
   # - Enter passphrase: Press ENTER (no passphrase for automation)
   # - Confirm passphrase: Press ENTER

   # Copy the public key:
   cat ~/.ssh/do_habit_bot.pub
   # Copy the output (starts with "ssh-ed25519")
   ```

   **On Windows (PowerShell):**
   ```powershell
   # Open PowerShell and run:
   ssh-keygen -t ed25519 -C "digitalocean-habit-bot" -f $env:USERPROFILE\.ssh\do_habit_bot

   # Copy the public key:
   type $env:USERPROFILE\.ssh\do_habit_bot.pub
   # Copy the output
   ```

7. **Add SSH key to Digital Ocean:**
   - Paste the copied public key into the "SSH key content" field
   - Give it a name: "habit-bot-key"
   - Click "Add SSH Key"
   - ✅ Select the checkbox next to your new key

8. **Finalize and create:**
   - Choose hostname: "habit-reward-bot" (or any name you prefer)
   - Leave "Enable backups" unchecked (save $1.20/month)
   - Leave other options as default
   - Click "Create Droplet" (green button at bottom)

9. **Wait for creation:**
   - You'll see a progress bar (takes 30-60 seconds)
   - When done, you'll see your droplet in the list

10. **Note your droplet's IP address:**
    - Click on your droplet name
    - Find "ipv4" address (e.g., 123.456.789.012)
    - **COPY THIS IP** - you'll need it many times
    - Suggested: Save it in a text file

✅ **Checkpoint:** You should see your droplet running with a green "Active" status

### Step 2.2: Initial Server Connection

1. **Connect to your server:**

   **On Mac/Linux:**
   ```bash
   # Replace YOUR_IP with your actual droplet IP
   ssh -i ~/.ssh/do_habit_bot root@YOUR_IP

   # Example:
   # ssh -i ~/.ssh/do_habit_bot root@123.456.789.012

   # If prompted "Are you sure you want to continue connecting?":
   # Type: yes
   # Press ENTER
   ```

   **On Windows (PowerShell):**
   ```powershell
   ssh -i $env:USERPROFILE\.ssh\do_habit_bot root@YOUR_IP
   ```

2. **First-time connection:**
   - You should see a welcome message from Ubuntu
   - Your prompt will change to: `root@habit-reward-bot:~#`
   - ✅ You're now connected to your VPS!

3. **Update system packages:**
   ```bash
   apt update && apt upgrade -y
   ```
   - This will take 2-5 minutes
   - You'll see a lot of packages being updated
   - If prompted about kernel upgrades or services, choose default options

4. **Reboot if kernel was updated:**
   ```bash
   # Check if reboot is required:
   ls -l /var/run/reboot-required

   # If file exists, reboot:
   reboot

   # Wait 30 seconds, then reconnect:
   ssh -i ~/.ssh/do_habit_bot root@YOUR_IP
   ```

✅ **Checkpoint:** You should be connected to a fully updated Ubuntu server

---

## Phase 3: Server Configuration (20 minutes)

### Step 3.1: Install Docker

1. **Remove old Docker versions (if any):**
   ```bash
   apt remove docker docker-engine docker.io containerd runc -y
   ```

2. **Install prerequisites:**
   ```bash
   apt install -y ca-certificates curl gnupg lsb-release
   ```

3. **Add Docker's official GPG key:**
   ```bash
   mkdir -p /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   ```

4. **Add Docker repository:**
   ```bash
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

5. **Install Docker:**
   ```bash
   apt update
   apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
   - This takes 2-3 minutes

6. **Verify Docker installation:**
   ```bash
   docker --version
   # Should show: Docker version 24.x.x or higher

   systemctl status docker
   # Should show: "active (running)" in green
   # Press 'q' to exit
   ```

✅ **Checkpoint:** Docker is installed and running

### Step 3.2: Install Docker Compose

1. **Download Docker Compose:**
   ```bash
   DOCKER_COMPOSE_VERSION="2.24.0"
   curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   ```

2. **Make it executable:**
   ```bash
   chmod +x /usr/local/bin/docker-compose
   ```

3. **Verify installation:**
   ```bash
   docker-compose --version
   # Should show: Docker Compose version v2.24.0 or higher
   ```

✅ **Checkpoint:** Docker Compose is installed

### Step 3.3: Create Deployment User

1. **Create a dedicated user for deployment:**
   ```bash
   adduser deploy
   ```
   - Enter password: (create a strong password)
   - Re-enter password: (same password)
   - Full Name: Press ENTER (skip)
   - Room Number: Press ENTER (skip)
   - Work Phone: Press ENTER (skip)
   - Home Phone: Press ENTER (skip)
   - Other: Press ENTER (skip)
   - Is the information correct? Type: Y

2. **Add user to Docker group:**
   ```bash
   usermod -aG docker deploy
   ```

3. **Grant sudo privileges:**
   ```bash
   usermod -aG sudo deploy
   ```

4. **Set up SSH key for deploy user:**
   ```bash
   # Create SSH directory for deploy user
   mkdir -p /home/deploy/.ssh

   # Copy root's authorized_keys to deploy user
   cp ~/.ssh/authorized_keys /home/deploy/.ssh/

   # Set correct permissions
   chown -R deploy:deploy /home/deploy/.ssh
   chmod 700 /home/deploy/.ssh
   chmod 600 /home/deploy/.ssh/authorized_keys
   ```

5. **Test deploy user login:**
   ```bash
   # Open a NEW terminal window (keep current one open)
   # Try to connect as deploy user:
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP

   # If successful, you'll see deploy@habit-reward-bot:~$
   # Type 'exit' to close this test connection
   ```

✅ **Checkpoint:** Deploy user created and can connect via SSH

### Step 3.4: Configure Firewall

1. **Back in your root SSH session, configure UFW:**
   ```bash
   # Allow SSH (IMPORTANT - don't lock yourself out!)
   ufw allow 22/tcp

   # Allow HTTP
   ufw allow 80/tcp

   # Allow HTTPS
   ufw allow 443/tcp

   # Enable firewall (will ask for confirmation)
   ufw enable
   # Type: y
   # Press ENTER
   ```

2. **Verify firewall rules:**
   ```bash
   ufw status
   ```
   - Should show rules for 22, 80, and 443

✅ **Checkpoint:** Firewall is configured and active

### Step 3.5: Create Deployment Directory

1. **Switch to deploy user:**
   ```bash
   su - deploy
   # Enter the deploy user password you created
   ```

2. **Create deployment directory:**
   ```bash
   mkdir -p /home/deploy/habit_reward_bot
   cd /home/deploy/habit_reward_bot
   pwd
   # Should show: /home/deploy/habit_reward_bot
   ```

3. **Generate SSH key for GitHub Actions:**
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions -N ""
   ```

4. **Add public key to authorized_keys:**
   ```bash
   cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
   ```

5. **Display private key (you'll need this for GitHub):**
   ```bash
   cat ~/.ssh/github_actions
   ```
   - **COPY THE ENTIRE OUTPUT** (including "-----BEGIN OPENSSH PRIVATE KEY-----" and "-----END OPENSSH PRIVATE KEY-----")
   - Save it in a text file temporarily - you'll add this to GitHub Secrets

✅ **Checkpoint:** Deployment directory created, SSH keys generated

---

## Phase 4: Domain Setup (10 minutes)

### Step 4.1: Register a Domain (if you don't have one)

**Option 1: Use Existing Domain**
- Skip to Step 4.2

**Option 2: Register New Domain**
1. Go to domain registrar (recommended: Namecheap, Google Domains, Cloudflare)
2. Search for available domain name
3. Register domain (~$10-15/year)
4. Complete purchase

**Option 3: Use Free Subdomain (for testing)**
1. Use services like: afraid.org, duckdns.org
2. Create free subdomain (e.g., mybot.duckdns.org)

### Step 4.2: Configure DNS

1. **Log in to your domain registrar:**
   - Go to your domain management panel
   - Find "DNS Settings" or "Manage DNS"

2. **Add A Record:**
   - Type: `A`
   - Name: `@` (or leave blank for root domain)
   - Value/Points to: `YOUR_DROPLET_IP` (e.g., 123.456.789.012)
   - TTL: `3600` (or "Automatic")
   - Click "Add Record" or "Save"

3. **Add www subdomain (optional but recommended):**
   - Type: `A`
   - Name: `www`
   - Value: `YOUR_DROPLET_IP`
   - TTL: `3600`
   - Click "Add Record" or "Save"

4. **Wait for DNS propagation:**
   ```bash
   # On your local machine (not VPS):
   # Test if DNS is working:
   ping yourdomain.com

   # Or use online tool:
   # https://dnschecker.org/
   # Enter your domain and check if IP matches
   ```
   - DNS typically takes 5-60 minutes to propagate
   - Can take up to 24-48 hours in rare cases
   - ☕ Take a coffee break if needed

✅ **Checkpoint:** Domain points to your VPS IP address

---

## Phase 5: Telegram Bot Setup (5 minutes)

### Step 5.1: Create Telegram Bot

1. **Open Telegram app on your phone or desktop**

2. **Search for BotFather:**
   - In search, type: `@BotFather`
   - Click on official BotFather (verified blue checkmark)

3. **Create new bot:**
   - Send message: `/newbot`
   - BotFather will ask for a name
   - Enter your bot name: `Habit Reward Bot` (or any name you like)
   - BotFather will ask for username
   - Enter username: `habit_reward_bot` (or similar, must end with 'bot')
   - If taken, try: `your_habit_reward_bot` or `habitreward_bot`

4. **Save your bot token:**
   - BotFather will reply with a message containing your token
   - Token looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **COPY THIS TOKEN** - you'll need it for deployment
   - **IMPORTANT:** Keep this secret! Anyone with this token can control your bot
   - Save it in a text file temporarily

5. **Configure bot settings (optional but recommended):**
   ```
   /setdescription
   # Choose your bot
   # Enter: "Track your habits and earn rewards!"

   /setabouttext
   # Choose your bot
   # Enter: "Habit tracking bot with gamification"

   /setuserpic
   # Choose your bot
   # Upload a profile picture (optional)
   ```

✅ **Checkpoint:** Telegram bot created, token saved

---

## Phase 6: GitHub Repository Setup (15 minutes)

### Step 6.1: Prepare GitHub Secrets

1. **Generate Django SECRET_KEY:**

   **On your local machine:**
   ```bash
   # If you have Python installed:
   python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

   # OR use online generator:
   # https://djecrety.ir/
   # Click "Generate" and copy the key
   ```
   - **COPY the generated key** (50+ characters)
   - Save in your text file

2. **Generate database password:**
   ```bash
   # Strong random password:
   openssl rand -base64 32

   # OR online:
   # https://passwordsgenerator.net/
   # Generate 32-character password
   ```
   - **COPY the password**
   - Save in your text file

3. **Prepare all secrets in a text file:**

   Create a file called `secrets.txt` on your local machine with:

   ```
   # Database
   POSTGRES_DB=habit_reward
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your-generated-password>

   # Django
   DJANGO_SECRET_KEY=<your-generated-secret-key>
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

   # Telegram
   TELEGRAM_BOT_TOKEN=<your-bot-token-from-botfather>
   TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook/telegram

   # Superuser (for Django admin)
   DJANGO_SUPERUSER_USERNAME=admin
   DJANGO_SUPERUSER_EMAIL=your-email@example.com
   DJANGO_SUPERUSER_PASSWORD=<create-strong-admin-password>

   # Deployment
   SERVER_HOST=<your-droplet-ip>
   SSH_USER=deploy
   SSH_PRIVATE_KEY=<paste-the-entire-private-key-from-step-3.5>
   DEPLOY_PATH=/home/deploy/habit_reward_bot

   # Optional: AI/LLM (if you have OpenAI account)
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-3.5-turbo
   LLM_API_KEY=<your-openai-api-key>  # or leave empty
   ```

### Step 6.2: Add Secrets to GitHub

1. **Go to your GitHub repository:**
   - Open: https://github.com/YOUR_USERNAME/YOUR_REPO

2. **Navigate to Settings:**
   - Click "Settings" tab (top of page)
   - Click "Secrets and variables" → "Actions" (left sidebar)

3. **Add each secret:**
   - Click "New repository secret" (green button)
   - For each line in your `secrets.txt`:
     1. Name: Enter the variable name (e.g., `POSTGRES_DB`)
     2. Secret: Enter the value
     3. Click "Add secret"
   - Repeat for ALL secrets (15-18 total)

   **Secret names to add:**
   - `POSTGRES_DB`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `DJANGO_SECRET_KEY`
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_URL`
   - `DJANGO_SUPERUSER_USERNAME`
   - `DJANGO_SUPERUSER_EMAIL`
   - `DJANGO_SUPERUSER_PASSWORD`
   - `SERVER_HOST`
   - `SSH_USER`
   - `SSH_PRIVATE_KEY`
   - `DEPLOY_PATH`
   - `LLM_PROVIDER` (optional)
   - `LLM_MODEL` (optional)
   - `LLM_API_KEY` (optional)

4. **Verify all secrets are added:**
   - You should see all secret names listed
   - Values will be hidden (this is normal)

✅ **Checkpoint:** All secrets added to GitHub

### Step 6.3: Enable GitHub Actions

1. **In your repository, go to Settings:**
   - Click "Actions" → "General" (left sidebar)

2. **Configure permissions:**
   - Under "Actions permissions":
     - Select "Allow all actions and reusable workflows"
   - Under "Workflow permissions":
     - Select "Read and write permissions"
     - ✅ Check "Allow GitHub Actions to create and approve pull requests"
   - Click "Save"

✅ **Checkpoint:** GitHub Actions enabled and configured

---

## Phase 7: Initial Deployment (20 minutes)

### Step 7.1: Prepare for Deployment

1. **Update nginx configuration with your domain:**

   **On your local machine:**
   ```bash
   cd /path/to/your/project
   nano deployment/nginx/conf.d/habit_reward.conf

   # Find all instances of "example.com" and replace with your domain
   # Use Ctrl+W to search, Ctrl+\ to replace
   # Replace: example.com
   # With: yourdomain.com

   # Save: Ctrl+O, then ENTER
   # Exit: Ctrl+X
   ```

2. **Commit the changes:**
   ```bash
   git add deployment/nginx/conf.d/habit_reward.conf
   git commit -m "feat: configure nginx for yourdomain.com"
   ```

### Step 7.2: Deploy via GitHub Actions

1. **Push to main branch:**
   ```bash
   git push origin main
   ```

2. **Monitor GitHub Actions:**
   - Go to your GitHub repository
   - Click "Actions" tab
   - You should see a new workflow running
   - Click on the workflow to see details

3. **Watch the progress:**
   - **Test job** - Runs tests (1-2 min)
   - **Build job** - Builds Docker image (3-5 min)
   - **Deploy job** - Deploys to VPS (2-3 min)
   - **Health check** - Verifies deployment (30 sec)

4. **If build fails:**
   - Click on the failed step to see error
   - Common issues:
     - Missing secrets → Go back to Phase 6.2
     - SSH connection failed → Check SSH_PRIVATE_KEY format
     - Nginx config error → Check domain name in config
     - **"scripts/deploy.sh: No such file or directory"** → The workflow has been updated to use `tar` for reliable file copying. If you still see this error, check the "Copy deployment files to server" step logs to verify files were copied correctly.

5. **Wait for green checkmark:**
   - ✅ All jobs should show green checkmark
   - Total time: ~10-15 minutes

✅ **Checkpoint:** GitHub Actions deployment completed successfully

### Step 7.3: Manual Deployment (Alternative if GitHub Actions fails)

**If GitHub Actions doesn't work, deploy manually:**

1. **SSH to your VPS:**
   ```bash
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
   cd /home/deploy/habit_reward_bot
   ```

2. **Clone repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
   ```

3. **Create .env file:**
   ```bash
   nano .env
   ```
   - Paste all your environment variables from `secrets.txt`
   - Save: Ctrl+O, ENTER
   - Exit: Ctrl+X

4. **Start deployment:**
   ```bash
   cd deployment
   chmod +x scripts/deploy.sh

   # Note: First deployment without GitHub Actions requires pulling images manually
   cd docker
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull postgres:16-alpine
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull certbot/certbot:latest

   # Build application image
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml build web

   # Start services
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

---

## Phase 8: SSL Certificate Setup (10 minutes)

### Step 8.1: Obtain SSL Certificate

1. **SSH to your VPS:**
   ```bash
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
   cd /home/deploy/habit_reward_bot
   ```

2. **Verify domain is pointing to VPS:**
   ```bash
   # Check if domain resolves to your IP:
   ping yourdomain.com
   # Should show your VPS IP
   # Press Ctrl+C to stop
   ```

3. **Stop nginx temporarily:**
   ```bash
   cd docker
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx
   ```

4. **Obtain certificate:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml run --rm \
     --entrypoint certbot \
     -p 80:80 \
     certbot certonly \
     --standalone \
     --email your-email@example.com \
     --agree-tos \
     --no-eff-email \
     -d yourdomain.com

   # Replace:
   # - your-email@example.com with your actual email
   # - yourdomain.com with your actual domain
   ```
   - **Note:** The `--entrypoint certbot` flag is required to override the default entrypoint that runs renewals
   - **Note:** The `-p 80:80` flag is required to expose port 80 so Let's Encrypt can validate your domain
   - This takes 30-60 seconds
   - You should see "Successfully received certificate"

5. **Start nginx:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml start nginx
   ```

6. **Verify HTTPS is working:**
   ```bash
   # On your local machine, open browser:
   # https://habitreward.duckdns.org

   # Should show secure lock icon
   # May show login page or 404 (this is normal)
   ```

The certificate is stored in the Docker volume and nginx will use it automatically. The certbot container is configured to auto-renew certificates (see the entrypoint in docker-compose.yml), so renewal should happen automatically.

Proceed to Phase 9: Verification & Testing to verify everything is working.

---

## Phase 9: Verification & Testing (10 minutes)

### Step 9.1: Check All Services

1. **SSH to VPS and check containers:**
   ```bash
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
   cd /home/deploy/habit_reward_bot/docker
   docker-compose --env-file ../.env  -f docker-compose.yml -f docker-compose.prod.yml ps
   ```
   - All containers should show "Up" status
   - If any show "Exit" or "Restarting", check logs:
     ```bash
     docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml logs <service-name>
     ```

2. **Check web container logs:**
   ```bash
   docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml logs web
   ```
   - Should see "Uvicorn running" or similar
   - No red ERROR messages

3. **Check database:**
   ```bash
   docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml exec db psql -U postgres -d habit_reward -c "SELECT COUNT(*) FROM users;"
   ```
   - Should return a count (even if 0)
   - No connection errors

### Step 9.2: Access Django Admin

1. **Open browser:**
   - Go to: `https://yourdomain.com/admin/`
   - Should see Django administration login page

2. **Login:**
   - Username: (from DJANGO_SUPERUSER_USERNAME secret)
   - Password: (from DJANGO_SUPERUSER_PASSWORD secret)
   - Click "Log in"

3. **Verify admin access:**
   - Should see Django admin dashboard
   - Can see Users, Habits, Rewards tables

✅ **Checkpoint:** Django admin accessible

### Step 9.3: Test Telegram Bot

1. **Check webhook status:**
   ```bash
   # On VPS:
   cd /home/deploy/habit_reward_bot/docker
   docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
   import asyncio
   from telegram import Bot

   async def check():
       bot = Bot('YOUR_BOT_TOKEN')
       info = await bot.get_webhook_info()
       print(f'Webhook URL: {info.url}')
       print(f'Pending updates: {info.pending_update_count}')

   asyncio.run(check())
   "
   # Replace YOUR_BOT_TOKEN with actual token
   ```
   - Should show your webhook URL
   - Pending updates should be 0 or low number

2. **Test bot in Telegram:**
   - Open Telegram app
   - Search for your bot
   - Send: `/start`
   - Bot should respond

3. **Test bot features:**
   - Try creating a habit
   - Try marking habit as done
   - Try viewing habits
   - All features should work

✅ **Checkpoint:** Bot is working!

---

## Phase 10: Post-Deployment Setup (10 minutes)

### Step 10.1: Set Up Automatic Backups

1. **Create backup script:**
   ```bash
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
   nano ~/backup_db.sh
   ```

2. **Add backup script:**
   ```bash
   #!/bin/bash
   BACKUP_DIR="/home/deploy/backups"
   DATE=$(date +%Y%m%d_%H%M%S)

   mkdir -p $BACKUP_DIR
   cd /home/deploy/habit_reward_bot/docker

   docker-compose --env-file ../.env  -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
     pg_dump -U postgres habit_reward > $BACKUP_DIR/backup_$DATE.sql

   # Keep only last 7 days
   find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete

   # Compress old backups
   find $BACKUP_DIR -name "backup_*.sql" -mtime +1 -exec gzip {} \;
   ```
   - Save: Ctrl+O, ENTER
   - Exit: Ctrl+X

3. **Make executable:**
   ```bash
   chmod +x ~/backup_db.sh
   ```

4. **Schedule daily backups:**
   ```bash
   crontab -e
   # Choose editor (if prompted): 1 (nano)

   # Add this line at the end:
   0 2 * * * /home/deploy/backup_db.sh

   # Save and exit
   ```
   - Backup will run daily at 2 AM

### Step 10.2: Monitor Resources

1. **Check disk space:**
   ```bash
   df -h
   ```
   - Should have plenty of free space

2. **Check memory:**
   ```bash
   free -h
   ```

3. **Set up monitoring (optional):**
   - Use services like:
     - UptimeRobot (free): https://uptimerobot.com/
     - Pingdom
     - StatusCake
   - Monitor: `https://yourdomain.com/admin/login/`
   - Get alerts if site goes down

✅ **Checkpoint:** Backups configured, monitoring set up

---

## Phase 11: Ongoing Maintenance

### Daily Tasks (1 minute)
- Check bot is responding
- Monitor any error messages from users

### Weekly Tasks (5 minutes)
```bash
# SSH to VPS
ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP

# Check disk space
df -h

# Check container health
cd /home/deploy/habit_reward_bot/docker
docker-compose --env-file ../.env -f docker-compose.yml -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose --env-file ../.env  -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100
```

### Monthly Tasks (10 minutes)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Check backups exist
ls -lh ~/backups/

# Test backup restore (on test system)
```

### Updates & Deployments
- Make code changes locally
- Test locally with: `./deployment/scripts/local-test.sh`
- Commit and push to GitHub
- GitHub Actions will auto-deploy
- Monitor deployment in Actions tab
- Test bot after deployment

---

## Troubleshooting Common Issues

### Issue: Can't connect to VPS via SSH
**Solution:**
```bash
# Check SSH key path:
ls -la ~/.ssh/do_habit_bot

# Try with verbose output:
ssh -v -i ~/.ssh/do_habit_bot deploy@YOUR_IP

# Check firewall on VPS allows port 22
```

### Issue: Domain not resolving
**Solution:**
```bash
# Check DNS propagation:
nslookup yourdomain.com

# Wait longer (DNS can take up to 48 hours)
# Use IP address temporarily for testing
```

### Issue: SSL certificate failed
**Solution:**
```bash
# Ensure domain points to VPS
# Ensure ports 80 and 443 are open
# Stop nginx before running certbot
# Check certbot logs:
docker-compose logs certbot
```

### Issue: Bot not responding
**Solution:**
```bash
# Check webhook:
docker-compose --env-file ../.env  -f docker-compose.yml -f docker-compose.prod.yml exec web python -c "
import asyncio
from telegram import Bot
async def check():
    bot = Bot('TOKEN')
    print(await bot.get_webhook_info())
asyncio.run(check())
"

# Check web logs:
docker-compose logs web

# Restart web container:
docker-compose restart web
```

### Issue: Database connection error
**Solution:**
```bash
# Check database is running:
docker-compose ps db

# Check database logs:
docker-compose logs db

# Restart database:
docker-compose restart db
docker-compose restart web
```

### Issue: Out of memory
**Solution:**
```bash
# Check memory usage:
free -h

# Upgrade droplet to 2GB RAM ($12/month)
# Or optimize containers (reduce resource limits)
```

### Issue: "scripts/deploy.sh: No such file or directory" in GitHub Actions
**Solution:**
This error occurs when deployment files aren't copied correctly to the server. The workflow has been updated to use `tar` for reliable copying.

1. **Check the "Copy deployment files to server" step logs:**
   - Look for the verification output showing directory contents
   - Verify that `scripts/`, `docker/`, and `nginx/` directories are listed

2. **If files are still missing, manually verify on server:**
   ```bash
   ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP
   cd /home/deploy/habit_reward_bot
   ls -la
   ls -la scripts/
   ```

3. **If scripts directory is missing, manually copy files:**
   ```bash
   # On your local machine:
   cd /path/to/your/project
   tar czf - -C deployment . | ssh -i ~/.ssh/do_habit_bot deploy@YOUR_IP "cd /home/deploy/habit_reward_bot && tar xzf -"
   ```

4. **Verify the workflow is using the latest version:**
   - Ensure you've pulled the latest changes from the repository
   - The workflow should use `tar` to copy files, not `scp -r deployment/*`

---

## Cost Summary

| Item | Cost | Frequency |
|------|------|-----------|
| Digital Ocean Droplet (1GB) | $6 | /month |
| Domain name | $10-15 | /year |
| SSL Certificate (Let's Encrypt) | FREE | - |
| **Total monthly cost** | **~$6-7** | |

**Ways to save:**
- Use Digital Ocean $200 free credit (60 days)
- Use free subdomain (duckdns.org) instead of buying domain
- Optimize resources to use smaller droplet

---

## Checklist - Did You Complete Everything?

- [ ] Digital Ocean account created
- [ ] Droplet created and running
- [ ] SSH connection working
- [ ] Docker and Docker Compose installed
- [ ] Deploy user created
- [ ] Firewall configured
- [ ] Domain configured (DNS)
- [ ] Telegram bot created
- [ ] GitHub secrets added (all 15-18)
- [ ] GitHub Actions enabled
- [ ] Code pushed to GitHub
- [ ] Deployment successful
- [ ] SSL certificate obtained
- [ ] HTTPS working
- [ ] Django admin accessible
- [ ] Bot responding to /start
- [ ] Backups configured
- [ ] Monitoring set up

If all checked ✅ - **Congratulations! Your bot is live! 🎉**

---

## Next Steps After Deployment

1. **Customize your bot:**
   - Add more habits
   - Configure rewards
   - Customize messages

2. **Promote your bot:**
   - Share with friends
   - Add to Telegram bot directory
   - Get feedback from users

3. **Scale as needed:**
   - Upgrade droplet if you get more users
   - Add caching (Redis)
   - Add CDN for static files

4. **Keep learning:**
   - Monitor logs
   - Understand the code
   - Make improvements

---

**Last Updated:** 2025-11-08
**Estimated Total Time:** 60-90 minutes
**Difficulty:** Intermediate

**Questions?** Check `/docs/DEPLOYMENT.md` for detailed troubleshooting.
