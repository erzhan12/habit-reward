"""In-memory WebSocket connection manager for real-time updates."""

import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per user.

    Maps user_id to a set of WebSocket connections. When a habit is
    completed/reverted, notify_user sends a refresh signal to all
    connected browsers for that user.
    """

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        logger.info("WebSocket connected for user %s (total: %d)", user_id, len(self._connections[user_id]))

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WebSocket disconnected for user %s", user_id)

    async def notify_user(self, user_id: int, event_type: str = "dashboard_update") -> None:
        """Send a refresh signal to all connections for a user."""
        connections = self._connections.get(user_id)
        if not connections:
            return

        dead: list[WebSocket] = []
        message = {"type": event_type}

        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                logger.debug("Removing dead WebSocket for user %s", user_id)
                dead.append(ws)

        for ws in dead:
            connections.discard(ws)
        if not connections:
            del self._connections[user_id]


connection_manager = ConnectionManager()
