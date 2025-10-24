"""
ASGI config for habit_reward_project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Note: Telegram bot handlers are initialized via CoreConfig.ready()
# in src/core/apps.py when Django starts. This ensures handlers are
# registered exactly once with proper event loop handling.

application = django_asgi_app
