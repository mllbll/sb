from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.anyio
async def test_create_location_and_camera(client):
    loc_resp = await client.post(
        "/api/locations",
        json={"name": "Warehouse 1", "address": "Somewhere", "tags": ["test"]},
    )
    assert loc_resp.status_code == 200
    loc = loc_resp.json()
    assert loc["id"]
    assert loc["name"] == "Warehouse 1"

    cam_resp = await client.post(
        "/api/cameras",
        json={
            "location_id": loc["id"],
            "name": "Cam A",
            "external_id": f"cam-ext-{loc['id']}",
            "rtsp_uri_masked": "rtsp://***",
            "is_active": True,
        },
    )
    assert cam_resp.status_code == 200
    cam = cam_resp.json()
    assert cam["id"]
    assert cam["location_id"] == loc["id"]
    assert cam["name"] == "Cam A"


@pytest.mark.anyio
async def test_create_camera_invalid_location(client):
    resp = await client.post(
        "/api/cameras",
        json={
            "location_id": "00000000-0000-0000-0000-000000000000",
            "name": "Cam",
            "external_id": "cam-x",
            "is_active": True,
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"


@pytest.mark.anyio
async def test_patch_camera_updates_name(client):
    loc = (await client.post("/api/locations", json={"name": "Loc patch"})).json()
    cam = (
        await client.post(
            "/api/cameras",
            json={
                "location_id": loc["id"],
                "name": "Cam patch",
                "external_id": f"patch-{loc['id']}",
                "is_active": True,
            },
        )
    ).json()

    resp = await client.patch(f"/api/cameras/{cam['id']}", json={"name": "Cam patched"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == cam["id"]
    assert body["name"] == "Cam patched"
    assert body["updated_at"]


@pytest.mark.anyio
async def test_batch_ingest_dedup_key_upserts_instead_of_duplicates(client):
    loc = (
        await client.post(
            "/api/locations",
            json={"name": "Loc dedup"},
        )
    ).json()

    cam = (
        await client.post(
            "/api/cameras",
            json={
                "location_id": loc["id"],
                "name": "Cam dedup",
                "external_id": f"dedup-{loc['id']}",
                "is_active": True,
            },
        )
    ).json()

    started_at = datetime.now(timezone.utc).replace(microsecond=0)

    r1 = await client.post(
        "/api/fight-events/batch",
        json={
            "events": [
                {
                    "camera_id": cam["id"],
                    "started_at": started_at.isoformat(),
                    "ended_at": None,
                    "peak_score": 0.9,
                    "mean_score": 0.7,
                    "dedup_key": "k1",
                }
            ],
            "auto_create_camera": False,
        },
    )
    assert r1.status_code == 200
    assert r1.json() == {"inserted": 1, "upserted": 0, "created_cameras": 0}

    r2 = await client.post(
        "/api/fight-events/batch",
        json={
            "events": [
                {
                    "camera_id": cam["id"],
                    "started_at": started_at.isoformat(),
                    "ended_at": (started_at + timedelta(seconds=12)).isoformat(),
                    "peak_score": 0.95,
                    "mean_score": 0.75,
                    "dedup_key": "k1",
                }
            ],
            "auto_create_camera": False,
        },
    )
    assert r2.status_code == 200
    assert r2.json() == {"inserted": 0, "upserted": 1, "created_cameras": 0}

    listing = await client.get("/api/fight-events", params={"camera_id": cam["id"], "limit": 10})
    assert listing.status_code == 200
    events = listing.json()
    assert len(events) == 1
    assert events[0]["dedup_key"] == "k1"
    assert events[0]["ended_at"] is not None
    assert events[0]["mean_score"] == 0.75
    assert events[0]["status"] == "closed"


@pytest.mark.anyio
async def test_summaries_camera_and_location(client):
    loc = (await client.post("/api/locations", json={"name": "Loc summary"})).json()
    cam = (
        await client.post(
            "/api/cameras",
            json={
                "location_id": loc["id"],
                "name": "Cam summary",
                "external_id": f"sum-{loc['id']}",
                "is_active": True,
            },
        )
    ).json()

    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    ingest = await client.post(
        "/api/fight-events/batch",
        json={
            "events": [
                {
                    "camera_id": cam["id"],
                    "started_at": base.isoformat(),
                    "ended_at": (base + timedelta(seconds=10)).isoformat(),
                    "peak_score": 0.9,
                    "mean_score": 0.8,
                    "status": "confirmed",
                    "dedup_key": "s1",
                },
                {
                    "camera_id": cam["id"],
                    "started_at": (base + timedelta(minutes=5)).isoformat(),
                    "ended_at": (base + timedelta(minutes=5, seconds=5)).isoformat(),
                    "peak_score": 0.4,
                    "mean_score": 0.3,
                    "status": "false_positive",
                    "dedup_key": "s2",
                },
            ],
            "auto_create_camera": False,
        },
    )
    assert ingest.status_code == 200

    cam_sum = await client.get(f"/api/cameras/{cam['id']}/summary")
    assert cam_sum.status_code == 200
    cs = cam_sum.json()
    assert cs["total_events"] == 2
    assert cs["confirmed"] == 1
    assert cs["false_positive"] == 1
    assert cs["avg_event_len_sec"] is not None
    assert abs(cs["avg_event_len_sec"] - 7.5) < 0.01
    assert len(cs["events_per_day"]) == 1
    assert cs["events_per_day"][0]["count"] == 2

    loc_sum = await client.get(f"/api/locations/{loc['id']}/summary")
    assert loc_sum.status_code == 200
    ls = loc_sum.json()
    assert ls["total_events"] == 2
    assert ls["confirmed"] == 1
    assert ls["false_positive"] == 1
    assert abs(ls["avg_event_len_sec"] - 7.5) < 0.01
    assert len(ls["events_per_day"]) == 1
    assert ls["events_per_day"][0]["count"] == 2
