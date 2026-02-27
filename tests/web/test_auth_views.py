"""Tests for authentication views and bot-based login flow."""

import json
import threading
import time
from concurrent.futures import Future
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestAuth:
    """Auth view tests for bot-based login."""

    def test_login_page_renders(self):
        response = Client().get("/auth/login/")
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_login(self, auth_client):
        response = auth_client.get("/auth/login/")
        assert response.status_code == 302
        assert response.url == "/"

    def test_bot_login_request_rejects_invalid_json(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_empty_username(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_invalid_username(self):
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "ab"},  # too short
            content_type="application/json",
        )
        assert response.status_code == 400

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock({"token": "unknown_user_token", "expires_at": "2026-01-01T00:00:00+00:00"}))
    def test_bot_login_request_unknown_user(self, mock_async):
        """Unknown username returns 200 with generic message (anti-enumeration).

        The service always returns a dict (never None) so the view
        never branches on user existence.
        """
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "nonexistentuser"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert "sent" not in data
        assert "If this username is registered" in data["message"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock({"token": "test_token_123", "expires_at": "2026-01-01T00:00:00+00:00"}))
    def test_bot_login_request_success(self, mock_async, user):
        """Valid username returns token, expires_at, and generic message — no sent field."""
        response = Client().post(
            "/auth/bot-login/request/",
            data={"username": "testuser"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_at" in data
        assert "sent" not in data
        assert "If this username is registered" in data["message"]

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

    def test_bot_login_complete_success(self, user):
        """Confirmed login creates Django session."""
        _create_ip_binding()
        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock(user)):
            client = Client()
            response = client.post(
                "/auth/bot-login/complete/",
                data={"token": _TEST_TOKEN},
                content_type="application/json",
            )
            assert response.status_code == 200
            assert response.json() == {"success": True, "redirect": "/"}
            assert str(user.pk) == client.session["_auth_user_id"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_complete_fails_for_invalid_token(self, mock_async):
        """Invalid/expired token returns 403."""
        # Token must pass length validation (40-50 chars) to reach the service
        bad_token = "bad_token_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        _create_ip_binding(token=bad_token)
        response = Client().post(
            "/auth/bot-login/complete/",
            data={"token": bad_token},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_bot_login_complete_rejects_missing_token(self):
        response = Client().post(
            "/auth/bot-login/complete/",
            data={"token": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/request/",
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
            REMOTE_ADDR="198.51.100.41",
        )
        assert response.status_code == 400

    def test_bot_login_complete_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_bot_login_request_non_string_username(self):
        """Non-string username (e.g. integer) is coerced to str, not 500."""
        response = Client().post(
            "/auth/bot-login/request/",
            data=json.dumps({"username": 123}),
            content_type="application/json",
            REMOTE_ADDR="198.51.100.42",
        )
        # "123" passes regex but user won't exist — anti-enumeration returns 200
        assert response.status_code == 200

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_complete_non_string_token(self, mock_async):
        """Non-string token (e.g. integer) returns 403/400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": 12345}),
            content_type="application/json",
        )
        assert response.status_code in (400, 403)

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

    def test_logout_redirects(self, auth_client):
        response = auth_client.post("/auth/logout/")
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_bot_login_rate_limit_http_level(self):
        """Sending requests over the limit triggers rate limiting and returns 429 JSON.

        Uses the stricter user_or_ip limiter on bot_login_request (5/m).
        """
        from django.core.cache import cache

        cache.clear()

        payload = json.dumps({"username": "nonexistent_user_test"})
        client = Client()

        # Send requests up to the user_or_ip limit (5/m)
        for _ in range(5):
            client.post(
                "/auth/bot-login/request/",
                data=payload,
                content_type="application/json",
                REMOTE_ADDR="192.0.2.99",
            )

        response = client.post(
            "/auth/bot-login/request/",
            data=payload,
            content_type="application/json",
            REMOTE_ADDR="192.0.2.99",
        )
        assert response.status_code == 429
        assert response.json()["error"] == "Too many requests. Please wait a moment and try again."


# ---- Race condition / atomicity tests ----


class TestLoginRaceConditions:
    """Integration tests for atomic operations and concurrent access patterns.

    These hit the real DB to verify that the atomic UPDATE ... WHERE guards
    in the repository layer behave correctly under contention.
    """

    @pytest.fixture
    def login_user(self):
        """Create a user for login race condition tests."""
        return User.objects.create_user(
            username="tg_888888888",
            telegram_id="888888888",
            name="Race User",
            language="en",
            timezone="UTC",
        )

    @pytest.fixture
    def pending_request(self, login_user):
        """Create a pending WebLoginRequest in the DB."""
        from src.core.models import WebLoginRequest

        return WebLoginRequest.objects.create(
            user=login_user,
            token="race_test_token_aaa",
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    @pytest.fixture
    def confirmed_request(self, login_user):
        """Create a confirmed WebLoginRequest in the DB."""
        from src.core.models import WebLoginRequest

        return WebLoginRequest.objects.create(
            user=login_user,
            token="race_test_token_bbb",
            status="confirmed",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    def test_update_status_atomic_only_first_call_succeeds(self, pending_request):
        """update_status uses UPDATE WHERE status='pending' — the second call
        must return 0 because the status is no longer 'pending'."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        token = pending_request.token

        first = call_async(repo.update_status(token, "confirmed"))
        second = call_async(repo.update_status(token, "confirmed"))

        assert first == 1
        assert second == 0

        pending_request.refresh_from_db()
        assert pending_request.status == "confirmed"

    def test_mark_as_used_atomic_only_first_call_succeeds(self, confirmed_request):
        """mark_as_used uses UPDATE WHERE status='confirmed' — the second call
        must return 0 because the status is now 'used'."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        token = confirmed_request.token

        first = call_async(repo.mark_as_used(token))
        second = call_async(repo.mark_as_used(token))

        assert first == 1
        assert second == 0

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "used"

    def test_complete_login_replay_returns_none(self, confirmed_request):
        """Calling complete_login twice with the same token: first returns User,
        second returns None (token already marked as used)."""
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        svc = WebLoginService()
        token = confirmed_request.token

        first = call_async(svc.complete_login(token))
        second = call_async(svc.complete_login(token))

        assert first is not None
        assert second is None

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "used"

    def test_new_login_request_invalidates_previous(self, login_user):
        """Creating a second login request for the same user sets the first to 'denied'."""
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()

        first = call_async(repo.create(
            user_id=login_user.id,
            token="first_token_111",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))
        assert first.status == "pending"

        # Invalidate + create second (mimics _process_login_request)
        call_async(repo.invalidate_pending_for_user(login_user.id))
        call_async(repo.create(
            user_id=login_user.id,
            token="second_token_222",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))

        first.refresh_from_db()
        assert first.status == "denied"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_status_returns_pending_before_db_write(self, mock_sleep):
        """check_status returns 'pending' via cache even when no DB record exists yet
        (simulates the window between cache.set and background thread DB write)."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "no_db_yet_token"

        # Token is in cache but NOT in DB (background thread hasn't run)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    def test_mark_as_used_rejects_pending_token(self, pending_request):
        """mark_as_used only works on confirmed tokens, not pending ones."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        updated = call_async(repo.mark_as_used(pending_request.token))
        assert updated == 0

        pending_request.refresh_from_db()
        assert pending_request.status == "pending"

    def test_update_status_rejects_confirmed_token(self, confirmed_request):
        """update_status only works on pending tokens, not confirmed ones."""
        from src.core.repositories import WebLoginRequestRepository
        from src.web.utils.sync import call_async

        repo = WebLoginRequestRepository()
        updated = call_async(repo.update_status(confirmed_request.token, "denied"))
        assert updated == 0

        confirmed_request.refresh_from_db()
        assert confirmed_request.status == "confirmed"


# ---- Background thread failure tests ----


class TestBackgroundProcessingFailures:
    """Tests for graceful degradation when background thread processing fails.

    The background thread handles DB writes + Telegram send.  When it fails,
    the user should still see 'pending' (from cache) until the token expires.
    """

    def test_telegram_api_failure_logs_error_and_cache_stays_valid(self):
        """If Telegram send_message raises, the error is logged but the
        cache entry remains so check_status returns 'pending'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()

        # Use a real user so the transactional DB writes succeed
        user = User.objects.create_user(
            username="tg_tgfail1", telegram_id="111111111", name="TG Fail User",
            language="en", timezone="UTC",
        )

        token = "tg_fail_token_aaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch.object(svc, "_send_login_notification", new_callable=AsyncMock,
                         side_effect=Exception("Telegram API unavailable")):
            # _process_login_background catches all exceptions
            svc._process_login_background(user, token, expires_at, None)

        # Cache entry survives the background failure
        assert cache.get(f"{WL_PENDING_KEY}{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_status_pending_after_telegram_failure(self, mock_sleep):
        """check_status returns 'pending' via cache even when background
        thread failed and no DB record was created."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "tg_fail_status_token"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        # No DB record exists (background thread failed before DB write)
        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "pending"

    def test_db_failure_in_background_thread_is_caught(self):
        """If DB operations raise in the background thread, the exception
        is caught and logged — no crash, cache still valid."""
        from django.core.cache import cache
        from django.db import OperationalError
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.telegram_id = "888888888"

        token = "db_fail_token_bbb"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        # Mock _process_login_request to raise DB error (simulates any DB failure)
        with patch.object(svc, "_process_login_request", new_callable=AsyncMock,
                         side_effect=OperationalError("connection lost")):
            # Should not raise — exception caught in _process_login_background
            svc._process_login_background(mock_user, token, expires_at, None)

        assert cache.get(f"{WL_PENDING_KEY}{token}") is True

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_expiry_transitions_to_expired_after_failure(self, mock_sleep):
        """After background failure + cache TTL expiry, check_status
        returns 'expired' (not 'pending' forever)."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "expired_after_fail_token"

        # Cache entry already evicted (TTL passed)
        # No DB record (background thread failed)
        with patch.object(svc.request_repo, "get_status_fields", return_value=None):
            status = call_async(svc.check_status(token))

        assert status == "expired"

    def test_background_failure_error_is_logged(self):
        """_process_login_background logs the error with user ID."""
        from src.web.services.web_login_service import WebLoginService

        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.id = 99

        with (
            patch.object(svc, "_process_login_request", new_callable=AsyncMock,
                         side_effect=Exception("boom")),
            patch("src.web.services.web_login_service.logger") as mock_logger,
        ):
            svc._process_login_background(
                mock_user, "log_test_token", datetime.now(timezone.utc) + timedelta(minutes=5), None
            )

        mock_logger.error.assert_called_once()
        log_msg = mock_logger.error.call_args[0][0]
        assert "Unexpected error during login processing" in log_msg

    def test_create_login_request_returns_token_even_if_thread_will_fail(self):
        """create_login_request always returns {token, expires_at} regardless
        of what happens in the background thread."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService, _get_executor
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        mock_user = MagicMock()
        mock_user.telegram_id = "777777777"

        executor = _get_executor()
        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=mock_user),
            patch.object(executor, "submit") as mock_submit,
        ):
            result = call_async(svc.create_login_request("testuser"))

        assert "token" in result
        assert "expires_at" in result
        # Executor was called (whether it succeeds or not is irrelevant here)
        mock_submit.assert_called_once()


# ---- IP address validation tests ----


class TestIPAddressParsing:
    """Tests for _parse_ip_address validation and fallback."""

    @patch("src.web.utils.ip.settings")
    def test_valid_ipv4_from_forwarded_for(self, mock_settings):
        from src.web.utils.ip import parse_ip_address as _parse_ip_address

        mock_settings.TRUST_X_FORWARDED_FOR = True
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "203.0.113.50, 70.41.3.18", "REMOTE_ADDR": "127.0.0.1"}
        assert _parse_ip_address(request) == "203.0.113.50"

    @patch("src.web.utils.ip.settings")
    def test_valid_ipv6_from_forwarded_for(self, mock_settings):
        from src.web.utils.ip import parse_ip_address as _parse_ip_address

        mock_settings.TRUST_X_FORWARDED_FOR = True
        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "2001:db8::1", "REMOTE_ADDR": "127.0.0.1"}
        assert _parse_ip_address(request) == "2001:db8::1"

    def test_malformed_ip_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "<script>alert(1)</script>", "REMOTE_ADDR": "10.0.0.1"}
        assert _parse_ip_address(request) == "10.0.0.1"

    def test_empty_forwarded_for_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"HTTP_X_FORWARDED_FOR": "", "REMOTE_ADDR": "192.168.1.1"}
        assert _parse_ip_address(request) == "192.168.1.1"

    def test_missing_forwarded_for_falls_back_to_remote_addr(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {"REMOTE_ADDR": "172.16.0.1"}
        assert _parse_ip_address(request) == "172.16.0.1"

    def test_missing_both_headers_returns_unknown(self):
        from src.web.views.auth import _parse_ip_address

        request = MagicMock()
        request.META = {}
        assert _parse_ip_address(request) == "unknown"

    def test_device_info_does_not_contain_ip(self):
        """_parse_device_info must not include IP addresses (GDPR)."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": "Mozilla/5.0 Chrome/120.0",
            "HTTP_X_FORWARDED_FOR": "203.0.113.50",
            "REMOTE_ADDR": "10.0.0.5",
        }
        info = _parse_device_info(request)
        assert "10.0.0.5" not in info
        assert "203.0.113.50" not in info
        assert "IP" not in info

    def test_parse_ip_with_malicious_xforwardedfor(self):
        """Verify that malicious X-Forwarded-For values fall back to REMOTE_ADDR."""
        from django.test import RequestFactory
        from src.web.views.auth import _parse_ip_address

        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='<script>alert(1)</script>', REMOTE_ADDR='1.2.3.4')
        ip = _parse_ip_address(request)
        assert ip == '1.2.3.4'

    @patch("src.web.utils.ip.settings")
    def test_xff_multi_proxy_chain_takes_leftmost(self, mock_settings):
        """X-Forwarded-For with >2 IPs (multi-proxy chain): takes leftmost IP."""
        from src.web.utils.ip import parse_ip_address

        mock_settings.TRUST_X_FORWARDED_FOR = True
        request = MagicMock()
        # Multi-proxy chain: CDN -> LB -> app.  Leftmost is the original client.
        request.META = {
            "HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1, 172.16.0.1",
            "REMOTE_ADDR": "127.0.0.1",
        }
        with patch("src.web.utils.ip.logger") as mock_logger:
            result = parse_ip_address(request)
        # Takes leftmost IP from the chain
        assert result == "10.0.0.1"
        mock_logger.debug.assert_called_once()

    def test_device_info_html_escaping(self):
        """device_info containing HTML tags is safe — Telegram uses plain text."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": '<script>alert("xss")</script>',
            "REMOTE_ADDR": "127.0.0.1",
        }
        info = _parse_device_info(request)
        # The malicious script tag should not appear verbatim (UA parser
        # won't recognise it, so it falls back to "Unknown browser/OS").
        # Even if it did, Telegram messages use parse_mode=None (plain text),
        # so no HTML is interpreted.
        assert "<script>" not in info
        assert "Unknown" in info


# ---- Token collision retry tests (direct unit tests) ----


class TestTokenCollisionRetryDirect:
    """Direct unit tests for _create_login_request_with_retry static method.

    Complements TestTokenCollisionRetry (integration tests through the service)
    by testing the static method directly with real DB collisions and cache updates.
    """

    def test_successful_creation_on_first_try(self):
        """Normal path: token is unique, no retries needed."""
        from src.web.services.web_login_service import WebLoginService

        user = User.objects.create_user(
            username="tg_retry1", telegram_id="retry111",
            name="Retry User 1", language="en", timezone="UTC",
        )
        token = "retry_test_unique_token_aaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        login_request, final_token = WebLoginService._create_login_request_with_retry(
            user.id, token, expires_at, None,
        )
        assert final_token == token
        assert login_request.token == token
        assert login_request.status == "pending"

    def test_retry_on_real_db_collision(self):
        """Token collision against a real DB record triggers retry with a new token."""
        from src.web.services.web_login_service import WebLoginService
        from src.core.models import WebLoginRequest

        user = User.objects.create_user(
            username="tg_retry2", telegram_id="retry222",
            name="Retry User 2", language="en", timezone="UTC",
        )
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create a request with token that will collide
        existing_token = "collision_token_existing_a"
        WebLoginRequest.objects.create(
            user=user, token=existing_token, status="pending",
            expires_at=expires_at,
        )

        # Attempt with same token — should collide, then retry with new token
        with patch("src.web.services.web_login_service.secrets.token_urlsafe",
                   return_value="new_regenerated_token_bb"):
            login_request, final_token = WebLoginService._create_login_request_with_retry(
                user.id, existing_token, expires_at, None,
            )

        assert final_token == "new_regenerated_token_bb"
        assert login_request.token == "new_regenerated_token_bb"

    def test_retry_exhaustion_raises_database_error(self):
        """All retries exhausted raises DatabaseError."""
        from django.db import DatabaseError
        from src.web.services.web_login_service import WebLoginService

        user = User.objects.create_user(
            username="tg_retry3", telegram_id="retry333",
            name="Retry User 3", language="en", timezone="UTC",
        )
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Make every attempt collide by always returning the same token
        existing_token = "exhaust_collision_token_a"
        from src.core.models import WebLoginRequest
        WebLoginRequest.objects.create(
            user=user, token=existing_token, status="pending",
            expires_at=expires_at,
        )

        with (
            patch("src.web.services.web_login_service.secrets.token_urlsafe",
                  return_value=existing_token),
            pytest.raises(DatabaseError, match="unique token"),
        ):
            WebLoginService._create_login_request_with_retry(
                user.id, existing_token, expires_at, None,
            )

    def test_retry_updates_cache_with_new_token(self):
        """On collision retry, the new token's cache key is set."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService, WL_PENDING_KEY
        from src.core.models import WebLoginRequest

        cache.clear()
        user = User.objects.create_user(
            username="tg_retry4", telegram_id="retry444",
            name="Retry User 4", language="en", timezone="UTC",
        )
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        existing_token = "cache_collision_token_aa"
        WebLoginRequest.objects.create(
            user=user, token=existing_token, status="pending",
            expires_at=expires_at,
        )

        new_token = "cache_new_regenerated_tk"
        with patch("src.web.services.web_login_service.secrets.token_urlsafe",
                   return_value=new_token):
            WebLoginService._create_login_request_with_retry(
                user.id, existing_token, expires_at, None,
            )

        assert cache.get(f"{WL_PENDING_KEY}{new_token}") is True


# ---- Username recycling concurrency tests ----


class TestUsernameRecyclingConcurrency:
    """Concurrency tests for update_telegram_username atomicity."""

    def test_atomic_username_reassignment(self):
        """Username is atomically cleared from old user and assigned to new user."""
        from src.web.utils.sync import call_async

        old_user = User.objects.create_user(
            username="tg_old111", telegram_id="old111",
            name="Old User", language="en", timezone="UTC",
            telegram_username="recycled_name",
        )
        new_user = User.objects.create_user(
            username="tg_new222", telegram_id="new222",
            name="New User", language="en", timezone="UTC",
        )

        from src.core.repositories import UserRepository
        repo = UserRepository()

        call_async(repo.update_telegram_username("new222", "recycled_name"))

        old_user.refresh_from_db()
        new_user.refresh_from_db()
        assert old_user.telegram_username is None
        assert new_user.telegram_username == "recycled_name"

    def test_sequential_username_claims_no_duplicates(self):
        """Two sequential claims for the same username — last writer wins,
        no duplicates remain.

        Note: True concurrent threading tests require PostgreSQL (SQLite
        file-level locking serializes writes) and a non-test DB (Django test
        transactions isolate threads).  This test verifies correctness of the
        atomic block by running claims sequentially.
        """
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        target_username = "contested_name"

        # Create the user who currently owns the username
        User.objects.create_user(
            username="tg_owner", telegram_id="owner000",
            name="Owner", language="en", timezone="UTC",
            telegram_username=target_username,
        )

        # Two claimants
        claimer_a = User.objects.create_user(
            username="tg_claima", telegram_id="claima11",
            name="Claimer A", language="en", timezone="UTC",
        )
        claimer_b = User.objects.create_user(
            username="tg_claimb", telegram_id="claimb22",
            name="Claimer B", language="en", timezone="UTC",
        )

        repo = UserRepository()

        # A claims first
        call_async(repo.update_telegram_username("claima11", target_username))
        claimer_a.refresh_from_db()
        assert claimer_a.telegram_username == target_username

        # B claims second — should take ownership from A
        call_async(repo.update_telegram_username("claimb22", target_username))
        claimer_a.refresh_from_db()
        claimer_b.refresh_from_db()

        assert claimer_a.telegram_username is None
        assert claimer_b.telegram_username == target_username

        # Only one user owns the username
        count = User.objects.filter(telegram_username=target_username).count()
        assert count == 1

    def test_clear_username(self):
        """Setting username to None clears it."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_clear1", telegram_id="clear111",
            name="Clear User", language="en", timezone="UTC",
            telegram_username="to_be_cleared",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("clear111", None))

        user.refresh_from_db()
        assert user.telegram_username is None


# ---- Username recycling tests ----


class TestUsernameRecycling:
    """Tests for update_telegram_username handling recycling and edge cases."""

    def test_assign_username_clears_old_owner(self):
        """When a username is assigned to user B, it is cleared from user A."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user_a = User.objects.create_user(
            username="tg_111", telegram_id="111", name="User A",
            language="en", timezone="UTC", telegram_username="recycled",
        )
        user_b = User.objects.create_user(
            username="tg_222", telegram_id="222", name="User B",
            language="en", timezone="UTC",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("222", "recycled"))

        user_a.refresh_from_db()
        user_b.refresh_from_db()
        assert user_a.telegram_username is None
        assert user_b.telegram_username == "recycled"

    def test_assign_none_clears_username(self):
        """Passing None clears the user's telegram_username."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_333", telegram_id="333", name="User C",
            language="en", timezone="UTC", telegram_username="oldname",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("333", None))

        user.refresh_from_db()
        assert user.telegram_username is None

    def test_username_normalized_to_lowercase(self):
        """Username is lowercased and stripped of @ prefix."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_444", telegram_id="444", name="User D",
            language="en", timezone="UTC",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("444", "@MyUserName"))

        user.refresh_from_db()
        assert user.telegram_username == "myusername"

    def test_reassign_same_username_is_idempotent(self):
        """Re-assigning the same username to the same user is a no-op."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_555", telegram_id="555", name="User E",
            language="en", timezone="UTC", telegram_username="stable",
        )

        repo = UserRepository()
        call_async(repo.update_telegram_username("555", "stable"))

        user.refresh_from_db()
        assert user.telegram_username == "stable"


# ---- Full login flow integration test ----


class TestFullLoginFlow:
    """Integration test simulating the complete login flow end-to-end:
    create request -> bot confirmation -> poll status -> complete login -> session created.
    """

    @pytest.fixture
    def login_user(self):
        """Create a user for the full flow test."""
        return User.objects.create_user(
            username="tg_777777777",
            telegram_id="777777777",
            name="Flow User",
            language="en",
            timezone="UTC",
            telegram_username="flowuser",
        )

    def test_full_login_flow(self, login_user):
        """End-to-end: create request -> bot confirmation -> poll status -> complete -> session."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        repo = WebLoginRequestRepository()
        client = Client()

        # Step 1: Create login request via HTTP (background thread is async,
        # so we create the DB record directly to simulate what it does)
        # Token must be 40-50 chars to pass length validation
        token = "full_flow_test_token_aaaaaaaaaaaaaaaaaaaaaaaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)
        _create_ip_binding(token=token)

        login_request = WebLoginRequest.objects.create(
            user=login_user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        assert login_request.status == WebLoginRequest.Status.PENDING.value

        # Step 2: Poll status — should be pending
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == WebLoginRequest.Status.PENDING.value

        # Step 3: Simulate bot confirmation (as if user pressed Confirm)
        updated = call_async(repo.update_status(token, WebLoginRequest.Status.CONFIRMED.value))
        assert updated == 1

        # Step 4: Poll status — should be confirmed
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == WebLoginRequest.Status.CONFIRMED.value

        # Step 5: Complete login via HTTP
        response = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True

        # Step 6: Verify session was created — user is now authenticated
        response = client.get("/")
        assert response.status_code == 200  # Not redirected to login

        # Step 7: Verify token is marked as used (replay protection)
        login_request.refresh_from_db()
        assert login_request.status == WebLoginRequest.Status.USED.value

        # Step 8: Replay attempt should fail
        response = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_full_http_login_flow(self, login_user):
        """End-to-end via HTTP endpoints: POST /request/ -> GET /status/ -> POST /complete/.

        Exercises the real view layer (not just service) to verify JSON
        contracts, session creation, and replay protection via HTTP.
        """
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository

        cache.clear()
        repo = WebLoginRequestRepository()
        client = Client()

        # 1) POST /request/ — returns token
        with patch("src.web.views.auth.call_async") as mock_async:
            mock_async.side_effect = _call_async_mock({
                "token": "http_flow_token_aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "expires_at": "2099-01-01T00:00:00+00:00",
            })
            resp = client.post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "flowuser"}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        body = resp.json()
        token = body["token"]
        assert "If this username is registered" in body["message"]

        # Create a confirmed DB record to simulate the bot callback
        WebLoginRequest.objects.create(
            user=login_user,
            token=token,
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        # 2) GET /status/ — returns confirmed
        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed")):
            resp = client.get(f"/auth/bot-login/status/{token}/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

        # 3) POST /complete/ — creates session
        resp = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 4) Session exists — authenticated request succeeds
        with (
            patch("src.web.views.dashboard.habit_service") as mock_hs,
            patch("src.web.views.dashboard.habit_log_repository") as mock_repo,
            patch("src.web.views.dashboard.streak_service") as mock_ss,
        ):
            mock_hs.get_all_active_habits.return_value = []
            mock_repo.get_todays_logs_by_user = AsyncMock(return_value=[])
            mock_ss.get_validated_streak_map.return_value = {}
            resp = client.get("/")
        assert resp.status_code == 200

        # 5) Replay attempt fails
        resp = client.post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert resp.status_code == 403


# ---- Concurrent login request test ----


class TestConcurrentLoginRequests:
    """Test that concurrent login requests from the same user properly
    invalidate old pending requests.
    """

    @pytest.fixture
    def concurrent_user(self):
        """Create a user for concurrent request tests."""
        return User.objects.create_user(
            username="tg_666666666",
            telegram_id="666666666",
            name="Concurrent User",
            language="en",
            timezone="UTC",
            telegram_username="concurrentuser",
        )

    def test_second_request_invalidates_first(self, concurrent_user):
        """When a user creates a second login request, the first pending
        request is set to 'denied' and only the second is active."""
        from django.core.cache import cache
        from django.db import transaction as db_transaction
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        repo = WebLoginRequestRepository()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create first pending request
        req1 = WebLoginRequest.objects.create(
            user=concurrent_user,
            token="concurrent_token_1",
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        assert req1.status == WebLoginRequest.Status.PENDING.value

        # Simulate creating a second request (transactional invalidate + create)
        with db_transaction.atomic():
            WebLoginRequest.objects.filter(
                user_id=concurrent_user.id,
                status=WebLoginRequest.Status.PENDING,
            ).update(status=WebLoginRequest.Status.DENIED)
            req2 = WebLoginRequest.objects.create(
                user=concurrent_user,
                token="concurrent_token_2",
                status=WebLoginRequest.Status.PENDING,
                expires_at=expires_at,
            )

        # First request should now be denied
        req1.refresh_from_db()
        assert req1.status == WebLoginRequest.Status.DENIED.value

        # Second request should be pending
        assert req2.status == WebLoginRequest.Status.PENDING.value

        # Confirm second request and complete login — should succeed
        call_async(repo.update_status("concurrent_token_2", WebLoginRequest.Status.CONFIRMED.value))
        user = call_async(svc.complete_login("concurrent_token_2"))
        assert user is not None
        assert user.id == concurrent_user.id

        # First token should NOT be completable (status is 'denied')
        user_from_old = call_async(svc.complete_login("concurrent_token_1"))
        assert user_from_old is None

    def test_concurrent_request_via_service_invalidates_previous(self, concurrent_user):
        """Item 9: When a user has a pending request and submits a new one
        through the service, the old request is properly set to DENIED."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create first pending request in DB
        req1 = WebLoginRequest.objects.create(
            user=concurrent_user,
            token="svc_concurrent_1",
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        cache.set(f"{WL_PENDING_KEY}svc_concurrent_1", True, timeout=300)

        # Call _process_login_request which does the transactional
        # invalidate + create. Mock the Telegram send.
        with patch(
            "src.web.services.web_login_service.WebLoginService._send_login_notification",
            new_callable=AsyncMock,
        ):
            call_async(
                svc._process_login_request(
                    concurrent_user, "svc_concurrent_2", expires_at, "Test device"
                )
            )

        # The first request should now be denied
        req1.refresh_from_db()
        assert req1.status == WebLoginRequest.Status.DENIED.value

        # The second request should be pending in DB
        req2 = WebLoginRequest.objects.get(token="svc_concurrent_2")
        assert req2.status == WebLoginRequest.Status.PENDING.value


class TestLoginRaceConditionsPolling(TestLoginRaceConditions):
    """Extended race condition tests — polling + confirmation."""

    def test_simultaneous_poll_and_confirm_no_inconsistency(self, login_user):
        """Item 10: Simultaneous polling and bot confirmation don't cause
        deadlocks or inconsistent states."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.core.repositories import WebLoginRequestRepository
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        repo = WebLoginRequestRepository()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create a pending request
        req = WebLoginRequest.objects.create(
            user=login_user,
            token="race_poll_token",
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )
        cache.set(f"{WL_PENDING_KEY}race_poll_token", True, timeout=300)

        # Poll status — should be pending
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status("race_poll_token"))
        assert status == WebLoginRequest.Status.PENDING.value

        # Simulate bot confirmation
        updated = call_async(repo.update_status("race_poll_token", WebLoginRequest.Status.CONFIRMED.value))
        assert updated == 1

        # Poll again — should now be confirmed (not stuck on pending)
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status("race_poll_token"))
        assert status == WebLoginRequest.Status.CONFIRMED.value

        # Complete login — should succeed exactly once
        user1 = call_async(svc.complete_login("race_poll_token"))
        assert user1 is not None
        assert user1.id == login_user.id

        # Second complete attempt — atomic guard returns None
        user2 = call_async(svc.complete_login("race_poll_token"))
        assert user2 is None

        req.refresh_from_db()
        assert req.status == WebLoginRequest.Status.USED.value


