"""Tests for WebSocket authentication and endpoint behavior."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.realtime.websocket import (
    _authenticate_websocket,
    _check_rate_limit,
    _connection_attempts,
    _validate_origin,
    _MAX_RATE_LIMITER_ENTRIES,
    router,
)
from src.realtime.manager import ConnectionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_websocket(session_cookie=None):
    """Create a mock WebSocket with cookies."""
    ws = AsyncMock()
    ws.cookies = {}
    if session_cookie:
        ws.cookies["sessionid"] = session_cookie
    ws.close = AsyncMock()
    return ws


def _patch_auth_valid(user_id=42):
    """Context manager that makes _authenticate_websocket return user_id."""
    return patch(
        "src.realtime.websocket._authenticate_websocket",
        new_callable=AsyncMock,
        return_value=user_id,
    )


def _patch_auth_invalid():
    """Context manager that makes _authenticate_websocket return None."""
    return patch(
        "src.realtime.websocket._authenticate_websocket",
        new_callable=AsyncMock,
        return_value=None,
    )


def _patch_origin_valid():
    """Context manager that makes _validate_origin return True."""
    return patch(
        "src.realtime.websocket._validate_origin",
        return_value=True,
    )


def _build_test_app():
    """Build a minimal FastAPI app with just the ws router for testing."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Unit tests: _validate_origin
# ---------------------------------------------------------------------------

def _make_origin_ws(origin=None):
    """Create a mock WebSocket with an Origin header."""
    ws = MagicMock()
    headers = {}
    if origin is not None:
        headers["origin"] = origin
    ws.headers = headers
    return ws


def test_validate_origin_missing_header():
    """Missing Origin header returns False."""
    ws = _make_origin_ws(origin=None)
    assert _validate_origin(ws) is False


def test_validate_origin_matching_host(settings):
    """Origin matching an entry in ALLOWED_HOSTS returns True."""
    settings.ALLOWED_HOSTS = ["example.com"]
    settings.DEBUG = False
    ws = _make_origin_ws(origin="https://example.com")
    assert _validate_origin(ws) is True


def test_validate_origin_wildcard_debug_true(settings):
    """Wildcard '*' in ALLOWED_HOSTS returns True when DEBUG=True."""
    settings.ALLOWED_HOSTS = ["*"]
    settings.DEBUG = True
    ws = _make_origin_ws(origin="https://anything.test")
    assert _validate_origin(ws) is True


def test_validate_origin_wildcard_debug_false(settings):
    """Wildcard '*' in ALLOWED_HOSTS is ignored when DEBUG=False."""
    settings.ALLOWED_HOSTS = ["*"]
    settings.DEBUG = False
    ws = _make_origin_ws(origin="https://anything.test")
    assert _validate_origin(ws) is False


def test_validate_origin_not_in_allowed_hosts(settings):
    """Origin not in ALLOWED_HOSTS returns False."""
    settings.ALLOWED_HOSTS = ["example.com"]
    settings.DEBUG = False
    ws = _make_origin_ws(origin="https://evil.com")
    assert _validate_origin(ws) is False


def test_validate_origin_subdomain_matching(settings):
    """Subdomain pattern '.example.com' matches sub.example.com and example.com."""
    settings.ALLOWED_HOSTS = [".example.com"]
    settings.DEBUG = False

    # Subdomain should match
    ws_sub = _make_origin_ws(origin="https://sub.example.com")
    assert _validate_origin(ws_sub) is True

    # Bare domain should also match
    ws_bare = _make_origin_ws(origin="https://example.com")
    assert _validate_origin(ws_bare) is True

    # Unrelated domain should not match
    ws_other = _make_origin_ws(origin="https://notexample.com")
    assert _validate_origin(ws_other) is False


