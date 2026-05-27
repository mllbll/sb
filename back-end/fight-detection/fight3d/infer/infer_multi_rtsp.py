from __future__ import annotations

import argparse
import multiprocessing as mp
import re
import signal
import time
from dataclasses import dataclass
from pathlib import Path

from fight3d.infer.rtsp_runner import run_rtsp
from fight3d.settings_yaml import load_settings
from fight3d.utils.io import ensure_dir


def _safe_name(name: str, idx: int) -> str:
    s = (name or "").strip()
    if not s:
        return f"cam_{idx}"
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    return s or f"cam_{idx}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()

    p.add_argument(
        "--config",
        type=str,
        default="",
        help="Optional path to config.yaml. If omitted, uses $FIGHT3D_CONFIG or ./config.yaml.",
    )

    p.add_argument(
        "--rtsp",
        type=str,
        action="append",
        default=[],
        help='Repeatable. RTSP URL or "file:video.avi". Example: --rtsp "rtsp://..." --rtsp "rtsp://..."',
    )
    p.add_argument(
        "--sources",
        type=str,
        default="",
        help="Optional text file with one RTSP/file source per line (blank lines and #comments ignored).",
    )

    p.add_argument("--ckpt", type=str, default="")
    p.add_argument("--yolo_model", type=str, default=None)
    p.add_argument("--device", type=str, default=None, choices=["auto", "cpu", "cuda"])

    p.add_argument(
        "--save_dir",
        type=str,
        default=None,
        help="Optional directory to save one mp4 per camera (cam_0.mp4, cam_1.mp4, ...).",
    )
    p.add_argument("--fight_threshold", type=float, default=None)
    p.add_argument("--people_min", type=int, default=None)
    p.add_argument("--clip_len", type=int, default=None)
    p.add_argument("--stride", type=int, default=None)

    p.add_argument(
        "--show",
        type=int,
        default=None,
        choices=[0, 1],
        help="0 recommended for server (no GUI). If 1, opens one window per camera.",
    )

    p.add_argument("--yolo_conf", type=float, default=None)
    p.add_argument("--yolo_iou", type=float, default=None)

    return p.parse_args()


def _maybe_load_settings(args: argparse.Namespace):
    if args.config:
        return load_settings(args.config)
    need_config = (not str(args.ckpt or "").strip()) or (not (args.rtsp or []) and not args.sources)
    if not need_config:
        return None
    return load_settings()


def _load_sources(args: argparse.Namespace, settings) -> list[tuple[str, str]]:
    sources: list[tuple[str, str, float | None]] = []
    for i, s in enumerate(args.rtsp or []):
        ss = str(s).strip()
        if not ss:
            continue
        sources.append((f"cam-{i}", ss, None))

    if args.sources:
        txt = Path(args.sources)
        lines = txt.read_text(encoding="utf-8").splitlines()
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            sources.append((f"cam-{len(sources)}", s, None))

    if not sources and settings is not None:
        for cam in settings.cameras:
            sources.append((cam.name, cam.rtsp, cam.fight_threshold))

    # de-dupe but keep order
    seen: set[str] = set()
    out: list[tuple[str, str, float | None]] = []
    for name, url, ft in sources:
        if url in seen:
            continue
        seen.add(url)
        out.append((name, url, ft))

    return out


def _worker(
    *,
    idx: int,
    name: str,
    rtsp: str,
    args: argparse.Namespace,
    save_path: str,
    fight_threshold: float,
) -> None:
    safe = _safe_name(name, idx)
    window_name = f"fight3d-{safe}"
    run_rtsp(
        rtsp=rtsp,
        ckpt=args.ckpt,
        yolo_model=args.yolo_model,
        device=args.device,
        save=save_path,
        fight_threshold=float(fight_threshold),
        people_min=int(args.people_min),
        clip_len=int(args.clip_len),
        stride=int(args.stride),
        show=int(args.show),
        yolo_conf=float(args.yolo_conf),
        yolo_iou=float(args.yolo_iou),
        window_name=window_name,
        camera_external_id=safe,
    )


@dataclass
class _WorkerSpec:
    idx: int
    name: str
    rtsp: str
    save_path: str
    fight_threshold: float
    proc: mp.Process | None = None
    restarts: int = 0
    last_start_ts: float = 0.0


def _start_proc(*, ctx: mp.context.BaseContext, spec: _WorkerSpec, args: argparse.Namespace) -> mp.Process:
    p = ctx.Process(
        target=_worker,
        kwargs={
            "idx": spec.idx,
            "name": spec.name,
            "rtsp": spec.rtsp,
            "args": args,
            "save_path": spec.save_path,
            "fight_threshold": spec.fight_threshold,
        },
        daemon=False,
    )
    p.start()
    return p


