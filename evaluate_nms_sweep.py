"""
Separate NMS IoU Comparison Script.

Runs Ultralytics validation at NMS IoU thresholds: 0.45, 0.60, and 0.70.
Maintains default confidence settings (conf=0.25) so that NMS effects
are evaluated strictly independently of confidence threshold post-processing.
Results are saved to runs/detect/nms_eval/ without altering any weights.

Usage:
    python evaluate_nms_sweep.py
"""

import sys
from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = "models/best.pt"
DATA_CONFIG = "configs/pcb_final.yaml"
OUTPUT_DIR = "runs/detect/nms_eval"

NMS_THRESHOLDS = [0.45, 0.60, 0.70]


def main():
    print("=" * 70)
    print("NMS IoU THRESHOLD EVALUATION (conf=0.25, evaluating NMS 0.45 vs 0.60 vs 0.70)")
    print("=" * 70)

    model = YOLO(MODEL_PATH)
    results_summary = []

    for nms_iou in NMS_THRESHOLDS:
        run_name = f"nms_{int(nms_iou * 100):03d}"
        print(f"\nEvaluating NMS IoU = {nms_iou:.2f} -> {OUTPUT_DIR}/{run_name}")

        metrics = model.val(
            data=DATA_CONFIG,
            split="val",
            imgsz=640,
            conf=0.25,
            iou=nms_iou,
            project=OUTPUT_DIR,
            name=run_name,
            plots=False,
            verbose=False,
        )

        p = metrics.results_dict.get("metrics/precision(B)", 0.0)
        r = metrics.results_dict.get("metrics/recall(B)", 0.0)
        map50 = metrics.results_dict.get("metrics/mAP50(B)", 0.0)
        map50_95 = metrics.results_dict.get("metrics/mAP50-95(B)", 0.0)

        results_summary.append({
            "iou": nms_iou,
            "precision": p,
            "recall": r,
            "mAP50": map50,
            "mAP50-95": map50_95,
        })

    print("\n" + "=" * 70)
    print(f"{'NMS IoU':>10s}  {'Precision':>12s}  {'Recall':>10s}  {'mAP@50':>10s}  {'mAP@50-95':>12s}")
    print("-" * 70)
    for r in results_summary:
        print(f"{r['iou']:10.2f}  {r['precision']:12.4f}  {r['recall']:10.4f}  {r['mAP50']:10.4f}  {r['mAP50-95']:12.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
