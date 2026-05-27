from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import perf_counter
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2
import numpy as np
import torch

from fight3d.data.transforms import make_val_transform
from fight3d.infer.yolo_people import PeopleDetector
from fight3d.models.r3d import build_r3d, load_checkpoint
from fight3d.utils.io import ensure_dir
from fight3d.utils.viz import draw_boxes, put_status_line


BLINK_HZ = 2.0


def _redact_rtsp(rtsp_or_file: str) -> str:
    s = (rtsp_or_file or "").strip()
    if s.lower().startswith("rtsp://") and "@" in s:
        # rtsp://user:pass@host/... -> rtsp://***@host/...
        prefix, rest = s.split("rtsp://", 1)
        creds, tail = rest.split("@", 1)
        return "rtsp://***@" + tail
    return s


def _is_dir_save_path(save: str) -> bool:
    s = (save or "").strip()
    if not s:
        return False
    p = Path(s)
    if p.exists() and p.is_dir():
        return True
    if s.endswith("/") or s.endswith(os.sep):
        return True
    return p.suffix == ""


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
        if not torch.cuda.is_available():
            return "cpu"
        # CUDA may look available in a container even when the host driver isn't.
        # Try a tiny allocation; if it fails, fall back to CPU.
        try:
            _ = torch.zeros(1, device="cuda")
            return "cuda"
        except Exception:
            return "cpu"
    return d


def _open_source(rtsp_or_file: str) -> cv2.VideoCapture:
    src = (rtsp_or_file or "").strip()
    if src.lower().startswith("file:"):
        src = src.split(":", 1)[1]
    cap = cv2.VideoCapture(src)
    return cap


def _preprocess_clip(frames_bgr: list[np.ndarray], tfm) -> torch.Tensor:
    frames_rgb = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_bgr], axis=0)
    x = tfm(frames_rgb)  # (C,T,H,W)
    return x.unsqueeze(0)


@torch.inference_mode()
def _fight_score(model: torch.nn.Module, x: torch.Tensor) -> float:
    logits = model(x)
    proba = torch.softmax(logits, dim=-1)
    return float(proba[0, 1].detach().cpu().item())