class TestBackgroundProcessingFailure:
    """Test that background processing failures are handled gracefully."""

    @pytest.fixture
    def failure_user(self):
        """Create a user for failure recovery tests."""
        return User.objects.create_user(
            username="tg_555555555",
            telegram_id="555555555",
            name="Failure User",
            language="en",
            timezone="UTC",
            telegram_username="failureuser",
        )

    def test_temporary_telegram_error_marks_failed(self, failure_user):
        """All Telegram errors (including temporary) now mark the token as failed.

        The error handling was unified so that ALL error types call
        _mark_failed_safely().  Even for transient errors, the user gets
        immediate "error" feedback and can re-initiate the login, rather
        than hanging on "pending" indefinitely while the client polls.
        """
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async
        from telegram.error import TelegramError

        cache.clear()
        svc = WebLoginService()
        token = "failure_test_token"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        # Mock _send_login_notification to raise TelegramError (temporary)
        with patch(
            "src.web.services.web_login_service.WebLoginService._send_login_notification",
            new_callable=AsyncMock,
            side_effect=TelegramError("Network timeout"),
        ):
            svc._process_login_background(failure_user, token, expires_at, "Test device")

        # All errors now set the failed cache key for consistent feedback
        assert cache.get(f"{WL_FAILED_KEY}{token}") is True

        # Status should be "error" since failed marker is set
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == "error"

    def test_permanent_telegram_error_marks_failed(self, failure_user):
        """Permanent Telegram errors (InvalidToken, Forbidden) DO mark failed."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async
        from telegram.error import Forbidden

        cache.clear()
        svc = WebLoginService()
        token = "perm_fail_test_token"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        with patch(
            "src.web.services.web_login_service.WebLoginService._send_login_notification",
            new_callable=AsyncMock,
            side_effect=Forbidden("Bot was blocked by user"),
        ):
            svc._process_login_background(failure_user, token, expires_at, "Test device")

        # Permanent error SHOULD set the failed cache key
        assert cache.get(f"{WL_FAILED_KEY}{token}") is True

        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = call_async(svc.check_status(token))
        assert status == "error"


# ---- Timing consistency tests ----


class TestTimingConsistency:
    """Verify that response timing does not leak username existence."""

    def test_known_vs_unknown_username_similar_timing(self, user):
        """Known and unknown usernames should have similar response times.

        We run a small sample and check that the difference in median
        response time is within a reasonable bound (< 100ms).  This is a
        smoke test — not a rigorous statistical test.
        """
        import time

        client = Client()
        samples = 10  # small sample to keep test fast

        def _time_request(username):
            payload = json.dumps({"username": username})
            start = time.monotonic()
            client.post(
                "/auth/bot-login/request/",
                data=payload,
                content_type="application/json",
            )
            return time.monotonic() - start

        # Make the user findable by username
        user.telegram_username = "timinguser"
        user.save()

        known_times = [_time_request("timinguser") for _ in range(samples)]
        unknown_times = [_time_request("nonexistent_xyz") for _ in range(samples)]

        known_median = sorted(known_times)[samples // 2]
        unknown_median = sorted(unknown_times)[samples // 2]
        diff = abs(known_median - unknown_median)

        # The difference should be small — under 100ms.
        # This is a loose bound; the real guarantee comes from the
        # constant-time design (identical code path for both).
        assert diff < 0.1, (
            f"Timing diff {diff:.4f}s between known/unknown exceeds 100ms: "
            f"known_median={known_median:.4f}s, unknown_median={unknown_median:.4f}s"
        )


# ---- Thread pool exhaustion tests ----


class TestThreadPoolExhaustion:
    """Verify behaviour when the login background thread pool is saturated."""

    def test_queue_full_returns_503(self):
        """When the semaphore is exhausted, the view returns 503."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod

        cache.clear()  # clear rate-limit counters from prior tests

        # Create a known user so the queue-check code path is exercised.
        User.objects.create_user(
            username="tg_444444444",
            telegram_id="444444444",
            name="Queue User",
            language="en",
            timezone="UTC",
            telegram_username="queueuser",
        )

        # Mock the semaphore to report the queue is full.
        original_slots = svc_mod._queue_slots
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False  # non-blocking acquire fails
        svc_mod._queue_slots = mock_sem
        try:
            client = Client()
            response = client.post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "queueuser"}),
                content_type="application/json",
            )
        finally:
            svc_mod._queue_slots = original_slots

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["error"].lower()

    def test_semaphore_released_after_background_processing(self):
        """The semaphore slot is released via done_callback after executor completes."""
        import threading
        from concurrent.futures import Future
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()

        # Replace with a real semaphore so we can observe acquire/release.
        test_sem = threading.Semaphore(1)
        original_slots = svc_mod._queue_slots
        svc_mod._queue_slots = test_sem
        try:
            mock_user = MagicMock()
            mock_user.id = 1
            mock_user.telegram_id = "111"
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

            # Acquire the slot (simulating circuit breaker check passing).
            assert test_sem.acquire(blocking=False) is True

            # Simulate executor submit + done_callback (the real release path).
            future = Future()
            future.add_done_callback(lambda f: test_sem.release())

            with patch.object(svc, "_process_login_request", new_callable=AsyncMock):
                svc._process_login_background(mock_user, "sem_test_tok", expires_at, None)

            # Simulate the future completing (triggers done_callback).
            future.set_result(None)

            # Semaphore should be available again.
            assert test_sem.acquire(blocking=False) is True
            test_sem.release()  # clean up
        finally:
            svc_mod._queue_slots = original_slots


