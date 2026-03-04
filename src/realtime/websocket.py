"""FastAPI WebSocket endpoint with Django session authentication."""

import asyncio
import logging
from importlib import import_module

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from asgiref.sync import sync_to_async

from src.realtime.manager import connection_manager
from src.core.repositories import user_repository
from src.utils.async_compat import maybe_await

logger = logging.getLogger(__name__)

router = APIRouter()

PING_INTERVAL_SECONDS = 30


async def _authenticate_websocket(websocket: WebSocket) -> int | None:
    """Authenticate a WebSocket connection using Django session cookie.

    Returns user_id if authenticated, None otherwise.
    """
    session_key = websocket.cookies.get("sessionid")
    if not session_key:
        return None

    try:
        from django.conf import settings

        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore(session_key)

        # Load session data (sync ORM call)
        session_data = await sync_to_async(session.load)()
        user_id_str = session_data.get("_auth_user_id")
        if not user_id_str:
            return None

        user_id = int(user_id_str)

        # Verify user exists and is active
        user = await maybe_await(user_repository.get_by_id(user_id))
        if not user or not user.is_active:
            return None

        return user_id
    except Exception:
        logger.exception("WebSocket authentication error")
        return None


@router.websocket("/ws/updates/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates.

    Authenticates via Django session cookie, then keeps the connection
    open and forwards notification signals from the ConnectionManager.
    """
    user_id = await _authenticate_websocket(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await connection_manager.connect(user_id, websocket)

    # Background task for keep-alive pings
    ping_task = asyncio.create_task(_ping_loop(websocket))

    try:
        while True:
            # Wait for client messages (keeps connection alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        await connection_manager.disconnect(user_id, websocket)


async def _ping_loop(websocket: WebSocket) -> None:
    """Send periodic pings to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            await websocket.send_json({"type": "ping"})
    except Exception:
        pass  # Connection closed, task will be cancelled
