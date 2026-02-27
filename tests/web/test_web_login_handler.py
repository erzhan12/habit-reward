"""Tests for bot web login callback handler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async

from src.core.models import User, WebLoginRequest
from src.core.repositories import WebLoginRequestRepository

pytestmark = pytest.mark.django_db


@pytest.fixture
def handler_user():
    """Create a user for handler tests."""
    return User.objects.create_user(
        username="tg_555555555",
        telegram_id="555555555",
        name="Handler User",
        language="en",
        timezone="UTC",
    )


@pytest.fixture
def pending_login(handler_user):
    """Create a pending WebLoginRequest."""
    return WebLoginRequest.objects.create(
        user=handler_user,
        token="handler_test_token_aaa",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


@pytest.fixture
def expired_login(handler_user):
    """Create an expired WebLoginRequest."""
    return WebLoginRequest.objects.create(
        user=handler_user,
        token="handler_expired_token",
        status="pending",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


@pytest.fixture
def confirmed_login(handler_user):
    """Create a confirmed (already processed) WebLoginRequest."""
    return WebLoginRequest.objects.create(
        user=handler_user,
        token="handler_confirmed_tkn",
        status="confirmed",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def _make_update(user_id, callback_data):
    """Build a mock Telegram Update for callback queries."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


async def _refresh(obj):
    """Async-safe refresh_from_db."""
    await sync_to_async(obj.refresh_from_db)()


class TestWebLoginCallback:
    """Tests for web_login_callback handler logic."""

    @pytest.mark.asyncio
    async def test_confirm_success(self, handler_user, pending_login):
        """Owner confirms a pending request — status becomes confirmed."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{pending_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(pending_login)
        assert pending_login.status == "confirmed"
        update.callback_query.edit_message_text.assert_awaited_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "confirmed" in msg.lower() or "\u2705" in msg

    @pytest.mark.asyncio
    async def test_deny_success(self, handler_user, pending_login):
        """Owner denies a pending request — status becomes denied."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_d_{pending_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(pending_login)
        assert pending_login.status == "denied"
        update.callback_query.edit_message_text.assert_awaited_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "denied" in msg.lower() or "\u274c" in msg

    @pytest.mark.asyncio
    async def test_non_owner_cannot_confirm(self, handler_user, pending_login):
        """A different user pressing Confirm is rejected silently."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            999999999,  # different user
            f"wl_c_{pending_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(pending_login)
        assert pending_login.status == "pending"  # unchanged

    @pytest.mark.asyncio
    async def test_expired_request(self, handler_user, expired_login):
        """Confirming an expired request shows expiry message."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{expired_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(expired_login)
        assert expired_login.status == "pending"  # unchanged
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "expired" in msg.lower()

    @pytest.mark.asyncio
    async def test_already_confirmed_request(self, handler_user, confirmed_login):
        """Pressing Confirm on an already-confirmed request shows 'already processed'."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{confirmed_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(confirmed_login)
        assert confirmed_login.status == "confirmed"  # unchanged
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "already" in msg.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_token(self, handler_user):
        """Callback with unknown token shows 'not found' message."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            "wl_c_nonexistent_token_xyz",
        )
        await web_login_callback(update, MagicMock())

        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "expired" in msg.lower() or "not found" in msg.lower()

    @pytest.mark.asyncio
    async def test_invalid_status_in_db(self, handler_user):
        """A login request with invalid status in DB shows error message."""
        from src.bot.handlers.web_login_handler import web_login_callback

        login_req = await sync_to_async(WebLoginRequest.objects.create)(
            user=handler_user,
            token="handler_invalid_status",
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        # Force invalid status directly in DB (bypasses Django choices validation)
        await sync_to_async(
            WebLoginRequest.objects.filter(pk=login_req.pk).update
        )(status="bogus")

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{login_req.token}",
        )
        await web_login_callback(update, MagicMock())

        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "invalid" in msg.lower()

    def test_pattern_does_not_match_unrelated_callback(self):
        """Callback data that doesn't match WEB_LOGIN_PATTERN is ignored."""
        from src.bot.handlers.web_login_handler import WEB_LOGIN_PATTERN

        assert WEB_LOGIN_PATTERN.match("some_other_callback") is None
        assert WEB_LOGIN_PATTERN.match("wl_x_something") is None
        assert WEB_LOGIN_PATTERN.match("wl_c_token123") is not None
        assert WEB_LOGIN_PATTERN.match("wl_d_token123") is not None

    @pytest.mark.asyncio
    async def test_confirm_race_condition_second_call_gets_zero(self, handler_user, pending_login):
        """If two confirmations race, the second gets updated==0 and shows 'already processed'."""
        from src.bot.handlers.web_login_handler import web_login_callback

        # First confirm
        update1 = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{pending_login.token}",
        )
        await web_login_callback(update1, MagicMock())

        await _refresh(pending_login)
        assert pending_login.status == "confirmed"

        # Second confirm (same token, already confirmed)
        update2 = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{pending_login.token}",
        )
        await web_login_callback(update2, MagicMock())

        msg = update2.callback_query.edit_message_text.call_args[0][0]
        assert "already" in msg.lower()
