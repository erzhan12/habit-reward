"""Authentication URL patterns."""

from django.conf import settings
from django.urls import path

from src.web.views.auth import (
    login_page,
    logout_view,
    bot_login_request,
    bot_login_status,
    bot_login_complete,
)

urlpatterns = [
    path("login/", login_page, name="web_login"),
    path("bot-login/request/", bot_login_request, name="bot_login_request"),
    path("bot-login/status/<str:token>/", bot_login_status, name="bot_login_status"),
    path("bot-login/complete/", bot_login_complete, name="bot_login_complete"),
    path("logout/", logout_view, name="web_logout"),
]

if settings.DEBUG:
    from src.web.views.auth import dev_login

    urlpatterns.append(path("dev-login/", dev_login, name="dev_login"))
