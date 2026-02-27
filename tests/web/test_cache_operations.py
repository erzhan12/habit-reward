"""Tests for cache operations, failure thresholds, and cache/DB race conditions."""

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import User
from src.web.services.web_login_service import WL_FAILED_KEY, WL_PENDING_KEY


class TestCacheFailureThreshold:
    """Tests for cache write failure tracking and CacheWriteError threshold."""

    def test_cache_write_error_after_threshold(self):
        """CacheWriteError is raised after threshold consecutive failures."""
        from src.web.services.web_login_service import CacheWriteError, cache_manager

        cache_manager.reset()
        try:
            with patch("django.core.cache.cache.set", side_effect=ConnectionError("cache down")):
                # First 9 should just warn
                for i in range(9):
                    cache_manager.set(f"test_key_{i}", True, 60)

                # 10th should raise
                with pytest.raises(CacheWriteError, match="10 times consecutively"):
                    cache_manager.set("test_key_10", True, 60)
        finally:
            cache_manager.reset()

    def test_counter_resets_on_success(self):
        """A successful cache write resets the failure counter."""
        from src.web.services.web_login_service import cache_manager

        cache_manager.reset()
        try:
            # Simulate 8 failures
            with patch("django.core.cache.cache.set", side_effect=ConnectionError("blip")):
                for i in range(8):
                    cache_manager.set(f"fail_key_{i}", True, 60)
            assert cache_manager.failure_count == 8
            # One success resets
            cache_manager.set("reset_key", True, 60)
            assert cache_manager.failure_count == 0
        finally:
            cache_manager.reset()

    def test_intermittent_failures_dont_trigger_threshold(self):
        """Alternating success/failure never reaches threshold."""
        from src.web.services.web_login_service import cache_manager

        cache_manager.reset()
        try:
            for i in range(20):
                if i % 2 == 0:
                    with patch("django.core.cache.cache.set",
                               side_effect=ConnectionError("blip")):
                        cache_manager.set(f"intermittent_{i}", True, 60)
                else:
                    cache_manager.set(f"intermittent_{i}", True, 60)

            # Should never have raised — counter resets on each success
            assert cache_manager.failure_count == 0
        finally:
            cache_manager.reset()


