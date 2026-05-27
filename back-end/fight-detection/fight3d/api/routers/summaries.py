from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.db import get_session
from fight3d.api.errors import APIError
from fight3d.api.repos.fight_events import locations_summary
from fight3d.api.repos.locations import get_location
from fight3d.api.schemas import SummaryOut


router = APIRouter(prefix="/api/locations", tags=["summaries"])


@router.get("/{location_id}/summary", response_model=SummaryOut)
async def get_location_summary(
    location_id: uuid.UUID,
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    from datetime import datetime

    loc = await get_location(session, location_id)
    if loc is None:
        raise APIError("not_found", "Location not found", http_status=404)

    f = datetime.fromisoformat(from_dt) if from_dt else None
    t = datetime.fromisoformat(to_dt) if to_dt else None

    data = await locations_summary(session, location_id=location_id, from_dt=f, to_dt=t)
    return SummaryOut.model_validate(data)
