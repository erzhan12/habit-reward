"""Tests for the WebSocket connection manager."""

import pytest
from unittest.mock import AsyncMock

from src.realtime.manager import ConnectionManager


def _make_mock_ws():
    """Create a mock WebSocket with async methods."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_registers_websocket():
    manager = ConnectionManager()
    ws = _make_mock_ws()

    await manager.connect(1, ws)

    ws.accept.assert_awaited_once()
    assert ws in manager._connections[1]


@pytest.mark.asyncio
async def test_disconnect_removes_websocket():
    manager = ConnectionManager()
    ws = _make_mock_ws()

    await manager.connect(1, ws)
    await manager.disconnect(1, ws)

    assert 1 not in manager._connections


@pytest.mark.asyncio
async def test_notify_user_sends_message():
    manager = ConnectionManager()
    ws = _make_mock_ws()

    await manager.connect(1, ws)
    await manager.notify_user(1, "dashboard_update")

    ws.send_json.assert_awaited_once_with({"type": "dashboard_update"})


@pytest.mark.asyncio
async def test_notify_user_no_connections():
    """Notifying a user with no connections should not raise."""
    manager = ConnectionManager()
    await manager.notify_user(999)  # No error


@pytest.mark.asyncio
async def test_notify_removes_dead_connections():
    manager = ConnectionManager()
    ws = _make_mock_ws()
    ws.send_json.side_effect = RuntimeError("connection closed")

    await manager.connect(1, ws)
    await manager.notify_user(1)

    assert 1 not in manager._connections


@pytest.mark.asyncio
async def test_multiple_connections_per_user():
    manager = ConnectionManager()
    ws1 = _make_mock_ws()
    ws2 = _make_mock_ws()

    await manager.connect(1, ws1)
    await manager.connect(1, ws2)
    await manager.notify_user(1)

    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_only_target_user():
    manager = ConnectionManager()
    ws1 = _make_mock_ws()
    ws2 = _make_mock_ws()

    await manager.connect(1, ws1)
    await manager.connect(2, ws2)
    await manager.notify_user(1)

    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_disconnect_nonexistent_user():
    """Disconnecting a user that was never connected should not raise."""
    manager = ConnectionManager()
    ws = _make_mock_ws()
    await manager.disconnect(999, ws)  # No error


@pytest.mark.asyncio
async def test_default_event_type():
    manager = ConnectionManager()
    ws = _make_mock_ws()

    await manager.connect(1, ws)
    await manager.notify_user(1)  # No event_type arg

    ws.send_json.assert_awaited_once_with({"type": "dashboard_update"})
