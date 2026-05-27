import asyncio
import logging
from fastapi import FastAPI
from api.stats_endpoints import router as stats_router
from api.websocket import router as ws_router, broadcast_loop
from api.db_conn import query_db

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# REST endpoints
app.include_router(stats_router, prefix="/api")

# WebSocket endpoint  (/ws/crowd)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def _start_broadcast_loop():
    asyncio.create_task(broadcast_loop())
