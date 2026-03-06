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
async def test_connect_rejects_over_limit():
    """Exceeding MAX_CONNECTIONS_PER_USER should close the websocket."""
    manager = ConnectionManager()
    manager.MAX_CONNECTIONS_PER_USER = 2

    ws1 = _make_mock_ws()
    ws2 = _make_mock_ws()
    ws3 = _make_mock_ws()

    assert await manager.connect(1, ws1) is True
    assert await manager.connect(1, ws2) is True
    assert await manager.connect(1, ws3) is False

    ws3.close.assert_awaited_once_with(code=4429)
    ws3.accept.assert_not_awaited()
    assert len(manager._connections[1]) == 2


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


@pytest.mark.asyncio
async def test_notify_dead_connection_after_disconnect_no_negative_counter():
    """Verify _total_connections doesn't go negative when disconnect() and
    notify_user() both try to remove the same dead WebSocket."""
    manager = ConnectionManager()
    ws = _make_mock_ws()
    ws.send_json.side_effect = RuntimeError("connection closed")

    await manager.connect(1, ws)
    assert manager._total_connections == 1

    # disconnect removes ws first
    await manager.disconnect(1, ws)
    assert manager._total_connections == 0

    # Re-add user with empty set to simulate timing window
    # notify_user should not decrement because ws is no longer in the set
    manager._connections[1] = set()
    await manager.notify_user(1)
    assert manager._total_connections == 0  # must NOT be -1


@pytest.mark.asyncio
async def test_notify_user_removes_only_dead_connections():
    """Dead connections are removed during notify while live ones remain."""
    manager = ConnectionManager()
    ws_live = _make_mock_ws()
    ws_dead = _make_mock_ws()
    ws_dead.send_json.side_effect = RuntimeError("connection closed")

    await manager.connect(1, ws_live)
    await manager.connect(1, ws_dead)
    assert len(manager._connections[1]) == 2

    await manager.notify_user(1)

    # Only the dead connection should be removed
    assert ws_live in manager._connections[1]
    assert ws_dead not in manager._connections[1]
    assert len(manager._connections[1]) == 1
    assert manager._total_connections == 1
    # Live connection received the message
    ws_live.send_json.assert_awaited_once_with({"type": "dashboard_update"})


@pytest.mark.asyncio
async def test_connect_rejects_over_global_limit():
    """Exceeding MAX_TOTAL_CONNECTIONS should reject connections for any user."""
    manager = ConnectionManager()
    manager.MAX_TOTAL_CONNECTIONS = 3

    ws1 = _make_mock_ws()
    ws2 = _make_mock_ws()
    ws3 = _make_mock_ws()
    ws4 = _make_mock_ws()

    # Three different users fill the global limit
    assert await manager.connect(1, ws1) is True
    assert await manager.connect(2, ws2) is True
    assert await manager.connect(3, ws3) is True
    assert manager._total_connections == 3

    # Fourth connection (new user) should be rejected
    assert await manager.connect(4, ws4) is False
    ws4.close.assert_awaited_once_with(code=4429)
    ws4.accept.assert_not_awaited()
    assert manager._total_connections == 3
