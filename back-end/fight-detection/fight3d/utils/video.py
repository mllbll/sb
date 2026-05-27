from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class VideoReader:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._cap = cv2.VideoCapture(self.path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")

        self.fps: float = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.total_frames: int = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    def __iter__(self) -> "VideoReader":
        return self

    def __next__(self) -> np.ndarray:
        ok, frame = self._cap.read()
        if not ok or frame is None:
            self.close()
            raise StopIteration
        return frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "VideoReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def read_clip(
    frames: list[np.ndarray],
    start_idx: int,
    clip_len: int,
    stride: int,
) -> list[np.ndarray]:
    if clip_len <= 0:
        return []
    if stride <= 0:
        raise ValueError("stride must be > 0")

    n = len(frames)
    if n == 0:
        return []

    out: list[np.ndarray] = []
    last = frames[-1]
    for i in range(clip_len):
        src_i = start_idx + i * stride
        if 0 <= src_i < n:
            out.append(frames[src_i])
        else:
            out.append(last)
    return out


def get_video_meta(path: str | Path) -> tuple[int, float, int, int]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {path}")
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return n_frames, fps, w, h


def sample_indices(n_frames: int, clip_len: int, stride: int, start: int | None = None) -> np.ndarray:
    if n_frames <= 0:
        return np.zeros((clip_len,), dtype=np.int64)
    max_start = max(0, n_frames - (clip_len - 1) * stride - 1)
    if start is None:
        start = np.random.randint(0, max_start + 1) if max_start > 0 else 0
    idx = start + np.arange(clip_len, dtype=np.int64) * stride
    idx = np.clip(idx, 0, n_frames - 1)
    return idx


def read_video_frames_at(path: str | Path, indices: np.ndarray) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {path}")

    frames: list[np.ndarray] = []
    last_i = -1
    for i in indices.tolist():
        if i != last_i:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, frame_bgr = cap.read()
            if not ok or frame_bgr is None:
                frame_bgr = np.zeros((224, 224, 3), dtype=np.uint8)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)
        last_i = i

    cap.release()
    return np.stack(frames, axis=0)  # (T, H, W, C)

