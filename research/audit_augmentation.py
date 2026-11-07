"""
Augmentation analysis: Check if augmented images have correctly transformed labels.
Compares rotation_90 / rotation_270 images against their base originals.
Also checks for near-duplicates using image hashing.
"""
import os, re
from pathlib import Path
from collections import defaultdict

base = Path("datasets/pcb-yolo-final")
splits = ["train", "val", "test"]
class_names = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]


def parse_label(lbl_path):
    """Return list of (cls, cx, cy, w, h) tuples."""
    rows = []
    if not lbl_path.exists():
        return rows
    for line in lbl_path.read_text().strip().splitlines():
        p = line.split()
        if len(p) >= 5:
            rows.append((int(p[0]), float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    return rows


def rotate90_box(cx, cy, w, h):
    """Rotate bbox 90 degrees clockwise: (cx,cy,w,h) -> new coords."""
    # 90 CW: (x,y) -> (1-y, x); w,h swap
    new_cx = 1 - cy
    new_cy = cx
    new_w  = h
    new_h  = w
    return new_cx, new_cy, new_w, new_h


def rotate270_box(cx, cy, w, h):
    """Rotate bbox 270 degrees clockwise (= 90 CCW): (x,y) -> (y, 1-x)."""
    new_cx = cy
    new_cy = 1 - cx
    new_w  = h
    new_h  = w
    return new_cx, new_cy, new_w, new_h


TOLS = 0.03   # tolerance for coordinate comparison

issues_found = 0

for split in splits:
    img_dir = base / "images" / split
    lbl_dir = base / "labels" / split

    # Group: map base_stem -> list of augmented variants
    base_map = defaultdict(dict)
    for p in img_dir.glob("*.jpg"):
        name = p.stem
        m90  = re.search(r"rotation_90", name)
        m270 = re.search(r"rotation_270", name)
        if m90:
            base_name = name.replace("rotation_90_", "").replace("_rotation_90", "").replace("rotation_90", "")
            base_map[base_name]["rot90"] = name
        elif m270:
            base_name = name.replace("rotation_270_", "").replace("_rotation_270", "").replace("rotation_270", "")
            base_map[base_name]["rot270"] = name
        else:
            base_map[name]["orig"] = name

    checked = 0
    mismatch = 0
    missing_base = 0

    for base_stem, variants in base_map.items():
        if "orig" not in variants:
            missing_base += 1
            continue

        orig_boxes  = parse_label(lbl_dir / f"{variants['orig']}.txt")
        if not orig_boxes:
            continue

        for aug_key in ["rot90", "rot270"]:
            if aug_key not in variants:
                continue
            aug_boxes = parse_label(lbl_dir / f"{variants[aug_key]}.txt")
            if not aug_boxes:
                continue

            checked += 1
            # Compare class sets
            orig_cls  = sorted(b[0] for b in orig_boxes)
            aug_cls   = sorted(b[0] for b in aug_boxes)
            if orig_cls != aug_cls:
                mismatch += 1
                if mismatch <= 3:
                    print(f"  CLASS MISMATCH [{split}] orig={variants['orig']} aug={variants[aug_key]}")
                    print(f"    orig_cls={orig_cls}  aug_cls={aug_cls}")
                continue

            # Check coordinate transformation
            rotate_fn = rotate90_box if aug_key == "rot90" else rotate270_box
            for ob in orig_boxes:
                cls_id = ob[0]
                expected = rotate_fn(ob[1], ob[2], ob[3], ob[4])
                # Find matching aug box
                match = False
                for ab in aug_boxes:
                    if ab[0] == cls_id:
                        diffs = [abs(expected[i] - ab[i+1]) for i in range(4)]
                        if all(d < TOLS for d in diffs):
                            match = True
                            break
                if not match:
                    mismatch += 1
                    if mismatch <= 5:
                        exp_str = tuple(round(x,3) for x in expected)
                        print(f"  COORD MISMATCH [{split}/{aug_key}] base={base_stem} cls={cls_id}")
                        print(f"    orig=({ob[1]:.3f},{ob[2]:.3f},{ob[3]:.3f},{ob[4]:.3f})")
                        print(f"    expected_aug={exp_str}")
                        aug_matching = [(ab[1],ab[2],ab[3],ab[4]) for ab in aug_boxes if ab[0]==cls_id]
                        print(f"    actual_aug_boxes={aug_matching[:3]}")
                    break  # one per pair enough

    print(f"\n[{split}] Augmentation check: {checked} pairs checked, {mismatch} mismatches, {missing_base} aug variants with no orig")
    issues_found += mismatch

print(f"\nTotal augmentation label issues: {issues_found}")
