"""Central configuration for the PCB-AI-Inspector backend.

Values can be overridden with environment variables or a `backend/.env` file
(see `.env.example`). Nothing here needs to change for normal local use.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = BACKEND_DIR.parent


def _load_dotenv() -> None:
    """Tiny .env reader so we do not need an extra dependency."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# ---- Model -----------------------------------------------------------------
# Your trained weights live at <project root>/models/best.pt
MODEL_PATH = Path(os.environ.get("PCB_MODEL_PATH", BASE_DIR / "models" / "best.pt"))
MODEL_NAME = "YOLO11n"
IMAGE_SIZE = 640          # same as the original /predict endpoint
CONF_THRESHOLD = 0.25     # detections at or above this are reported (same as before)
# Detections between WEAK_CONF_THRESHOLD and CONF_THRESHOLD are NOT reported as
# defects. They only make the conclusion "Inconclusive" when nothing else is found.
WEAK_CONF_THRESHOLD = 0.10
# Images whose shorter side is below this are too small to judge reliably.
MIN_RELIABLE_SIDE = 320

# Held-out test results supplied by the project owner (two PCB boards only).
EVALUATION = {
    "precision": 0.8000,
"recall": 0.9683,
"map50": 0.9404,
"map50_95": 0.4244,
    "test_set": "Held-out test set containing two PCB boards",
    "note": (
        "These are experimental results on a very small held-out test set. "
        "They are not a guarantee of real-world performance."
    ),
}

# ---- Uploads ---------------------------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # 10 MB
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}   # PIL format -> extension
MAX_IMAGE_PIXELS = 60_000_000                 # protects against decompression bombs

# ---- Storage ---------------------------------------------------------------
STORAGE_DIR = Path(os.environ.get("PCB_STORAGE_DIR", BACKEND_DIR / "storage"))
ORIGINALS_DIR = STORAGE_DIR / "originals"
ANNOTATED_DIR = STORAGE_DIR / "annotated"
REPORTS_DIR = STORAGE_DIR / "reports"
THUMBNAILS_DIR = STORAGE_DIR / "thumbnails"
DB_PATH = Path(os.environ.get("PCB_DB_PATH", BACKEND_DIR / "inspections.db"))

# ---- CORS ------------------------------------------------------------------
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if o.strip()
]
