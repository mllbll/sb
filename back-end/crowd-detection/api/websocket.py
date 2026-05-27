import asyncio
import json
import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

_secrets_path = os.path.join(os.path.dirname(__file__), "..", "keys", "secrets.json")
with open(_secrets_path) as _f:
    _secrets = json.load(_f)

ZONES: list[dict] = _secrets.get("zones", [])
WS_INTERVAL: float = float(_secrets.get("ws_broadcast_interval_sec", 3))

_DB_CONFIG = {
    "dbname":   _secrets["DB_NAME"],
    "user":     _secrets["DB_USER"],
    "password": _secrets["DB_PASSWORD"],
    "host":     _secrets["DB_HOST"],
    "port":     int(_secrets.get("PORT", 5432)),
}


class _ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)
        logger.info("WS client connected (total=%d)", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)
        logger.info("WS client disconnected (total=%d)", len(self._clients))

    async def broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        data = json.dumps(message, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self._clients:
                self._clients.remove(ws)

    @property
    def has_clients(self) -> bool:
        return bool(self._clients)


manager = _ConnectionManager()


def _fetch_latest_counts() -> dict[str, int]:
    # Берём последнюю запись по каждой камере
    query = """
        SELECT DISTINCT ON (camera_id) camera_id, people_count
        FROM crowd_data
        ORDER BY camera_id, time DESC;
    """
    try:
        with psycopg2.connect(**_DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return {row["camera_id"]: int(row["people_count"]) for row in rows}
    except Exception as exc:
        logger.warning("WS DB query failed: %s", exc)
        return {}


def _build_message(counts: dict[str, int]) -> dict:
    zones = []
    total = 0
    for zone in ZONES:
        current = counts.get(zone["camera_id"], 0)
        total += current
        zones.append({"id": zone["id"], "current": current})
    return {
        "type": "crowd.update",
        "payload": {
            "total": total,
            "zones": zones,
        },
    }


async def broadcast_loop() -> None:
    logger.info("WS broadcast loop started (interval=%.1fs, zones=%d)", WS_INTERVAL, len(ZONES))
    while True:
        await asyncio.sleep(WS_INTERVAL)
        if not manager.has_clients:
            continue
        counts = await asyncio.to_thread(_fetch_latest_counts)
        await manager.broadcast(_build_message(counts))


@router.websocket("/ws/crowd")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    counts = await asyncio.to_thread(_fetch_latest_counts)
    await ws.send_text(json.dumps(_build_message(counts), ensure_ascii=False))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as exc:
        logger.warning("WS connection error: %s", exc)
        manager.disconnect(ws)
