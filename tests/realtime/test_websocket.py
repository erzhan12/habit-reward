"""Tests for WebSocket authentication and endpoint behavior."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.realtime.websocket import _authenticate_websocket, router
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


def _build_test_app():
    """Build a minimal FastAPI app with just the ws router for testing."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


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

    with _patch_auth_invalid():
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
        patch("src.realtime.websocket.connection_manager", manager),
    ):
        client = TestClient(app)
        with client.websocket_connect("/ws/updates/"):
            assert 9 in manager._connections

        # After context exit (disconnect), connection should be cleaned up
        assert 9 not in manager._connections
