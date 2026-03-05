"""In-memory WebSocket connection manager for real-time updates."""

import logging
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per user.

    Maps user_id to a set of WebSocket connections. When a habit is
    completed/reverted, notify_user sends a refresh signal to all
    connected browsers for that user.
    """

    MAX_CONNECTIONS_PER_USER = 10
    MAX_TOTAL_CONNECTIONS = 100

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._total_connections: int = 0

    async def connect(self, user_id: int, websocket: WebSocket) -> bool:
        """Accept and register a WebSocket connection.

        Returns True if accepted, False if rejected (connection limit).
        """
        # Check global limit first (O(1) via maintained counter)
        if self._total_connections >= self.MAX_TOTAL_CONNECTIONS:
            logger.warning(
                "Global WebSocket connection limit reached (%d), rejecting user %s",
                self.MAX_TOTAL_CONNECTIONS, user_id
            )
            await websocket.close(code=1008)
            return False

        existing = self._connections.get(user_id)
        if existing and len(existing) >= self.MAX_CONNECTIONS_PER_USER:
            logger.warning(
                "User %s exceeded max WebSocket connections (%d), rejecting",
                user_id, self.MAX_CONNECTIONS_PER_USER,
            )
            await websocket.close(code=4429)
            return False
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        self._total_connections += 1
        logger.info("WebSocket connected for user %s (total: %d)", user_id, len(self._connections[user_id]))
        return True

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if user_id in self._connections:
            if websocket in self._connections[user_id]:
                self._connections[user_id].discard(websocket)
                self._total_connections -= 1
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
            except (RuntimeError, ConnectionError, WebSocketDisconnect):
                logger.debug("Removing dead WebSocket for user %s", user_id)
                dead.append(ws)

        for ws in dead:
            connections.discard(ws)
            self._total_connections -= 1
        if not connections:
            del self._connections[user_id]


connection_manager = ConnectionManager()
