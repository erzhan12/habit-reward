"""Tests for WebAuthMiddleware and unauthenticated redirect behavior."""

from unittest.mock import AsyncMock, patch

from django.test import Client


class TestWebAuthMiddleware:
    """Direct tests for WebAuthMiddleware exempt prefixes and auth enforcement."""

    EXEMPT_PATHS = [
        "/auth/login/",
        "/admin/",
        "/webhook/test/",
        "/api/health/",
    ]

    def test_unauthenticated_protected_path_redirects_to_login(self):
        response = Client().get("/")
        assert response.status_code == 302
        assert response.url == "/auth/login/"

    def test_authenticated_protected_path_is_allowed_through(self, auth_client):
        """Middleware passes authenticated requests; downstream view returns 200."""
        from unittest.mock import AsyncMock, patch

        with (
            patch("src.web.views.dashboard.habit_service") as mock_hs,
            patch("src.web.views.dashboard.habit_log_repository") as mock_repo,
            patch("src.web.views.dashboard.streak_service") as mock_ss,
        ):
            mock_hs.get_all_active_habits.return_value = []
            mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
            mock_ss.get_validated_streak_map.return_value = {}
            response = auth_client.get("/")
        assert response.status_code == 200

    def test_auth_prefix_exempt_unauthenticated(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200

    def test_admin_prefix_exempt_unauthenticated(self):
        """Admin path is handled by Django admin, not redirected to /auth/login/."""
        response = Client().get("/admin/")
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_webhook_prefix_exempt_unauthenticated(self):
        """/webhook/* paths pass through the middleware (may 404, not redirect)."""
        response = Client().get("/webhook/nonexistent/")
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_api_prefix_exempt_unauthenticated(self):
        """/api/* paths pass through the middleware (may 404, not redirect)."""
        response = Client().get("/api/nonexistent/")
        assert response.status_code != 302 or "/auth/login/" not in (response.url or "")

    def test_redirect_target_is_exact_login_url(self):
        """Redirect must point to exactly /auth/login/, not a partial match."""
        response = Client().get("/dashboard/")
        assert response.status_code == 302
        assert response.url == "/auth/login/"


class TestUnauthenticatedRedirect:
    """Unauthenticated users should be redirected to login by middleware."""

    def test_dashboard_redirects(self):
        response = Client().get("/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_streaks_redirects(self):
        response = Client().get("/streaks/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_history_redirects(self):
        response = Client().get("/history/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_rewards_redirects(self):
        response = Client().get("/rewards/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_login_page_accessible(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200