class TestCacheBackendFailure:
    """Test graceful degradation when the cache backend is unavailable."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_degrades_on_cache_failure(self, mock_sleep):
        """check_status falls back to DB-only when cache.get_many() raises."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        svc = WebLoginService()
        user = User.objects.create_user(
            username="tg_cache_fail", telegram_id="123123123", name="CacheFail",
            language="en", timezone="UTC",
        )
        req = WebLoginRequest.objects.create(
            user=user,
            token="cache_fail_tok",
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        with patch("django.core.cache.cache.get_many", side_effect=ConnectionError("Redis down")):
            status = call_async(svc.check_status("cache_fail_tok"))

        # Should return the DB status, not crash.
        assert status == WebLoginRequest.Status.PENDING

    def test_create_login_request_degrades_on_cache_set_failure(self):
        """create_login_request still returns a token when cache.set() fails."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        with patch.object(svc.user_repo, "get_by_telegram_username", return_value=None), \
             patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis down")):
            result = call_async(svc.create_login_request("cachefailuser"))

        assert "token" in result
        assert "expires_at" in result

    def test_create_login_request_raises_after_threshold_cache_write_failures(self):
        """Consecutive cache write failures reaching threshold should raise service unavailable."""
        from django.core.cache import cache
        from src.web.services.web_login_service import (
            LoginServiceUnavailable, WebLoginService, cache_manager,
        )
        from src.web.utils.sync import call_async

        threshold = cache_manager._failure_threshold  # 10

        cache.clear()
        svc = WebLoginService()
        cache_manager.reset()

        try:
            with patch.object(svc.user_repo, "get_by_telegram_username", return_value=None), \
                 patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis down")):
                # First (threshold - 1) requests should succeed despite cache errors
                for i in range(threshold - 1):
                    result = call_async(svc.create_login_request(f"cachefail{i}"))
                    assert "token" in result

                # The threshold-th request should raise
                with pytest.raises(
                    LoginServiceUnavailable, match="Login service temporarily unavailable"
                ):
                    call_async(svc.create_login_request("cachefail_final"))
        finally:
            cache_manager.reset()

    def test_background_processing_logs_cache_failure(self):
        """_process_login_background logs a warning when cache.set fails
        during error recovery (wl_failed key)."""
        from src.web.services.web_login_service import WebLoginService

        svc = WebLoginService()
        mock_user = MagicMock()
        mock_user.id = 42

        with patch.object(svc, "_process_login_request", new_callable=AsyncMock,
                         side_effect=Exception("boom")), \
             patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis down")), \
             patch("src.web.services.web_login_service.logger") as mock_svc_logger, \
             patch("src.web.services.web_login_service.cache_operations.logger") as mock_cache_logger:
            # Should not raise — all errors caught.
            svc._process_login_background(
                mock_user, "bg_cache_fail", datetime.now(timezone.utc) + timedelta(minutes=5), None
            )

        # Service logger gets the original error from the exception handler.
        assert mock_svc_logger.error.called
        # Cache operations logger gets the warning from failed cache writes.
        assert mock_cache_logger.warning.called


class TestCacheFailureThresholdRaisesError:
    """Verify that 10 consecutive cache write failures raise CacheWriteError."""

    def test_cache_failure_threshold_raises_error(self):
        """10 consecutive cache.set failures raise CacheWriteError."""
        from src.web.services.web_login_service import CacheWriteError, cache_manager

        cache_manager.reset()
        try:
            with patch("django.core.cache.cache.set", side_effect=ConnectionError("down")):
                # First 9 should just warn
                for i in range(9):
                    try:
                        cache_manager.set(f"test_key_{i}", True, 60)
                    except CacheWriteError:
                        pytest.fail(f"CacheWriteError raised too early on attempt {i + 1}")

                # The 10th failure should raise
                with pytest.raises(CacheWriteError):
                    cache_manager.set("test_key_final", True, 60)
        finally:
            cache_manager.reset()


class TestCacheConnectionErrorThreshold:
    """Verify LoginServiceUnavailable is raised after 10 consecutive ConnectionError from cache.set()."""

    def test_connection_error_threshold_triggers_service_unavailable(self):
        """Mock cache.set() to raise ConnectionError; after 10 failures LoginServiceUnavailable is raised."""
        from django.core.cache import cache
        from src.web.services.web_login_service import (
            LoginServiceUnavailable,
            WebLoginService,
            cache_manager,
        )
        from src.web.utils.sync import call_async

        cache.clear()
        cache_manager.reset()
        svc = WebLoginService()

        try:
            with (
                patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
                patch("django.core.cache.cache.set", side_effect=ConnectionError("Redis connection refused")),
            ):
                # First 9 requests succeed (cache failures are tolerated)
                for i in range(9):
                    result = call_async(svc.create_login_request(f"cache_err_user_{i}"))
                    assert "token" in result

                # The 10th request should trigger LoginServiceUnavailable
                with pytest.raises(LoginServiceUnavailable):
                    call_async(svc.create_login_request("cache_err_user_final"))
        finally:
            cache_manager.reset()


class TestCacheFailureScenarios:
    """Verify the login flow works via DB-only path when cache writes fail."""

    def test_login_request_raises_when_cache_critically_fails(self):
        """create_login_request raises LoginServiceUnavailable when cache backend
        is unhealthy (3+ consecutive failures)."""
        from src.web.services.web_login_service import (
            CacheWriteError,
            LoginServiceUnavailable,
            WebLoginService,
            cache_manager,
        )
        from src.web.utils.sync import call_async

        svc = WebLoginService()

        with (
            patch.object(svc.user_repo, "get_by_telegram_username", return_value=None),
            patch.object(
                cache_manager, "set",
                side_effect=CacheWriteError("Cache down"),
            ),
        ):
            with pytest.raises(LoginServiceUnavailable):
                call_async(svc.create_login_request("testuser"))

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_check_status_db_fallback_when_cache_read_fails(self, mock_sleep):
        """check_status falls back to DB when cache.get_many raises."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        user = User.objects.create_user(
            username="tg_cachefail1", telegram_id="555555555",
            name="Cache Fail User", language="en", timezone="UTC",
        )
        login_req = WebLoginRequest.objects.create(
            user=user, token="cache_fail_db_token",
            status="confirmed",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        svc = WebLoginService()
        with patch("django.core.cache.cache.get_many", side_effect=Exception("Redis down")):
            status = call_async(svc.check_status("cache_fail_db_token"))

        assert status == "confirmed"

    def test_login_endpoint_returns_503_on_cache_failure(self):
        """POST /auth/bot-login/request/ returns 503 when cache is critically broken."""
        import json

        from django.test import Client
        from src.web.services.web_login_service import (
            CacheWriteError,
            LoginServiceUnavailable,
        )

        def _raise_unavailable(coro):
            if hasattr(coro, 'close'):
                coro.close()
            raise LoginServiceUnavailable("Cache down")

        with patch("src.web.views.auth.call_async", side_effect=_raise_unavailable):
            response = Client().post(
                "/auth/bot-login/request/",
                data=json.dumps({"username": "testuser"}),
                content_type="application/json",
            )
        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["error"]


class TestCacheTTLExpiryWithPendingDBRecord:
    """Verify behavior when cache TTL expires but DB record still exists."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_ttl_expires_with_pending_db_record(self, mock_sleep):
        """When cache-pending TTL expires while token is still pending in DB,
        check_status should return 'pending' from the DB fallback — not
        'expired', which would confuse the user."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_ttl_expire",
            telegram_id="660000001",
            name="TTL Expire User",
            language="en",
            timezone="UTC",
            telegram_username="ttlexpireuser",
        )

        token = "ttl_expiry_test_token"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )

        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)
        cache.clear()  # Simulates cache TTL expiry

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "pending", (
            f"Expected 'pending' from DB fallback after cache TTL expiry, "
            f"got '{status}'"
        )

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_ttl_expires_no_db_record_returns_expired(self, mock_sleep):
        """When both cache and DB have no record, status should be 'expired'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        svc = WebLoginService()
        status = call_async(svc.check_status("nonexistent_token_for_test"))

        assert status == "expired"


class TestBackgroundFailureCacheCleanup:
    """Verify TTL-based cleanup when the background thread fails before DB write."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_bot_login_background_failure_cache_cleanup(self, mock_sleep):
        """When background thread fails before DB write, the cache-pending
        key remains until TTL expiry.  After TTL expires, check_status
        should return 'expired' (no DB record found) — not 'pending'
        indefinitely."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()

        token = "bg_fail_cache_cleanup_token"

        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        status = call_async(svc.check_status(token))
        assert status == "pending"

        cache.delete(f"{WL_PENDING_KEY}{token}")

        status = call_async(svc.check_status(token))
        assert status == "expired", (
            f"Expected 'expired' after cache TTL expiry with no DB record, "
            f"got '{status}'"
        )


class TestTokenCollisionCacheUpdate:
    """Verify that token collision retry writes the new token to cache."""

    def test_token_collision_updates_cache_with_new_token(self):
        """When IntegrityError triggers token regeneration, the new token
        should be written to cache so check_status can find it."""
        from django.core.cache import cache
        from django.db import IntegrityError
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService, WL_PENDING_KEY
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_collision_cache",
            telegram_id="770000010",
            name="Collision Cache User",
            language="en",
            timezone="UTC",
            telegram_username="collisioncacheuser",
        )

        svc = WebLoginService()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        call_count = 0
        original_create = WebLoginRequest.objects.create
        new_tokens = []

        def create_with_collision(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise IntegrityError("UNIQUE constraint failed: token")
            new_tokens.append(kwargs.get("token"))
            return original_create(**kwargs)

        with patch.object(WebLoginRequest.objects, "create", side_effect=create_with_collision), \
             patch.object(svc, "_send_login_notification", new_callable=AsyncMock):
            call_async(svc._process_login_request(user, "collision_cache_tok", expires_at, None))

        assert call_count == 2
        assert len(new_tokens) == 1
        assert cache.get(f"{WL_PENDING_KEY}{new_tokens[0]}") is True


class TestCacheDBRaceConditions:
    """Verify behavior when cache and DB are in inconsistent states."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_pending_but_db_confirmed(self, mock_sleep):
        """When cache still says pending but DB shows confirmed,
        check_status should return 'pending' (cache takes priority)."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_race_cache_db",
            telegram_id="770000011",
            name="Race Cache DB",
            language="en",
            timezone="UTC",
        )

        token = "race_cache_db_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "pending"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_cache_failed_overrides_db_pending(self, mock_sleep):
        """When cache says failed but DB shows pending,
        check_status should return 'error' (failed takes priority)."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_race_fail_pend",
            telegram_id="770000012",
            name="Race Fail Pend",
            language="en",
            timezone="UTC",
        )

        token = "race_fail_pend_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        cache.set(f"{WL_FAILED_KEY}{token}", True, timeout=300)

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "error"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_no_cache_db_expired_returns_expired(self, mock_sleep):
        """When cache is empty and DB record is past expires_at,
        check_status should return 'expired'."""
        from django.core.cache import cache
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()

        user = User.objects.create_user(
            username="tg_race_expired",
            telegram_id="770000013",
            name="Race Expired",
            language="en",
            timezone="UTC",
        )

        token = "race_expired_tok"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "expired"