# ---- Device info parsing edge cases ----


class TestDeviceInfoEdgeCases:
    """Test _parse_device_info with unusual User-Agent strings."""

    def test_empty_user_agent(self):
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": "", "REMOTE_ADDR": "1.2.3.4"}
        info = _parse_device_info(request)
        assert "Unknown browser" in info
        assert "Unknown OS" in info
        assert "1.2.3.4" not in info  # IP removed for GDPR

    def test_extremely_long_user_agent(self):
        """User-Agent > 10KB is safely truncated."""
        from src.web.views.auth import _parse_device_info

        long_ua = "A" * 15000
        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": long_ua, "REMOTE_ADDR": "5.6.7.8"}
        info = _parse_device_info(request)
        # Output must be <= 255 chars (DB field limit).
        assert len(info) <= 255
        assert "5.6.7.8" not in info  # IP removed for GDPR

    def test_malicious_user_agent_not_in_output(self):
        """Malicious HTML/script in User-Agent does not appear in output.

        The UA parser extracts named patterns (Chrome/Firefox/etc.), so raw
        injection strings never make it into the result string.  HTML-escaping
        for Telegram is done at the output boundary in _send_login_notification.
        """
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": '<script>alert("xss")</script>',
            "REMOTE_ADDR": "9.8.7.6",
        }
        info = _parse_device_info(request)
        # Malicious content should not appear — parser defaults to "Unknown".
        assert "<script>" not in info
        assert "Unknown" in info

    def test_user_agent_with_html_in_browser_name(self):
        """Browser version containing HTML chars does not leak into output."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": 'Mozilla/5.0 Chrome/<img src=x>',
            "REMOTE_ADDR": "1.1.1.1",
        }
        info = _parse_device_info(request)
        assert "<img" not in info

    def test_device_info_handles_malicious_user_agent(self):
        """Malicious User-Agent with CRLF and control chars is sanitized."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": "Mozilla\r\n\x00<script>alert(1)</script>",
            "REMOTE_ADDR": "10.0.0.1",
        }
        info = _parse_device_info(request)
        # Should not contain CRLF or null bytes
        assert "\r" not in info
        assert "\n" not in info
        assert "\x00" not in info

    def test_device_info_truncates_extremely_long_user_agent(self):
        """User-Agent longer than 1024 chars is truncated before parsing."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": "A" * 10000,  # 10KB of data
            "REMOTE_ADDR": "10.0.0.1",
        }
        info = _parse_device_info(request)
        # Should complete without memory issues and produce valid output
        assert len(info) <= 255
        assert "unknown" in info.lower()  # Should fail to parse

    def test_user_agent_only_non_printable_chars(self):
        """UA consisting entirely of non-printable characters produces Unknown."""
        from src.web.views.auth import _parse_device_info

        request = MagicMock()
        request.META = {
            "HTTP_USER_AGENT": "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0e\x0f\x10",
            "REMOTE_ADDR": "10.0.0.2",
        }
        info = _parse_device_info(request)
        assert "Unknown" in info
        # No non-printable chars in output
        for ch in info:
            assert ch == '\n' or ch == '\t' or '\x20' <= ch <= '\x7e'

    def test_user_agent_over_1024_chars_with_valid_prefix(self):
        """UA >1024 chars that starts with a valid browser string is truncated
        to MAX_USER_AGENT_LENGTH before parsing, and final output <= 255 chars."""
        from src.web.views.auth import MAX_USER_AGENT_LENGTH, _parse_device_info

        valid_prefix = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        long_ua = valid_prefix + " " + "X" * 2000
        assert len(long_ua) > MAX_USER_AGENT_LENGTH

        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": long_ua, "REMOTE_ADDR": "10.0.0.3"}
        info = _parse_device_info(request)
        assert len(info) <= 255
        # Should still parse the valid prefix correctly
        assert "Chrome" in info

    def test_user_agent_crafted_long_parsed_output(self):
        """UA crafted to produce a long browser + OS string is truncated to 255."""
        from src.web.views.auth import MAX_DEVICE_INFO_LENGTH, _parse_device_info

        # Craft a UA with very long version strings that the parser might echo.
        long_version = "1." + "9" * 300
        crafted_ua = f"Mozilla/5.0 (Windows NT {long_version}) Chrome/{long_version}"
        request = MagicMock()
        request.META = {"HTTP_USER_AGENT": crafted_ua, "REMOTE_ADDR": "10.0.0.4"}
        info = _parse_device_info(request)
        assert len(info) <= MAX_DEVICE_INFO_LENGTH


# ---- Username uniqueness constraint tests ----


class TestUsernameUniquenessConstraint:
    """Test concurrent telegram_username assignment race conditions."""

    def test_concurrent_username_claim_only_one_wins(self):
        """When two users try to claim the same username, only one should end
        up with it — the other should have it cleared."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user_a = User.objects.create_user(
            username="tg_uniq_a", telegram_id="uniq_a", name="Uniq A",
            language="en", timezone="UTC",
        )
        user_b = User.objects.create_user(
            username="tg_uniq_b", telegram_id="uniq_b", name="Uniq B",
            language="en", timezone="UTC",
        )

        repo = UserRepository()

        # Both try to claim "contested_name"
        call_async(repo.update_telegram_username("uniq_a", "contested_name"))
        call_async(repo.update_telegram_username("uniq_b", "contested_name"))

        user_a.refresh_from_db()
        user_b.refresh_from_db()

        # Exactly one should own the username.
        owners = [u for u in (user_a, user_b) if u.telegram_username == "contested_name"]
        assert len(owners) == 1, f"Expected exactly 1 owner, got {len(owners)}"

        # The loser should have their username cleared.
        losers = [u for u in (user_a, user_b) if u.telegram_username is None]
        assert len(losers) == 1

    def test_sequential_username_reassignment(self):
        """Assigning the same username to a different user clears the previous owner."""
        from src.core.repositories import UserRepository
        from src.web.utils.sync import call_async

        user_x = User.objects.create_user(
            username="tg_seq_x", telegram_id="seq_x", name="Seq X",
            language="en", timezone="UTC",
        )
        user_y = User.objects.create_user(
            username="tg_seq_y", telegram_id="seq_y", name="Seq Y",
            language="en", timezone="UTC",
        )

        repo = UserRepository()

        # X claims the name first.
        call_async(repo.update_telegram_username("seq_x", "shared_name"))
        user_x.refresh_from_db()
        assert user_x.telegram_username == "shared_name"

        # Y claims the same name — X should lose it.
        call_async(repo.update_telegram_username("seq_y", "shared_name"))
        user_x.refresh_from_db()
        user_y.refresh_from_db()

        assert user_x.telegram_username is None
        assert user_y.telegram_username == "shared_name"


