"""
Офлайн-тест: прогоняет модель на клипах из data/ и выводит score.
Позволяет понять, как модель оценивает non-fall vs fall клипы.

Использование:
  python test_model_scores.py --ckpt outputs/r3d_falls_v3/best.pt --split val
  python test_model_scores.py --ckpt outputs/r3d_falls_v3/best.pt --split val --label non-fall --top 30
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch

from fight3d.data.transforms import make_val_transform
from fight3d.models.r3d import build_r3d, load_checkpoint


def read_video(path: Path, max_frames: int = 300) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open: {path}")
    frames = []
    for _ in range(max_frames):
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release()
    if not frames:
        raise RuntimeError(f"Empty video: {path}")
    return np.stack(frames)


def sample_indices(t: int, clip_len: int, stride: int) -> np.ndarray:
    """Детерминированный сэмплинг (center) — как будет на val."""
    need = clip_len * stride
    if t >= need:
        start = (t - need) // 2  # center crop temporally
        return start + np.arange(clip_len) * stride
    elif t >= clip_len:
        return np.linspace(0, t - 1, clip_len).astype(np.int64)
    else:
        idx = np.arange(t)
        pad = np.full(clip_len - t, t - 1, dtype=np.int64)
        return np.concatenate([idx, pad])


@torch.inference_mode()
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--data_root", default="data")
    p.add_argument("--split", default="val", choices=["train", "val"])
    p.add_argument("--label", default=None, choices=["fall", "non-fall"],
                   help="Filter by class. If omitted, show both.")
    p.add_argument("--clip_len", type=int, default=16)
    p.add_argument("--clip_stride", type=int, default=5)
    p.add_argument("--resize_short", type=int, default=288)
    p.add_argument("--crop_size", type=int, default=224)
    p.add_argument("--top", type=int, default=0,
                   help="Show only top-N highest scores (useful for finding FP in non-fall)")
    p.add_argument("--device", default="cuda")
    args = p.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    model = build_r3d(num_classes=2, pretrained=False).to(device)
    load_checkpoint(model, args.ckpt, map_location=device)
    model.eval()

    tfm = make_val_transform(resize_short=args.resize_short, crop_size=args.crop_size)

    root = Path(args.data_root) / args.split
    classes = ["non-fall", "fall"] if args.label is None else [args.label]

    results = []

    for cls in classes:
        folder = root / cls
        if not folder.exists():
            print(f"[SKIP] {folder} not found")
            continue
        videos = sorted(folder.glob("*.mp4"))
        print(f"[INFO] {cls}: {len(videos)} videos")

        for vi, vp in enumerate(videos):
            if (vi + 1) % 50 == 0:
                print(f"  [{cls}] {vi+1}/{len(videos)}...")
            try:
                frames = read_video(vp)
            except Exception as e:
                print(f"  [ERR] {vp.name}: {e}")
                continue

            idx = sample_indices(frames.shape[0], args.clip_len, args.clip_stride)
            clip = frames[idx]
            x = tfm(clip).unsqueeze(0).to(device)

            logits = model(x)
            proba = torch.softmax(logits, dim=-1)
            fall_score = float(proba[0, 1].item())

            results.append((cls, vp.name, fall_score, frames.shape[0]))

    # Sort by fall_score descending
    results.sort(key=lambda r: r[2], reverse=True)

    if args.top > 0:
        results = results[:args.top]

    print(f"\n{'Label':<10} {'Score':>6} {'Frames':>6}  File")
    print("-" * 70)
    for cls, name, score, nf in results:
        marker = " <<<" if (cls == "non-fall" and score > 0.8) else ""
        marker = marker or (" !!!" if (cls == "fall" and score < 0.5) else "")
        print(f"{cls:<10} {score:>6.3f} {nf:>6}  {name}{marker}")

    # Summary
    fall_scores = [s for c, _, s, _ in results if c == "fall"]
    nonfall_scores = [s for c, _, s, _ in results if c == "non-fall"]

    if fall_scores:
        print(f"\n[FALL]     mean={np.mean(fall_scores):.3f}  median={np.median(fall_scores):.3f}  "
              f"min={min(fall_scores):.3f}  max={max(fall_scores):.3f}  n={len(fall_scores)}")
    if nonfall_scores:
        fp_count = sum(1 for s in nonfall_scores if s >= 0.9)
        print(f"[NON-FALL] mean={np.mean(nonfall_scores):.3f}  median={np.median(nonfall_scores):.3f}  "
              f"min={min(nonfall_scores):.3f}  max={max(nonfall_scores):.3f}  n={len(nonfall_scores)}  "
              f"FP(>=0.9)={fp_count}")


if __name__ == "__main__":
    main()
