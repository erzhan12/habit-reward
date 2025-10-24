"""Pytest configuration for Django integration."""

import os
import django
from django.conf import settings

# Configure Django settings before any tests run
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
    django.setup()
