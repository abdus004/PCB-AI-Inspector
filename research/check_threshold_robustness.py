"""
Robustness evaluation script across:
1. Original validation images only (407 images).
2. light_09 original images (264 images).
3. light_10 original images (143 images).
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from collections import defaultdict

GT_DIR = Path("datasets/pcb-yolo-final/labels/val")
PRED_DIR = Path("runs/detect/runs/diagnostics/val_predictions/labels")

CLASSES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

DEFAULT_THRESHOLDS = {c: 0.25 for c in CLASSES}
PROPOSED_THRESHOLDS = {
    0: 0.25,
    1: 0.45,
    2: 0.25,
    3: 0.30,
    4: 0.25,
    5: 0.40,
}


def read_gt(path):
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) >= 5:
            boxes.append({"class": int(float(p[0])), "box": tuple(map(float, p[1:5]))})
    return boxes


def read_pred(path):
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) >= 6:
            boxes.append({"class": int(float(p[0])), "box": tuple(map(float, p[1:5])), "conf": float(p[5])})
    return boxes


def compute_iou(box_a, box_b):
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


def eval_subset(items, thresholds, iou_thresh=0.5):
    stats = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
    for stem, gt_boxes, pred_boxes in items:
        preds = [p for p in pred_boxes if p["conf"] >= thresholds.get(p["class"], 0.25)]
        preds.sort(key=lambda x: x["conf"], reverse=True)
        matched_gt = set()
        for p in preds:
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
        for idx, g in enumerate(gt_boxes):
            if idx not in matched_gt:
                stats[g["class"]]["FN"] += 1
    res = {}
    for c in sorted(CLASSES.keys()):
        tp = stats[c]["TP"]
        fp = stats[c]["FP"]
        fn = stats[c]["FN"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        res[c] = {"name": CLASSES[c], "TP": tp, "FP": fp, "FN": fn, "prec": prec, "rec": rec, "f1": f1}
    return res


def print_comparison(title, subset):
    print("\n" + "=" * 90)
    print(f"{title} (n = {len(subset)} images)")
    print("=" * 90)
    base = eval_subset(subset, DEFAULT_THRESHOLDS)
    prop = eval_subset(subset, PROPOSED_THRESHOLDS)

    hdr = f"{'Class':16s} | {'Base(0.25)':>10s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'Prec':>6s} {'Rec':>6s} {'F1':>6s} | {'Prop':>6s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'Prec':>6s} {'Rec':>6s} {'F1':>6s}"
    print(hdr)
    print("-" * 90)

    b_tp = sum(base[c]["TP"] for c in base)
    b_fp = sum(base[c]["FP"] for c in base)
    b_fn = sum(base[c]["FN"] for c in base)

    p_tp = sum(prop[c]["TP"] for c in prop)
    p_fp = sum(prop[c]["FP"] for c in prop)
    p_fn = sum(prop[c]["FN"] for c in prop)

    for c in sorted(CLASSES.keys()):
        b = base[c]
        p = prop[c]
        prop_c = PROPOSED_THRESHOLDS[c]
        row = f"{b['name']:16s} | {'0.25':>10s} {b['TP']:4d} {b['FP']:4d} {b['FN']:4d} {b['prec']:6.3f} {b['rec']:6.3f} {b['f1']:6.3f} | {prop_c:6.2f} {p['TP']:4d} {p['FP']:4d} {p['FN']:4d} {p['prec']:6.3f} {p['rec']:6.3f} {p['f1']:6.3f}"
        print(row)

    print("-" * 90)
    bp = b_tp / (b_tp + b_fp) if (b_tp + b_fp) > 0 else 0
    br = b_tp / (b_tp + b_fn) if (b_tp + b_fn) > 0 else 0
    bf1 = 2 * bp * br / (bp + br) if (bp + br) > 0 else 0

    pp = p_tp / (p_tp + p_fp) if (p_tp + p_fp) > 0 else 0
    pr = p_tp / (p_tp + p_fn) if (p_tp + p_fn) > 0 else 0
    pf1 = 2 * pp * pr / (pp + pr) if (pp + pr) > 0 else 0

    tot_row = f"{'TOTAL':16s} | {'-':>10s} {b_tp:4d} {b_fp:4d} {b_fn:4d} {bp:6.3f} {br:6.3f} {bf1:6.3f} | {'-':>6s} {p_tp:4d} {p_fp:4d} {p_fn:4d} {pp:6.3f} {pr:6.3f} {pf1:6.3f}"
    print(tot_row)
    print(f"FP delta: {b_fp} -> {p_fp} ({- (b_fp - p_fp):+d}, {((p_fp - b_fp) / b_fp) * 100:.1f}%) | TP delta: {b_tp} -> {p_tp} ({- (b_tp - p_tp):+d}, {((p_tp - b_tp) / b_tp) * 100:.1f}%)")


def main():
    all_gt = sorted(GT_DIR.glob("*.txt"))
    dataset = []
    for gf in all_gt:
        dataset.append((gf.stem, read_gt(gf), read_pred(PRED_DIR / gf.name)))

    orig_all = [x for x in dataset if "rotation_90" not in x[0] and "rotation_270" not in x[0] and not x[0].startswith("l_light")]
    orig_l09 = [x for x in orig_all if "light_09" in x[0]]
    orig_l10 = [x for x in orig_all if "light_10" in x[0]]

    print(f"Total dataset: {len(dataset)} validation images")
    print(f"  - Original images only: {len(orig_all)}")
    print(f"  - Original light_09:    {len(orig_l09)}")
    print(f"  - Original light_10:    {len(orig_l10)}")

    print_comparison("1. ORIGINAL VALIDATION IMAGES ONLY", orig_all)
    print_comparison("2. LIGHT_09 ORIGINAL IMAGES ONLY", orig_l09)
    print_comparison("3. LIGHT_10 ORIGINAL IMAGES ONLY", orig_l10)


if __name__ == "__main__":
    main()
