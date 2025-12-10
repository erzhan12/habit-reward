"""ASGI application entry point.

This module provides the FastAPI application for the Habit Reward REST API.

The FastAPI app serves:
- REST API endpoints at /v1/*
- Health check at /health
- API documentation at /docs and /redoc

For Django admin access, run: python manage.py runserver

Run the API with: uvicorn asgi:app --reload --port 8000
"""

import os
import django

# Setup Django before importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.habit_reward_project.settings')
django.setup()

# Import the FastAPI application
from src.api.main import app
