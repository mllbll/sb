from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from fight3d.api.models import FightEvent


def _default_status(*, ended_at: datetime | None) -> str:
    return "open" if ended_at is None else "closed"


async def upsert_fight_event(
    session: AsyncSession,
    *,
    camera_id: uuid.UUID,
    started_at: datetime,
    ended_at: datetime | None,
    peak_score: float,
    mean_score: float,
    status: str | None,
    notes: str | None,
    tags: list[str] | None,
    meta: dict[str, Any] | None,
    dedup_key: str | None,
) -> tuple[uuid.UUID, bool]:
    """Returns (event_id, was_upserted). If dedup_key is None → pure insert (was_upserted=False)."""

    payload: dict[str, Any] = {
        "camera_id": camera_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "peak_score": float(peak_score),
        "mean_score": float(mean_score),
        "status": status or _default_status(ended_at=ended_at),
        "notes": notes,
        "tags": tags,
        "meta": meta,
        "dedup_key": dedup_key,
        "updated_at": func.now(),
    }

    if dedup_key:
        existing_id = (
            await session.execute(
                select(FightEvent.id).where(
                    FightEvent.camera_id == camera_id,
                    FightEvent.dedup_key == dedup_key,
                )
            )
        ).scalar_one_or_none()

        stmt = (
            insert(FightEvent)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[FightEvent.camera_id, FightEvent.dedup_key],
                set_={
                    "ended_at": payload["ended_at"],
                    "peak_score": payload["peak_score"],
                    "mean_score": payload["mean_score"],
                    "status": payload["status"],
                    "notes": payload["notes"],
                    "tags": payload["tags"],
                    "meta": payload["meta"],
                    "updated_at": func.now(),
                },
                index_where=FightEvent.dedup_key.is_not(None),
            )
            .returning(FightEvent.id)
        )
        res = await session.execute(stmt)
        event_id = res.scalar_one()
        return event_id, existing_id is not None

    ev = FightEvent(**payload)
    session.add(ev)
    await session.flush()
    return ev.id, False


async def patch_event(
    session: AsyncSession,
    event_id: uuid.UUID,
    *,
    ended_at: datetime | None,
    status: str | None,
    notes: str | None,
    tags: list[str] | None,
) -> FightEvent | None:
    ev = await session.get(FightEvent, event_id)
    if ev is None:
        return None

    if ended_at is not None:
        ev.ended_at = ended_at

    if status is not None:
        ev.status = status
    elif ended_at is not None and (ev.status == "open"):
        ev.status = "closed"

    if notes is not None:
        ev.notes = notes
    if tags is not None:
        ev.tags = tags

    session.add(ev)
    await session.flush()
    return ev


def query_fight_events(
    *,
    camera_id: uuid.UUID | None,
    location_id: uuid.UUID | None,
    status: str | None,
    from_dt: datetime | None,
    to_dt: datetime | None,
    limit: int,
    offset: int,
) -> Select:
    from fight3d.api.models import Camera

    stmt = select(FightEvent)

    if location_id is not None:
        stmt = stmt.join(Camera, Camera.id == FightEvent.camera_id).where(Camera.location_id == location_id)

    if camera_id is not None:
        stmt = stmt.where(FightEvent.camera_id == camera_id)

    if status is not None:
        stmt = stmt.where(FightEvent.status == status)

    if from_dt is not None:
        stmt = stmt.where(FightEvent.started_at >= from_dt)

    if to_dt is not None:
        stmt = stmt.where(FightEvent.started_at <= to_dt)

    stmt = stmt.order_by(FightEvent.started_at.desc()).limit(int(limit)).offset(int(offset))
    return stmt


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> FightEvent | None:
    return await session.get(FightEvent, event_id)


async def cameras_summary(
    session: AsyncSession,
    *,
    camera_id: uuid.UUID,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict[str, Any]:
    filters = [FightEvent.camera_id == camera_id]
    if from_dt is not None:
        filters.append(FightEvent.started_at >= from_dt)
    if to_dt is not None:
        filters.append(FightEvent.started_at <= to_dt)

    base = and_(*filters)

    total_q = select(func.count()).select_from(FightEvent).where(base)
    confirmed_q = select(func.count()).select_from(FightEvent).where(base, FightEvent.status == "confirmed")
    fp_q = select(func.count()).select_from(FightEvent).where(base, FightEvent.status == "false_positive")

    duration_expr = func.extract("epoch", FightEvent.ended_at - FightEvent.started_at)
    avg_len_q = (
        select(func.avg(duration_expr))
        .select_from(FightEvent)
        .where(base, FightEvent.ended_at.is_not(None))
    )

    per_day_q = (
        select(func.date_trunc("day", FightEvent.started_at).label("day"), func.count().label("count"))
        .select_from(FightEvent)
        .where(base)
        .group_by("day")
        .order_by("day")
    )

    total = (await session.execute(total_q)).scalar_one()
    confirmed = (await session.execute(confirmed_q)).scalar_one()
    false_positive = (await session.execute(fp_q)).scalar_one()
    avg_len = (await session.execute(avg_len_q)).scalar_one()

    per_day_rows = (await session.execute(per_day_q)).all()
    events_per_day = [{"day": r.day, "count": int(r.count)} for r in per_day_rows]

    return {
        "total_events": int(total),
        "confirmed": int(confirmed),
        "false_positive": int(false_positive),
        "avg_event_len_sec": (float(avg_len) if avg_len is not None else None),
        "events_per_day": events_per_day,
    }


async def locations_summary(
    session: AsyncSession,
    *,
    location_id: uuid.UUID,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> dict[str, Any]:
    from fight3d.api.models import Camera

    filters = [Camera.location_id == location_id]
    if from_dt is not None:
        filters.append(FightEvent.started_at >= from_dt)
    if to_dt is not None:
        filters.append(FightEvent.started_at <= to_dt)

    base = and_(*filters)

    join_stmt = FightEvent.__table__.join(Camera.__table__, Camera.id == FightEvent.camera_id)

    total_q = select(func.count()).select_from(join_stmt).where(base)
    confirmed_q = select(func.count()).select_from(join_stmt).where(base, FightEvent.status == "confirmed")
    fp_q = select(func.count()).select_from(join_stmt).where(base, FightEvent.status == "false_positive")

    duration_expr = func.extract("epoch", FightEvent.ended_at - FightEvent.started_at)
    avg_len_q = select(func.avg(duration_expr)).select_from(join_stmt).where(base, FightEvent.ended_at.is_not(None))

    per_day_q = (
        select(func.date_trunc("day", FightEvent.started_at).label("day"), func.count().label("count"))
        .select_from(join_stmt)
        .where(base)
        .group_by("day")
        .order_by("day")
    )

    total = (await session.execute(total_q)).scalar_one()
    confirmed = (await session.execute(confirmed_q)).scalar_one()
    false_positive = (await session.execute(fp_q)).scalar_one()
    avg_len = (await session.execute(avg_len_q)).scalar_one()

    per_day_rows = (await session.execute(per_day_q)).all()
    events_per_day = [{"day": r.day, "count": int(r.count)} for r in per_day_rows]

    return {
        "total_events": int(total),
        "confirmed": int(confirmed),
        "false_positive": int(false_positive),
        "avg_event_len_sec": (float(avg_len) if avg_len is not None else None),
        "events_per_day": events_per_day,
    }
