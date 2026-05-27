from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.db import get_session
from fight3d.api.errors import APIError
from fight3d.api.repos.locations import create_location, get_location, query_locations
from fight3d.api.schemas import LocationCreate, LocationOut


router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.post("", response_model=LocationOut)
async def post_location(payload: LocationCreate, session: AsyncSession = Depends(get_session)) -> LocationOut:
    async with session.begin():
        loc = await create_location(session, name=payload.name, address=payload.address, tags=payload.tags)
    return LocationOut.model_validate(loc)


@router.get("", response_model=list[LocationOut])
async def get_locations(
    query: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[LocationOut]:
    stmt = query_locations(query=query, limit=limit)
    res = await session.execute(stmt)
    return [LocationOut.model_validate(x) for x in res.scalars().all()]


@router.get("/{location_id}", response_model=LocationOut)
async def get_location_by_id(
    location_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> LocationOut:
    loc = await get_location(session, location_id)
    if loc is None:
        raise APIError("not_found", "Location not found", http_status=404)
    return LocationOut.model_validate(loc)
