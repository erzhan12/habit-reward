"""URL configuration for habit_reward_project."""

from django.contrib import admin
from django.urls import include, path
from src.bot.webhook_handler import telegram_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhook/telegram', telegram_webhook, name='telegram_webhook'),
    # Web interface
    path('auth/', include('src.web.urls_auth')),
    path('', include('src.web.urls')),
]

handler403 = 'src.web.views.auth.rate_limited_view'
