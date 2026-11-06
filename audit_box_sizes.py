"""
Box size distribution per class and per split.
Identifies extreme boxes, duplicate annotations within a file,
and builds a stat summary suitable for the audit report.
"""
import os
from pathlib import Path
import statistics

base = Path("datasets/pcb-yolo-final")
splits = ["train", "val", "test"]
class_names = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]

for split in splits:
    lbl_dir = base / "labels" / split
    class_areas = {i: [] for i in range(6)}
    class_w     = {i: [] for i in range(6)}
    class_h     = {i: [] for i in range(6)}

    for lbl_path in lbl_dir.glob("*.txt"):
        content = lbl_path.read_text().strip()
        if not content:
            continue
        for line in content.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                cls_id = int(parts[0])
                w, h   = float(parts[3]), float(parts[4])
            except ValueError:
                continue
            if 0 <= cls_id <= 5:
                class_areas[cls_id].append(w * h)
                class_w[cls_id].append(w)
                class_h[cls_id].append(h)

    print(f"\n=== {split.upper()} — Box size statistics ===")
    print(f"{'Class':22s} {'Count':>6} {'AvgArea%':>9} {'MinArea%':>9} {'MaxArea%':>9} {'AvgW':>7} {'AvgH':>7}")
    for i, name in enumerate(class_names):
        areas = class_areas[i]
        ws    = class_w[i]
        hs    = class_h[i]
        if not areas:
            print(f"  {name:20s} {'0':>6}")
            continue
        avg_a = statistics.mean(areas) * 100
        min_a = min(areas) * 100
        max_a = max(areas) * 100
        avg_w = statistics.mean(ws)
        avg_h = statistics.mean(hs)
        print(f"  {name:20s} {len(areas):>6} {avg_a:>9.3f} {min_a:>9.5f} {max_a:>9.3f} {avg_w:>7.4f} {avg_h:>7.4f}")
