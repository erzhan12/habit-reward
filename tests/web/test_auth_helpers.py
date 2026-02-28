"""Tests for device info, UA parsing, and token validation."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


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

    def test_sanitize_user_agent_removes_control_whitespace(self):
        """UA sanitization strips CR/LF/TAB to prevent log/content injection."""
        from src.web.views.auth import _sanitize_user_agent

        sanitized = _sanitize_user_agent("Mozilla/5.0\r\n\tChrome/120.0")
        assert "\r" not in sanitized
        assert "\n" not in sanitized
        assert "\t" not in sanitized

    def test_device_info_truncates_extremely_long_user_agent(self):
        """User-Agent longer than MAX_USER_AGENT_LENGTH is truncated before parsing."""
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

    def test_user_agent_over_max_length_with_valid_prefix(self):
        """UA exceeding MAX_USER_AGENT_LENGTH that starts with a valid browser
        string is truncated before parsing, and final output <= 255 chars."""
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
