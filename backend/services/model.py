"""Loads the YOLO11n ONNX model once and runs inference with ONNX Runtime.

Drop-in replacement for the Ultralytics/PyTorch version. It exposes the same
functions (load_model, is_loaded, class_names, run_inference) and returns an
object with the small part of the Ultralytics ``Results`` API that the rest of
the backend uses: ``.boxes`` (each with ``conf``, ``cls``, ``xyxy``), ``.names``
and ``.plot()``. PyTorch and Ultralytics are NOT needed at runtime.
"""
import ast
import os
import threading
from dataclasses import dataclass

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageFont

try:  # exact Ultralytics resize (cv2.INTER_LINEAR); falls back to Pillow if OpenCV is absent
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

import config

_session: "ort.InferenceSession | None" = None
_names: dict = {}
_input_name = ""
_lock = threading.Lock()

_IMGSZ = config.IMAGE_SIZE          # longest side is resized to 640 (the ONNX file is exported with dynamic shapes)
_STRIDE = 32                     # YOLO11 stride
_PAD_VALUE = 114                    # Ultralytics letterbox padding colour
# NMS IoU: current Ultralytics predict() defaults to 0.5 (older releases used 0.7).
# Pinned here so behaviour no longer depends on the installed Ultralytics version.
_IOU_THRESHOLD = float(os.environ.get("PCB_NMS_IOU", "0.5"))
_MAX_DET = 300                      # Ultralytics predict() default

_COLORS = [(230, 214, 79), (76, 176, 242), (120, 230, 129), (140, 112, 236), (255, 140, 160), (90, 226, 250)]


@dataclass
class _Box:
    conf: np.ndarray    # shape (1,)   -> box.conf[0]
    cls: np.ndarray     # shape (1,)   -> box.cls[0]
    xyxy: np.ndarray    # shape (1, 4) -> box.xyxy[0].tolist()


class _Result:
    def __init__(self, image: Image.Image, boxes: list, names: dict):
        self._image = image
        self.boxes = boxes
        self.names = names

    def plot(self) -> np.ndarray:
        """Boxes + labels drawn on the image; returns a BGR array (like Ultralytics)."""
        img = self._image.copy()
        draw = ImageDraw.Draw(img)
        width = max(2, round(min(img.size) / 300))
        font = ImageFont.load_default(size=max(12, round(min(img.size) / 40)))
        for b in self.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            k = int(b.cls[0])
            color = _COLORS[k % len(_COLORS)]
            draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
            label = f"{self.names.get(k, k)} {float(b.conf[0]):.2f}"
            tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), label, font=font)
            th = ty1 - ty0 + 4
            top = y1 - th if y1 - th >= 0 else y1
            draw.rectangle([x1, top, x1 + (tx1 - tx0) + 6, top + th], fill=color)
            draw.text((x1 + 3, top + 1), label, fill=(0, 0, 0), font=font)
        return np.asarray(img)[:, :, ::-1].copy()


def load_model():
    """Load the ONNX model (called once at startup)."""
    global _session, _names, _input_name
    if _session is None:
        if not config.MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Model file not found at: {config.MODEL_PATH}\n"
                "Place the exported model at <project root>/models/best.onnx "
                "or set PCB_MODEL_PATH."
            )
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = int(os.environ.get("PCB_ORT_THREADS", "1"))
        opts.inter_op_num_threads = 1
        opts.enable_cpu_mem_arena = False      # lower memory, slightly slower
        opts.enable_mem_pattern = False
        opts.log_severity_level = 3
        _session = ort.InferenceSession(str(config.MODEL_PATH), sess_options=opts,
                                        providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
        meta = _session.get_modelmeta().custom_metadata_map
        _names = {int(k): v for k, v in ast.literal_eval(meta["names"]).items()}
    return _session


def is_loaded() -> bool:
    return _session is not None


def class_names() -> dict:
    load_model()
    return _names


def _letterbox(image: Image.Image):
    """Resize keeping aspect ratio, then pad only to a multiple of 32 (rectangular inference).

    This is exactly what Ultralytics' PyTorch predict() does for a single image, so a
    dynamic-shape ONNX export reproduces its detections for square and non-square images.
    """
    w, h = image.size
    r = min(_IMGSZ / h, _IMGSZ / w)
    new_w, new_h = round(w * r), round(h * r)
    dw, dh = (_IMGSZ - new_w) % _STRIDE, (_IMGSZ - new_h) % _STRIDE
    dw, dh = dw / 2, dh / 2
    arr = np.asarray(image)
    if (new_w, new_h) != (w, h):
        if cv2 is not None:
            arr = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            arr = np.asarray(image.resize((new_w, new_h), Image.BILINEAR))
    top, bottom = round(dh - 0.1), round(dh + 0.1)
    left, right = round(dw - 0.1), round(dw + 0.1)
    canvas = np.full((new_h + top + bottom, new_w + left + right, 3), _PAD_VALUE, dtype=np.uint8)
    canvas[top:top + new_h, left:left + new_w] = arr
    x = canvas.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return np.ascontiguousarray(x), r, left, top


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list:
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0]); yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2]); yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_r = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (area_i + area_r - inter + 1e-9)
        order = rest[iou <= iou_thr]
    return keep


def run_inference(image: Image.Image, conf: float):
    """Run YOLO once and return a Results-like object (same role as before)."""
    load_model()
    w, h = image.size
    x, r, left, top = _letterbox(image)
    with _lock:
        out = _session.run(None, {_input_name: x})[0]          # (1, 4 + nc, 8400)
    pred = out[0].T                                              # (8400, 4 + nc)
    scores_all = pred[:, 4:]
    conf_max = scores_all.max(1)
    keep = conf_max > conf
    pred, scores_all, conf_max = pred[keep], scores_all[keep], conf_max[keep]
    boxes = []
    if pred.shape[0]:
        cls = scores_all.argmax(1)
        cx, cy, bw, bh = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        xyxy = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 1)
        # class-aware NMS: offset boxes by class so different classes never suppress each other
        offset = cls[:, None].astype(np.float32) * 7680.0
        idx = _nms(xyxy + offset, conf_max, _IOU_THRESHOLD)[:_MAX_DET]
        xyxy = xyxy[idx]
        xyxy[:, [0, 2]] = np.clip((xyxy[:, [0, 2]] - left) / r, 0, w)
        xyxy[:, [1, 3]] = np.clip((xyxy[:, [1, 3]] - top) / r, 0, h)
        for k in range(len(idx)):
            boxes.append(_Box(conf=np.array([conf_max[idx[k]]]), cls=np.array([cls[idx[k]]]),
                              xyxy=xyxy[k:k + 1].astype(np.float32)))
    return _Result(image, boxes, _names)