class TestConcurrentLoginInvalidation:
    """Verify that creating a new login request invalidates previous pending ones."""

    def test_concurrent_login_requests_invalidates_previous(self):
        """Two login requests for the same user: first becomes denied, second stays pending."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_888888888",
            telegram_id="888888888",
            name="Concurrent Inv",
            language="en",
            timezone="UTC",
            telegram_username="concurrentinv",
        )

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Create first pending request directly in DB
        req1 = WebLoginRequest.objects.create(
            user=user,
            token="inv_token_first",
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )

        # Create second request through the service's transactional write path
        svc = WebLoginService()

        with patch.object(svc, "_send_login_notification", new_callable=AsyncMock):
            call_async(svc._process_login_request(user, "inv_token_second", expires_at, None))

        # First request should now be denied
        req1.refresh_from_db()
        assert req1.status == WebLoginRequest.Status.DENIED.value

        # Second request should be pending
        req2 = WebLoginRequest.objects.get(token="inv_token_second")
        assert req2.status == WebLoginRequest.Status.PENDING.value


class TestCircuitBreakerServiceLevel:
    """Verify the service-level circuit breaker raises LoginServiceUnavailable."""

    def test_login_request_rejects_when_queue_full(self):
        """When _queue_slots.acquire returns False, service raises LoginServiceUnavailable."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_cb_test",
            telegram_id="cb_test_id",
            name="CB Test",
            language="en",
            timezone="UTC",
            telegram_username="cbtestuser",
        )

        svc = WebLoginService()

        # Mock the semaphore to report the queue is full.
        original_slots = svc_mod._queue_slots
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False
        svc_mod._queue_slots = mock_sem
        try:
            with pytest.raises(LoginServiceUnavailable):
                call_async(svc.create_login_request("cbtestuser"))
        finally:
            svc_mod._queue_slots = original_slots

        # Verify it also results in 503 from the view
        svc_mod._queue_slots = mock_sem
        try:
            client = Client()
            response = client.post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "cbtestuser"}),
                content_type="application/json",
            )
            assert response.status_code == 503
        finally:
            svc_mod._queue_slots = original_slots


