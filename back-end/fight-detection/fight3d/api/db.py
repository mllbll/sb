from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from fight3d.settings_yaml import database_url_from_config


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        url = (database_url_from_config() or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set and config.yaml postgres.url not found")
    return url


def create_engine(url: str | None = None) -> AsyncEngine:
    db_url = url or _database_url()
    return create_async_engine(db_url, pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.session_maker
    async with session_maker() as session:
        yield session