def main() -> None:
    args = _parse_args()

    settings = _maybe_load_settings(args)
    if settings is not None:
        inf = settings.inference
        if not str(args.ckpt or "").strip():
            args.ckpt = inf.ckpt
        if args.yolo_model is None:
            args.yolo_model = inf.yolo_model
        if args.device is None:
            args.device = inf.device
        if args.fight_threshold is None:
            args.fight_threshold = inf.fight_threshold
        if args.people_min is None:
            args.people_min = inf.people_min
        if args.clip_len is None:
            args.clip_len = inf.clip_len
        if args.stride is None:
            args.stride = inf.stride
        if args.show is None:
            args.show = inf.show
        if args.save_dir is None:
            args.save_dir = inf.save_dir
        if args.yolo_conf is None:
            args.yolo_conf = inf.yolo_conf
        if args.yolo_iou is None:
            args.yolo_iou = inf.yolo_iou

    if args.yolo_model is None:
        args.yolo_model = "yolov8m.pt"
    if args.device is None:
        args.device = "auto"
    if args.fight_threshold is None:
        args.fight_threshold = 0.7
    if args.people_min is None:
        args.people_min = 2
    if args.clip_len is None:
        args.clip_len = 16
    if args.stride is None:
        args.stride = 4
    if args.show is None:
        args.show = 0
    if args.save_dir is None:
        args.save_dir = ""
    if args.yolo_conf is None:
        args.yolo_conf = 0.25
    if args.yolo_iou is None:
        args.yolo_iou = 0.7

    sources = _load_sources(args, settings)
    if not sources:
        raise SystemExit(
            "No sources provided. Use --rtsp ... (repeatable), --sources sources.txt, or add cameras[] to config.yaml"
        )

    print(
        "[infer] sources="
        + ", ".join(
            [
                f"{name} -> {('rtsp://' + url.split('rtsp://',1)[1].split('@',1)[1]) if url.startswith('rtsp://') and '@' in url else url}"
                for name, url, _ft in sources
            ]
        ),
        flush=True,
    )

    if not str(args.ckpt or "").strip():
        raise SystemExit("No --ckpt provided and inference.ckpt is missing in config.yaml")

    save_dir = Path(args.save_dir) if args.save_dir else None
    if save_dir is not None:
        ensure_dir(save_dir)

    ctx = mp.get_context("spawn")

    specs: list[_WorkerSpec] = []
    for idx, (name, rtsp, ft_override) in enumerate(sources):
        save_path = str(save_dir) if save_dir is not None else ""
        ft = float(ft_override) if ft_override is not None else float(args.fight_threshold)
        specs.append(
            _WorkerSpec(
                idx=idx,
                name=name,
                rtsp=rtsp,
                save_path=save_path,
                fight_threshold=ft,
            )
        )

    stop = False

    def _handle_stop(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    # Start all workers.
    for spec in specs:
        print(f"[infer] starting worker idx={spec.idx} name={spec.name} save={spec.save_path or '-'}", flush=True)
        spec.proc = _start_proc(ctx=ctx, spec=spec, args=args)
        spec.last_start_ts = time.time()

    # Supervise: if a worker exits (RTSP hiccup, decode error, etc.), restart only that worker.
    # This prevents the whole container from exiting with code 0 and being restarted by Docker.
    while not stop:
        for spec in specs:
            p = spec.proc
            if p is None:
                continue
            if p.exitcode is None:
                continue

            # Process exited.
            code = p.exitcode
            runtime = time.time() - spec.last_start_ts
            spec.restarts += 1
            print(
                f"[infer] worker exited idx={spec.idx} name={spec.name} exitcode={code} runtime={runtime:.1f}s restarts={spec.restarts}",
                flush=True,
            )

            # Short backoff to avoid tight restart loops.
            time.sleep(1.0)
            if stop:
                break

            print(f"[infer] restarting worker idx={spec.idx} name={spec.name}", flush=True)
            spec.proc = _start_proc(ctx=ctx, spec=spec, args=args)
            spec.last_start_ts = time.time()

        time.sleep(0.5)

    # Stop requested: terminate all workers.
    for spec in specs:
        p = spec.proc
        if p is not None and p.is_alive():
            p.terminate()
    for spec in specs:
        p = spec.proc
        if p is not None:
            p.join(timeout=2)


if __name__ == "__main__":
    main()
