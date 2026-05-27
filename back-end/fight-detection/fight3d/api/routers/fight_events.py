from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.db import get_session
from fight3d.api.errors import APIError
from fight3d.api.repos import cameras as cameras_repo
from fight3d.api.repos.fight_events import (
    get_event,
    patch_event,
    query_fight_events,
    upsert_fight_event,
)
from fight3d.api.repos.locations import get_location, get_or_create_unknown_location
from fight3d.api.schemas import (
    BatchIngestResult,
    FightEventBatchRequest,
    FightEventOut,
    FightEventPatch,
)
from fight3d.api.ws_manager import ConnectionManager


logger = logging.getLogger("fight3d.api")

router = APIRouter(prefix="/api/fight-events", tags=["fight-events"])


@router.post("/batch", response_model=BatchIngestResult)
async def post_fight_events_batch(
    request: Request,
    payload: FightEventBatchRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchIngestResult:
    logger.info(
        "ingest_batch size=%d auto_create_camera=%s",
        len(payload.events),
        payload.auto_create_camera,
    )

    inserted = 0
    upserted = 0
    created_cameras = 0
    to_broadcast: list[dict] = []

    async with session.begin():
        for ev in payload.events:
            camera_id = ev.camera_id
            cam = None
            loc = None

            if camera_id is None:
                if not ev.camera_external_id:
                    raise APIError(
                        "invalid_event",
                        "Each event must have camera_id or camera_external_id",
                        http_status=400,
                    )
                cam = await cameras_repo.get_camera_by_external_id(session, ev.camera_external_id)
                if cam is None:
                    if not payload.auto_create_camera:
                        raise APIError(
                            "not_found",
                            "Camera not found for camera_external_id",
                            details={"camera_external_id": ev.camera_external_id},
                            http_status=404,
                        )

                    # determine location
                    if payload.location_id is not None:
                        loc = await get_location(session, payload.location_id)
                        if loc is None:
                            raise APIError("not_found", "Location not found", http_status=404)
                    else:
                        loc = await get_or_create_unknown_location(session)

                    try:
                        cam = await cameras_repo.create_camera(
                            session,
                            location_id=loc.id,
                            name=ev.camera_external_id,
                            external_id=ev.camera_external_id,
                            rtsp_uri_masked=None,
                            is_active=True,
                        )
                        created_cameras += 1
                    except IntegrityError:
                        cam = await cameras_repo.get_camera_by_external_id(session, ev.camera_external_id)
                        if cam is None:
                            raise APIError("conflict", "Failed to create camera", http_status=409)

                camera_id = cam.id
                loc = await get_location(session, cam.location_id)
            else:
                cam = await cameras_repo.get_camera(session, camera_id)
                if cam is not None:
                    loc = await get_location(session, cam.location_id)

            event_id, was_upsert = await upsert_fight_event(
                session,
                camera_id=camera_id,
                started_at=ev.started_at,
                ended_at=ev.ended_at,
                peak_score=ev.peak_score,
                mean_score=ev.mean_score,
                status=ev.status,
                notes=ev.notes,
                tags=ev.tags,
                meta=ev.meta,
                dedup_key=ev.dedup_key,
            )
            if was_upsert:
                upserted += 1
                is_closed = (ev.ended_at is not None) or (ev.status not in (None, "open"))
                if is_closed:
                    to_broadcast.append(
                        {
                            "type": "fight.resolved",
                            "payload": {"id": str(event_id)},
                        }
                    )
            else:
                inserted += 1

                # Emit fight.detected once per newly inserted open fight.
                is_open = (ev.ended_at is None) and (ev.status in (None, "open"))
                if is_open:
                    meta = ev.meta or {}
                    participants_raw = (
                        meta.get("participants")
                        or meta.get("people_count")
                        or meta.get("participants_count")
                        or meta.get("people_min")
                        or 0
                    )
                    try:
                        participants = int(participants_raw)
                    except Exception:
                        participants = 0

                    camera_key = (
                        (cam.external_id if cam is not None else None)
                        or ev.camera_external_id
                        or str(camera_id)
                    )
                    location_name = (loc.name if loc is not None else None) or "Unknown"

                    to_broadcast.append(
                        {
                            "type": "fight.detected",
                            "payload": {
                                "id": str(event_id),
                                "location": location_name,
                                "camera_id": str(camera_key),
                                "participants": participants,
                            },
                        }
                    )

    logger.info(
        "ingest_batch done inserted=%d upserted=%d created_cameras=%d",
        inserted,
        upserted,
        created_cameras,
    )

    mgr: ConnectionManager | None = getattr(request.app.state, "ws_manager", None)
    if mgr is not None:
        for msg in to_broadcast:
            await mgr.broadcast_json(msg)

    return BatchIngestResult(inserted=inserted, upserted=upserted, created_cameras=created_cameras)


@router.patch("/{event_id}", response_model=FightEventOut)
async def patch_fight_event(
    event_id: uuid.UUID,
    payload: FightEventPatch,
    session: AsyncSession = Depends(get_session),
) -> FightEventOut:
    async with session.begin():
        ev = await patch_event(
            session,
            event_id,
            ended_at=payload.ended_at,
            status=payload.status,
            notes=payload.notes,
            tags=payload.tags,
        )

    if ev is None:
        raise APIError("not_found", "Fight event not found", http_status=404)

    return FightEventOut.model_validate(ev)


@router.get("", response_model=list[FightEventOut])
async def get_fight_events(
    camera_id: uuid.UUID | None = Query(default=None),
    location_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[FightEventOut]:
    from datetime import datetime

    f = datetime.fromisoformat(from_dt) if from_dt else None
    t = datetime.fromisoformat(to_dt) if to_dt else None

    stmt = query_fight_events(
        camera_id=camera_id,
        location_id=location_id,
        status=status,
        from_dt=f,
        to_dt=t,
        limit=limit,
        offset=offset,
    )
    res = await session.execute(stmt)
    return [FightEventOut.model_validate(x) for x in res.scalars().all()]


@router.get("/{event_id}", response_model=FightEventOut)
async def get_fight_event(event_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> FightEventOut:
    ev = await get_event(session, event_id)
    if ev is None:
        raise APIError("not_found", "Fight event not found", http_status=404)
    return FightEventOut.model_validate(ev)
