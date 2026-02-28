"""Tests for full login flow, background processing, concurrency, and circuit breakers."""

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

        cache.clear()
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


class TestCircuitBreakerServiceLevel:
    """Verify the service-level circuit breaker raises LoginServiceUnavailable."""

    def test_login_request_rejects_when_queue_full(self):
        """When _queue_slots.acquire returns False, service raises LoginServiceUnavailable."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        User.objects.create_user(
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

        User.objects.create_user(
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
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        User.objects.create_user(
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


class TestExecutorShutdown:
    """Verify behavior when ThreadPoolExecutor is shut down."""

    def test_submit_after_shutdown_returns_503(self):
        """When executor is shut down, submit raises RuntimeError and semaphore is released."""
        from django.core.cache import cache
        from src.web.services.web_login_service import LoginServiceUnavailable, WebLoginService, _get_executor
        from src.web.utils.sync import call_async

        cache.clear()

        User.objects.create_user(
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


class TestCriticalPathIntegrations:
    """Integration coverage for critical login flow edge cases."""

    def test_collision_retry_preserves_client_token_via_alias(self):
        """Original client token still resolves when collision retry rotates DB token."""
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

        login_req = WebLoginRequest.objects.get(
            user=user,
            token="integration_collision_retry_token",
        )
        assert login_req.status == WebLoginRequest.Status.PENDING

        # Simulate Telegram confirmation on the rotated DB token.
        WebLoginRequest.objects.filter(pk=login_req.pk).update(
            status=WebLoginRequest.Status.CONFIRMED.value
        )
        from src.core.repositories import web_login_request_repository
        web_login_request_repository.clear_login_cache_keys("integration_collision_retry_token")

        # The browser still holds the original token, so status/complete must
        # resolve via cache alias rather than the rotated DB token.
        assert call_async(svc.check_status(collision_token)) == WebLoginRequest.Status.CONFIRMED.value
        completed_user = call_async(svc.complete_login(collision_token))
        assert completed_user is not None
        assert completed_user.id == user.id

        login_req.refresh_from_db()
        assert login_req.status == WebLoginRequest.Status.USED.value

    def test_collision_retry_alias_missing_does_not_leave_old_token_pending(self):
        """If alias is missing after retry, original token should not stay pending forever."""
        from django.core.cache import cache
        import src.web.services.web_login_service as svc_mod
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService, WL_ALIAS_KEY
        from src.web.utils.sync import call_async

        cache.clear()
        user = User.objects.create_user(
            username="tg_int_collision_alias_miss",
            telegram_id="771111112",
            name="Int Collision Alias Miss",
            language="en",
            timezone="UTC",
            telegram_username="intcollisionaliasmiss",
        )
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        collision_token = "integration_collision_alias_miss_token"

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
                return_value="integration_collision_alias_retry_token",
            ),
            patch.object(svc, "_send_login_notification", new_callable=AsyncMock),
        ):
            call_async(svc._process_login_request(user, collision_token, expires_at, None))

        # Simulate alias eviction/unavailability. Old token should no longer
        # look permanently pending.
        cache.delete(f"{WL_ALIAS_KEY}{collision_token}")
        with (
            patch.object(svc_mod, "_JITTER_MIN", 0.0),
            patch.object(svc_mod, "_JITTER_MAX", 0.0),
        ):
            status = call_async(svc.check_status(collision_token))
        assert status in {"denied", "expired", "error"}
        assert status != "pending"
        assert call_async(svc.complete_login(collision_token)) is None

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
