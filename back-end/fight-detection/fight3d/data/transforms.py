from __future__ import annotations

from typing import Callable, Protocol

import numpy as np
import torch


class VideoTransform(Protocol):
    def __call__(self, frames_rgb: np.ndarray) -> torch.Tensor: ...


def _resize_short_side(frames: np.ndarray, resize_short: int) -> np.ndarray:
    import cv2

    t, h, w, c = frames.shape
    if min(h, w) == resize_short:
        return frames

    if h < w:
        new_h = resize_short
        new_w = int(round(w * resize_short / max(1, h)))
    else:
        new_w = resize_short
        new_h = int(round(h * resize_short / max(1, w)))

    out = np.empty((t, new_h, new_w, c), dtype=frames.dtype)
    for i in range(t):
        out[i] = cv2.resize(frames[i], (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return out


def _center_crop(frames: np.ndarray, crop_size: int) -> np.ndarray:
    t, h, w, c = frames.shape
    if h < crop_size or w < crop_size:
        return frames
    y1 = (h - crop_size) // 2
    x1 = (w - crop_size) // 2
    return frames[:, y1 : y1 + crop_size, x1 : x1 + crop_size, :]


def _random_crop(frames: np.ndarray, crop_size: int) -> np.ndarray:
    t, h, w, c = frames.shape
    if h < crop_size or w < crop_size:
        return frames
    y1 = int(np.random.randint(0, h - crop_size + 1))
    x1 = int(np.random.randint(0, w - crop_size + 1))
    return frames[:, y1 : y1 + crop_size, x1 : x1 + crop_size, :]


def _ensure_min_size(frames: np.ndarray, min_size: int) -> np.ndarray:
    import cv2

    t, h, w, c = frames.shape
    if h >= min_size and w >= min_size:
        return frames
    out = np.empty((t, min_size, min_size, c), dtype=frames.dtype)
    for i in range(t):
        out[i] = cv2.resize(frames[i], (min_size, min_size), interpolation=cv2.INTER_LINEAR)
    return out


def _hflip(frames: np.ndarray) -> np.ndarray:
    # Slicing with ::-1 creates a negative-stride view; make it contiguous.
    return frames[:, :, ::-1, :].copy()


def _to_tensor_and_normalize(frames_rgb: np.ndarray) -> torch.Tensor:
    frames_rgb = np.ascontiguousarray(frames_rgb)
    x = torch.from_numpy(frames_rgb).permute(3, 0, 1, 2).float() / 255.0  # (C,T,H,W)

    # Kinetics-400 normalization used by torchvision video models
    mean = torch.tensor([0.43216, 0.394666, 0.37645])[:, None, None, None]
    std = torch.tensor([0.22803, 0.22145, 0.216989])[:, None, None, None]
    return (x - mean) / std

class TrainTransform:
    """Train transform that can be pickled."""
    
    def __init__(self, resize_short: int = 256, crop_size: int = 224, p_hflip: float = 0.5):
        self.resize_short = resize_short
        self.crop_size = crop_size
        self.p_hflip = p_hflip
    
    def __call__(self, frames_rgb: np.ndarray) -> torch.Tensor:
        # Защита от OpenCV в каждом вызове
        try:
            import cv2
            cv2.setNumThreads(0)
        except:
            pass
            
        frames = _resize_short_side(frames_rgb, resize_short=self.resize_short)
        frames = _ensure_min_size(frames, min_size=self.crop_size)
        frames = _random_crop(frames, crop_size=self.crop_size)
        if self.p_hflip > 0 and np.random.rand() < self.p_hflip:
            frames = _hflip(frames)
        return _to_tensor_and_normalize(frames)

class ValTransform:
    """Validation transform that can be pickled."""
    
    def __init__(self, resize_short: int = 256, crop_size: int = 224):
        self.resize_short = resize_short
        self.crop_size = crop_size
    
    def __call__(self, frames_rgb: np.ndarray) -> torch.Tensor:
        frames = _resize_short_side(frames_rgb, resize_short=self.resize_short)
        frames = _ensure_min_size(frames, min_size=self.crop_size)
        frames = _center_crop(frames, crop_size=self.crop_size)
        return _to_tensor_and_normalize(frames)

def make_train_transform(
    *,
    resize_short: int = 256,
    crop_size: int = 224,
    p_hflip: float = 0.5,
) -> TrainTransform:
    """Factory function for train transform."""
    return TrainTransform(
        resize_short=resize_short,
        crop_size=crop_size,
        p_hflip=p_hflip
    )


def make_val_transform(
    *,
    resize_short: int = 256,
    crop_size: int = 224,
) -> ValTransform:
    """Factory function for validation transform."""
    return ValTransform(
        resize_short=resize_short,
        crop_size=crop_size
    )

# def make_train_transform(
#     *,
#     resize_short: int = 256,
#     crop_size: int = 224,
#     p_hflip: float = 0.5,
# ) -> Callable[[np.ndarray], torch.Tensor]:
#     def _tfm(frames_rgb: np.ndarray) -> torch.Tensor:
#         frames = _resize_short_side(frames_rgb, resize_short=resize_short)
#         frames = _ensure_min_size(frames, min_size=crop_size)
#         frames = _random_crop(frames, crop_size=crop_size)
#         if float(p_hflip) > 0 and np.random.rand() < float(p_hflip):
#             frames = _hflip(frames)
#         return _to_tensor_and_normalize(frames)

#     return _tfm


# def make_val_transform(
#     *,
#     resize_short: int = 256,
#     crop_size: int = 224,
# ) -> Callable[[np.ndarray], torch.Tensor]:
#     def _tfm(frames_rgb: np.ndarray) -> torch.Tensor:
#         frames = _resize_short_side(frames_rgb, resize_short=resize_short)
#         frames = _ensure_min_size(frames, min_size=crop_size)
#         frames = _center_crop(frames, crop_size=crop_size)
#         return _to_tensor_and_normalize(frames)

#     return _tfm
