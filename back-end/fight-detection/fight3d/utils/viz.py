from __future__ import annotations

import cv2
import numpy as np


DEFAULT_FIGHT_THRESHOLD = 0.7


def _clip_box(box: tuple[int, int, int, int], w: int, h: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    x1 = int(max(0, min(w - 1, x1)))
    x2 = int(max(0, min(w - 1, x2)))
    y1 = int(max(0, min(h - 1, y1)))
    y2 = int(max(0, min(h - 1, y2)))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return x1, y1, x2, y2


def _rounded_rect(
    img: np.ndarray,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    thickness: int = 3,
    radius: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    r = int(max(1, min(radius, w // 2, h // 2)))

    # straight edges
    cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness, cv2.LINE_AA)

    # rounded corners
    cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness, cv2.LINE_AA)
    cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness, cv2.LINE_AA)


def _text_plate(
    frame: np.ndarray,
    text: str,
    org: tuple[int, int],
    fg: tuple[int, int, int] = (255, 255, 255),
    bg: tuple[int, int, int] = (0, 0, 0),
    alpha: float = 0.45,
    font_scale: float = 0.7,
    thickness: int = 2,
    pad: int = 6,
) -> None:
    x, y = org
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    th_full = th + baseline
    x1 = x
    y1 = y - th_full - pad * 2
    x2 = x + tw + pad * 2
    y2 = y

    h, w = frame.shape[:2]
    x1 = max(0, min(w - 1, x1))
    x2 = max(0, min(w - 1, x2))
    y1 = max(0, min(h - 1, y1))
    y2 = max(0, min(h - 1, y2))

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), bg, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)
    cv2.putText(
        frame,
        text,
        (x + pad, y - pad - baseline),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        fg,
        thickness,
        cv2.LINE_AA,
    )


def draw_boxes(
    frame: np.ndarray,
    boxes: list[tuple[int, int, int, int]] | np.ndarray,
    color_by_state: bool = True,
    state: str = "IDLE",
    score: float | None = None,
) -> np.ndarray:
    """Draw CCTV-style boxes with rounded corners and text overlay.

    - state: "IDLE" | "FIGHT"
    - score: optional probability/score for fight.
    """
    if frame is None:
        return frame
    if boxes is None:
        return frame

    if isinstance(boxes, np.ndarray):
        boxes_list = [tuple(map(int, b.tolist())) for b in boxes.reshape(-1, 4)]
    else:
        boxes_list = [tuple(map(int, b)) for b in boxes]

    h, w = frame.shape[:2]
    state_up = (state or "IDLE").upper()

    if color_by_state:
        color = (0, 255, 0) if state_up == "IDLE" else (0, 0, 255)
    else:
        color = (255, 200, 0)

    thickness = 3
    for box in boxes_list:
        x1, y1, x2, y2 = _clip_box(box, w=w, h=h)
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        radius = max(8, min(20, min(bw, bh) // 8))
        _rounded_rect(frame, (x1, y1, x2, y2), color=color, thickness=thickness, radius=radius)

        if score is None:
            label = state_up
        else:
            label = f"{state_up} {score:.2f}"
        _text_plate(frame, label, org=(x1, y1), fg=(255, 255, 255), bg=(0, 0, 0), alpha=0.35)

    # strong fight alert over the biggest box
    thr = float(DEFAULT_FIGHT_THRESHOLD)
    if state_up == "FIGHT" and score is not None and score >= thr and len(boxes_list) > 0:
        def area(b: tuple[int, int, int, int]) -> int:
            x1, y1, x2, y2 = b
            return max(0, x2 - x1) * max(0, y2 - y1)

        biggest = max(boxes_list, key=area)
        x1, y1, x2, y2 = _clip_box(biggest, w=w, h=h)
        _text_plate(
            frame,
            "! Fight !",
            org=(x1, max(0, y1 - 2)),
            fg=(255, 255, 255),
            bg=(0, 0, 255),
            alpha=0.45,
            font_scale=0.9,
            thickness=2,
        )

    return frame


def put_status_line(frame: np.ndarray, text: str) -> np.ndarray:
    if frame is None:
        return frame
    h, w = frame.shape[:2]
    overlay = frame.copy()
    bar_h = max(28, int(h * 0.06))
    y1 = h - bar_h
    cv2.rectangle(overlay, (0, y1), (w - 1, h - 1), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, dst=frame)
    cv2.putText(
        frame,
        text,
        (12, int(y1 + bar_h * 0.7)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


def draw_label(frame_bgr: np.ndarray, text: str, org: tuple[int, int] = (10, 30)) -> np.ndarray:
    out = frame_bgr
    cv2.putText(
        out,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return out


def draw_box(frame_bgr: np.ndarray, box_xyxy: tuple[int, int, int, int], color=(255, 0, 0)) -> np.ndarray:
    x1, y1, x2, y2 = box_xyxy
    cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)
    return frame_bgr
