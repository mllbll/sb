from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class PostgresSettings:
    url: str


@dataclass(frozen=True)
class APISettings:
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


@dataclass(frozen=True)
class CameraSettings:
    name: str
    rtsp: str
    fight_threshold: float | None = None


@dataclass(frozen=True)
class InferenceSettings:
    ckpt: str
    yolo_model: str = "yolov8m.pt"
    device: str = "auto"

    fight_threshold: float = 0.7
    people_min: int = 2
    clip_len: int = 16
    stride: int = 4
    show: int = 0
    save_dir: str = ""

    yolo_conf: float = 0.25
    yolo_iou: float = 0.7


@dataclass(frozen=True)
class Settings:
    postgres: PostgresSettings
    api: APISettings
    cameras: list[CameraSettings]
    inference: InferenceSettings


def _config_path(path: str | None = None) -> Path:
    if path:
        return Path(path)
    env = os.getenv("FIGHT3D_CONFIG", "").strip()
    if env:
        return Path(env)
    return Path("config.yaml")


def load_settings(path: str | None = None) -> Settings:
    cfg_path = _config_path(path)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")

    pg = data.get("postgres") or {}
    pg_url = str(pg.get("url") or "").strip()
    if not pg_url:
        raise ValueError("config.yaml: postgres.url is required")

    api_raw = data.get("api") or {}
    api = APISettings(
        host=str(api_raw.get("host") or "0.0.0.0"),
        port=int(api_raw.get("port") or 8000),
        log_level=str(api_raw.get("log_level") or "info"),
    )

    cameras_raw = data.get("cameras") or []
    cameras: list[CameraSettings] = []
    if not isinstance(cameras_raw, list):
        raise ValueError("config.yaml: cameras must be a list")
    for i, item in enumerate(cameras_raw):
        if not isinstance(item, dict):
            raise ValueError(f"config.yaml: cameras[{i}] must be a mapping")
        name = str(item.get("name") or f"cam-{i}")
        rtsp = str(item.get("rtsp") or "").strip()
        if not rtsp:
            raise ValueError(f"config.yaml: cameras[{i}].rtsp is required")
        ft_raw = item.get("fight_threshold", None)
        fight_threshold = None
        if ft_raw is not None and str(ft_raw).strip() != "":
            try:
                fight_threshold = float(ft_raw)
            except Exception as e:
                raise ValueError(
                    f"config.yaml: cameras[{i}].fight_threshold must be a number"
                ) from e

        cameras.append(CameraSettings(name=name, rtsp=rtsp, fight_threshold=fight_threshold))

    inf_raw: dict[str, Any] = data.get("inference") or {}
    ckpt = str(inf_raw.get("ckpt") or "").strip()
    if not ckpt:
        raise ValueError("config.yaml: inference.ckpt is required")
    inference = InferenceSettings(
        ckpt=ckpt,
        yolo_model=str(inf_raw.get("yolo_model") or "yolov8m.pt"),
        device=str(inf_raw.get("device") or "auto"),
        fight_threshold=float(inf_raw.get("fight_threshold") or 0.7),
        people_min=int(inf_raw.get("people_min") or 2),
        clip_len=int(inf_raw.get("clip_len") or 16),
        stride=int(inf_raw.get("stride") or 4),
        show=int(inf_raw.get("show") or 0),
        save_dir=str(inf_raw.get("save_dir") or ""),
        yolo_conf=float(inf_raw.get("yolo_conf") or 0.25),
        yolo_iou=float(inf_raw.get("yolo_iou") or 0.7),
    )

    return Settings(
        postgres=PostgresSettings(url=pg_url),
        api=api,
        cameras=cameras,
        inference=inference,
    )


def database_url_from_config(path: str | None = None) -> str | None:
    try:
        return load_settings(path).postgres.url
    except Exception:
        return None
