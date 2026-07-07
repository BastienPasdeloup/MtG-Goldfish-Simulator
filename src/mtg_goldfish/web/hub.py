"""WebSocket hub: broadcast live simulation events to a session's clients."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class Hub:
    def __init__(self) -> None:
        self._conns: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._conns[session_id].add(ws)

    def disconnect(self, session_id: str, ws: WebSocket) -> None:
        self._conns[session_id].discard(ws)

    async def broadcast(self, session_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._conns.get(session_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)

    def broadcast_threadsafe(
        self, loop: asyncio.AbstractEventLoop, session_id: str, message: dict
    ) -> None:
        """Called from the simulation worker thread."""
        asyncio.run_coroutine_threadsafe(self.broadcast(session_id, message), loop)


HUB = Hub()
