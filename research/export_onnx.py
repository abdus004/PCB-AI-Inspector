"""Export models/best.pt to models/best.onnx for the lightweight (PyTorch-free) backend.

Run from the repository root, in a SEPARATE environment that has the training stack:

    pip install ultralytics onnx onnxslim onnxruntime
    python research/export_onnx.py                  # export only
    python research/export_onnx.py --verify DIR     # export, then compare ONNX vs PyTorch on DIR/*.jpg|png

models/best.pt is only read, never modified. The ONNX file uses dynamic input shapes so
that non-square images are letterboxed exactly like Ultralytics' PyTorch predict().
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path.cwd()
PT = ROOT / "models" / "best.pt"
ONNX = ROOT / "models" / "best.onnx"
CONF, IOU = 0.25, 0.5          # same as the backend (confidence threshold, NMS IoU)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export() -> None:
    from ultralytics import YOLO
    if not PT.is_file():
        sys.exit(f"Not found: {PT}  (run from the repository root)")
    before = sha256(PT)
    out = YOLO(str(PT)).export(format="onnx", imgsz=640, dynamic=True, simplify=True, half=False, nms=False)
    assert Path(out).resolve() == ONNX.resolve(), out
    assert sha256(PT) == before, "best.pt changed - this should never happen"
    print(f"best.pt   sha256 {before}  (unchanged)")
    print(f"best.onnx sha256 {sha256(ONNX)}  ({ONNX.stat().st_size / 1e6:.1f} MB)")


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9)


def verify(folder: str) -> None:
    from ultralytics import YOLO
    os.environ["PCB_MODEL_PATH"] = str(ONNX)
    sys.path.insert(0, str(ROOT / "backend"))
    from services import model as onnx_model          # the real runtime code, not a copy
    pt = YOLO(str(PT))
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not files:
        sys.exit(f"No images found in {folder}")
    n_pt = n_onnx = matched = 0
    max_dconf, min_iou, diff_images = 0.0, 1.0, 0
    for f in files:
        img = Image.open(f).convert("RGB")
        a = [(int(b.cls[0]), float(b.conf[0]), b.xyxy[0].tolist())
             for b in pt.predict(source=img, imgsz=640, conf=CONF, iou=IOU, verbose=False)[0].boxes]
        b_ = [(int(b.cls[0]), float(b.conf[0]), b.xyxy[0].tolist()) for b in onnx_model.run_inference(img, CONF).boxes]
        used, m = set(), 0
        for c, s, box in a:
            best = max(((_iou(box, box2), j) for j, (c2, s2, box2) in enumerate(b_) if j not in used and c2 == c), default=None)
            if best and best[0] > 0.5:
                used.add(best[1]); m += 1
                max_dconf = max(max_dconf, abs(s - b_[best[1]][1])); min_iou = min(min_iou, best[0])
        n_pt += len(a); n_onnx += len(b_); matched += m
        diff_images += (len(a) != len(b_)) or (m != len(a))
    print(f"images={len(files)}  PyTorch detections={n_pt}  ONNX detections={n_onnx}  matched={matched}")
    print(f"images with any difference={diff_images}  max |conf diff|={max_dconf:.5f}  min matched IoU={min_iou:.4f}")
    ok = n_pt == n_onnx == matched and max_dconf < 1e-3 and min_iou > 0.95
    print("VERIFY:", "PASS - ONNX matches PyTorch" if ok else "FAIL - investigate before deploying")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", metavar="DIR", help="folder of test images to compare ONNX vs PyTorch")
    args = ap.parse_args()
    export()
    if args.verify:
        verify(args.verify)