def run_rtsp(
    *,
    rtsp: str,
    ckpt: str,
    yolo_model: str = "yolov8m.pt",
    device: str = "auto",
    save: str = "",
    fight_threshold: float = 0.7,
    people_min: int = 2,
    clip_len: int = 16,
    stride: int = 4,
    show: int = 1,
    yolo_conf: float = 0.25,
    yolo_iou: float = 0.7,
    window_name: str = "fight3d-rtsp",
    camera_external_id: str | None = None,
) -> None:
    device_str = _auto_device(device)
    torch_device = torch.device(device_str)

    debug_every_sec = float(os.getenv("FIGHT3D_INFER_DEBUG_EVERY_SEC", "5") or 0.0)
    if debug_every_sec < 0:
        debug_every_sec = 0.0
    last_debug_t = perf_counter()

    print(
        f"[START] src={window_name} device={device_str} rtsp={_redact_rtsp(rtsp)} "
        f"fight_threshold={float(fight_threshold)} people_min={int(people_min)} clip_len={int(clip_len)} stride={int(stride)}",
        flush=True,
    )

    # OpenCV GUI calls (imshow/waitKey) require a working X11/Wayland display.
    # In Docker this frequently crashes with Qt/xcb errors even if DISPLAY is set.
    # Default behavior: disable GUI in Docker unless explicitly allowed.
    in_docker = Path("/.dockerenv").exists()
    allow_gui = str(os.getenv("FIGHT3D_ALLOW_GUI", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    has_display = bool(os.getenv("DISPLAY", "").strip() or os.getenv("WAYLAND_DISPLAY", "").strip())
    if show == 1 and in_docker and not allow_gui:
        print(f"[VIS] disabled src={window_name} reason=docker_headless", flush=True)
        show = 0
    elif show == 1 and not has_display:
        print(f"[VIS] disabled src={window_name} reason=no_display", flush=True)
        show = 0

    import fight3d.utils.viz as viz

    viz.DEFAULT_FIGHT_THRESHOLD = float(fight_threshold)

    model = build_r3d(num_classes=2, pretrained=False).to(torch_device)
    load_checkpoint(model, ckpt, map_location=torch_device)
    model.eval()

    people = PeopleDetector(
        yolo_model=yolo_model,
        device=device,
        conf=float(yolo_conf),
        iou=float(yolo_iou),
        imgsz=(int(os.getenv("FIGHT3D_YOLO_IMGSZ", "0") or 0) or None),
    )

    # Performance knobs (useful on CPU with multiple cameras).
    # - FIGHT3D_YOLO_EVERY_N: run YOLO every N frames (reuse previous boxes between runs)
    # - FIGHT3D_YOLO_MAX_W: if >0, downscale frame to this width for YOLO (boxes are scaled back)
    try:
        yolo_every_n = int(os.getenv("FIGHT3D_YOLO_EVERY_N", "1") or 1)
    except Exception:
        yolo_every_n = 1
    if yolo_every_n < 1:
        yolo_every_n = 1
    try:
        yolo_max_w = int(os.getenv("FIGHT3D_YOLO_MAX_W", "0") or 0)
    except Exception:
        yolo_max_w = 0
    if yolo_max_w < 0:
        yolo_max_w = 0

    last_boxes: list[list[int]] = []
    last_scores: list[float] = []

    tfm = make_val_transform(resize_short=256, crop_size=224)

    src_str = (rtsp or "").strip()
    is_rtsp = src_str.lower().startswith("rtsp://")
    reconnect_enabled = os.getenv("FIGHT3D_RTSP_RECONNECT", "1").strip() not in {
        "0",
        "false",
        "False",
        "no",
        "NO",
    }
    reconnect_sleep_min = float(os.getenv("FIGHT3D_RTSP_RECONNECT_SLEEP_MIN", "1.0") or 1.0)
    reconnect_sleep_max = float(os.getenv("FIGHT3D_RTSP_RECONNECT_SLEEP_MAX", "10.0") or 10.0)

    cap: cv2.VideoCapture | None = None
    fps_in = 0.0
    w = 0
    h = 0

    save_is_dir = _is_dir_save_path(save)
    save_dir = Path(save) if save_is_dir else None
    if save_dir is not None:
        ensure_dir(save_dir)

    writer = None
    save_path = None
    if save and not save_is_dir:
        save_path = Path(save)
        ensure_dir(save_path.parent)
        fps_out = fps_in if fps_in > 1e-3 else 25.0
        if w <= 0 or h <= 0:
            writer = (save_path, fps_out)
        else:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(save_path), fourcc, float(fps_out), (w, h))

    fight_writer = None
    fight_save_path_final: Path | None = None
    fight_save_path_part: Path | None = None

    def _rec_finalize() -> None:
        nonlocal fight_writer, fight_save_path_final, fight_save_path_part
        if fight_writer is None:
            return
        try:
            fight_writer.release()
        finally:
            fight_writer = None
        if fight_save_path_part is not None and fight_save_path_final is not None:
            if fight_save_path_part.exists():
                try:
                    os.replace(str(fight_save_path_part), str(fight_save_path_final))
                    print(f"[REC] stop src={window_name} path={fight_save_path_final}", flush=True)
                except Exception as e:
                    print(
                        f"[REC] stop src={window_name} path={fight_save_path_final} err={e}",
                        flush=True,
                    )
            else:
                print(
                    f"[REC] stop src={window_name} path={fight_save_path_final} err=missing_temp_file temp={fight_save_path_part}",
                    flush=True,
                )
        fight_save_path_final = None
        fight_save_path_part = None

    buf: deque[np.ndarray] = deque(maxlen=int(clip_len))
    frame_idx = 0
    state = "IDLE"
    score: float | None = None
    last_event_fight = False

    # Optional Events API reporting (writes fight events to PostgreSQL via Events API).
    # Enabled by setting env var FIGHT3D_EVENTS_API, e.g. http://api:8000
    events_api = os.getenv("FIGHT3D_EVENTS_API", "").strip().rstrip("/")
    events_enabled = bool(events_api) and bool((camera_external_id or "").strip())
    events_auto_create_camera = os.getenv("FIGHT3D_EVENTS_AUTO_CREATE_CAMERA", "1").strip() not in {
        "0",
        "false",
        "False",
        "no",
        "NO",
    }
    events_location_id = os.getenv("FIGHT3D_EVENTS_LOCATION_ID", "").strip() or None

    fight_opened_at: datetime | None = None
    fight_dedup_key: str | None = None
    fight_peak: float = 0.0
    fight_sum: float = 0.0
    fight_cnt: int = 0

    def _post_fight_event(
        *,
        started_at: datetime,
        ended_at: datetime | None,
        peak: float,
        mean: float,
        status: str,
        participants: int | None = None,
    ):
        if not events_enabled:
            return
        cam_ext = str(camera_external_id or "").strip()
        if not cam_ext:
            return

        meta: dict[str, object] = {
            "src": window_name,
            "people_min": int(people_min),
            "fight_threshold": float(fight_threshold),
            "device": device_str,
        }
        if participants is not None:
            meta["participants"] = int(participants)

        payload: dict[str, object] = {
            "events": [
                {
                    "camera_external_id": cam_ext,
                    "started_at": started_at.isoformat().replace("+00:00", "Z"),
                    "ended_at": ended_at.isoformat().replace("+00:00", "Z") if ended_at is not None else None,
                    "peak_score": float(peak),
                    "mean_score": float(mean),
                    "status": status,
                    "tags": ["infer"],
                    "meta": meta,
                    "dedup_key": fight_dedup_key,
                }
            ],
            "auto_create_camera": bool(events_auto_create_camera),
        }
        if events_location_id is not None:
            payload["location_id"] = events_location_id

        url = f"{events_api}/api/fight-events/batch"
        try:
            req = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5) as resp:
                _ = resp.read()
        except URLError as e:
            print(f"[events_api] failed url={url} err={e}")

    paused = False
    last_vis = None
    t0 = perf_counter()
    fps_smooth = None

    def _close_open_fight_segment(reason: str) -> None:
        nonlocal fight_opened_at, fight_dedup_key, fight_peak, fight_sum, fight_cnt
        if not events_enabled:
            return
        if fight_opened_at is None:
            return
        ended_at = datetime.now(timezone.utc)
        try:
            _post_fight_event(
                started_at=fight_opened_at,
                ended_at=ended_at,
                peak=fight_peak,
                mean=fight_sum / max(1, fight_cnt),
                status="closed",
            )
        finally:
            fight_opened_at = None
            fight_dedup_key = None
            fight_peak = 0.0
            fight_sum = 0.0
            fight_cnt = 0
        print(f"[events_api] closed open segment src={window_name} reason={reason}", flush=True)

    connect_attempt = 0
    should_exit = False
    while True:
        # (Re)connect to source.
        cap = _open_source(rtsp)
        if not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            cap = None

            if not is_rtsp or not reconnect_enabled:
                raise RuntimeError("Failed to open RTSP/file source")

            connect_attempt += 1
            sleep_s = min(reconnect_sleep_max, reconnect_sleep_min * (2.0 ** min(connect_attempt - 1, 5)))
            print(
                f"[RTSP] open failed src={window_name} url={_redact_rtsp(rtsp)} attempt={connect_attempt} sleep={sleep_s:.1f}s",
                flush=True,
            )
            time.sleep(max(0.1, sleep_s))
            continue

        fps_in = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        print(f"[OPEN] src={window_name} w={w} h={h} fps={fps_in:.2f}", flush=True)
        connect_attempt = 0

        # On reconnect, reset timing / buffers.
        buf.clear()
        frame_idx = 0
        t0 = perf_counter()
        fps_smooth = None

        while True:
            if paused:
                if show == 1:
                    if last_vis is not None:
                        cv2.imshow(window_name, last_vis)
                    key = cv2.waitKey(30) & 0xFF
                else:
                    time.sleep(0.03)
                    key = 0
                if key == ord("q"):
                    should_exit = True
                    break
                if key == ord("p"):
                    paused = False
                continue

            ok, frame = cap.read() if cap is not None else (False, None)
            if not ok or frame is None:
                if not is_rtsp or not reconnect_enabled:
                    should_exit = True
                else:
                    print(f"[RTSP] read failed src={window_name} reconnecting=1", flush=True)
                break

            frame_idx += 1
            buf.append(frame)

            # People detection (YOLO) is typically the main bottleneck.
            if yolo_every_n == 1 or (frame_idx % yolo_every_n == 0) or not last_boxes:
                det_frame = frame
                scale = 1.0
                if yolo_max_w > 0:
                    h0, w0 = det_frame.shape[:2]
                    if w0 > yolo_max_w and w0 > 0:
                        scale = float(yolo_max_w) / float(w0)
                        new_h = max(1, int(round(h0 * scale)))
                        det_frame = cv2.resize(det_frame, (int(yolo_max_w), int(new_h)))
                boxes, scores = people.detect(det_frame)
                if scale != 1.0 and boxes:
                    inv = 1.0 / scale
                    boxes = [[int(round(b[0] * inv)), int(round(b[1] * inv)), int(round(b[2] * inv)), int(round(b[3] * inv))] for b in boxes]
                last_boxes, last_scores = boxes, scores
            boxes, _scores = last_boxes, last_scores
            people_count = len(boxes)

            if fps_in > 1e-3:
                ts = frame_idx / fps_in
            else:
                ts = perf_counter() - t0

            if people_count < int(people_min):
                state = "IDLE"
                score = None
                last_event_fight = False
            else:
                if len(buf) == int(clip_len) and (frame_idx % int(stride) == 0):
                    x = _preprocess_clip(list(buf), tfm=tfm).to(torch_device)
                    score = _fight_score(model, x)
                    state = "FIGHT" if score >= float(fight_threshold) else "IDLE"

                    if state == "FIGHT" and not last_event_fight:
                        print(
                            f"[FIGHT] src={window_name} t={ts:.2f}s score={score:.3f} people={people_count}",
                            flush=True,
                        )
                        last_event_fight = True
                    if state != "FIGHT":
                        last_event_fight = False

            # Send events on state transitions.
            if events_enabled:
                now = datetime.now(timezone.utc)
                if state == "FIGHT":
                    if fight_opened_at is None and score is not None:
                        fight_opened_at = now
                        fight_dedup_key = f"{camera_external_id}:{fight_opened_at.isoformat()}"
                        fight_peak = float(score)
                        fight_sum = float(score)
                        fight_cnt = 1
                        _post_fight_event(
                            started_at=fight_opened_at,
                            ended_at=None,
                            peak=fight_peak,
                            mean=fight_sum / max(1, fight_cnt),
                            status="open",
                            participants=int(people_count),
                        )
                    elif fight_opened_at is not None and score is not None:
                        fight_peak = max(float(score), fight_peak)
                        fight_sum += float(score)
                        fight_cnt += 1
                else:
                    if fight_opened_at is not None:
                        # close the segment by upserting with the same dedup_key
                        ended_at = now
                        _post_fight_event(
                            started_at=fight_opened_at,
                            ended_at=ended_at,
                            peak=fight_peak,
                            mean=fight_sum / max(1, fight_cnt),
                            status="closed",
                        )
                        fight_opened_at = None
                        fight_dedup_key = None
                        fight_peak = 0.0
                        fight_sum = 0.0
                        fight_cnt = 0

            vis = frame

            # Record video segments on fight start/end when save is a directory.
            if save_dir is not None:
                if state == "FIGHT":
                    if fight_writer is None:
                        # Use sub-second precision to avoid collisions when state toggles quickly.
                        ts_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
                        cam = (camera_external_id or window_name or "cam").strip() or "cam"
                        fight_save_path_final = save_dir / f"{cam}-{ts_name}.mp4"
                        # IMPORTANT: keep a real .mp4 extension so OpenCV can select the MP4 muxer.
                        fight_save_path_part = save_dir / f"{cam}-{ts_name}.part.mp4"
                        try:
                            if fight_save_path_part.exists():
                                fight_save_path_part.unlink()
                        except Exception:
                            pass

                        fps_out = fps_in if fps_in > 1e-3 else 25.0
                        hh, ww = vis.shape[:2]
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        fight_writer = cv2.VideoWriter(str(fight_save_path_part), fourcc, float(fps_out), (ww, hh))
                        if not fight_writer.isOpened():
                            print(
                                f"[REC] start failed src={window_name} path={fight_save_path_final} temp={fight_save_path_part}",
                                flush=True,
                            )
                            try:
                                fight_writer.release()
                            except Exception:
                                pass
                            fight_writer = None
                            fight_save_path_final = None
                            fight_save_path_part = None
                        else:
                            print(
                                f"[REC] start src={window_name} path={fight_save_path_final}",
                                flush=True,
                            )
                    if fight_writer is not None:
                        fight_writer.write(vis)
                else:
                    _rec_finalize()

            if debug_every_sec > 0:
                t_dbg = perf_counter()
                if (t_dbg - last_debug_t) >= debug_every_sec:
                    last_debug_t = t_dbg
                    s_txt = "-" if score is None else f"{score:.3f}"
                    fps_dbg = frame_idx / max(1e-6, (t_dbg - t0))
                    print(
                        f"[STAT] src={window_name} fps={fps_dbg:.1f} state={state} people={people_count} score={s_txt}",
                        flush=True,
                    )

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
                vis = draw_boxes(vis, boxes, state="IDLE", score=None)

            t_now = perf_counter()
            inst_fps = frame_idx / max(1e-6, (t_now - t0))
            fps_smooth = inst_fps if fps_smooth is None else (0.9 * fps_smooth + 0.1 * inst_fps)
            score_txt = "-" if score is None else f"{score:.3f}"
            status = f"fps={fps_smooth:.1f}  state={state}  fight_score={score_txt}  people={people_count}"
            if paused:
                status += "  PAUSED"
            vis = put_status_line(vis, status)
            last_vis = vis

            if isinstance(writer, tuple):
                save_path, fps_out = writer
                hh, ww = vis.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(save_path), fourcc, float(fps_out), (ww, hh))

            if writer is not None and not isinstance(writer, tuple):
                writer.write(vis)

            if show == 1:
                cv2.imshow(window_name, vis)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    should_exit = True
                    break
                if key == ord("p"):
                    paused = True

        # Leaving inner loop: either exiting or reconnecting.
        try:
            if cap is not None:
                cap.release()
        finally:
            cap = None

        # Finalize recording and close any open segment on disconnect.
        _rec_finalize()
        _close_open_fight_segment("disconnect")

        if should_exit:
            break

        # Short backoff before reconnect.
        time.sleep(1.0)

    if writer is not None and not isinstance(writer, tuple):
        writer.release()
    _rec_finalize()
    _close_open_fight_segment("shutdown")
    if show == 1:
        cv2.destroyWindow(window_name)

    if save and not save_is_dir:
        print(f"Saved: {save} (codec=mp4v)")
