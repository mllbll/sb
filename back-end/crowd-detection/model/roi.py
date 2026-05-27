import logging
import config


def clamp_roi(roi: list[int], w: int, h: int) -> list[int]:
    x1, y1, x2, y2 = map(int, roi)
    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h - 1))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    if x2 == x1:
        x2 = min(w - 1, x1 + 1)
    if y2 == y1:
        y2 = min(h - 1, y1 + 1)
    return [x1, y1, x2, y2]


def roi_from_env_frac(w: int, h: int) -> list[int] | None:
    if any(v is None for v in (config.ROI_X1_FRAC, config.ROI_Y1_FRAC,
                                config.ROI_X2_FRAC, config.ROI_Y2_FRAC)):
        return None
    return [
        int(config.ROI_X1_FRAC * w), int(config.ROI_Y1_FRAC * h),
        int(config.ROI_X2_FRAC * w), int(config.ROI_Y2_FRAC * h),
    ]


def maybe_scale_legacy_roi(roi: list[int], w: int, h: int) -> tuple[list[int], bool]:
    x1, y1, x2, y2 = roi
    if 0 <= x1 <= w and 0 <= x2 <= w and 0 <= y1 <= h and 0 <= y2 <= h:
        return roi, False

    sx = w / float(config.ROI_BASE_W)
    sy = h / float(config.ROI_BASE_H)
    scaled = [int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)]
    return scaled, True


def resolve_roi(w: int, h: int, legacy_roi: list[int]) -> list[int]:
    # Приоритет 1: дробный ROI из secrets.json (roi_frac)
    frac = roi_from_env_frac(w, h)
    if frac is not None:
        return clamp_roi(frac, w, h)

    # Приоритет 2: пиксельный ROI, масштабируется если нужно
    roi, scaled = maybe_scale_legacy_roi(legacy_roi, w, h)
    if scaled:
        logging.info(
            "ROI scaled to current frame: legacy=%s base=%sx%s frame=%sx%s -> %s",
            legacy_roi, config.ROI_BASE_W, config.ROI_BASE_H, w, h, roi,
        )
    return clamp_roi(roi, w, h)
