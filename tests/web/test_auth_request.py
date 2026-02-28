"""Tests for bot login request initiation endpoint."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.test import Client

from src.core.models import LoginTokenIpBinding
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
    """Auth view tests for bot-based login — request initiation subset."""

    def setup_method(self):
        """Clear rate limit counters between tests."""
        from django.core.cache import cache
        cache.clear()

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

    def test_bot_login_request_rejects_array_body(self):
        """POST with JSON array (not object) returns 400, not 500."""
        response = Client().post(
            "/auth/bot-login/request/",
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
            REMOTE_ADDR="198.51.100.41",
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
