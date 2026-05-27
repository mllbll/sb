from __future__ import annotations

import logging
import os

from fastapi import FastAPI, WebSocket
from fastapi.exceptions import RequestValidationError
from starlette.websockets import WebSocketDisconnect

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from fight3d.api.db import create_engine, create_sessionmaker
from fight3d.api.errors import APIError, api_error_handler, validation_error_handler
from fight3d.api.routers.cameras import router as cameras_router
from fight3d.api.routers.fight_events import router as fight_events_router
from fight3d.api.routers.locations import router as locations_router
from fight3d.api.routers.summaries import router as summaries_router
from fight3d.api.ws_manager import ConnectionManager


def create_app(
    *,
    engine: AsyncEngine | None = None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(title="fight3d-events-api")

    eng = engine or create_engine()
    app.state.engine = eng
    app.state.session_maker = session_maker or create_sessionmaker(eng)
    app.state.ws_manager = ConnectionManager()

    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    app.include_router(locations_router)
    app.include_router(cameras_router)
    app.include_router(fight_events_router)
    app.include_router(summaries_router)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        mgr: ConnectionManager = app.state.ws_manager
        await mgr.connect(websocket)
        try:
            while True:
                # Keep connection alive; client messages are currently ignored.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await mgr.disconnect(websocket)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app: FastAPI | None
if os.getenv("DATABASE_URL"):
    app = create_app()
else:
    app = None