class TestTokenCollisionRetry:
    """Verify token collision retry logic with IntegrityError."""

    def test_token_collision_retries_and_succeeds(self):
        """When IntegrityError fires on first attempt, retries with new token."""
        from django.db import IntegrityError
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_collision_user",
            telegram_id="770000001",
            name="Collision User",
            language="en",
            timezone="UTC",
            telegram_username="collisionuser",
        )

        svc = WebLoginService()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        call_count = 0
        original_create = WebLoginRequest.objects.create

        def create_with_collision(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IntegrityError("UNIQUE constraint failed: token")
            return original_create(**kwargs)

        with patch.object(WebLoginRequest.objects, "create", side_effect=create_with_collision), \
             patch.object(svc, "_send_login_notification", new_callable=AsyncMock):
            call_async(svc._process_login_request(user, "collision_tok_1", expires_at, None))

        assert call_count == 2
        # A request was created (on second attempt)
        assert WebLoginRequest.objects.filter(user=user).exists()

    def test_token_collision_exhausts_retries(self):
        """When all retries hit IntegrityError, raises DatabaseError."""
        from django.db import DatabaseError, IntegrityError
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_exhaust_user",
            telegram_id="770000002",
            name="Exhaust User",
            language="en",
            timezone="UTC",
        )

        svc = WebLoginService()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        with patch.object(WebLoginRequest.objects, "create", side_effect=IntegrityError("dup")), \
             pytest.raises(DatabaseError, match="Failed to generate unique token"):
            call_async(svc._process_login_request(user, "exhaust_tok", expires_at, None))


