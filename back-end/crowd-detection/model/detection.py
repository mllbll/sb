import datetime as _dt
import logging
import os
import queue
import threading
import time

import cv2
from ultralytics import YOLO

import config
from roi import resolve_roi
from utils import (
    draw_text_with_cv2,
    filter_bboxes_by_roi,
    find_crowd,
    get_last_saved_frame,
    store_frame_info,
    suggest_center_dist_threshold_px,
)
from write_to_db import insert_into_db

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
    force=True,
)

os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|stimeout;5000000|max_delay;5000000",
)

logging.info("Inference enabled: %s", config.INFERENCE_ENABLED)

_model = None
_model_lock = threading.Lock()

if config.INFERENCE_ENABLED:
    logging.info("Loading YOLO model from '%s'…", config.MODEL_PATH)
    _model = YOLO(config.MODEL_PATH, verbose=False)
    logging.info("YOLO model loaded.")

os.makedirs(config.OUTPUT_DIR, exist_ok=True)


class CameraWorker:
    _TARGET_FPS   = 30
    _FRAME_PERIOD = 1.0 / _TARGET_FPS

    def __init__(self, camera_id: str, rtsp_url: str, model, model_lock: threading.Lock):
        self.camera_id  = camera_id
        self.rtsp_url   = rtsp_url
        self._model      = model
        self._model_lock = model_lock
        self._log        = logging.getLogger(camera_id)

        self._frame_q: queue.Queue = queue.Queue(maxsize=1)
        self._db_q:    queue.Queue = queue.Queue(maxsize=64)

        self._inf_lock             = threading.Lock()
        self._cached_people_count  = 0
        self._cached_crowds: list  = []
        self._cached_crowd_boxes: list = []

        self._frame_count      = get_last_saved_frame(config.OUTPUT_DIR, camera_id) + 1
        self._frame_count_lock = threading.Lock()

        self._stop = threading.Event()
        self._main_thread: threading.Thread | None = None

    def start(self) -> None:
        threading.Thread(
            target=self._reader_thread,
            daemon=True, name=f"reader-{self.camera_id}",
        ).start()

        if config.INFERENCE_ENABLED:
            threading.Thread(
                target=self._inference_thread,
                daemon=True, name=f"inf-{self.camera_id}",
            ).start()

        threading.Thread(
            target=self._db_writer_thread,
            daemon=True, name=f"db-{self.camera_id}",
        ).start()

        self._main_thread = threading.Thread(
            target=self._main_loop,
            daemon=True, name=f"main-{self.camera_id}",
        )
        self._main_thread.start()

    def join(self) -> None:
        if self._main_thread:
            self._main_thread.join()

    def _open_capture(self) -> cv2.VideoCapture:
        self._log.info("Connecting to camera at: %s", self.rtsp_url)
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _reader_thread(self) -> None:
        cap = self._open_capture()
        fail_streak = 0

        while not self._stop.is_set():
            ret, frame = cap.read()

            if (not ret) or (frame is None):
                fail_streak += 1
                self._log.warning("Read fail streak=%d", fail_streak)
                time.sleep(0.2)
                if fail_streak >= config.READ_FAIL_MAX:
                    self._log.warning("Reconnecting in %.1fs…", config.RECONNECT_SLEEP_SEC)
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(config.RECONNECT_SLEEP_SEC)
                    cap = self._open_capture()
                    fail_streak = 0
                continue

            fail_streak = 0
            try:
                self._frame_q.get_nowait()
            except queue.Empty:
                pass
            self._frame_q.put(frame)

        try:
            cap.release()
        except Exception:
            pass

    def _inference_thread(self) -> None:
        last_log_ts   = 0.0
        process_every = max(1, getattr(config, "PROCESS_EVERY_N", 1))
        frame_idx     = 0

        while not self._stop.is_set():
            try:
                frame = self._frame_q.get(timeout=1.0)
            except queue.Empty:
                continue

            frame_idx += 1
            if frame_idx % process_every != 0:
                continue

            h, w       = frame.shape[:2]
            effective_roi = resolve_roi(w, h, config.ROI_BOX)

            bboxes = []
            if self._model is not None:
                with self._model_lock:
                    results = self._model(
                        frame, stream=True,
                        conf=config.YOLO_CONF, verbose=False,
                    )
                    for result in results:
                        for bbox, label in zip(result.boxes.xyxy, result.boxes.cls):
                            if int(label) == config.PEOPLE_CLASS_ID:
                                bboxes.append(tuple(map(int, bbox)))

            filtered_bboxes = filter_bboxes_by_roi(bboxes, effective_roi)
            people_count    = len(filtered_bboxes)

            center_dist_px = suggest_center_dist_threshold_px(
                frame_shape=frame.shape, roi=effective_roi,
            )
            crowds = find_crowd(
                filtered_bboxes,
                min_people=config.CROWD_MIN_PEOPLE,
                iou_threshold=config.CROWD_IOU_THRESHOLD,
                center_dist_threshold_px=center_dist_px,
            )
            crowd_boxes = [
                (min(b[0] for b in c), min(b[1] for b in c),
                 max(b[2] for b in c), max(b[3] for b in c))
                for c in crowds
            ]

            now_ts = time.time()
            if now_ts - last_log_ts >= config.CROWD_NO_CROWD_LOG_EVERY_SEC:
                self._log.info(
                    "people_in_roi=%s crowds=%s center_dist_px=%.1f",
                    people_count, len(crowds), center_dist_px,
                )
                last_log_ts = now_ts

            with self._inf_lock:
                self._cached_people_count = people_count
                self._cached_crowds       = crowds
                self._cached_crowd_boxes  = crowd_boxes

    def _db_writer_thread(self) -> None:
        while not self._stop.is_set():
            try:
                task = self._db_q.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                insert_into_db(
                    camera_id=task["camera_id"],
                    people_count=task["people_count"],
                    crowd_count=task["crowd_count"],
                    current_time=task["current_time"],
                    filename=task["filename"],
                )
            except Exception as exc:
                self._log.error("DB writer error: %s", exc)

    def _queue_db_write(self, people_count: int, crowd_count: int, filename: str | None) -> None:
        frame_info = store_frame_info(0, self.camera_id, people_count, crowd_count, filename)
        task = {
            "camera_id":    self.camera_id,
            "people_count": people_count,
            "crowd_count":  crowd_count,
            "current_time": frame_info["current_time"],
            "filename":     filename,
        }
        try:
            self._db_q.put_nowait(task)
        except queue.Full:
            self._log.warning("DB queue full, dropping write task")

    def _main_loop(self) -> None:
        if config.SHOW:
            cv2.namedWindow(self.camera_id, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.camera_id, 1280, 720)

        last_crowd_time  = 0.0
        last_write_time  = 0.0
        last_roi_log_ts  = 0.0
        last_preview_ts  = 0.0
        display_frame    = None

        self._log.info("Waiting for first frame…")
        while not self._stop.is_set():
            try:
                first = self._frame_q.get(timeout=10.0)
                self._frame_q.put(first)
                break
            except queue.Empty:
                self._log.warning("No frame yet, retrying…")

        self._log.info("Entering main display loop.")

        while not self._stop.is_set():
            loop_start = time.time()

            try:
                display_frame = self._frame_q.get_nowait()
            except queue.Empty:
                pass

            if display_frame is None:
                elapsed = time.time() - loop_start
                sleep_t = self._FRAME_PERIOD - elapsed
                if sleep_t > 0:
                    time.sleep(sleep_t)
                if config.SHOW and cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            now_ts = time.time()
            h, w   = display_frame.shape[:2]
            effective_roi = resolve_roi(w, h, config.ROI_BOX)

            if now_ts - last_roi_log_ts >= config.ROI_LOG_EVERY_SEC:
                self._log.info("frame=%sx%s roi=%s", w, h, effective_roi)
                last_roi_log_ts = now_ts

            rx1, ry1, rx2, ry2 = effective_roi
            cv2.rectangle(display_frame, (rx1, ry1), (rx2, ry2), (255, 0, 0), 2)

            with self._inf_lock:
                snap_people = self._cached_people_count
                snap_crowds = list(self._cached_crowds)
                snap_boxes  = list(self._cached_crowd_boxes)

            if not config.INFERENCE_ENABLED:
                display_frame = draw_text_with_cv2(
                    display_frame, "Inference disabled", (10, 30),
                    scale=0.9, color=(0, 0, 255), thickness=2,
                )
            else:
                for i, (cx1, cy1, cx2, cy2) in enumerate(snap_boxes):
                    cv2.rectangle(display_frame, (cx1, cy1), (cx2, cy2), (0, 255, 0), 2)
                    display_frame = draw_text_with_cv2(
                        display_frame, f"Crowd {i + 1}", (cx1, max(0, cy1 - 10)),
                        scale=0.9, color=(0, 255, 0), thickness=2,
                    )

                ts_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                display_frame = draw_text_with_cv2(
                    display_frame, f"People: {snap_people}", (10, 30),
                    scale=0.9, color=(0, 255, 255), thickness=2,
                )
                display_frame = draw_text_with_cv2(
                    display_frame, f"Crowds: {len(snap_crowds)}", (10, 60),
                    scale=0.9, color=(0, 255, 255), thickness=2,
                )
                display_frame = draw_text_with_cv2(
                    display_frame, self.camera_id, (10, 90),
                    scale=0.7, color=(200, 200, 200), thickness=1,
                )
                display_frame = draw_text_with_cv2(
                    display_frame, ts_str, (10, 120),
                    scale=0.7, color=(200, 200, 200), thickness=1,
                )

            if now_ts - last_preview_ts >= config.PREVIEW_INTERVAL_SEC:
                preview_path = os.path.join(config.OUTPUT_DIR, f"{self.camera_id}_preview.jpg")
                cv2.imwrite(preview_path, display_frame)
                last_preview_ts = now_ts

            if config.INFERENCE_ENABLED and snap_crowds:
                if now_ts - last_crowd_time > config.CROWD_TIMEOUT_SEC:
                    with self._frame_count_lock:
                        fc = self._frame_count
                        self._frame_count += 1
                    frame_filename = os.path.join(
                        config.OUTPUT_DIR, f"{self.camera_id}_frame_{fc}.jpg"
                    )
                    cv2.imwrite(frame_filename, display_frame)
                    self._log.info("Frame saved: %s", frame_filename)
                    self._queue_db_write(snap_people, len(snap_crowds), frame_filename)
                    last_crowd_time = now_ts

            if now_ts - last_write_time >= config.WRITE_INTERVAL_SEC:
                self._queue_db_write(snap_people, len(snap_crowds), None)
                self._log.info(
                    "Periodic write queued: people=%s crowds=%s",
                    snap_people, len(snap_crowds),
                )
                last_write_time = now_ts

            if config.SHOW:
                cv2.imshow(self.camera_id, display_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self._log.info("Quit command received.")
                    break
            else:
                elapsed = time.time() - loop_start
                sleep_t = self._FRAME_PERIOD - elapsed
                if sleep_t > 0:
                    time.sleep(sleep_t)

        self._stop.set()
        if config.SHOW:
            cv2.destroyWindow(self.camera_id)
        self._log.info("Main loop exited.")


if not config.SOURCES:
    logging.error("No sources defined in secrets.json — exiting.")
    raise SystemExit(1)

workers: list[CameraWorker] = []
for src in config.SOURCES:
    w = CameraWorker(
        camera_id=src["id"],
        rtsp_url=src["rtsp_url"],
        model=_model,
        model_lock=_model_lock,
    )
    w.start()
    workers.append(w)

logging.info(
    "Started %d camera worker(s): %s",
    len(workers), [w.camera_id for w in workers],
)

try:
    for w in workers:
        w.join()
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt — stopping all workers.")
    for w in workers:
        w._stop.set()

logging.info("All workers finished. Exiting.")
