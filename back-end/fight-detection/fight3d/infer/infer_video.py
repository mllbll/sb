from __future__ import annotations

from collections import deque
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
import torch

from fight3d.data.transforms import make_val_transform
from fight3d.infer.yolo_people import PeopleDetector
from fight3d.models.r3d import build_r3d, load_checkpoint
from fight3d.utils.io import ensure_dir
from fight3d.utils.viz import DEFAULT_FIGHT_THRESHOLD, draw_boxes, put_status_line


BLINK_HZ = 2.0


def _union_xyxy(boxes: list[list[int]] | list[tuple[int, int, int, int]]) -> list[int] | None:
    if not boxes:
        return None
    x1 = min(int(b[0]) for b in boxes)
    y1 = min(int(b[1]) for b in boxes)
    x2 = max(int(b[2]) for b in boxes)
    y2 = max(int(b[3]) for b in boxes)
    return [x1, y1, x2, y2]


def _auto_device(device: str) -> str:
    d = (device or "auto").strip().lower()
    if d == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return d


def _preprocess_clip(frames_bgr: list[np.ndarray], tfm) -> torch.Tensor:
    frames_rgb = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr], axis=0)
    x = tfm(frames_rgb)  # (C,T,H,W)
    return x.unsqueeze(0)


@torch.inference_mode()
def _fight_score(model: torch.nn.Module, x: torch.Tensor) -> float:
    logits = model(x)
    proba = torch.softmax(logits, dim=-1)
    return float(proba[0, 1].detach().cpu().item())


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--video", type=str, required=True)
    p.add_argument("--ckpt", type=str, required=True)
    p.add_argument("--yolo_model", type=str, default="yolov8m.pt")
    p.add_argument("--device", type=str, default="auto")
    p.add_argument("--out", type=str, default="outputs/demo.mp4")
    p.add_argument("--fight_threshold", type=float, default=0.7)
    p.add_argument("--people_min", type=int, default=2)
    p.add_argument("--clip_len", type=int, default=16)
    p.add_argument("--stride", type=int, default=4, help="Temporal stride (compute every N frames)")
    p.add_argument("--yolo_conf", type=float, default=0.25)
    p.add_argument("--yolo_iou", type=float, default=0.7)
    args = p.parse_args()

    device_str = _auto_device(args.device)
    device = torch.device(device_str)

    # make viz threshold follow CLI without changing signature
    import fight3d.utils.viz as viz

    viz.DEFAULT_FIGHT_THRESHOLD = float(args.fight_threshold)

    model = build_r3d(num_classes=2, pretrained=False).to(device)
    load_checkpoint(model, args.ckpt, map_location=device)
    model.eval()

    people = PeopleDetector(
        yolo_model=args.yolo_model,
        device=device_str if device_str == "cpu" else "auto",
        conf=float(args.yolo_conf),
        iou=float(args.yolo_iou),
    )

    tfm = make_val_transform(resize_short=256, crop_size=224)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open: {args.video}")

    fps_in = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = Path(args.out)
    ensure_dir(out_path.parent)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps_in), (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open VideoWriter for: {out_path}")

    buf: deque[np.ndarray] = deque(maxlen=args.clip_len)
    frame_idx = 0

    state = "IDLE"
    score: float | None = None
    last_event_fight = False

    t_start = perf_counter()
    fps_smooth = None

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break

        frame_idx += 1
        buf.append(frame)

        boxes, scores = people.detect(frame)
        people_count = len(boxes)

        ts = frame_idx / max(1e-6, fps_in)

        if people_count < int(args.people_min):
            state = "IDLE"
            score = None
            last_event_fight = False
        else:
            if len(buf) == int(args.clip_len) and (frame_idx % int(args.stride) == 0):
                x = _preprocess_clip(list(buf), tfm=tfm).to(device)
                score = _fight_score(model, x)
                state = "FIGHT" if score >= float(args.fight_threshold) else "IDLE"

                if state == "FIGHT" and not last_event_fight:
                    print(f"[FIGHT] t={ts:.2f}s score={score:.3f} people={people_count}")
                    last_event_fight = True
                if state != "FIGHT":
                    last_event_fight = False

        vis = frame

        draw_state = state
        draw_score = score
        draw_boxes_list = boxes
        if draw_state == "FIGHT":
            blink_on = int(ts * BLINK_HZ) % 2 == 0
            if not blink_on:
                draw_state = "IDLE"

        if draw_state == "FIGHT":
            union = _union_xyxy(draw_boxes_list)
            vis = draw_boxes(vis, [union] if union is not None else [], state="FIGHT", score=draw_score)
        else:
            # still draw idle boxes (green) for context
            vis = draw_boxes(vis, boxes, state="IDLE", score=None)

        # bottom status line
        t_now = perf_counter()
        inst_fps = frame_idx / max(1e-6, (t_now - t_start))
        fps_smooth = inst_fps if fps_smooth is None else (0.9 * fps_smooth + 0.1 * inst_fps)
        score_txt = "-" if score is None else f"{score:.3f}"
        status = f"fps={fps_smooth:.1f}  state={state}  fight_score={score_txt}  people={people_count}"
        vis = put_status_line(vis, status)

        writer.write(vis)

    cap.release()
    writer.release()

    print(f"Saved: {out_path} (codec=mp4v, fps={fps_in:.2f}, size={w}x{h})")


if __name__ == "__main__":
    main()