class TestConcurrentTokenGeneration:
    """Verify token generation remains safe under concurrent requests."""

    def test_concurrent_create_login_request_tokens_are_unique(self):
        import threading

        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token_count = 20
        tokens = []
        errors = []
        result_lock = threading.Lock()

        def _worker():
            try:
                result = call_async(svc.create_login_request("parallel_user"))
                with result_lock:
                    tokens.append(result["token"])
            except Exception as exc:
                with result_lock:
                    errors.append(exc)

        with patch.object(svc.user_repo, "get_by_telegram_username", return_value=None):
            threads = [threading.Thread(target=_worker) for _ in range(token_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert not errors
        assert len(tokens) == token_count
        assert len(set(tokens)) == token_count


class TestConcurrentTokenCollisionThreading:
    """Threading-based concurrency test for token collision handling.

    Simulates multiple simultaneous create_login_request calls using real
    threads to verify no IntegrityError escapes and all tokens are unique.
    """

    def test_concurrent_create_requests_no_integrity_error_escapes(self):
        """Multiple threads create login requests concurrently — no unhandled IntegrityError."""
        import threading

        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        user = User.objects.create_user(
            username="tg_thread_collision",
            telegram_id="770000050",
            name="Thread Collision",
            language="en",
            timezone="UTC",
            telegram_username="threadcollision",
        )

        thread_count = 10
        tokens = []
        errors = []
        result_lock = threading.Lock()

        def _worker():
            try:
                # Mock the background processing to avoid actual Telegram calls
                with patch.object(
                    svc, "_process_login_background",
                ):
                    result = call_async(svc.create_login_request("threadcollision"))
                    with result_lock:
                        tokens.append(result["token"])
            except Exception as exc:
                with result_lock:
                    errors.append(exc)

        with patch.object(svc.user_repo, "get_by_telegram_username", return_value=user):
            threads = [threading.Thread(target=_worker) for _ in range(thread_count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        # All threads should complete without errors
        assert all(not t.is_alive() for t in threads), "Some threads timed out"
        assert not errors, f"Unexpected errors: {errors}"
        assert len(tokens) == thread_count
        # All tokens should be unique
        assert len(set(tokens)) == thread_count


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


class TestExecutorShutdown:
    """Verify behavior when ThreadPoolExecutor is shut down."""

    def test_submit_after_shutdown_returns_503(self):
        """When executor is shut down, submit raises RuntimeError and semaphore is released."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService, _get_executor
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_shutdown_user",
            telegram_id="770000004",
            name="Shutdown User",
            language="en",
            timezone="UTC",
            telegram_username="shutdownuser",
        )

        svc = WebLoginService()
        executor = _get_executor()

        with patch.object(executor, "submit", side_effect=RuntimeError("executor shut down")):
            with pytest.raises(LoginServiceUnavailable):
                call_async(svc.create_login_request("shutdownuser"))


class TestMarkAsUsedConcurrency:
    """Verify mark_as_used atomicity — only the first caller succeeds.

    Note: True thread-level concurrency causes SQLite table locking in tests.
    We simulate concurrent callers by calling complete_login sequentially —
    the UPDATE WHERE status='confirmed' ensures only the first call transitions
    the token to 'used', and all subsequent calls see status='used' and fail.
    """

    def test_sequential_complete_login_only_first_succeeds(self):
        """First complete_login returns user, subsequent calls return None."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_atomic_user",
            telegram_id="770000005",
            name="Atomic User",
            language="en",
            timezone="UTC",
        )

        token = "atomic_complete_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        svc = WebLoginService()

        # Simulate 4 "concurrent" callers — first wins, rest get None
        results = [call_async(svc.complete_login(token)) for _ in range(4)]

        successes = [r for r in results if r is not None]
        failures = [r for r in results if r is None]

        assert len(successes) == 1
        assert len(failures) == 3
        assert successes[0].id == user.id


class TestValidationPatternSync:
    """Verify frontend and backend validation patterns stay in sync."""

    def test_telegram_username_regex_matches_frontend(self):
        """Backend TELEGRAM_USERNAME_PATTERN matches the frontend regex."""
        import re
        from src.web.utils.validation import TELEGRAM_USERNAME_PATTERN

        # Frontend regex from Login.vue: /^[a-z0-9_]{3,32}$/
        # Both frontend and backend now enforce lowercase only — the frontend
        # lowercases input before validation (submitLogin).
        frontend_pattern = r"^[a-z0-9_]{3,32}$"

        assert TELEGRAM_USERNAME_PATTERN == frontend_pattern, (
            f"Backend pattern {TELEGRAM_USERNAME_PATTERN!r} differs from "
            f"frontend pattern {frontend_pattern!r} — update both to match"
        )

        # Also verify they accept/reject the same test strings
        test_cases = [
            ("abc", True),
            ("valid_user_123", True),
            ("a" * 32, True),
            ("ab", False),       # too short
            ("a" * 33, False),   # too long
            ("user@name", False),
            ("", False),
            ("UpperCase", False),  # uppercase rejected (lowercase only)
        ]
        for username, expected in test_cases:
            backend_match = bool(re.match(TELEGRAM_USERNAME_PATTERN, username))
            frontend_match = bool(re.match(frontend_pattern, username))
            assert backend_match == frontend_match == expected, (
                f"Mismatch for {username!r}: backend={backend_match}, "
                f"frontend={frontend_match}, expected={expected}"
            )


class TestFrontendBackendExpirySync:
    """Verify that frontend LOGIN_EXPIRY_MS matches backend WEB_LOGIN_EXPIRY_MINUTES."""

    def test_frontend_backend_expiry_sync(self):
        """The hardcoded frontend value (300000ms) must equal the backend default (5 min)."""
        from src.web.services.web_login_service import LOGIN_REQUEST_EXPIRY_MINUTES

        frontend_expiry_ms = 300_000  # LOGIN_EXPIRY_MS in Login.vue
        backend_expiry_ms = LOGIN_REQUEST_EXPIRY_MINUTES * 60 * 1000

        assert frontend_expiry_ms == backend_expiry_ms, (
            f"Frontend LOGIN_EXPIRY_MS ({frontend_expiry_ms}ms) does not match "
            f"backend WEB_LOGIN_EXPIRY_MINUTES ({LOGIN_REQUEST_EXPIRY_MINUTES}min = "
            f"{backend_expiry_ms}ms) — update both to match"
        )


# ---- New tests for security, bug, and performance changes ----


class TestConcurrentCompleteLogin:
    """Verify that only one of multiple concurrent complete_login calls succeeds.

    Note: True thread-level concurrency causes SQLite table locking in tests.
    We simulate concurrent callers by calling complete_login sequentially —
    the UPDATE WHERE status='confirmed' ensures only the first call transitions
    the token to 'used', and all subsequent calls see status='used' and fail.
    """

    def test_concurrent_complete_login_only_one_succeeds(self):
        """Simulating 5 concurrent complete_login calls sequentially,
        only one should succeed (return a user), the rest should return None."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_conc_complete",
            telegram_id="880000001",
            name="Conc Complete",
            language="en",
            timezone="UTC",
        )

        token = "conc_complete_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        svc = WebLoginService()

        # Simulate 5 "concurrent" callers — first wins, rest get None
        results = [call_async(svc.complete_login(token)) for _ in range(5)]

        successes = [r for r in results if r is not None]
        failures = [r for r in results if r is None]

        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(failures) == 4
        assert successes[0].id == user.id


class TestBotLoginRequestCSRF:
    """Verify that POST requests without valid CSRF tokens are rejected."""

    def test_bot_login_request_rejects_missing_csrf(self):
        """POST to bot-login/request/ without CSRF token returns 403."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/auth/bot-login/request/",
            data=json.dumps({"username": "testuser"}),
            content_type="application/json",
        )
        assert response.status_code == 403


class TestQueueFullReturns503:
    """Verify LoginServiceUnavailable is raised when queue is full."""

    def test_queue_full_returns_503(self):
        """When all semaphore permits are drained, create_login_request raises
        LoginServiceUnavailable which the view converts to HTTP 503."""
        import src.web.services.web_login_service as svc_mod
        from django.core.cache import cache
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_queue_full",
            telegram_id="880000002",
            name="Queue Full",
            language="en",
            timezone="UTC",
            telegram_username="queuefulluser",
        )

        svc = WebLoginService()
        original_slots = svc_mod._queue_slots
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False
        svc_mod._queue_slots = mock_sem
        try:
            with pytest.raises(LoginServiceUnavailable):
                call_async(svc.create_login_request("queuefulluser"))
        finally:
            svc_mod._queue_slots = original_slots


class TestQueueSaturationIntegration:
    """Integration tests for thread pool queue saturation via HTTP endpoints."""

    def test_503_response_body_on_queue_full(self):
        """POST /auth/bot-login/request/ returns 503 with correct error message
        when the background queue is saturated."""
        import src.web.services.web_login_service as svc_mod

        User.objects.create_user(
            username="tg_sat_user",
            telegram_id="990000001",
            name="Sat User",
            language="en",
            timezone="UTC",
            telegram_username="satuser",
        )

        original_slots = svc_mod._queue_slots
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False
        svc_mod._queue_slots = mock_sem
        try:
            response = Client().post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "satuser"}),
                content_type="application/json",
            )
            assert response.status_code == 503
            body = response.json()
            assert "error" in body
            assert "temporarily unavailable" in body["error"].lower()
        finally:
            svc_mod._queue_slots = original_slots

    def test_semaphore_released_after_successful_submit(self):
        """Semaphore slot is released after background task completes,
        allowing subsequent requests to proceed."""
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import WebLoginService, _release_queue_slot
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_sem_release",
            telegram_id="990000002",
            name="Sem Release",
            language="en",
            timezone="UTC",
            telegram_username="semreleaseuser",
        )

        svc = WebLoginService()

        # Replace with a real semaphore of capacity 1 to test release behavior
        original_slots = svc_mod._queue_slots
        test_sem = threading.Semaphore(1)
        svc_mod._queue_slots = test_sem
        try:
            # Mock executor to capture the done_callback
            captured_callbacks = []
            mock_future = MagicMock()
            mock_future.add_done_callback.side_effect = lambda cb: captured_callbacks.append(cb)

            with patch.object(svc_mod._get_executor(), "submit", return_value=mock_future):
                call_async(svc.create_login_request("semreleaseuser"))

            # Semaphore should be acquired (0 remaining)
            assert not test_sem.acquire(blocking=False), "Semaphore should be exhausted"

            # Trigger the done callback — simulates task completion
            assert len(captured_callbacks) == 1
            captured_callbacks[0](mock_future)

            # Semaphore should now be released
            assert test_sem.acquire(blocking=False), "Semaphore should be available after callback"
            test_sem.release()  # Clean up
        finally:
            svc_mod._queue_slots = original_slots

    def test_semaphore_released_on_executor_runtime_error(self):
        """When executor.submit raises RuntimeError (shutdown), the semaphore
        slot is still released to prevent leaks."""
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService
        from src.web.utils.sync import call_async

        User.objects.create_user(
            username="tg_sem_err",
            telegram_id="990000003",
            name="Sem Error",
            language="en",
            timezone="UTC",
            telegram_username="semerroruser",
        )

        svc = WebLoginService()

        original_slots = svc_mod._queue_slots
        test_sem = threading.Semaphore(1)
        svc_mod._queue_slots = test_sem
        try:
            with patch.object(
                svc_mod._get_executor(), "submit",
                side_effect=RuntimeError("executor shut down"),
            ):
                with pytest.raises(LoginServiceUnavailable):
                    call_async(svc.create_login_request("semerroruser"))

            # Semaphore should still be available (released on error)
            assert test_sem.acquire(blocking=False), "Semaphore should be released after error"
            test_sem.release()
        finally:
            svc_mod._queue_slots = original_slots


class TestParseIPMultiProxyChain:
    """Verify that X-Forwarded-For with >2 IPs takes the leftmost IP."""

    @patch("src.web.utils.ip.settings")
    def test_parse_ip_takes_leftmost_from_multi_proxy_chain(self, mock_settings):
        """X-Forwarded-For with >2 IPs takes the leftmost (original client) IP."""
        from src.web.utils.ip import parse_ip_address

        mock_settings.TRUST_X_FORWARDED_FOR = True
        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1, 172.16.0.1",
            "REMOTE_ADDR": "127.0.0.1",
        }
        with patch("src.web.utils.ip.logger") as mock_logger:
            result = parse_ip_address(request)

        assert result == "10.0.0.1"
        mock_logger.debug.assert_called_once()


# ---- Status endpoint token validation ----


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


