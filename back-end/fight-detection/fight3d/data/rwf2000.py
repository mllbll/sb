from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
from torch.utils.data import Dataset

from fight3d.data.transforms import VideoTransform


Split = Literal["train", "val"]


@dataclass(frozen=True)
class _VideoItem:
    path: Path
    label: int


def _list_videos(root: Path) -> list[Path]:
    exts = {".mp4", ".avi", ".mov", ".mkv"}
    if not root.exists():
        return []
    paths: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            paths.append(p)
    return sorted(paths)


def _discover_layout(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (fight_videos, nonfight_videos) from supported layouts.

    Supported:
    - root/Fight + root/NonFight
    - root/train/Fight + root/train/NonFight + root/val/Fight + root/val/NonFight
    """
    fight = _list_videos(root / "Fight")
    nonfight = _list_videos(root / "NonFight")
    if len(fight) > 0 or len(nonfight) > 0:
        return fight, nonfight

    fight = _list_videos(root / "train" / "Fight") + _list_videos(root / "val" / "Fight")
    nonfight = _list_videos(root / "train" / "NonFight") + _list_videos(root / "val" / "NonFight")
    return sorted(fight), sorted(nonfight)


def _split_paths(paths: list[Path], seed: int, train_ratio: float = 0.8) -> tuple[list[Path], list[Path]]:
    import random

    rng = random.Random(int(seed))
    paths = list(paths)
    rng.shuffle(paths)
    n_train = int(round(len(paths) * float(train_ratio)))
    n_train = max(0, min(len(paths), n_train))
    return paths[:n_train], paths[n_train:]


class RWFDataset(Dataset):
    """RWF-2000 fine-tune dataset with deterministic 80/20 split.

    - class mapping: Fight=1, NonFight=0
    - split is made randomly by *video*, but fixed by `seed`.
    - clip is sampled randomly per __getitem__ without loading full video into RAM.
    """

    def __init__(
        self,
        root: str | Path,
        split: Split,
        *,
        seed: int = 42,
        clip_len: int = 16,
        stride: int = 1,
        transform: VideoTransform | None = None,
        train_ratio: float = 0.8,
    ) -> None:
        self.root = Path(root)
        self.split: Split = split
        self.seed = int(seed)
        self.clip_len = int(clip_len)
        self.stride = int(stride)
        self.transform = transform

        if self.clip_len <= 0:
            raise ValueError("clip_len must be > 0")
        if self.stride <= 0:
            raise ValueError("stride must be > 0")
        if self.split not in ("train", "val"):
            raise ValueError("split must be 'train' or 'val'")

        fight_paths, nonfight_paths = _discover_layout(self.root)
        if len(fight_paths) == 0 and len(nonfight_paths) == 0:
            raise FileNotFoundError(
                "RWF-2000 videos not found under root. Expected either root/Fight+NonFight "
                "or root/train|val/(Fight|NonFight)."
            )

        # Stratified deterministic split per class
        fight_tr, fight_val = _split_paths(fight_paths, seed=self.seed + 1, train_ratio=train_ratio)
        nf_tr, nf_val = _split_paths(nonfight_paths, seed=self.seed + 2, train_ratio=train_ratio)

        if self.split == "train":
            selected = [(p, 1) for p in fight_tr] + [(p, 0) for p in nf_tr]
        else:
            selected = [(p, 1) for p in fight_val] + [(p, 0) for p in nf_val]

        # deterministic order
        import random

        rng = random.Random(self.seed + (0 if self.split == "train" else 999))
        rng.shuffle(selected)

        self.items: list[_VideoItem] = [_VideoItem(path=p, label=lab) for p, lab in selected]
        if len(self.items) == 0:
            raise RuntimeError(f"Empty split '{self.split}'. Check dataset root: {self.root}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int, dict]:
        item = self.items[idx]
        frames_rgb, start_frame = self._read_random_clip_rgb(item.path)

        if self.transform is not None:
            x = self.transform(frames_rgb)
        else:
            x = torch.from_numpy(frames_rgb).permute(3, 0, 1, 2).float() / 255.0

        meta = {
            "video_path": str(item.path),
            "start_frame": int(start_frame),
        }
        return x, int(item.label), meta

    def labels(self) -> list[int]:
        return [it.label for it in self.items]

    def _read_random_clip_rgb(self, path: Path):
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")

        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        need = (self.clip_len - 1) * self.stride + 1

        if n_frames > 0:
            max_start = max(0, n_frames - need)
            start_frame = int(np.random.randint(0, max_start + 1)) if max_start > 0 else 0
        else:
            start_frame = 0

        frames: list[np.ndarray] = []
        last_bgr: np.ndarray | None = None
        for t in range(self.clip_len):
            frame_idx = start_frame + t * self.stride
            if n_frames > 0 and frame_idx >= n_frames:
                if last_bgr is None:
                    last_bgr = np.zeros((self.crop_len_fallback_h(), self.crop_len_fallback_w(), 3), dtype=np.uint8)
                frames.append(cv2.cvtColor(last_bgr, cv2.COLOR_BGR2RGB))
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
            ok, frame_bgr = cap.read()
            if not ok or frame_bgr is None:
                if last_bgr is None:
                    # create a minimal black frame if we never got any data
                    frame_bgr = np.zeros((224, 224, 3), dtype=np.uint8)
                else:
                    frame_bgr = last_bgr
            last_bgr = frame_bgr
            frames.append(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

        cap.release()
        return np.stack(frames, axis=0), start_frame  # (T,H,W,C)

    @staticmethod
    def crop_len_fallback_h() -> int:
        return 224

    @staticmethod
    def crop_len_fallback_w() -> int:
        return 224
