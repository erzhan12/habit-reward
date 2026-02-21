"""Authentication URL patterns."""

from django.urls import path

from src.web.views.auth import login_page, logout_view, telegram_callback

urlpatterns = [
    path("login/", login_page, name="web_login"),
    path("telegram/callback/", telegram_callback, name="telegram_callback"),
    path("logout/", logout_view, name="web_logout"),
]
