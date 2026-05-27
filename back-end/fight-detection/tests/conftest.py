from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from fight3d.api.main import create_app
from fight3d.api.models import Base


def _test_db_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL", "").strip() or None


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine() -> AsyncEngine:
    url = _test_db_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping API DB tests")

    # fresh schema per session
    schema = f"test_{uuid.uuid4().hex[:10]}"

    bootstrap = create_async_engine(url, pool_pre_ping=True)
    async with bootstrap.begin() as conn:
        await conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    await bootstrap.dispose()

    eng = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield eng
    finally:
        cleanup = create_async_engine(url, pool_pre_ping=True)
        async with cleanup.begin() as conn:
            await conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        await cleanup.dispose()
        await eng.dispose()


@pytest.fixture(scope="session")
async def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
async def app(engine: AsyncEngine, session_maker: async_sessionmaker[AsyncSession]):
    # Ensure our app uses the test engine
    return create_app(engine=engine, session_maker=session_maker)


@pytest.fixture()
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
