import os
import cv2
import pytz

from datetime import datetime

import config


def draw_text_with_cv2(image, text: str, position, *, scale: float = 0.9,
                       color=(0, 255, 0), thickness: int = 2):
    x, y = int(position[0]), max(0, int(position[1]))
    cv2.putText(image, str(text), (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                float(scale), color, int(thickness), lineType=cv2.LINE_AA)
    return image


def get_last_saved_frame(output_dir: str, camera_id: str) -> int:
    try:
        files = os.listdir(output_dir)
    except FileNotFoundError:
        return 0
    prefix = f"{camera_id}_frame_"
    nums = []
    for f in files:
        if f.startswith(prefix) and f.endswith(".jpg"):
            try:
                nums.append(int(f.split("_")[-1].split(".")[0]))
            except Exception:
                pass
    return max(nums) if nums else 0


def store_frame_info(frame_id, camera_id, people_count, crowd_count, filename):
    moscow_tz = pytz.timezone("Europe/Moscow")
    current_time = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "frame_id": frame_id,
        "camera_id": camera_id,
        "people_count": people_count,
        "crowd_count": crowd_count,
        "filename": filename,
        "current_time": current_time,
    }


def _box_center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _box_iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter
    return (inter / denom) if denom > 0 else 0.0


def is_overlapping(box1, box2, *, iou_threshold: float | None = None,
                   center_dist_threshold_px: float | None = None) -> bool:
    if iou_threshold is None:
        iou_threshold = config.CROWD_IOU_THRESHOLD

    if _box_iou(box1, box2) > iou_threshold:
        return True

    c1x, c1y = _box_center(box1)
    c2x, c2y = _box_center(box2)
    dist2 = (c1x - c2x) ** 2 + (c1y - c2y) ** 2

    if config.CROWD_OVERLAP_MODE == "fixed":
        thr = center_dist_threshold_px if center_dist_threshold_px is not None else config.CROWD_CENTER_DIST_PX
        return dist2 <= thr * thr

    # adaptive (default): порог = CROWD_ADAPTIVE_DIST_MULT * диагональ большего бокса
    def _diag(b):
        w = max(1.0, float(b[2] - b[0]))
        h = max(1.0, float(b[3] - b[1]))
        return (w * w + h * h) ** 0.5

    thr = config.CROWD_ADAPTIVE_DIST_MULT * max(_diag(box1), _diag(box2))
    return dist2 <= thr * thr


def find_crowd(bboxes, *, min_people: int | None = None,
               iou_threshold: float | None = None,
               center_dist_threshold_px: float | None = None) -> list:
    if min_people is None:
        min_people = config.CROWD_MIN_PEOPLE

    visited = [False] * len(bboxes)
    crowds = []
    component_sizes = []

    for i in range(len(bboxes)):
        if visited[i]:
            continue
        current_crowd = []
        stack = [i]
        in_stack = {i}

        while stack:
            j = stack.pop()
            if visited[j]:
                continue
            visited[j] = True
            current_crowd.append(bboxes[j])
            for k in range(len(bboxes)):
                if visited[k] or k in in_stack:
                    continue
                if is_overlapping(bboxes[j], bboxes[k],
                                  iou_threshold=iou_threshold,
                                  center_dist_threshold_px=center_dist_threshold_px):
                    stack.append(k)
                    in_stack.add(k)

        component_sizes.append(len(current_crowd))
        if len(current_crowd) >= min_people:
            crowds.append(current_crowd)

    if config.CROWD_DEBUG_COMPONENTS:
        print(f"[crowd-debug] components={sorted(component_sizes, reverse=True)} "
              f"min_people={min_people} mode={config.CROWD_OVERLAP_MODE}")

    return crowds


def filter_bboxes_by_roi(bboxes, roi) -> list:
    x1_roi, y1_roi, x2_roi, y2_roi = roi
    mode = config.CROWD_ROI_MODE
    out = []

    for (x1, y1, x2, y2) in bboxes:
        if mode == "inside":
            if x1 >= x1_roi and y1 >= y1_roi and x2 <= x2_roi and y2 <= y2_roi:
                out.append((x1, y1, x2, y2))
        elif mode == "intersect":
            if min(x2, x2_roi) > max(x1, x1_roi) and min(y2, y2_roi) > max(y1, y1_roi):
                out.append((x1, y1, x2, y2))
        else:  # center (default)
            cx, cy = _box_center((x1, y1, x2, y2))
            if x1_roi <= cx <= x2_roi and y1_roi <= cy <= y2_roi:
                out.append((x1, y1, x2, y2))

    return out


def suggest_center_dist_threshold_px(*, frame_shape=None, roi=None,
                                     fraction: float | None = None) -> float:
    if fraction is None:
        fraction = config.CROWD_CENTER_DIST_FRACTION

    if roi is not None and len(roi) == 4:
        x1, y1, x2, y2 = roi
        w, h = max(1, x2 - x1), max(1, y2 - y1)
    elif frame_shape is not None:
        h, w = int(frame_shape[0]), int(frame_shape[1])
    else:
        return config.CROWD_CENTER_DIST_PX

    diag = (w * w + h * h) ** 0.5
    return float(max(60.0, min(diag * fraction, 400.0)))
