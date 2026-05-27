from __future__ import annotations

from pathlib import Path
from time import time

import multiprocessing as mp
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OPENCV_OPENCL_RUNTIME"] = ""
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"

import torch
from tqdm import tqdm

from fight3d.config import Config
from fight3d.data.sampler import build_dataloaders
from fight3d.models.r3d import build_r3d, save_checkpoint
from fight3d.train.eval import compute_metrics
from fight3d.utils.io import ensure_dir, save_json, set_seed


@torch.inference_mode()
def _run_val(model: torch.nn.Module, loader, device: torch.device) -> tuple[float, dict]:
    print(f"[DEBUG] Валидация: начало, устройство {device}")
    model.eval()
    ce = torch.nn.CrossEntropyLoss()

    total_loss = 0.0
    total = 0
    all_true: list[int] = []
    all_pred: list[int] = []

    for x, y, _meta in loader:
        # x = x.to(device)
    # for i, (x, y, _meta) in enumerate(loader):
    #     if i % 10 == 0:
    #         print(f"[DEBUG] Валидация: обработано {i} батчей")        
        x = x.to(device, non_blocking=True)
        y_t = torch.as_tensor(y, device=device).long()
        logits = model(x)
        loss = ce(logits, y_t)
        pred = logits.argmax(dim=1)

        bs = int(x.size(0))
        total_loss += float(loss.item()) * bs
        total += bs

        all_true.extend(y_t.detach().cpu().tolist())
        all_pred.extend(pred.detach().cpu().tolist())
    # print(f"[DEBUG] Валидация: обработано всего {total}")
    avg_loss = total_loss / max(1, total)
    metrics = compute_metrics(all_true, all_pred)
    metrics["val_loss"] = float(avg_loss)
    # print(f"[DEBUG] Валидация: метрики посчитаны")
    return float(avg_loss), metrics


def main() -> None:
    import argparse

    mp.set_start_method('spawn', force=True)

    p = argparse.ArgumentParser()
    p.add_argument("--data_root", type=str, default="data/rwf2000")
    p.add_argument("--epochs", type=int, required=True)
    p.add_argument("--batch_size", type=int, required=True)
    p.add_argument("--num_workers", type=int, default=4, help="Number of data loading workers")
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--device", type=str, default="auto", choices=["cpu", "cuda", "auto"])
    p.add_argument("--output", type=str, default="outputs/r3d_rwf")
    p.add_argument("--gpu_ids", type=str, default="0,1", help="GPU IDs to use, e.g. '0,1'")
    args = p.parse_args()

    cfg = Config(
        device=("cuda" if (args.device == "auto" and torch.cuda.is_available()) else ("cpu" if args.device == "auto" else args.device)),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        epochs=int(args.epochs),
        num_workers=int(args.num_workers),
    )
    set_seed(cfg.seed)

    out_dir = ensure_dir(args.output)
    out_dir = Path(out_dir)

    device = torch.device(cfg.device)
    train_loader, val_loader = build_dataloaders(cfg, root=Path(args.data_root))

    gpu_ids = [int(id) for id in args.gpu_ids.split(',')]
    num_gpus = len(gpu_ids)
    if cfg.batch_size % num_gpus != 0:
        print(f"Warning: batch_size ({cfg.batch_size}) should be divisible by number of GPUs ({num_gpus})")

    # model = build_r3d(num_classes=2, pretrained=True).to(device)
    model = build_r3d(num_classes=2, pretrained=True)
    if device.type == "cuda" and num_gpus > 1 and torch.cuda.device_count() >= num_gpus:
        print(f"Using DataParallel with GPUs: {gpu_ids}")
        model = torch.nn.DataParallel(model, device_ids=gpu_ids)
        model = model.to(device)
    else:
        print(f"Using single device: {device}")
        model = model.to(device)


    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=1e-4)
    criterion = torch.nn.CrossEntropyLoss()
    amp_enabled = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)

    history: list[dict] = []
    best_f1 = -1.0
    best_epoch = -1
    t0 = time()

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch}/{cfg.epochs}")

        for x, y, _meta in pbar:
            # x = x.to(device)
            x = x.to(device, non_blocking=True)
            y_t = torch.as_tensor(y, device=device).long()
            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast("cuda", enabled=amp_enabled):
                logits = model(x)
                loss = criterion(logits, y_t)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            bs = int(x.size(0))
            running_loss += float(loss.item()) * bs
            seen += bs
            pbar.set_postfix(train_loss=running_loss / max(1, seen))
        print(f"[DEBUG] Эпоха {epoch}: обучение завершено, запускаю валидацию")
        _val_loss, val_metrics = _run_val(model, val_loader, device)

        print(f"[DEBUG] Валидация завершена, loss: {_val_loss}")
        train_loss = running_loss / max(1, seen)
        # print(f"[DEBUG] Сохраняю метрики эпохи {epoch}")
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": float(train_loss),
            **val_metrics,
        }
        history.append(epoch_metrics)

        # save last
        # save_checkpoint(model, optimizer, epoch, out_dir / "last.pt", metrics=epoch_metrics)
        save_checkpoint(
            model.module if hasattr(model, 'module') else model, 
            optimizer, epoch, out_dir / "last.pt", metrics=epoch_metrics
        )
        # best by f1(Fight)
        # f1 = float(val_metrics.get("f1_fight", 0.0))
        # if f1 > best_f1:
        #     best_f1 = f1
        #     best_epoch = epoch
        #     save_checkpoint(model, optimizer, epoch, out_dir / "best.pt", metrics=epoch_metrics)
        f1 = float(val_metrics.get("f1_fight", 0.0))
        if f1 > best_f1:
            best_f1 = f1
            best_epoch = epoch
            save_checkpoint(
                model.module if hasattr(model, 'module') else model,
                optimizer, epoch, out_dir / "best.pt", metrics=epoch_metrics
            )

        print({"epoch": epoch, "acc": val_metrics["acc"], "f1_fight": f1, "best_f1": best_f1})

        metrics_payload = {
            "hparams": {
                "data_root": str(args.data_root),
                "epochs": cfg.epochs,
                "batch_size": cfg.batch_size,
                "lr": cfg.lr,
                "device": str(device),
                "gpu_ids": args.gpu_ids,
                "seed": cfg.seed,
                "clip_len": cfg.clip_len,
                "clip_stride": cfg.clip_stride,
                "resize_short": cfg.resize_short,
                "crop_size": cfg.crop_size,
            },
            "best": {
                "epoch": int(best_epoch),
                "f1_fight": float(best_f1),
            },
            "epochs": history,
            "wall_time_sec": float(time() - t0),
        }
        save_json(out_dir / "metrics.json", metrics_payload)


if __name__ == "__main__":
    main()
