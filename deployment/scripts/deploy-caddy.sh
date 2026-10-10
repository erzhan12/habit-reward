#!/bin/bash
# Manual deployment script for Caddy-based setup
# Use this if GitHub Actions deployment fails

set -e

echo "🚀 Deploying Habit Reward Bot (Caddy)..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env from .env.caddy.example"
    exit 1
fi

# Navigate to docker directory
cd "$(dirname "$0")/../docker"

echo "📦 Pulling latest images..."
docker-compose -f docker-compose.yml pull web

# No `down`: Caddy serves every *.habitreward.org site. `up` recreates only
# changed containers (normally web), and `caddy reload` applies Caddyfile edits.
echo "🚀 Updating containers..."
docker-compose -f docker-compose.yml up -d --pull never --remove-orphans

echo "🔄 Reloading Caddy config..."
# Retried: a freshly recreated Caddy may not have its admin API up yet.
for attempt in 1 2 3 4 5; do
    docker exec habit_reward_caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile && break
    if [ "$attempt" -eq 5 ]; then
        echo "❌ caddy reload failed 5 times"
        exit 1
    fi
    sleep 3
done

echo "⏳ Waiting for services to be ready..."
sleep 15

echo "📊 Container Status:"
docker-compose -f docker-compose.yml ps

echo ""
echo "📝 Recent Logs:"
echo "=== Web Container ==="
docker-compose -f docker-compose.yml logs --tail=20 web

echo ""
echo "=== Caddy Container ==="
docker-compose -f docker-compose.yml logs --tail=20 caddy

echo ""
echo "✅ Deployment complete!"
echo "🌐 Access your application at: https://habitreward.org"
echo "🔧 Admin panel: https://habitreward.org/admin/"
echo ""
echo "📋 Next steps:"
echo "1. Wait 1-2 minutes for Caddy to obtain SSL certificate"
echo "2. Test the admin panel"
echo "3. Test Telegram bot webhook"
echo ""
echo "🔍 Monitor logs with:"
echo "docker-compose -f docker-compose.yml logs -f"
