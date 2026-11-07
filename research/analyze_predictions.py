from pathlib import Path
from collections import defaultdict
import csv

GT_DIR = Path("datasets/pcb-yolo-final/labels/val")
PRED_DIR = Path("runs/detect/runs/diagnostics/val_predictions/labels")
OUT_DIR = Path("runs/diagnostics/error_analysis")

CLASSES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

IOU_THRESHOLD = 0.50
CONF_THRESHOLD = 0.25

def read_labels(path, prediction=False):
    items = []
    if not path.exists():
        return items

    for line in path.read_text().splitlines():
        values = line.split()
        if len(values) < 5:
            continue

        cls = int(float(values[0]))
        x, y, w, h = map(float, values[1:5])
        conf = float(values[5]) if prediction and len(values) >= 6 else 1.0

        if prediction and conf < CONF_THRESHOLD:
            continue

        items.append({
            "class": cls,
            "box": (x, y, w, h),
            "confidence": conf
        })
    return items

def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b

    ax1, ay1 = ax - aw / 2, ay - ah / 2
    ax2, ay2 = ax + aw / 2, ay + ah / 2
    bx1, by1 = bx - bw / 2, by - bh / 2
    bx2, by2 = bx + bw / 2, by + bh / 2

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = aw * ah
    area_b = bw * bh
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0

OUT_DIR.mkdir(parents=True, exist_ok=True)

stats = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0})
image_errors = []

gt_files = sorted(GT_DIR.glob("*.txt"))

for gt_file in gt_files:
    pred_file = PRED_DIR / gt_file.name

    gt = read_labels(gt_file)
    pred = read_labels(pred_file, prediction=True)
    matched_gt = set()

    # Match highest-confidence predictions first, within the same class.
    pred.sort(key=lambda item: item["confidence"], reverse=True)

    for p in pred:
        best_iou = 0
        best_index = None

        for index, g in enumerate(gt):
            if index in matched_gt or g["class"] != p["class"]:
                continue

            score = iou(p["box"], g["box"])
            if score > best_iou:
                best_iou = score
                best_index = index

        if best_index is not None and best_iou >= IOU_THRESHOLD:
            matched_gt.add(best_index)
            stats[p["class"]]["TP"] += 1
        else:
            stats[p["class"]]["FP"] += 1
            image_errors.append({
                "image": gt_file.stem,
                "error": "FALSE_POSITIVE",
                "class": CLASSES.get(p["class"], str(p["class"])),
                "confidence": round(p["confidence"], 4),
                "iou": round(best_iou, 4)
            })

    for index, g in enumerate(gt):
        if index not in matched_gt:
            stats[g["class"]]["FN"] += 1
            image_errors.append({
                "image": gt_file.stem,
                "error": "FALSE_NEGATIVE",
                "class": CLASSES.get(g["class"], str(g["class"])),
                "confidence": "",
                "iou": ""
            })

print("\n========== CLASS-WISE ERROR ANALYSIS ==========")
rows = []

for cls, name in CLASSES.items():
    tp = stats[cls]["TP"]
    fp = stats[cls]["FP"]
    fn = stats[cls]["FN"]

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    rows.append({
        "class": name, "TP": tp, "FP": fp, "FN": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4)
    })

    print(
        f"{name:18} TP={tp:4} FP={fp:4} FN={fn:4} "
        f"Precision={precision:.3%} Recall={recall:.3%}"
    )

with open(OUT_DIR / "class_metrics.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

with open(OUT_DIR / "image_errors.csv", "w", newline="") as f:
    fields = ["image", "error", "class", "confidence", "iou"]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(image_errors)

print("\nTotal GT images:", len(gt_files))
print("Images with prediction files:", len(list(PRED_DIR.glob("*.txt"))))
print("Total false-positive / false-negative records:", len(image_errors))
print("\nReports saved to:", OUT_DIR.resolve())
print(" - class_metrics.csv")
print(" - image_errors.csv")
