"""Tests for theme selection views."""

import json
from unittest.mock import AsyncMock, patch

from django.test import Client

from tests.web.conftest import INERTIA_HEADERS, _inertia_props


class TestThemePage:
    """Theme page view tests."""

    def test_theme_page_returns_200(self, auth_client):
        response = auth_client.get("/theme/", **INERTIA_HEADERS)
        assert response.status_code == 200

    def test_theme_page_includes_current_theme(self, auth_client, user):
        response = auth_client.get("/theme/", **INERTIA_HEADERS)
        component, props = _inertia_props(response)
        assert component == "Theme"
        assert props["currentTheme"] == user.theme

    def test_theme_page_unauthenticated_redirects(self):
        client = Client()
        response = client.get("/theme/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url


class TestSaveTheme:
    """Save theme view tests."""

    @patch("src.web.views.theme.user_repository")
    def test_save_valid_theme(self, mock_repo, auth_client, user):
        mock_repo.update = AsyncMock(return_value=user)
        response = auth_client.post(
            "/theme/save/",
            data=json.dumps({"theme": "neon_cyberpunk"}),
            content_type="application/json",
        )
        assert response.status_code == 302
        assert response.url == "/theme/"
        mock_repo.update.assert_called_once_with(user.id, {"theme": "neon_cyberpunk"})

    @patch("src.web.views.theme.user_repository")
    def test_save_invalid_theme_rejected(self, mock_repo, auth_client):
        response = auth_client.post(
            "/theme/save/",
            data=json.dumps({"theme": "does_not_exist"}),
            content_type="application/json",
        )
        assert response.status_code == 302
        assert response.url == "/theme/"
        mock_repo.update.assert_not_called()

    @patch("src.web.views.theme.user_repository")
    def test_save_empty_theme_rejected(self, mock_repo, auth_client):
        response = auth_client.post(
            "/theme/save/",
            data=json.dumps({"theme": ""}),
            content_type="application/json",
        )
        assert response.status_code == 302
        mock_repo.update.assert_not_called()

    @patch("src.web.views.theme.user_repository")
    def test_save_malformed_json_rejected(self, mock_repo, auth_client):
        response = auth_client.post(
            "/theme/save/",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 302
        mock_repo.update.assert_not_called()

    def test_save_theme_unauthenticated_redirects(self):
        client = Client()
        response = client.post(
            "/theme/save/",
            data=json.dumps({"theme": "neon_cyberpunk"}),
            content_type="application/json",
        )
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_save_theme_get_not_allowed(self, auth_client):
        response = auth_client.get("/theme/save/")
        assert response.status_code == 405
