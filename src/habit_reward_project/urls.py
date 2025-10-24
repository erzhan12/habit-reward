"""URL configuration for habit_reward_project."""

from django.contrib import admin
from django.urls import path
from src.bot.webhook_handler import telegram_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhook/telegram', telegram_webhook, name='telegram_webhook'),
]
