"""Loads the YOLO model once and runs inference."""
import threading

from ultralytics import YOLO

import config

_model = None
_lock = threading.Lock()   # the YOLO predictor is not thread-safe


def load_model():
    """Load models/best.pt (called once at startup)."""
    global _model
    if _model is None:
        if not config.MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Model weights not found at: {config.MODEL_PATH}\n"
                "Place your trained weights at <project root>/models/best.pt "
                "or set PCB_MODEL_PATH."
            )
        _model = YOLO(str(config.MODEL_PATH))
    return _model


def is_loaded() -> bool:
    return _model is not None


def class_names() -> dict:
    return load_model().names


def run_inference(image, conf: float):
    """Run YOLO once and return the first Results object."""
    model = load_model()
    with _lock:
        results = model.predict(
            source=image, imgsz=config.IMAGE_SIZE, conf=conf, verbose=False
        )
    return results[0]