# ---------------------------------------------------------------------------
# Unit tests: _authenticate_websocket
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticate_no_session_cookie():
    ws = _make_mock_websocket(session_cookie=None)
    result = await _authenticate_websocket(ws)
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_invalid_session():
    """Session key that doesn't resolve to a user."""
    ws = _make_mock_websocket(session_cookie="nonexistent-session-key")

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {}  # No _auth_user_id
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
    ):
        result = await _authenticate_websocket(ws)

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_valid_session():
    """Valid session with active user."""
    ws = _make_mock_websocket(session_cookie="valid-session-key")

    mock_user = MagicMock()
    mock_user.is_active = True
    mock_user.id = 42

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {"_auth_user_id": "42"}
    mock_session.get_expiry_age.return_value = 3600
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
        patch("src.realtime.websocket.user_repository") as mock_repo,
        patch("src.realtime.websocket.maybe_await", new_callable=AsyncMock, return_value=mock_user),
    ):
        mock_repo.get_by_id = MagicMock(return_value=mock_user)
        result = await _authenticate_websocket(ws)

    assert result == 42


@pytest.mark.asyncio
async def test_authenticate_inactive_user():
    """Valid session but user is inactive."""
    ws = _make_mock_websocket(session_cookie="valid-session-key")

    mock_user = MagicMock()
    mock_user.is_active = False

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {"_auth_user_id": "42"}
    mock_session.get_expiry_age.return_value = 3600
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
        patch("src.realtime.websocket.user_repository") as mock_repo,
        patch("src.realtime.websocket.maybe_await", new_callable=AsyncMock, return_value=mock_user),
    ):
        mock_repo.get_by_id = MagicMock(return_value=mock_user)
        result = await _authenticate_websocket(ws)

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Valid session but user doesn't exist in DB."""
    ws = _make_mock_websocket(session_cookie="valid-session-key")

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {"_auth_user_id": "42"}
    mock_session.get_expiry_age.return_value = 3600
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
        patch("src.realtime.websocket.user_repository") as mock_repo,
        patch("src.realtime.websocket.maybe_await", new_callable=AsyncMock, return_value=None),
    ):
        mock_repo.get_by_id = MagicMock(return_value=None)
        result = await _authenticate_websocket(ws)

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_expired_session():
    """Expired session (expiry_age <= 0) should return None."""
    ws = _make_mock_websocket(session_cookie="expired-session-key")

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {"_auth_user_id": "42"}
    mock_session.get_expiry_age.return_value = 0
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
    ):
        result = await _authenticate_websocket(ws)

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_exception_returns_none():
    """Any exception during auth should return None, not crash."""
    ws = _make_mock_websocket(session_cookie="valid-session-key")

    with patch("src.realtime.websocket.import_module", side_effect=Exception("boom")):
        result = await _authenticate_websocket(ws)

    assert result is None


# ---------------------------------------------------------------------------
# Integration tests: WebSocket endpoint via TestClient
# ---------------------------------------------------------------------------

def test_endpoint_rejects_unauthenticated():
    """Unauthenticated WebSocket should be closed with code 4401."""
    app = _build_test_app()

    with _patch_auth_invalid(), _patch_origin_valid():
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/updates/"):
                pass
        assert exc_info.value.code == 4401


def test_endpoint_accepts_authenticated():
    """Authenticated WebSocket should be accepted and receive messages."""
    app = _build_test_app()
    manager = ConnectionManager()

    with (
        _patch_auth_valid(user_id=7),
        _patch_origin_valid(),
        patch("src.realtime.websocket.connection_manager", manager),
    ):
        client = TestClient(app)
        with client.websocket_connect("/ws/updates/") as ws:
            # Connection accepted — verify we're registered
            assert 7 in manager._connections

            # Simulate server sending a notification
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(manager.notify_user(7))
            loop.close()

            data = ws.receive_json()
            assert data == {"type": "dashboard_update"}


