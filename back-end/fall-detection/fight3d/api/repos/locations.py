from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.models import Location


async def create_location(session: AsyncSession, *, name: str, address: str | None, tags: list[str] | None) -> Location:
    loc = Location(name=name, address=address, tags=tags)
    session.add(loc)
    await session.flush()
    return loc


def query_locations(*, query: str | None, limit: int) -> Select:
    stmt = select(Location).order_by(Location.created_at.desc()).limit(int(limit))
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(func.lower(Location.name).like(func.lower(q)))
    return stmt


async def get_location(session: AsyncSession, location_id: uuid.UUID) -> Location | None:
    return await session.get(Location, location_id)


async def get_or_create_unknown_location(session: AsyncSession) -> Location:
    stmt = select(Location).where(Location.name == "Unknown").limit(1)
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    loc = Location(name="Unknown")
    session.add(loc)
    await session.flush()
    return loc
