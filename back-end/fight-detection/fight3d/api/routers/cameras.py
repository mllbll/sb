from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.db import get_session
from fight3d.api.errors import APIError
from fight3d.api.repos.cameras import (
    create_camera,
    get_camera,
    patch_camera,
    query_cameras,
)
from fight3d.api.repos.locations import get_location
from fight3d.api.schemas import CameraCreate, CameraOut, CameraPatch, SummaryOut
from fight3d.api.repos.fight_events import cameras_summary


router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.post("", response_model=CameraOut)
async def post_camera(payload: CameraCreate, session: AsyncSession = Depends(get_session)) -> CameraOut:
    async with session.begin():
        loc = await get_location(session, payload.location_id)
        if loc is None:
            raise APIError("not_found", "Location not found", http_status=404)

        try:
            cam = await create_camera(
                session,
                location_id=payload.location_id,
                name=payload.name,
                external_id=payload.external_id,
                rtsp_uri_masked=payload.rtsp_uri_masked,
                is_active=bool(payload.is_active),
            )
        except IntegrityError:
            raise APIError(
                "conflict",
                "Camera external_id already exists",
                details={"field": "external_id"},
                http_status=409,
            )
    return CameraOut.model_validate(cam)


@router.patch("/{camera_id}", response_model=CameraOut)
async def patch_camera_by_id(
    camera_id: uuid.UUID,
    payload: CameraPatch,
    session: AsyncSession = Depends(get_session),
) -> CameraOut:
    async with session.begin():
        cam = await get_camera(session, camera_id)
        if cam is None:
            raise APIError("not_found", "Camera not found", http_status=404)

        if payload.location_id is not None:
            loc = await get_location(session, payload.location_id)
            if loc is None:
                raise APIError("not_found", "Location not found", http_status=404)

        try:
            cam = await patch_camera(
                session,
                cam,
                location_id=payload.location_id,
                name=payload.name,
                external_id=payload.external_id,
                rtsp_uri_masked=payload.rtsp_uri_masked,
                is_active=payload.is_active,
            )
            await session.refresh(cam)
        except IntegrityError:
            raise APIError(
                "conflict",
                "Camera external_id already exists",
                details={"field": "external_id"},
                http_status=409,
            )

    return CameraOut.model_validate(cam)


@router.get("", response_model=list[CameraOut])
async def get_cameras(
    location_id: uuid.UUID | None = Query(default=None),
    active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[CameraOut]:
    stmt = query_cameras(location_id=location_id, active=active, limit=limit)
    res = await session.execute(stmt)
    return [CameraOut.model_validate(x) for x in res.scalars().all()]


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera_by_id(camera_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> CameraOut:
    cam = await get_camera(session, camera_id)
    if cam is None:
        raise APIError("not_found", "Camera not found", http_status=404)
    return CameraOut.model_validate(cam)


@router.get("/{camera_id}/summary", response_model=SummaryOut)
async def get_camera_summary(
    camera_id: uuid.UUID,
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    from datetime import datetime

    cam = await get_camera(session, camera_id)
    if cam is None:
        raise APIError("not_found", "Camera not found", http_status=404)

    f = datetime.fromisoformat(from_dt) if from_dt else None
    t = datetime.fromisoformat(to_dt) if to_dt else None

    data = await cameras_summary(session, camera_id=camera_id, from_dt=f, to_dt=t)
    return SummaryOut.model_validate(data)
