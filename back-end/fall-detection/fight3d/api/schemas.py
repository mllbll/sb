from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


FightStatus = Literal["open", "closed", "confirmed", "false_positive"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Locations ---


class LocationCreate(BaseModel):
    name: str = Field(min_length=1)
    address: str | None = None
    tags: list[str] | None = None


class LocationOut(_Base):
    id: uuid.UUID
    name: str
    address: str | None
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime


# --- Cameras ---


class CameraCreate(BaseModel):
    location_id: uuid.UUID
    name: str = Field(min_length=1)
    external_id: str | None = None
    rtsp_uri_masked: str | None = None
    is_active: bool = True


class CameraPatch(BaseModel):
    location_id: uuid.UUID | None = None
    name: str | None = None
    external_id: str | None = None
    rtsp_uri_masked: str | None = None
    is_active: bool | None = None


class CameraOut(_Base):
    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    external_id: str | None
    rtsp_uri_masked: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Fight events ---


class FightEventIn(BaseModel):
    camera_id: uuid.UUID | None = None
    camera_external_id: str | None = None

    started_at: datetime
    ended_at: datetime | None = None

    peak_score: float
    mean_score: float

    status: FightStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None

    dedup_key: str | None = None


class FightEventBatchRequest(BaseModel):
    events: list[FightEventIn]
    auto_create_camera: bool = False
    location_id: uuid.UUID | None = None


class FightEventOut(_Base):
    id: uuid.UUID
    camera_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    peak_score: float
    mean_score: float
    status: FightStatus
    notes: str | None
    tags: list[str] | None
    meta: dict[str, Any] | None
    dedup_key: str | None
    created_at: datetime
    updated_at: datetime


class FightEventPatch(BaseModel):
    ended_at: datetime | None = None
    status: FightStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None


class BatchIngestResult(BaseModel):
    inserted: int
    upserted: int
    created_cameras: int


# --- Summaries ---


class EventsPerDay(BaseModel):
    day: datetime
    count: int


class SummaryOut(BaseModel):
    total_events: int
    confirmed: int
    false_positive: int
    avg_event_len_sec: float | None
    events_per_day: list[EventsPerDay]


# --- WebSocket messages ---


class CrowdZone(BaseModel):
    id: str
    current: int


class CrowdUpdatePayload(BaseModel):
    total: int
    zones: list[CrowdZone]


class FightDetectedPayload(BaseModel):
    id: str
    location: str
    camera_id: str
    participants: int


class FallDetectedPayload(BaseModel):
    id: str
    location: str
    camera_id: str
    person_type: str
    age: int


class WSMessageCrowdUpdate(BaseModel):
    type: Literal["crowd.update"]
    payload: CrowdUpdatePayload


class WSMessageFightDetected(BaseModel):
    type: Literal["fight.detected"]
    payload: FightDetectedPayload


class WSMessageFallDetected(BaseModel):
    type: Literal["fall.detected"]
    payload: FallDetectedPayload


WSMessage = WSMessageCrowdUpdate | WSMessageFightDetected | WSMessageFallDetected
