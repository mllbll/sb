from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger("fight3d.api.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("ws_connected total=%d", await self.count())

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("ws_disconnected total=%d", await self.count())

    async def count(self) -> int:
        async with self._lock:
            return len(self._connections)

    async def broadcast_json(self, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections)

        if not targets:
            return

        async def _send_one(ws: WebSocket) -> WebSocket | None:
            try:
                await ws.send_json(message)
                return ws
            except Exception:
                return None

        results = await asyncio.gather(*(_send_one(ws) for ws in targets), return_exceptions=False)
        dead = [ws for ws in results if ws is None]
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