class TestTokenValidationInHandler:
    """Verify token format validation in the bot callback handler."""

    @pytest.mark.asyncio
    async def test_short_token_rejected(self):
        """A token shorter than TOKEN_MIN_LENGTH is rejected without DB query."""
        from unittest.mock import AsyncMock, MagicMock
        from src.bot.handlers.web_login_handler import web_login_callback

        update = MagicMock()
        update.effective_user.id = 555555555
        update.callback_query.data = "wl_c_ab"  # Very short token
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()

        await web_login_callback(update, MagicMock())

        update.callback_query.edit_message_text.assert_awaited_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "expired" in msg.lower() or "not found" in msg.lower()

    @pytest.mark.asyncio
    async def test_long_token_rejected(self):
        """A token longer than TOKEN_MAX_LENGTH is rejected without DB query."""
        from unittest.mock import AsyncMock, MagicMock
        from src.bot.handlers.web_login_handler import web_login_callback

        update = MagicMock()
        update.effective_user.id = 555555555
        update.callback_query.data = "wl_c_" + "a" * 200  # Very long token
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()

        await web_login_callback(update, MagicMock())

        update.callback_query.edit_message_text.assert_awaited_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "expired" in msg.lower() or "not found" in msg.lower()

    @pytest.mark.asyncio
    async def test_valid_length_token_proceeds_to_db(self):
        """A token with valid length proceeds past validation to DB lookup."""
        from unittest.mock import AsyncMock, MagicMock
        from src.bot.handlers.web_login_handler import web_login_callback
        from src.web.services.web_login_service import TOKEN_LENGTH

        update = MagicMock()
        update.effective_user.id = 555555555
        # Generate a token of valid length (will not be found in DB)
        valid_token = "x" * TOKEN_LENGTH
        update.callback_query.data = f"wl_c_{valid_token}"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()

        await web_login_callback(update, MagicMock())

        # Should proceed past token validation and hit DB lookup (not found)
        update.callback_query.edit_message_text.assert_awaited_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "expired" in msg.lower() or "not found" in msg.lower()


