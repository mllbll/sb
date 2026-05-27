from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


Device = Literal["cpu", "cuda"]


@dataclass
class Config:
    seed: int = 42
    device: Device = "cuda"

    clip_len: int = 16
    clip_stride: int = 1
    resize_short: int = 256
    crop_size: int = 224

    batch_size: int = 32
    lr: float = 1e-4
    epochs: int = 10
    num_workers: int = 4

    output_dir: str = "outputs"

    yolo_model: str = "yolov8m.pt"
    yolo_conf: float = 0.25
    yolo_iou: float = 0.7
    people_min: int = 2
    fight_threshold: float = 0.7

    def __post_init__(self) -> None:
        if self.device not in ("cpu", "cuda"):
            raise ValueError("device must be 'cpu' or 'cuda'")
        if self.clip_len <= 0:
            raise ValueError("clip_len must be > 0")
        if self.clip_stride <= 0:
            raise ValueError("clip_stride must be > 0")
        if self.crop_size <= 0 or self.resize_short <= 0:
            raise ValueError("resize_short/crop_size must be > 0")
        if not (0.0 <= self.yolo_conf <= 1.0):
            raise ValueError("yolo_conf must be in [0,1]")
        if not (0.0 <= self.yolo_iou <= 1.0):
            raise ValueError("yolo_iou must be in [0,1]")
        if self.people_min < 0:
            raise ValueError("people_min must be >= 0")
        if not (0.0 <= self.fight_threshold <= 1.0):
            raise ValueError("fight_threshold must be in [0,1]")


@dataclass(frozen=True)
class Paths:
    project_root: Path = Path(".")
    default_data_root: Path = Path("data/rwf2000")
    default_outputs: Path = Path("outputs")


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}

