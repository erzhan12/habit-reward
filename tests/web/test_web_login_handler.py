"""Tests for bot web login callback handler."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async
from django.test import Client

from src.core.models import User, WebLoginRequest
from src.core.repositories import WebLoginRequestRepository, web_login_request_repository
from src.web.services.web_login_service import WL_PENDING_KEY

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
        token="handler_test_token_aaa_padded_to_43chars_x",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


@pytest.fixture
def expired_login(handler_user):
    """Create an expired WebLoginRequest."""
    return WebLoginRequest.objects.create(
        user=handler_user,
        token="handler_expired_token_padded_to_43chars_xx",
        status="pending",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


@pytest.fixture
def confirmed_login(handler_user):
    """Create a confirmed (already processed) WebLoginRequest."""
    return WebLoginRequest.objects.create(
        user=handler_user,
        token="handler_confirmed_tkn_padded_to_43chars_xx",
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
    async def test_web_login_callback_already_used_status(self, handler_user):
        """Pressing Confirm on an already-used request shows 'already completed'."""
        from src.bot.handlers.web_login_handler import web_login_callback

        used_login = await sync_to_async(WebLoginRequest.objects.create)(
            user=handler_user,
            token="handler_used_token_padded_to_43chars_xxxxx",
            status="used",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        update = _make_update(
            int(handler_user.telegram_id),
            f"wl_c_{used_login.token}",
        )
        await web_login_callback(update, MagicMock())

        await _refresh(used_login)
        assert used_login.status == "used"  # unchanged
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "already completed" in msg.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_token(self, handler_user):
        """Callback with unknown token shows 'not found' message."""
        from src.bot.handlers.web_login_handler import web_login_callback

        update = _make_update(
            int(handler_user.telegram_id),
            "wl_c_nonexistent_token_xyz_padded_to_43chars_x",
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
            token="handler_invalid_status_padded_to_43char_xx",
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


class TestSimultaneousButtonPress:
    """Verify the atomic WHERE clause prevents double-confirm/deny races.

    The ``update_status`` repository method uses
    ``WebLoginRequest.objects.filter(token=..., status='pending').update(...)``
    which is atomic at the DB level.  When two handlers call it concurrently,
    exactly one gets ``updated == 1`` and the other gets ``updated == 0``.
    """

    @pytest.mark.asyncio
    async def test_concurrent_confirm_only_one_succeeds(self, handler_user, pending_login):
        """Two concurrent confirm calls — only one succeeds at the DB level."""
        token = pending_login.token

        # Call update_status concurrently from two tasks
        results = await asyncio.gather(
            web_login_request_repository.update_status(token, "confirmed"),
            web_login_request_repository.update_status(token, "confirmed"),
        )

        # Exactly one should return 1 (success), the other 0 (already handled)
        assert sorted(results) == [0, 1]

        await _refresh(pending_login)
        assert pending_login.status == "confirmed"

    @pytest.mark.asyncio
    async def test_concurrent_confirm_and_deny_only_one_wins(self, handler_user, pending_login):
        """Concurrent confirm + deny — only one wins, the other gets 0."""
        token = pending_login.token

        results = await asyncio.gather(
            web_login_request_repository.update_status(token, "confirmed"),
            web_login_request_repository.update_status(token, "denied"),
        )

        assert sorted(results) == [0, 1]

        await _refresh(pending_login)
        assert pending_login.status in ("confirmed", "denied")


class TestEndToEndLoginFlowWithBotHandler:
    """Integration test: create request → poll pending → bot confirms → poll confirmed → complete → session.

    Exercises the real bot handler callback (web_login_callback) as the
    confirmation step, verifying the complete login flow end-to-end.
    """

    @pytest.fixture
    def e2e_user(self):
        """Create a user for end-to-end flow tests."""
        return User.objects.create_user(
            username="tg_e2e_flow",
            telegram_id="888888888",
            name="E2E Flow User",
            language="en",
            timezone="UTC",
            telegram_username="e2eflowuser",
        )

    @pytest.mark.asyncio
    async def test_full_flow_create_poll_confirm_complete(self, e2e_user):
        """End-to-end: create DB record → poll pending → bot confirm → poll confirmed → complete → session."""
        from django.core.cache import cache
        from src.bot.handlers.web_login_handler import web_login_callback
        from src.web.services.web_login_service import WebLoginService
        from src.web.utils.sync import call_async

        cache.clear()
        svc = WebLoginService()
        client = Client()

        token = "e2e_flow_token_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        # 1. Create login request in DB + cache (simulating background thread)
        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)
        login_request = await sync_to_async(WebLoginRequest.objects.create)(
            user=e2e_user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )

        # 2. Poll status — should be "pending"
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = await svc.check_status(token)
        assert status == "pending"

        # 3. Bot handler: user presses Confirm button
        update = _make_update(int(e2e_user.telegram_id), f"wl_c_{token}")
        await web_login_callback(update, MagicMock())

        await _refresh(login_request)
        assert login_request.status == "confirmed"

        # 4. Poll status — should be "confirmed"
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = await svc.check_status(token)
        assert status == "confirmed"

        # 5. Complete login via HTTP endpoint
        response = await sync_to_async(client.post)(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True

        # 6. Verify session — user is authenticated
        response = await sync_to_async(client.get)("/auth/login/")
        # Authenticated users get redirected away from login page
        assert response.status_code == 302

        # 7. Verify token is marked as "used" (replay protection)
        await _refresh(login_request)
        assert login_request.status == "used"

        # 8. Replay attempt — should fail with 403
        response = await sync_to_async(client.post)(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_full_flow_deny_prevents_completion(self, e2e_user):
        """End-to-end: create → bot denies → complete fails."""
        from django.core.cache import cache
        from src.bot.handlers.web_login_handler import web_login_callback
        from src.web.services.web_login_service import WebLoginService

        cache.clear()
        svc = WebLoginService()
        client = Client()

        token = "e2e_deny_token_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        cache.set(f"{WL_PENDING_KEY}{token}", True, timeout=300)
        await sync_to_async(WebLoginRequest.objects.create)(
            user=e2e_user,
            token=token,
            status=WebLoginRequest.Status.PENDING,
            expires_at=expires_at,
        )

        # Bot handler: user presses Deny button
        update = _make_update(int(e2e_user.telegram_id), f"wl_d_{token}")
        await web_login_callback(update, MagicMock())

        # Poll status — should be "denied"
        with patch("src.web.services.web_login_service.asyncio.sleep", new_callable=AsyncMock):
            status = await svc.check_status(token)
        assert status == "denied"

        # Complete login — should fail (not confirmed)
        response = await sync_to_async(client.post)(
            "/auth/bot-login/complete/",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert response.status_code == 403
