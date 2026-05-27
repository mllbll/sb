from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torchvision


def count_trainable_params(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def build_r3d(num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    if pretrained:
        weights = torchvision.models.video.R3D_18_Weights.DEFAULT
        model = torchvision.models.video.r3d_18(weights=weights)
    else:
        model = torchvision.models.video.r3d_18(weights=None)

    in_features = int(model.fc.in_features)
    model.fc = nn.Linear(in_features, int(num_classes))

    n_params = count_trainable_params(model)
    print(f"Trainable params: {n_params:,}")
    return model


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None,
    epoch: int,
    path: str | Path,
    **extra: Any,
) -> None:
    payload: dict[str, Any] = {
        "model": model.state_dict(),
        "epoch": int(epoch),
    }
    if optimizer is not None:
        payload["optimizer"] = optimizer.state_dict()
    payload.update(extra)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def load_checkpoint(
    model: nn.Module,
    path: str | Path,
    optimizer: torch.optim.Optimizer | None = None,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    payload = torch.load(Path(path), map_location=map_location)
    model.load_state_dict(payload["model"], strict=True)
    if optimizer is not None and "optimizer" in payload:
        optimizer.load_state_dict(payload["optimizer"])
    return payload


@torch.inference_mode()
def predict_proba(model: nn.Module, x: torch.Tensor) -> torch.Tensor:
    logits = model(x)
    return torch.softmax(logits, dim=-1)
