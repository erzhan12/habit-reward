#!/bin/bash
set -e

echo "Starting Habit Reward Bot entrypoint script..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up and running!"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if credentials are provided and user doesn't exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Checking for Django superuser..."
  python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
END
fi

# Set Telegram webhook if URL is provided
if [ -n "$TELEGRAM_WEBHOOK_URL" ]; then
  echo "Setting Telegram webhook to: $TELEGRAM_WEBHOOK_URL"
  python -c "
import asyncio
from telegram import Bot

async def set_webhook():
    bot = Bot('$TELEGRAM_BOT_TOKEN')
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != '$TELEGRAM_WEBHOOK_URL':
        await bot.set_webhook(url='$TELEGRAM_WEBHOOK_URL')
        print(f'Webhook set to: $TELEGRAM_WEBHOOK_URL')
    else:
        print(f'Webhook already set to: {webhook_info.url}')

asyncio.run(set_webhook())
"
fi

echo "Entrypoint script completed successfully!"
echo "Starting application..."

# Execute the CMD passed to the container
exec "$@"
