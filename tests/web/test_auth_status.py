"""Tests for bot login status polling endpoint."""

from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from django.test import Client

from src.core.models import LoginTokenIpBinding, User
from src.web.services.web_login_service import WL_FAILED_KEY, WL_PENDING_KEY
from tests.web.conftest import _call_async_mock

pytestmark = pytest.mark.django_db

# Default test token (40-50 chars, URL-safe base64)
_TEST_TOKEN = "abcdefghij0123456789_ABCDEFGHIJ0123456789_ab"
# Default test client IP (Django test Client sends 127.0.0.1)
_TEST_IP = "127.0.0.1"


def _create_ip_binding(token=_TEST_TOKEN, ip=_TEST_IP, minutes=5):
    """Create a LoginTokenIpBinding in the DB for test tokens."""
    return LoginTokenIpBinding.objects.create(
        token=token,
        ip_address=ip,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
    )


class TestAuthStatus:
    """Auth view tests for bot-based login — status polling subset."""

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("pending"))
    def test_bot_login_status_pending(self, mock_async):
        """Status endpoint returns pending."""
        _create_ip_binding()
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed"))
    def test_bot_login_status_confirmed(self, mock_async):
        """Status endpoint returns confirmed."""
        _create_ip_binding()
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("denied"))
    def test_bot_login_status_denied(self, mock_async):
        """Status endpoint returns denied."""
        _create_ip_binding()
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "denied"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("expired"))
    def test_bot_login_status_expired(self, mock_async):
        """Status endpoint returns expired."""
        _create_ip_binding()
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    def test_bot_login_status_rejects_post(self):
        """POST to status endpoint returns 405 (GET only)."""
        response = Client().post("/auth/bot-login/status/abcdefghij0123456789_ABCDEFGHIJ0123456789_ab/")
        assert response.status_code == 405

    def test_token_cached_for_status_polling(self):
        """Service caches every token (wl_pending:) so status returns 'pending'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService, _get_executor

        cache.clear()
        svc = WebLoginService()

        def _submit_inline(job, *args):
            future = Future()
            job(*args)
            future.set_result(None)
            return future

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
            patch.object(_get_executor(), "submit", side_effect=_submit_inline),
        ):
            from src.web.utils.sync import call_async
            result = call_async(svc.create_login_request("unknownuser"))
        token = result["token"]
        assert cache.get(f"{WL_PENDING_KEY}{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_falls_back_to_cache_on_db_lock(self, mock_sleep):
        """check_status returns 'pending' (not 500) when SQLite DB is locked."""
        from django.core.cache import cache
        from django.db import OperationalError
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "locked_token_abc"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch.object(
            svc.request_repo, "get_status_fields",
            side_effect=OperationalError("database table is locked"),
        ):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_uses_cache_and_skips_db_when_cache_hit(self, mock_sleep):
        """Status check should avoid DB reads when cache already has state."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "cache_hit_token"

        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with (
            patch.object(svc.request_repo, "get_status_fields") as mock_db,
            patch.object(cache, "get_many", wraps=cache.get_many) as mock_cache_get_many,
        ):
            status = call_async(svc.check_status(token))

        assert status == "pending"
        mock_cache_get_many.assert_called_once_with(
            [f"{WL_PENDING_KEY}{token}", f"{WL_FAILED_KEY}{token}"]
        )
        mock_db.assert_not_called()

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_applies_jitter(self, mock_sleep):
        """check_status calls asyncio.sleep with a random jitter value."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "jitter_test_token"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            call_async(svc.check_status(token))

        mock_sleep.assert_called_once()
        jitter = mock_sleep.call_args[0][0]
        assert 0.05 <= jitter <= 0.2

    def test_cache_ttl_derived_from_expires_at(self):
        """Cache timeout is derived from expires_at, not a separate constant."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService, _get_executor
        from src.web.utils.sync import call_async

        svc = WebLoginService()

        def _submit_inline(job, *args):
            future = Future()
            job(*args)
            future.set_result(None)
            return future

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
            patch.object(cache, "set", wraps=cache.set) as mock_set,
            patch.object(_get_executor(), "submit", side_effect=_submit_inline),
        ):
            result = call_async(svc.create_login_request("unknownuser"))

        token = result["token"]
        mock_set.assert_called_once()
        call_args = mock_set.call_args
        assert call_args[0][0] == f"{WL_PENDING_KEY}{token}"
        # timeout should be close to 300s but derived from expires_at
        timeout = call_args[1].get("timeout") or call_args[0][2]
        assert 295 <= timeout <= 300

    def test_rate_limited_view(self):
        """Rate limit handler returns 429 with JSON error."""
        import json as json_module

        from django_ratelimit.exceptions import Ratelimited

        from src.web.views.auth import rate_limited_view

        request = type("Request", (), {"META": {"REMOTE_ADDR": "1.2.3.4"}, "path": "/auth/bot-login/request/"})()
        response = rate_limited_view(request, exception=Ratelimited())
        assert response.status_code == 429
        assert json_module.loads(response.content)["error"] == "Too many requests. Please wait a moment and try again."


class TestStatusEndpointTokenValidation:
    """Verify that bot_login_status rejects malformed tokens."""

    def test_short_token_returns_400(self):
        """Token shorter than 40 chars is rejected."""
        response = Client().get("/auth/bot-login/status/short_token/")
        assert response.status_code == 400
        assert response.json()["error"] == "Invalid token format"

    def test_long_token_returns_400(self):
        """Token longer than 50 chars is rejected."""
        long_token = "a" * 51
        response = Client().get(f"/auth/bot-login/status/{long_token}/")
        assert response.status_code == 400
        assert response.json()["error"] == "Invalid token format"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("pending"))
    def test_valid_length_token_passes_validation(self, mock_async):
        """Token with valid length (40-50 chars) passes to the service."""
        valid_token = "a" * 43
        _create_ip_binding(token=valid_token)
        response = Client().get(f"/auth/bot-login/status/{valid_token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"


class TestConcurrentStatusChecks:
    """Verify concurrent status checks for the same token."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_concurrent_status_checks_return_consistent_results(self, mock_sleep):
        """Multiple status checks for the same token all return the same result."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_concurrent_status",
            telegram_id="770000003",
            name="Concurrent Status",
            language="en",
            timezone="UTC",
        )

        token = "concurrent_status_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        svc = WebLoginService()

        # Run multiple checks — all should return "pending"
        results = [call_async(svc.check_status(token)) for _ in range(5)]
        assert all(r == "pending" for r in results)