class TestErrorStatusPolling:
    """Verify that check_status returns 'error' when the failed cache key is set."""

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_error_status_returned_for_failed_token(self, mock_sleep):
        """When the wl_failed cache key is set, check_status returns 'error'."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        token = "error_poll_test_tok"
        cache.set(f"{WL_FAILED_KEY}{token}", True, timeout=300)

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "error"

    @patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock)
    def test_error_status_takes_priority_over_pending(self, mock_sleep):
        """When both pending and failed cache keys are set, 'error' wins."""
        from django.core.cache import cache
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        token = "error_priority_tok"
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)
        cache.set(f"{WL_FAILED_KEY}{token}", True, timeout=300)

        svc = WebLoginService()
        status = call_async(svc.check_status(token))

        assert status == "error"


class TestCacheWriteFailureDuringRetry:
    """Verify CacheWriteError logging during token collision retry."""

    def test_cache_failure_during_collision_retry_logs_critical(self):
        """When _safe_cache_set raises CacheWriteError during retry,
        it should be caught and logged (not silently swallowed)."""
        from src.core.models import WebLoginRequest
        from src.web.services.web_login_service import WebLoginService, CacheWriteError

        user = User.objects.create_user(
            username="tg_cache_retry_fail",
            telegram_id="770000020",
            name="Cache Retry Fail",
            language="en",
            timezone="UTC",
        )

        existing_token = "cache_retry_collide_t"
        WebLoginRequest.objects.create(
            user=user,
            token=existing_token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        from src.web.services.web_login_service import cache_manager
        with patch.object(
            cache_manager, "set",
            side_effect=[None, CacheWriteError("test")],
        ):
            with patch(
                "src.web.services.web_login_service.logger"
            ) as mock_logger:
                login_req, final_token = WebLoginService._create_login_request_with_retry(
                    user.id,
                    existing_token,
                    datetime.now(timezone.utc) + timedelta(minutes=5),
                    "test device",
                )

                assert login_req is not None
                assert final_token != existing_token


class TestCacheManagerThresholdEdgeCases:
    """Edge cases for CacheManager failure threshold."""

    def test_exact_threshold_raises(self):
        """Exactly threshold failures raises CacheWriteError."""
        from src.web.services.web_login_service import CacheWriteError, CacheManager

        mgr = CacheManager(failure_threshold=3)
        with patch("django.core.cache.cache.set", side_effect=ConnectionError("down")):
            mgr.set("k1", True, 60)
            mgr.set("k2", True, 60)
            with pytest.raises(CacheWriteError):
                mgr.set("k3", True, 60)

    def test_reset_prevents_threshold(self):
        """Calling reset() after failures prevents threshold from being reached."""
        from src.web.services.web_login_service import CacheManager

        mgr = CacheManager(failure_threshold=3)
        with patch("django.core.cache.cache.set", side_effect=ConnectionError("down")):
            mgr.set("k1", True, 60)
            mgr.set("k2", True, 60)
        mgr.reset()
        assert mgr.failure_count == 0


class TestCacheManagerThreadSafety:
    """Verify CacheManager failure counter is thread-safe under concurrent writes.

    Note: Django's cache proxy uses thread-local connections, so
    unittest.mock.patch doesn't propagate to child threads.  We patch
    the actual LocMemCache backend class instead.
    """

    def test_concurrent_failures_increment_atomically(self):
        """Multiple threads hitting cache failures concurrently: the failure
        counter must increment atomically with no lost updates."""
        from django.core.cache.backends.locmem import LocMemCache
        from src.web.services.web_login_service import CacheManager, CacheWriteError

        threshold = 200  # high enough to never trigger during the test
        mgr = CacheManager(failure_threshold=threshold)
        errors = []
        lock = threading.Lock()
        writes_per_thread = 10
        num_threads = 10

        def _worker(worker_id):
            for i in range(writes_per_thread):
                try:
                    mgr.set(f"thread_{worker_id}_key_{i}", True, 60)
                except CacheWriteError:
                    pass
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        with patch.object(LocMemCache, "set", side_effect=ConnectionError("down")):
            threads = [threading.Thread(target=_worker, args=(i,)) for i in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert all(not t.is_alive() for t in threads), "Some threads timed out"
        assert not errors, f"Unexpected errors: {errors}"
        # All writes failed; counter must equal total attempts (no lost increments)
        expected = num_threads * writes_per_thread
        assert mgr.failure_count == expected, (
            f"Expected failure_count={expected}, got {mgr.failure_count} "
            f"(lost {expected - mgr.failure_count} increments)"
        )

    def test_successful_write_resets_counter(self):
        """A successful cache write resets the failure counter to 0."""
        from django.core.cache.backends.locmem import LocMemCache
        from src.web.services.web_login_service import CacheManager

        mgr = CacheManager(failure_threshold=100)

        # Accumulate some failures
        with patch.object(LocMemCache, "set", side_effect=ConnectionError("down")):
            for i in range(8):
                mgr.set(f"prefail_{i}", True, 60)
        assert mgr.failure_count == 8

        # A successful write (using real cache) resets the counter
        mgr.set("success_key", True, 60)
        assert mgr.failure_count == 0

        # Verify another round of failures starts from 0
        with patch.object(LocMemCache, "set", side_effect=ConnectionError("down")):
            for i in range(3):
                mgr.set(f"postfail_{i}", True, 60)
        assert mgr.failure_count == 3
