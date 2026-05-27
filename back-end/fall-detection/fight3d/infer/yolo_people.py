from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


DeviceArg = Literal["auto", "cpu", "cuda"] | str | int


@dataclass(frozen=True)
class PersonDet:
    xyxy: tuple[int, int, int, int]
    conf: float


def _normalize_device(device: DeviceArg) -> str | int:
    if isinstance(device, int):
        return device

    d = str(device).strip().lower()
    if d in ("", "auto"):
        try:
            import torch

            return 0 if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    if d in ("cpu",):
        return "cpu"
    if d in ("cuda", "gpu", "0"):
        return 0
    if d.startswith("cuda:"):
        try:
            return int(d.split(":", 1)[1])
        except Exception:
            return 0
    return d


class PeopleDetector:
    def __init__(
        self,
        yolo_model: str = "yolov8m.pt",
        device: DeviceArg = "auto",
        conf: float = 0.25,
        iou: float = 0.7,
        imgsz: int | None = None,
    ) -> None:
        from ultralytics import YOLO

        self.yolo_model = yolo_model
        self.device = _normalize_device(device)
        self.conf = float(conf)
        self.iou = float(iou)
        self.imgsz = int(imgsz) if imgsz is not None else None
        self.top_k = 10
        self.model = YOLO(yolo_model)

    def detect(self, frame_bgr: np.ndarray) -> tuple[list[list[int]], list[float]]:
        # ultralytics expects BGR OK
        kwargs = {
            "source": frame_bgr,
            "verbose": False,
            "conf": self.conf,
            "iou": self.iou,
            "device": self.device,
            "classes": [0],
        }
        if self.imgsz is not None and self.imgsz > 0:
            kwargs["imgsz"] = int(self.imgsz)

        res = self.model.predict(
            **kwargs,
        )[0]

        if res.boxes is None or len(res.boxes) == 0:
            return [], []

        boxes = res.boxes.xyxy.detach().cpu().numpy()
        scores = res.boxes.conf.detach().cpu().numpy()
        clss = res.boxes.cls.detach().cpu().numpy().astype(int)

        persons: list[tuple[int, int, int, int, float, int]] = []
        for xyxy, s, c in zip(boxes, scores, clss):
            if int(c) != 0:
                continue
            x1, y1, x2, y2 = [int(v) for v in xyxy.tolist()]
            area = max(0, x2 - x1) * max(0, y2 - y1)
            persons.append((x1, y1, x2, y2, float(s), int(area)))

        persons.sort(key=lambda t: t[5], reverse=True)  # area desc
        persons = persons[: self.top_k]
        out_boxes = [[p[0], p[1], p[2], p[3]] for p in persons]
        out_scores = [p[4] for p in persons]
        return out_boxes, out_scores


# Backward compatible wrapper for existing inference code
class YoloPeople:
    def __init__(self, model_name: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.7, device: DeviceArg = "auto") -> None:
        self.detector = PeopleDetector(yolo_model=model_name, device=device, conf=conf, iou=iou)

    def detect(self, frame_bgr: np.ndarray) -> list[PersonDet]:
        boxes, scores = self.detector.detect(frame_bgr)
        return [PersonDet(xyxy=tuple(b), conf=float(s)) for b, s in zip(boxes, scores)]


def crop_box(frame_bgr: np.ndarray, xyxy: tuple[int, int, int, int], pad: float = 0.1) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = xyxy
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    px = int(bw * pad)
    py = int(bh * pad)
    x1 = max(0, x1 - px)
    y1 = max(0, y1 - py)
    x2 = min(w - 1, x2 + px)
    y2 = min(h - 1, y2 + py)
    return frame_bgr[y1 : y2 + 1, x1 : x2 + 1]
