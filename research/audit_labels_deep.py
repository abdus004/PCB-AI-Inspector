"""
Deep label quality audit for PCB-AI-Inspector.
Checks: class distribution, OOB boxes, empty labels, missing pairs,
augmentation filename patterns, duplicate stems, tiny/huge boxes.
"""
import os, re, hashlib
from pathlib import Path
from collections import Counter

base = Path("datasets/pcb-yolo-final")
splits = ["train", "val", "test"]
class_names = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]

AUG_PATTERNS = ["rotation_90", "rotation_270", "l_light"]

all_stems_by_split = {}

for split in splits:
    img_dir = base / "images" / split
    lbl_dir = base / "labels" / split

    imgs = set(p.stem for p in img_dir.glob("*.jpg")) | set(p.stem for p in img_dir.glob("*.png"))
    lbls = set(p.stem for p in lbl_dir.glob("*.txt"))

    imgs_no_lbl = imgs - lbls
    lbls_no_img = lbls - imgs

    # Filename pattern breakdown
    pat_counts = Counter()
    for n in imgs:
        matched = False
        for ap in AUG_PATTERNS:
            if ap in n:
                pat_counts[ap] += 1
                matched = True
                break
        if not matched:
            m = re.search(r"light_(\d+)", n)
            if m:
                pat_counts[f"light_{m.group(1)}"] += 1
            else:
                pat_counts["original"] += 1

    # Label analysis
    class_counts = [0] * 6
    empty_labels = []
    invalid_cls = []
    oob_boxes = []
    tiny_boxes = []   # w*h < 0.0001 (normalized)
    large_boxes = []  # w > 0.95 or h > 0.95
    total_ann = 0
    duplicate_ann = []  # same line repeated in same file

    for lbl_path in sorted(lbl_dir.glob("*.txt")):
        content = lbl_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            empty_labels.append(lbl_path.name)
            continue
        lines = content.splitlines()
        seen_lines = set()
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            if line in seen_lines:
                duplicate_ann.append((lbl_path.name, line))
            seen_lines.add(line)
            try:
                cls_id = int(parts[0])
                cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            except ValueError:
                continue
            total_ann += 1
            if 0 <= cls_id <= 5:
                class_counts[cls_id] += 1
            else:
                invalid_cls.append((lbl_path.name, cls_id))
            # OOB check (strict)
            if cx < 0 or cy < 0 or w <= 0 or h <= 0 or (cx + w/2) > 1 or (cy + h/2) > 1:
                oob_boxes.append((lbl_path.name, cls_id, round(cx,4), round(cy,4), round(w,4), round(h,4)))
            # Tiny box
            if w * h < 0.00005:
                tiny_boxes.append((lbl_path.name, cls_id, round(w,5), round(h,5)))
            # Very large box
            if w > 0.95 or h > 0.95:
                large_boxes.append((lbl_path.name, cls_id, round(w,4), round(h,4)))

    all_stems_by_split[split] = imgs

    print(f"\n{'='*60}")
    print(f"SPLIT: {split.upper()}  (images: {len(imgs)}, labels: {len(lbls)})")
    print(f"{'='*60}")
    print(f"  Images without label file : {len(imgs_no_lbl)}")
    if imgs_no_lbl:
        print(f"    Samples: {list(imgs_no_lbl)[:5]}")
    print(f"  Labels without image file : {len(lbls_no_img)}")
    if lbls_no_img:
        print(f"    Samples: {list(lbls_no_img)[:5]}")
    print(f"\n  Filename patterns:")
    for k, v in sorted(pat_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:30s}: {v:5d}  ({v/len(imgs)*100:.1f}%)")
    print(f"\n  Annotation summary:")
    print(f"    Total annotations : {total_ann}")
    for i, name in enumerate(class_names):
        pct = class_counts[i] / max(total_ann, 1) * 100
        print(f"    [{i}] {name:20s}: {class_counts[i]:5d}  ({pct:.1f}%)")
    print(f"\n  Issues:")
    print(f"    Empty label files  : {len(empty_labels)}")
    if empty_labels:
        print(f"      Samples: {empty_labels[:5]}")
    print(f"    Invalid class IDs  : {len(invalid_cls)}")
    if invalid_cls:
        print(f"      Samples: {invalid_cls[:5]}")
    print(f"    OOB boxes          : {len(oob_boxes)}")
    if oob_boxes:
        print(f"      Samples: {oob_boxes[:5]}")
    print(f"    Tiny boxes (<0.005%area): {len(tiny_boxes)}")
    if tiny_boxes:
        print(f"      Samples: {tiny_boxes[:5]}")
    print(f"    Very large boxes   : {len(large_boxes)}")
    if large_boxes:
        print(f"      Samples: {large_boxes[:5]}")
    print(f"    Duplicate annotations: {len(duplicate_ann)}")
    if duplicate_ann:
        print(f"      Samples: {duplicate_ann[:5]}")

# Cross-split duplicate stem check
print(f"\n{'='*60}")
print("CROSS-SPLIT DUPLICATE STEM ANALYSIS")
print(f"{'='*60}")
tv  = all_stems_by_split["train"] & all_stems_by_split["val"]
tt  = all_stems_by_split["train"] & all_stems_by_split["test"]
vt  = all_stems_by_split["val"]   & all_stems_by_split["test"]
print(f"  Train ∩ Val  : {len(tv)}")
print(f"  Train ∩ Test : {len(tt)}")
print(f"  Val   ∩ Test : {len(vt)}")
if tv:
    print(f"  Train∩Val samples : {list(tv)[:5]}")
if tt:
    print(f"  Train∩Test samples: {list(tt)[:5]}")
if vt:
    print(f"  Val∩Test samples  : {list(vt)[:5]}")

print("\nAudit complete.")