def test_endpoint_sends_ping():
    """Server should send periodic pings (test with 0-second interval)."""
    app = _build_test_app()
    manager = ConnectionManager()

    with (
        _patch_auth_valid(user_id=8),
        _patch_origin_valid(),
        patch("src.realtime.websocket.connection_manager", manager),
        patch("src.realtime.websocket.PING_INTERVAL_SECONDS", 0),
    ):
        client = TestClient(app)
        with client.websocket_connect("/ws/updates/") as ws:
            data = ws.receive_json()
            assert data == {"type": "ping"}


def test_endpoint_cleans_up_on_disconnect():
    """After client disconnects, connection should be removed from manager."""
    app = _build_test_app()
    manager = ConnectionManager()

    with (
        _patch_auth_valid(user_id=9),
        _patch_origin_valid(),
        patch("src.realtime.websocket.connection_manager", manager),
    ):
        client = TestClient(app)
        with client.websocket_connect("/ws/updates/"):
            assert 9 in manager._connections

        # After context exit (disconnect), connection should be cleaned up
        assert 9 not in manager._connections


# ---------------------------------------------------------------------------
# Rate limiter eviction tests
# ---------------------------------------------------------------------------

def test_endpoint_origin_and_auth_full_chain(settings):
    """Integration test: origin validation + session auth without patching either.

    Exercises the full security chain by configuring Django settings and
    mocking the session engine at a lower level.
    """
    settings.ALLOWED_HOSTS = ["testserver"]
    settings.DEBUG = False

    app = _build_test_app()
    manager = ConnectionManager()

    mock_user = MagicMock()
    mock_user.is_active = True
    mock_user.id = 55

    mock_engine = MagicMock()
    mock_session = MagicMock()
    mock_session.load.return_value = {"_auth_user_id": "55"}
    mock_session.get_expiry_age.return_value = 3600
    mock_engine.SessionStore.return_value = mock_session

    with (
        patch("src.realtime.websocket.import_module", return_value=mock_engine),
        patch("src.realtime.websocket.sync_to_async", side_effect=lambda fn: AsyncMock(return_value=fn())),
        patch("src.realtime.websocket.maybe_await", new_callable=AsyncMock, return_value=mock_user),
        patch("src.realtime.websocket.connection_manager", manager),
    ):
        client = TestClient(app, cookies={"sessionid": "real-session-key"})
        with client.websocket_connect(
            "/ws/updates/",
            headers={"origin": "https://testserver"},
        ) as ws:
            assert 55 in manager._connections

            # Send a notification through the full chain
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(manager.notify_user(55))
            loop.close()

            data = ws.receive_json()
            assert data == {"type": "dashboard_update"}


def test_endpoint_origin_and_auth_rejects_bad_origin(settings):
    """Integration test: valid auth but bad origin should reject."""
    settings.ALLOWED_HOSTS = ["goodhost.com"]
    settings.DEBUG = False

    app = _build_test_app()

    with pytest.raises(WebSocketDisconnect) as exc_info:
        client = TestClient(app, cookies={"sessionid": "real-session-key"})
        with client.websocket_connect(
            "/ws/updates/",
            headers={"origin": "https://evil.com"},
        ):
            pass
    assert exc_info.value.code == 4403


def test_rate_limiter_evicts_oldest_entry():
    """When _connection_attempts reaches _MAX_RATE_LIMITER_ENTRIES, oldest entry is evicted."""
    import time
    # Clear global state
    _connection_attempts.clear()

    try:
        # Fill rate limiter to capacity with unique IPs
        base_time = time.monotonic()
        for i in range(_MAX_RATE_LIMITER_ENTRIES):
            ip = f"10.0.{i // 256}.{i % 256}"
            _connection_attempts[ip] = [base_time + i]

        oldest_ip = "10.0.0.0"
        assert oldest_ip in _connection_attempts

        # One more connection should trigger eviction of the oldest
        new_ip = "192.168.1.1"
        result = _check_rate_limit(new_ip)

        assert result is True
        assert new_ip in _connection_attempts
        assert oldest_ip not in _connection_attempts
        assert len(_connection_attempts) <= _MAX_RATE_LIMITER_ENTRIES
    finally:
        _connection_attempts.clear()
