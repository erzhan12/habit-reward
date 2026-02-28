"""Tests for login completion and replay prevention."""

import json
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.test import Client

from src.core.models import LoginTokenIpBinding, User
from src.web.services.web_login_service import WL_PENDING_KEY
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


class TestAuthComplete:
    """Auth view tests for bot-based login — completion subset."""

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

    def test_bot_login_complete_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )
        assert response.status_code == 400

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock(None))
    def test_bot_login_complete_non_string_token(self, mock_async):
        """Non-string token (e.g. integer) returns 403/400, not 500."""
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": 12345}),
            content_type="application/json",
        )
        assert response.status_code in (400, 403)


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


class TestConcurrentDoubleClickConfirmDeny:
    """Verify that double-clicking Confirm/Deny buttons only transitions status once.

    Uses the SELECT FOR UPDATE lock in web_login_handler._atomic_status_transition
    to ensure that concurrent button presses result in exactly one state change.
    """

    def test_double_click_confirm_only_one_transition(self):
        """Simulating rapid double-click on Confirm — only one transitions to confirmed."""
        from django.db import transaction
        from src.core.models import WebLoginRequest

        user = User.objects.create_user(
            username="tg_doubleclick",
            telegram_id="880200001",
            name="Double Click",
            language="en",
            timezone="UTC",
        )

        token = "doubleclick_confirm_tok_aaaaaabbbbbbcccccc"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        def _atomic_status_transition(new_status):
            """Replica of web_login_handler._atomic_status_transition."""
            with transaction.atomic():
                try:
                    lr = (
                        WebLoginRequest.objects
                        .select_for_update()
                        .get(token=token)
                    )
                except WebLoginRequest.DoesNotExist:
                    return 0, None
                if lr.status != WebLoginRequest.Status.PENDING.value:
                    return 0, lr.status
                lr.status = new_status
                lr.save(update_fields=['status'])
                return 1, new_status

        confirmed = WebLoginRequest.Status.CONFIRMED.value
        results = [
            _atomic_status_transition(confirmed)
            for _ in range(3)
        ]

        successes = [r for r in results if r[0] == 1]
        failures = [r for r in results if r[0] == 0]

        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(failures) == 2
        assert successes[0][1] == confirmed

        lr = WebLoginRequest.objects.get(token=token)
        assert lr.status == confirmed

    def test_double_click_confirm_then_deny_only_first_wins(self):
        """Simulating Confirm followed by Deny — only first transition wins."""
        from django.db import transaction
        from src.core.models import WebLoginRequest

        user = User.objects.create_user(
            username="tg_doubleclick2",
            telegram_id="880200002",
            name="Double Click 2",
            language="en",
            timezone="UTC",
        )

        token = "doubleclick_mixed_tok_aaaaaabbbbbbccccccc"
        WebLoginRequest.objects.create(
            user=user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        def _atomic_status_transition(new_status):
            with transaction.atomic():
                try:
                    lr = (
                        WebLoginRequest.objects
                        .select_for_update()
                        .get(token=token)
                    )
                except WebLoginRequest.DoesNotExist:
                    return 0, None
                if lr.status != WebLoginRequest.Status.PENDING.value:
                    return 0, lr.status
                lr.status = new_status
                lr.save(update_fields=['status'])
                return 1, new_status

        confirmed = WebLoginRequest.Status.CONFIRMED.value
        denied = WebLoginRequest.Status.DENIED.value

        # First: Confirm wins
        r1 = _atomic_status_transition(confirmed)
        # Second: Deny is rejected
        r2 = _atomic_status_transition(denied)

        assert r1 == (1, confirmed)
        assert r2 == (0, confirmed)  # sees confirmed, can't transition

        lr = WebLoginRequest.objects.get(token=token)
        assert lr.status == confirmed
