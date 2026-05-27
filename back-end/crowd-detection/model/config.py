import json
import logging
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
secrets_path = os.path.join(current_dir, "..", "keys", "secrets.json")

with open(secrets_path, "r") as _f:
    _s: dict = json.load(_f)

SOURCES: list[dict] = _s["sources"]

DB_HOST:     str = _s["DB_HOST"]
DB_NAME:     str = _s["DB_NAME"]
DB_USER:     str = _s["DB_USER"]
DB_PASSWORD: str = _s["DB_PASSWORD"]
DB_PORT:     int = int(_s.get("PORT", 5432))

# INFERENCE_ENABLED можно переопределить через ENV в docker-compose
_env_inf = os.getenv("INFERENCE_ENABLED")
if _env_inf is not None:
    INFERENCE_ENABLED: bool = _env_inf.strip() not in ("0", "false", "no")
else:
    INFERENCE_ENABLED = bool(_s.get("inference_enabled", True))

MODEL_PATH:      str   = _s.get("model_path",   "models_yolo/yolo11x.pt")
YOLO_CONF:       float = float(_s.get("yolo_conf", 0.35))
PEOPLE_CLASS_ID: int   = 0

CROWD_MIN_PEOPLE:           int   = int(_s.get("crowd_min_people",           5))
CROWD_IOU_THRESHOLD:        float = float(_s.get("crowd_iou_threshold",      0.0))
CROWD_OVERLAP_MODE:         str   = _s.get("crowd_overlap_mode",             "adaptive")
CROWD_ADAPTIVE_DIST_MULT:   float = float(_s.get("crowd_adaptive_dist_mult", 1.2))
CROWD_CENTER_DIST_PX:       float = float(_s.get("crowd_center_dist_px",     160))
CROWD_CENTER_DIST_FRACTION: float = float(_s.get("crowd_center_dist_fraction", 0.06))
CROWD_ROI_MODE:             str   = _s.get("crowd_roi_mode",                 "center")
CROWD_DEBUG_COMPONENTS:     bool  = str(_s.get("crowd_debug_components",     "0")) == "1"

CROWD_TIMEOUT_SEC:            float = float(_s.get("crowd_timeout_sec",            2))
WRITE_INTERVAL_SEC:           float = float(_s.get("write_interval_sec",           30))
PREVIEW_INTERVAL_SEC:         float = float(_s.get("preview_interval_sec",         2))
RECONNECT_SLEEP_SEC:          float = float(_s.get("reconnect_sleep_sec",          2))
READ_FAIL_MAX:                int   = int(_s.get("read_fail_max",                  30))
CROWD_NO_CROWD_LOG_EVERY_SEC: float = float(_s.get("crowd_no_crowd_log_every_sec", 5))

ROI_BOX:           list[int] = _s.get("roi_box",          [450, 100, 1500, 1000])
ROI_BASE_W:        int       = int(_s.get("roi_base_w",   1920))
ROI_BASE_H:        int       = int(_s.get("roi_base_h",   1080))
ROI_LOG_EVERY_SEC: float     = float(_s.get("roi_log_every_sec", 10))

# Дробный ROI (опционально, приоритет над roi_box)
_roi_frac = _s.get("roi_frac")
ROI_X1_FRAC: float | None = float(_roi_frac["x1"]) if _roi_frac else None
ROI_Y1_FRAC: float | None = float(_roi_frac["y1"]) if _roi_frac else None
ROI_X2_FRAC: float | None = float(_roi_frac["x2"]) if _roi_frac else None
ROI_Y2_FRAC: float | None = float(_roi_frac["y2"]) if _roi_frac else None

OUTPUT_DIR: str  = _s.get("output_dir", "images")
SHOW:       bool = str(_s.get("show", "0")) not in ("0", "false", "no")
LOG_LEVEL:  str  = _s.get("log_level", "INFO").upper()

logging.info(
    "Config loaded | inference=%s model=%s min_people=%s roi_mode=%s overlap=%s",
    INFERENCE_ENABLED, MODEL_PATH, CROWD_MIN_PEOPLE, CROWD_ROI_MODE, CROWD_OVERLAP_MODE,
)
