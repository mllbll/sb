from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.models import Camera


async def create_camera(
    session: AsyncSession,
    *,
    location_id: uuid.UUID,
    name: str,
    external_id: str | None,
    rtsp_uri_masked: str | None,
    is_active: bool,
) -> Camera:
    cam = Camera(
        location_id=location_id,
        name=name,
        external_id=external_id,
        rtsp_uri_masked=rtsp_uri_masked,
        is_active=is_active,
    )
    session.add(cam)
    try:
        await session.flush()
    except IntegrityError:
        raise
    return cam


async def get_camera(session: AsyncSession, camera_id: uuid.UUID) -> Camera | None:
    return await session.get(Camera, camera_id)


async def get_camera_by_external_id(session: AsyncSession, external_id: str) -> Camera | None:
    stmt = select(Camera).where(Camera.external_id == external_id).limit(1)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def patch_camera(session: AsyncSession, cam: Camera, **fields) -> Camera:
    for k, v in fields.items():
        if v is None:
            continue
        setattr(cam, k, v)
    session.add(cam)
    await session.flush()
    return cam


def query_cameras(*, location_id: uuid.UUID | None, active: bool | None, limit: int) -> Select:
    stmt = select(Camera).order_by(Camera.created_at.desc()).limit(int(limit))
    if location_id:
        stmt = stmt.where(Camera.location_id == location_id)
    if active is not None:
        stmt = stmt.where(Camera.is_active.is_(bool(active)))
    return stmt