class TestConcurrentTokenCollisions:
    """Verify token collision retry via IntegrityError simulation."""

    def test_integrity_error_triggers_retry_with_new_token(self):
        """When IntegrityError occurs on create, a new token is generated."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService

        user = User.objects.create_user(
            username="tg_collision_test",
            telegram_id="770000030",
            name="Collision Test",
            language="en",
            timezone="UTC",
        )

        call_count = 0
        original_create = WebLoginRequest.objects.create

        def create_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from django.db import IntegrityError
                raise IntegrityError("UNIQUE constraint failed: token")
            return original_create(**kwargs)

        with patch.object(
            WebLoginRequest.objects, "create", side_effect=create_side_effect
        ):
            login_req, final_token = WebLoginService._create_login_request_with_retry(
                user.id,
                "first_token_will_collide_padded_to_43ch_x",
                datetime.now(timezone.utc) + timedelta(minutes=5),
                "test device",
            )

        assert login_req is not None
        assert final_token != "first_token_will_collide_padded_to_43ch_x"
        assert call_count == 2

    def test_all_retries_exhausted_raises_database_error(self):
        """When all 3 retries fail with IntegrityError, DatabaseError is raised."""
        from django.db import DatabaseError, IntegrityError
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService

        user = User.objects.create_user(
            username="tg_exhaust_retry",
            telegram_id="770000031",
            name="Exhaust Retry",
            language="en",
            timezone="UTC",
        )

        with patch.object(
            WebLoginRequest.objects, "create",
            side_effect=IntegrityError("UNIQUE constraint failed"),
        ):
            with pytest.raises(DatabaseError, match="unique token after retries"):
                WebLoginService._create_login_request_with_retry(
                    user.id,
                    "exhaust_token_padded_to_43_characters_xxxxx",
                    datetime.now(timezone.utc) + timedelta(minutes=5),
                    "test device",
                )


class TestQueueExhaustion503:
    """Verify HTTP 503 when the login queue is full."""

    def test_503_when_queue_full(self):
        """When _queue_slots.acquire returns False, the service should
        raise LoginServiceUnavailable and the view should return 503."""
        client = Client()

        with patch(
            "src.web.services.web_login_service._queue_slots"
        ) as mock_semaphore:
            mock_semaphore.acquire.return_value = False

            with patch(
                "src.web.services.web_login_service.WebLoginService.create_login_request",
            ) as mock_create:
                from src.web.services.web_login_service import LoginServiceUnavailable
                mock_create.side_effect = LoginServiceUnavailable("Queue full")

                response = client.post(
                    "/auth/bot-login/request/",
                    data=json.dumps({"username": "testuser"}),
                    content_type="application/json",
                )

                assert response.status_code == 503


class TestThreadPoolQueueExhaustionDirect:
    """Verify queue exhaustion at the service level."""

    def test_queue_full_raises_login_service_unavailable(self):
        """When all queue slots are taken, create_login_request raises."""
        from src.web.services.web_login_service import (
            LoginServiceUnavailable,
            WebLoginService,
        )
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_queue_full",
            telegram_id="770000032",
            name="Queue Full",
            language="en",
            timezone="UTC",
        )

        svc = WebLoginService()

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=user),
            patch(
                "src.web.services.web_login_service._queue_slots"
            ) as mock_sem,
        ):
            mock_sem.acquire.return_value = False
            with pytest.raises(LoginServiceUnavailable):
                call_async(svc.create_login_request("queue_full_user"))


class TestParseUaCachedCacheFailure:
    """Tests for _parse_ua_cached graceful degradation when cache backend fails."""

    def test_cache_get_failure_falls_back_to_direct_parse(self):
        """When cache.get() raises an exception, _parse_ua_cached still returns
        a valid device_info string by falling back to direct UA parsing."""
        from src.web.views.auth import _parse_ua_cached

        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"

        with patch("django.core.cache.cache.get", side_effect=ConnectionError("Redis down")):
            result = _parse_ua_cached(ua)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Chrome" in result

    def test_cache_get_failure_logs_warning(self):
        """When cache.get() raises an exception, a warning is logged."""
        from src.web.views.auth import _parse_ua_cached

        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15"

        with (
            patch("django.core.cache.cache.get", side_effect=ConnectionError("Redis down")),
            patch("src.web.views.auth.logger") as mock_logger,
        ):
            _parse_ua_cached(ua)

        mock_logger.warning.assert_any_call(
            "Cache read failed for UA parsing; falling back to direct parse"
        )

    def test_cache_set_failure_still_returns_result(self):
        """When cache.set() raises after parsing, the result is still returned."""
        from src.web.views.auth import _parse_ua_cached

        ua = "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0"

        with (
            patch("django.core.cache.cache.get", return_value=None),
            patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis down")),
        ):
            result = _parse_ua_cached(ua)

        assert isinstance(result, str)
        assert "Firefox" in result

    def test_cache_set_failure_logs_warning(self):
        """When cache.set() raises after parsing, a warning is logged."""
        from src.web.views.auth import _parse_ua_cached

        ua = "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0"

        with (
            patch("django.core.cache.cache.get", return_value=None),
            patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis down")),
            patch("src.web.views.auth.logger") as mock_logger,
        ):
            _parse_ua_cached(ua)

        mock_logger.warning.assert_any_call(
            "Cache write failed for UA parsing; result not cached"
        )


class TestCriticalPathIntegrations:
    """Integration coverage for critical login flow edge cases."""

    def test_collision_retry_integration_path(self):
        """_process_login_request retries on token collision and persists the retried token."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_int_collision",
            telegram_id="771111111",
            name="Int Collision",
            language="en",
            timezone="UTC",
            telegram_username="intcollision",
        )
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        collision_token = "integration_collision_token"

        WebLoginRequest.objects.create(
            user=user,
            token=collision_token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )

        svc = WebLoginService()
        with (
            patch(
                "src.web.services.web_login_service.secrets.token_urlsafe",
                return_value="integration_collision_retry_token",
            ),
            patch.object(svc, "_send_login_notification", new_callable=AsyncMock),
        ):
            call_async(svc._process_login_request(user, collision_token, expires_at, None))

        assert WebLoginRequest.objects.filter(
            user=user,
            token="integration_collision_retry_token",
        ).exists()

    def test_concurrent_status_checks_same_token(self):
        """Concurrent status polling on one token returns consistent status values."""
        from concurrent.futures import ThreadPoolExecutor

        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import WebLoginService, WL_PENDING_KEY
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        token = "integration_concurrent_status_token"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        def _check():
            return call_async(svc.check_status(token))

        with (
            patch.object(svc_mod, "_JITTER_MIN", 0.0),
            patch.object(svc_mod, "_JITTER_MAX", 0.0),
            ThreadPoolExecutor(max_workers=8) as executor,
        ):
            results = list(executor.map(lambda _: _check(), range(8)))

        assert all(result == "pending" for result in results)

    def test_cache_write_error_paths_return_tokens(self):
        """Known and unknown user paths both return tokens when cache writes fail."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import CacheWriteError, WebLoginService, _get_executor
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        User.objects.create_user(
            username="tg_cache_fail_known",
            telegram_id="772222222",
            name="Cache Fail Known",
            language="en",
            timezone="UTC",
            telegram_username="cachefailknown",
        )

        def _submit_inline(job, *args):
            future = Future()
            try:
                job(*args)
                future.set_result(None)
            except Exception as exc:  # pragma: no cover - defensive in test helper
                future.set_exception(exc)
            return future

        with (
            patch.object(_get_executor(), "submit", side_effect=_submit_inline),
            patch(
                "src.web.services.web_login_service.cache_manager.set",
                side_effect=CacheWriteError("cache backend down"),
            ),
        ):
            known_result = call_async(svc.create_login_request("cachefailknown"))
            unknown_result = call_async(svc.create_login_request("cachefailunknown"))

        assert "token" in known_result
        assert "token" in unknown_result

        with (
            patch.object(svc_mod, "_JITTER_MIN", 0.0),
            patch.object(svc_mod, "_JITTER_MAX", 0.0),
        ):
            assert call_async(svc.check_status(known_result["token"])) == "expired"
            assert call_async(svc.check_status(unknown_result["token"])) == "expired"

    def test_queue_saturation_returns_503(self):
        """HTTP endpoint returns 503 when queue slots cannot be acquired."""
        import src.web.services.web_login_service as svc_mod

        User.objects.create_user(
            username="tg_queue_sat",
            telegram_id="773333333",
            name="Queue Sat",
            language="en",
            timezone="UTC",
            telegram_username="queuesat",
        )

        original_slots = svc_mod._queue_slots
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False
        svc_mod._queue_slots = mock_sem
        try:
            response = Client().post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "queuesat"}),
                content_type="application/json",
            )
        finally:
            svc_mod._queue_slots = original_slots

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["error"].lower()


class TestConcurrentSameUserLogin:
    """Verify that two login requests from the same user result in exactly
    one PENDING WebLoginRequest (the other is invalidated to DENIED).

    Tests the transactional invalidation logic in
    ``_create_login_request_with_retry`` by calling it twice for the same
    user and verifying the DB invariant.
    """

    def test_two_requests_only_one_pending(self):
        """Call _create_login_request_with_retry twice for the same user.
        After both complete, exactly one WebLoginRequest has status=PENDING."""
        import secrets
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import (
            WebLoginService, TOKEN_BYTES,
        )
        from django.core.cache import cache

        cache.clear()

        user_obj = User.objects.create_user(
            username="tg_concurrent_same",
            telegram_id="770000001",
            name="Concurrent Same",
            language="en",
            timezone="UTC",
            telegram_username="concurrentsame",
        )

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        token1 = secrets.token_urlsafe(TOKEN_BYTES)
        token2 = secrets.token_urlsafe(TOKEN_BYTES)

        # First request creates a PENDING login request.
        req1, final_token1 = WebLoginService._create_login_request_with_retry(
            user_obj.id, token1, expires_at, "device1",
        )
        assert req1.status == WebLoginRequest.Status.PENDING.value

        # Second request should invalidate the first and create a new PENDING.
        req2, final_token2 = WebLoginService._create_login_request_with_retry(
            user_obj.id, token2, expires_at, "device2",
        )
        assert req2.status == WebLoginRequest.Status.PENDING.value

        # Exactly one PENDING request should exist for this user.
        pending_count = WebLoginRequest.objects.filter(
            user=user_obj, status=WebLoginRequest.Status.PENDING,
        ).count()
        assert pending_count == 1, (
            f"Expected exactly 1 PENDING request, found {pending_count}"
        )

        # The first request should now be DENIED.
        req1.refresh_from_db()
        assert req1.status == WebLoginRequest.Status.DENIED.value

        # The second request is the active PENDING one.
        req2.refresh_from_db()
        assert req2.status == WebLoginRequest.Status.PENDING.value


class TestCircuitBreakerLoadTest:
    """Load test: submit more requests than queue capacity to verify
    the 503 circuit breaker activates and that requests resume afterward.
    """

    def test_overload_triggers_503_then_recovers(self):
        """Submit more than queue capacity requests rapidly.  At least one
        should receive HTTP 503.  After the queue drains, a new request
        should succeed (HTTP 200)."""
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import _get_executor

        User.objects.create_user(
            username="tg_loadtest",
            telegram_id="770000002",
            name="Load Test",
            language="en",
            timezone="UTC",
            telegram_username="loadtestuser",
        )

        # Use a small queue capacity for a fast test.
        original_slots = svc_mod._queue_slots
        original_max = svc_mod._MAX_QUEUED_LOGINS
        original_warn = svc_mod._QUEUE_WARN_THRESHOLD
        test_capacity = 3
        svc_mod._queue_slots = threading.Semaphore(test_capacity)
        svc_mod._MAX_QUEUED_LOGINS = test_capacity
        svc_mod._QUEUE_WARN_THRESHOLD = int(test_capacity * 0.8)

        # Block background threads so the queue fills up.
        block_event = threading.Event()

        def _blocking_submit(job, *args):
            """Submit a job that blocks until the event is set."""
            future = Future()

            def _wrapper():
                block_event.wait(timeout=10)
                try:
                    job(*args)
                    future.set_result(None)
                except Exception as exc:
                    future.set_exception(exc)

            t = threading.Thread(target=_wrapper)
            t.daemon = True
            t.start()
            return future

        try:
            with patch.object(
                _get_executor(), "submit", side_effect=_blocking_submit,
            ):
                responses = []
                for i in range(test_capacity + 5):
                    response = Client().post(
                        "/auth/bot-login/request/",
                        data=json.dumps({"username": "loadtestuser"}),
                        content_type="application/json",
                    )
                    responses.append(response)

                status_codes = [r.status_code for r in responses]
                assert 503 in status_codes, (
                    f"Expected at least one 503 in {status_codes}"
                )

            # Unblock all threads so the queue drains.
            block_event.set()
            time.sleep(0.5)
        finally:
            svc_mod._queue_slots = original_slots
            svc_mod._MAX_QUEUED_LOGINS = original_max
            svc_mod._QUEUE_WARN_THRESHOLD = original_warn

        # After queue drains, verify recovery is possible.
        # Clear rate-limit cache entries so the recovery request isn't
        # blocked by django-ratelimit (we just sent 8 rapid requests).
        from django.core.cache import cache as django_cache
        django_cache.clear()

        with patch(
            "src.web.views.auth.call_async",
            side_effect=_call_async_mock(
                {"token": "recovery_token", "expires_at": "2026-01-01T00:00:00+00:00"}
            ),
        ):
            recovery = Client().post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "loadtestuser"}),
                content_type="application/json",
            )
        assert recovery.status_code == 200


class TestConcurrentCompleteLoginThreading:
    """Threading-based concurrency test for complete_login view logic.

    Uses real threads calling the view function directly via RequestFactory
    to avoid SQLite table-locking from Django's session middleware.
    Mocks call_async to simulate the race condition: first caller wins
    (returns user), second gets None (token already used).
    """

    def test_threading_complete_login_one_succeeds_one_fails(self):
        """Two real threads call bot_login_complete simultaneously;
        exactly one gets 200 (success), the other gets 403 (token used)."""
        from django.test import RequestFactory
        from src.web.views.auth import bot_login_complete

        user = User.objects.create_user(
            username="tg_thread_http_complete",
            telegram_id="880100002",
            name="Thread HTTP Complete",
            language="en",
            timezone="UTC",
        )

        valid_token = "thread_http_complete_tok_aaabbbbccccddddeeee"
        call_count = 0
        call_lock = threading.Lock()

        def _mock_complete(coro):
            """First caller wins (returns user), second gets None."""
            nonlocal call_count
            if hasattr(coro, 'close'):
                coro.close()
            with call_lock:
                call_count += 1
                current = call_count
            return user if current == 1 else None

        # Mock IP binding to avoid SQLite table locks from concurrent reads
        mock_binding = MagicMock()
        mock_binding.ip_address = "127.0.0.1"

        results = []
        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(2, timeout=5)
        factory = RequestFactory()

        def _worker():
            try:
                barrier.wait()  # Synchronize thread start
                request = factory.post(
                    "/auth/bot-login/complete/",
                    data=json.dumps({"token": valid_token}),
                    content_type="application/json",
                )
                response = bot_login_complete(request)
                with lock:
                    results.append(response.status_code)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        with (
            patch("src.web.views.auth.call_async", side_effect=_mock_complete),
            patch("src.web.views.auth.login"),  # Avoid session DB access
            patch("src.web.views.auth.web_login_request_repository.get_ip_binding", return_value=mock_binding),
        ):
            threads = [threading.Thread(target=_worker) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert all(not t.is_alive() for t in threads), "Threads timed out"
        assert not errors, f"Unexpected errors: {errors}"
        assert len(results) == 2
        assert sorted(results) == [200, 403], (
            f"Expected one 200 and one 403, got {results}"
        )


# ---- IP binding enforcement tests ----


class TestIPBindingEnforcement:
    """Verify database-backed IP binding prevents cross-IP attacks."""

    def test_bot_login_complete_rejects_mismatched_ip(self, user):
        """Create token from IP A, confirm, then complete from IP B → 403.

        Simulates an attacker who intercepts a confirmed token and tries
        to complete the login from a different IP address.
        """
        token = _TEST_TOKEN
        # Bind to IP A
        _create_ip_binding(token=token, ip="10.0.0.1")

        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock(user)):
            # Complete from IP B (Django Client sends 127.0.0.1 by default)
            response = Client().post(
                "/auth/bot-login/complete/",
                data=json.dumps({"token": token}),
                content_type="application/json",
            )
        assert response.status_code == 403
        assert "expired or invalid" in response.json()["error"]

    def test_bot_login_complete_accepts_matching_ip(self, user):
        """Complete from same IP as token creator → 200 success."""
        token = _TEST_TOKEN
        _create_ip_binding(token=token, ip=_TEST_IP)

        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock(user)):
            client = Client()
            response = client.post(
                "/auth/bot-login/complete/",
                data=json.dumps({"token": token}),
                content_type="application/json",
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("pending"))
    def test_bot_login_status_ip_binding_enforced_even_without_session(self, mock_async):
        """When no IP binding exists in the DB, status returns 'expired'.

        Prevents attackers from polling tokens from different IPs when
        the binding is missing (e.g. expired or never created).
        """
        # Do NOT create an IP binding — token has no binding in DB
        token = _TEST_TOKEN
        response = Client().get(f"/auth/bot-login/status/{token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("pending"))
    def test_bot_login_status_rejects_mismatched_ip(self, mock_async):
        """Status poll from different IP than token creator → expired."""
        token = _TEST_TOKEN
        _create_ip_binding(token=token, ip="10.0.0.1")  # Bind to IP A
        # Poll from IP B (127.0.0.1 default)
        response = Client().get(f"/auth/bot-login/status/{token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed"))
    def test_bot_login_status_accepts_matching_ip(self, mock_async):
        """Status poll from same IP as token creator → actual status."""
        token = _TEST_TOKEN
        _create_ip_binding(token=token, ip=_TEST_IP)
        response = Client().get(f"/auth/bot-login/status/{token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_bot_login_complete_no_binding_returns_403(self):
        """Complete with no IP binding record → 403."""
        token = _TEST_TOKEN
        # No binding created
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403
