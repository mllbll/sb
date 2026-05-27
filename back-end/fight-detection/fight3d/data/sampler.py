from __future__ import annotations

from collections import Counter
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from fight3d.config import Config
from fight3d.data.rwf2000 import RWFDataset
from fight3d.data.transforms import make_train_transform, make_val_transform

def make_weighted_sampler(labels: list[int]) -> torch.utils.data.WeightedRandomSampler:
    counts = Counter(labels)
    weights = np.array([1.0 / counts[int(y)] for y in labels], dtype=np.float64)
    weights_t = torch.from_numpy(weights)
    return torch.utils.data.WeightedRandomSampler(weights=weights_t, num_samples=len(labels), replacement=True)


def worker_init_fn(worker_id: int, seed: int) -> None:
    """Инициализация seed для воркера."""
    try:
        import cv2
        cv2.setNumThreads(0)
        cv2.ocl.setUseOpenCL(False)
    except ImportError:
        pass
    
    # Отключаем многопоточность в numpy и torch
    import torch
    torch.set_num_threads(1)
    
    # Устанавливаем seed
    random.seed(seed + worker_id)
    np.random.seed(seed + worker_id)
    torch.manual_seed(seed + worker_id)
    
    # Дополнительная защита для PyTorch
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

class WorkerInitializer:
    """Callable class for worker initialization that can be pickled."""
    
    def __init__(self, seed: int):
        self.seed = seed
    
    def __call__(self, worker_id: int) -> None:
        worker_init_fn(worker_id, self.seed)


def build_dataloaders(cfg: Config, root: str | Path):
    root = Path(root)
    train_tfm = make_train_transform(resize_short=cfg.resize_short, crop_size=cfg.crop_size)
    val_tfm = make_val_transform(resize_short=cfg.resize_short, crop_size=cfg.crop_size)

    train_ds = RWFDataset(
        root=root,
        split="train",
        seed=cfg.seed,
        clip_len=cfg.clip_len,
        stride=cfg.clip_stride,
        transform=train_tfm,
    )
    val_ds = RWFDataset(
        root=root,
        split="val",
        seed=cfg.seed,
        clip_len=cfg.clip_len,
        stride=cfg.clip_stride,
        transform=val_tfm,
    )

    pin = cfg.device == "cuda"
    gen = torch.Generator()
    gen.manual_seed(int(cfg.seed))

    train_loader = DataLoader(
        train_ds,
        batch_size=int(cfg.batch_size),
        shuffle=True,
        num_workers=int(cfg.num_workers),
        pin_memory=pin,
        drop_last=True,
        # worker_init_fn=lambda worker_id: worker_init_fn(worker_id, cfg.seed),
        worker_init_fn=WorkerInitializer(cfg.seed),
        generator=gen,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=int(cfg.batch_size),
        shuffle=False,
        num_workers=int(cfg.num_workers),
        pin_memory=pin,
        drop_last=False,
        worker_init_fn=WorkerInitializer(cfg.seed + 10000),
        # worker_init_fn=_worker_init_fn(cfg.seed + 10_000),
    )
    return train_loader, val_loader
