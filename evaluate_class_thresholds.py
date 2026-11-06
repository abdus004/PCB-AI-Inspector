"""
Reproducible Class-Specific Confidence Threshold Evaluation Script.

Evaluates existing predictions against ground-truth validation annotations.
Does NOT modify any backend code, datasets, or weights.
Keeps default confidence settings for standard mAP validation and applies
thresholds strictly for post-inference TP/FP/FN analysis.

Usage:
    python evaluate_class_thresholds.py
    python evaluate_class_thresholds.py --gt datasets/pcb-yolo-final/labels/val --pred runs/detect/runs/diagnostics/val_predictions/labels
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

CLASSES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

# Baseline uniform threshold
DEFAULT_THRESHOLDS = {c: 0.25 for c in CLASSES}

# Proposed class-specific thresholds based on validation empirical optimization
PROPOSED_THRESHOLDS = {
    0: 0.25,  # mouse_bite: preserve recall on small defect
    1: 0.45,  # spur: drastically cut false positives (-154 FPs)
    2: 0.25,  # missing_hole: already high precision (94.7%) & recall (99.8%)
    3: 0.30,  # short: moderate FP cut (-15 FPs) while protecting recall
    4: 0.25,  # open_circuit: smallest defect, preserve recall
    5: 0.40,  # spurious_copper: cut false positives (-145 FPs)
}


def read_gt_boxes(path: Path):
    """Read ground-truth boxes: list of (class_id, cx, cy, w, h)."""
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 5:
            try:
                boxes.append({
                    "class": int(float(parts[0])),
                    "box": tuple(map(float, parts[1:5])),
                })
            except ValueError:
                continue
    return boxes


def read_pred_boxes(path: Path):
    """Read predicted boxes: list of (class_id, cx, cy, w, h, conf)."""
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 6:
            try:
                boxes.append({
                    "class": int(float(parts[0])),
                    "box": tuple(map(float, parts[1:5])),
                    "confidence": float(parts[5]),
                })
            except ValueError:
                continue
    return boxes


def compute_iou(box_a, box_b):
    """Compute IoU between two (cx, cy, w, h) boxes."""
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    ax1, ay1 = ax - aw / 2.0, ay - ah / 2.0
    ax2, ay2 = ax + aw / 2.0, ay + ah / 2.0
    bx1, by1 = bx - bw / 2.0, by - bh / 2.0
    bx2, by2 = bx + bw / 2.0, by + bh / 2.0

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (aw * ah) + (bw * bh) - inter
    return inter / union if union > 0.0 else 0.0


def evaluate_with_thresholds(all_data, thresholds, iou_thresh=0.50):
    """Evaluate matching at specified per-class confidence thresholds."""
    stats = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
    detailed_errors = []

    for img_stem, gt_boxes, pred_boxes in all_data:
        # Filter predictions by class-specific threshold
        active_preds = [
            p for p in pred_boxes
            if p["confidence"] >= thresholds.get(p["class"], 0.25)
        ]
        # Match highest-confidence first
        active_preds.sort(key=lambda x: x["confidence"], reverse=True)
        matched_gt = set()

        for p in active_preds:
            best_iou = 0.0
            best_idx = None
            for idx, g in enumerate(gt_boxes):
                if idx in matched_gt or g["class"] != p["class"]:
                    continue
                score = compute_iou(p["box"], g["box"])
                if score > best_iou:
                    best_iou = score
                    best_idx = idx

            if best_idx is not None and best_iou >= iou_thresh:
                matched_gt.add(best_idx)
                stats[p["class"]]["TP"] += 1
            else:
                stats[p["class"]]["FP"] += 1
                detailed_errors.append({
                    "image": img_stem,
                    "error": "FALSE_POSITIVE",
                    "class": CLASSES.get(p["class"], str(p["class"])),
                    "confidence": round(p["confidence"], 4),
                    "iou": round(best_iou, 4),
                })

        for idx, g in enumerate(gt_boxes):
            if idx not in matched_gt:
                stats[g["class"]]["FN"] += 1
                detailed_errors.append({
                    "image": img_stem,
                    "error": "FALSE_NEGATIVE",
                    "class": CLASSES.get(g["class"], str(g["class"])),
                    "confidence": "",
                    "iou": "",
                })

    metrics = {}
    for cls_id in sorted(CLASSES.keys()):
        tp = stats[cls_id]["TP"]
        fp = stats[cls_id]["FP"]
        fn = stats[cls_id]["FN"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        metrics[cls_id] = {
            "name": CLASSES[cls_id],
            "threshold": thresholds.get(cls_id, 0.25),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }
    return metrics, detailed_errors


def main():
    parser = argparse.ArgumentParser(description="Evaluate class-specific confidence thresholds")
    parser.add_argument("--gt", type=str, default="datasets/pcb-yolo-final/labels/val",
                        help="Path to ground truth labels directory")
    parser.add_argument("--pred", type=str, default="runs/detect/runs/diagnostics/val_predictions/labels",
                        help="Path to prediction labels directory")
    parser.add_argument("--iou", type=float, default=0.50, help="Matching IoU threshold")
    parser.add_argument("--out", type=str, default="runs/diagnostics/threshold_comparison.csv",
                        help="Output path for summary CSV")
    args = parser.parse_args()

    gt_dir = Path(args.gt)
    pred_dir = Path(args.pred)
    out_path = Path(args.out)

    if not gt_dir.exists():
        print(f"Error: GT directory not found: {gt_dir}")
        return
    if not pred_dir.exists():
        print(f"Error: Prediction directory not found: {pred_dir}")
        return

    # Load paired data
    all_data = []
    gt_files = sorted(gt_dir.glob("*.txt"))
    for gf in gt_files:
        pf = pred_dir / gf.name
        gt_boxes = read_gt_boxes(gf)
        pred_boxes = read_pred_boxes(pf)
        all_data.append((gf.stem, gt_boxes, pred_boxes))

    print(f"Loaded {len(all_data)} images for validation comparison.\n")

    baseline_metrics, _ = evaluate_with_thresholds(all_data, DEFAULT_THRESHOLDS, args.iou)
    proposed_metrics, _ = evaluate_with_thresholds(all_data, PROPOSED_THRESHOLDS, args.iou)

    # Print Side-by-Side Comparison
    print("=" * 95)
    print("CLASS-SPECIFIC CONFIDENCE EVALUATION: BASELINE (0.25) vs PROPOSED THRESHOLDS")
    print("=" * 95)
    print(f"{'Class':16s} | {'Base Conf':>9s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'Prec':>6s} {'Rec':>6s} {'F1':>6s} | "
          f"{'Prop Conf':>9s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'Prec':>6s} {'Rec':>6s} {'F1':>6s}")
    print("-" * 95)

    total_base_tp = sum(m["TP"] for m in baseline_metrics.values())
    total_base_fp = sum(m["FP"] for m in baseline_metrics.values())
    total_base_fn = sum(m["FN"] for m in baseline_metrics.values())

    total_prop_tp = sum(m["TP"] for m in proposed_metrics.values())
    total_prop_fp = sum(m["FP"] for m in proposed_metrics.values())
    total_prop_fn = sum(m["FN"] for m in proposed_metrics.values())

    rows_to_save = []
    for cls_id in sorted(CLASSES.keys()):
        b = baseline_metrics[cls_id]
        p = proposed_metrics[cls_id]
        print(f"{b['name']:16s} | {b['threshold']:9.2f} {b['TP']:4d} {b['FP']:4d} {b['FN']:4d} {b['precision']:6.3f} {b['recall']:6.3f} {b['f1']:6.3f} | "
              f"{p['threshold']:9.2f} {p['TP']:4d} {p['FP']:4d} {p['FN']:4d} {p['precision']:6.3f} {p['recall']:6.3f} {p['f1']:6.3f}")
        rows_to_save.append({
            "class": b["name"],
            "baseline_conf": b["threshold"],
            "baseline_TP": b["TP"], "baseline_FP": b["FP"], "baseline_FN": b["FN"],
            "baseline_precision": round(b["precision"], 4), "baseline_recall": round(b["recall"], 4), "baseline_f1": round(b["f1"], 4),
            "proposed_conf": p["threshold"],
            "proposed_TP": p["TP"], "proposed_FP": p["FP"], "proposed_FN": p["FN"],
            "proposed_precision": round(p["precision"], 4), "proposed_recall": round(p["recall"], 4), "proposed_f1": round(p["f1"], 4),
        })

    print("-" * 95)
    base_prec = total_base_tp / (total_base_tp + total_base_fp) if (total_base_tp + total_base_fp) > 0 else 0
    base_rec = total_base_tp / (total_base_tp + total_base_fn) if (total_base_tp + total_base_fn) > 0 else 0
    base_f1 = 2 * base_prec * base_rec / (base_prec + base_rec) if (base_prec + base_rec) > 0 else 0

    prop_prec = total_prop_tp / (total_prop_tp + total_prop_fp) if (total_prop_tp + total_prop_fp) > 0 else 0
    prop_rec = total_prop_tp / (total_prop_tp + total_prop_fn) if (total_prop_tp + total_prop_fn) > 0 else 0
    prop_f1 = 2 * prop_prec * prop_rec / (prop_prec + prop_rec) if (prop_prec + prop_rec) > 0 else 0

    print(f"{'OVERALL TOTAL':16s} | {'-':>9s} {total_base_tp:4d} {total_base_fp:4d} {total_base_fn:4d} {base_prec:6.3f} {base_rec:6.3f} {base_f1:6.3f} | "
          f"{'-':>9s} {total_prop_tp:4d} {total_prop_fp:4d} {total_prop_fn:4d} {prop_prec:6.3f} {prop_rec:6.3f} {prop_f1:6.3f}")
    print("=" * 95)
    print(f"\nNet FP reduction: {total_base_fp} -> {total_prop_fp} ({- (total_base_fp - total_prop_fp):+d} FPs, {((total_prop_fp - total_base_fp) / total_base_fp) * 100:.1f}%)")
    print(f"Net TP retained:  {total_base_tp} -> {total_prop_tp} ({- (total_base_tp - total_prop_tp):+d} TPs, {((total_prop_tp - total_base_tp) / total_base_tp) * 100:.1f}%)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows_to_save[0].keys())
        writer.writeheader()
        writer.writerows(rows_to_save)
    print(f"\nSaved comparison summary to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
