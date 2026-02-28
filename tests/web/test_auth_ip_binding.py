"""Tests for IP binding and address parsing."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

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


class TestIPBindingMismatch:
    """Tests for IP binding enforcement on status polling and login completion.

    Tokens are bound to the originating IP at creation time.  Requests from
    a different IP must be rejected to prevent cross-IP token theft.
    """

    def test_status_poll_from_different_ip_returns_expired(self):
        """Polling token status from a different IP than creation returns 'expired'."""
        # Create binding for IP A (default 127.0.0.1)
        _create_ip_binding(token=_TEST_TOKEN, ip="10.0.0.1")
        # Poll from IP B (Django test client uses 127.0.0.1 by default)
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    def test_complete_from_different_ip_returns_403(self):
        """Completing login from a different IP than creation returns 403."""
        # Create binding for IP A
        _create_ip_binding(token=_TEST_TOKEN, ip="10.0.0.1")
        # Complete from IP B (Django test client uses 127.0.0.1)
        response = Client().post(
            "/auth/bot-login/complete/",
            data={"token": _TEST_TOKEN},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert "expired or invalid" in response.json()["error"]

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed"))
    def test_status_poll_from_same_ip_succeeds(self, mock_async):
        """Polling from the same IP that created the token succeeds."""
        _create_ip_binding(token=_TEST_TOKEN, ip=_TEST_IP)
        response = Client().get(f"/auth/bot-login/status/{_TEST_TOKEN}/")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_complete_from_same_ip_with_confirmed_token_succeeds(self, user):
        """Completing login from the same IP succeeds when token is confirmed."""
        _create_ip_binding(token=_TEST_TOKEN, ip=_TEST_IP)
        with patch("src.web.views.auth.call_async", side_effect=_call_async_mock(user)):
            response = Client().post(
                "/auth/bot-login/complete/",
                data={"token": _TEST_TOKEN},
                content_type="application/json",
            )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestIPBindingEnforcement:
    """Verify database-backed IP binding prevents cross-IP attacks."""

    def test_bot_login_complete_rejects_mismatched_ip(self, user):
        """Create token from IP A, confirm, then complete from IP B -> 403.

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
        """Complete from same IP as token creator -> 200 success."""
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
        """Status poll from different IP than token creator -> expired."""
        token = _TEST_TOKEN
        _create_ip_binding(token=token, ip="10.0.0.1")  # Bind to IP A
        # Poll from IP B (127.0.0.1 default)
        response = Client().get(f"/auth/bot-login/status/{token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

    @patch("src.web.views.auth.call_async", side_effect=_call_async_mock("confirmed"))
    def test_bot_login_status_accepts_matching_ip(self, mock_async):
        """Status poll from same IP as token creator -> actual status."""
        token = _TEST_TOKEN
        _create_ip_binding(token=token, ip=_TEST_IP)
        response = Client().get(f"/auth/bot-login/status/{token}/")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_bot_login_complete_no_binding_returns_403(self):
        """Complete with no IP binding record -> 403."""
        token = _TEST_TOKEN
        # No binding created
        response = Client().post(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403


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


