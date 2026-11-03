
from pathlib import Path
from collections import Counter
import csv
import math
import cv2

DATASET_DIR = Path("datasets/pcb-defect-dataset")
REPORT_DIR = Path("reports")
NUM_CLASSES = 6

CLASS_NAMES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

REPORT_DIR.mkdir(exist_ok=True)

class_counts = Counter()
box_sizes = Counter()
errors = []
image_rows = []

total_images = 0
total_boxes = 0
total_empty_labels = 0
total_unmatched_images = 0
total_orphan_labels = 0
total_corrupt_images = 0
total_duplicate_boxes = 0

for split in ("train", "val", "test"):

    print(f"\nChecking {split.upper()}...")

    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    images = [
        p for p in image_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    labels = list(label_dir.glob("*.txt"))

    image_map = {p.stem: p for p in images}
    label_map = {p.stem: p for p in labels}

    missing = set(image_map) - set(label_map)
    orphaned = set(label_map) - set(image_map)

    total_unmatched_images += len(missing)
    total_orphan_labels += len(orphaned)

    print("Images:", len(images))
    print("Labels:", len(labels))
    print("Missing labels:", len(missing))
    print("Orphan labels:", len(orphaned))

    for stem in sorted(missing):
        errors.append([split, stem, "Missing label file"])

    for stem in sorted(orphaned):
        errors.append([split, stem, "Label without image"])

    for stem, image_path in image_map.items():

        total_images += 1

        image = cv2.imread(str(image_path))

        if image is None:
            total_corrupt_images += 1
            errors.append([split, stem, "Unreadable image"])
            continue

        height, width = image.shape[:2]

        label_path = label_map.get(stem)

        if label_path is None:
            continue

        try:
            lines = label_path.read_text(
                encoding="utf-8"
            ).splitlines()

            if not lines:
                total_empty_labels += 1
                image_rows.append([
                    split, stem, width, height, 0
                ])
                continue

            image_box_count = 0
            seen_boxes = set()

            for line_number, line in enumerate(lines, start=1):

                parts = line.split()

                if len(parts) != 5:
                    raise ValueError(
                        f"Line {line_number}: expected 5 values"
                    )

                values = [float(v) for v in parts]

                if not all(math.isfinite(v) for v in values):
                    raise ValueError(
                        f"Line {line_number}: NaN or infinity"
                    )

                class_value = values[0]

                if not class_value.is_integer():
                    raise ValueError(
                        f"Line {line_number}: invalid class ID"
                    )

                class_id = int(class_value)

                if class_id not in CLASS_NAMES:
                    raise ValueError(
                        f"Line {line_number}: unknown class {class_id}"
                    )

                x, y, w, h = values[1:]

                if not all(0 <= v <= 1 for v in (x, y, w, h)):
                    raise ValueError(
                        f"Line {line_number}: coordinate outside 0-1"
                    )

                if w <= 0 or h <= 0:
                    raise ValueError(
                        f"Line {line_number}: zero or negative box size"
                    )

                if x - w / 2 < 0 or x + w / 2 > 1:
                    raise ValueError(
                        f"Line {line_number}: box outside image horizontally"
                    )

                if y - h / 2 < 0 or y + h / 2 > 1:
                    raise ValueError(
                        f"Line {line_number}: box outside image vertically"
                    )

                box_key = tuple(round(v, 8) for v in values)

                if box_key in seen_boxes:
                    total_duplicate_boxes += 1
                    errors.append([
                        split, stem,
                        f"Duplicate box on line {line_number}"
                    ])

                seen_boxes.add(box_key)

                class_counts[class_id] += 1
                total_boxes += 1
                image_box_count += 1

                area = w * h

                if area < 0.001:
                    box_sizes["Very small (<0.1%)"] += 1
                elif area < 0.01:
                    box_sizes["Small (0.1%-1%)"] += 1
                elif area < 0.05:
                    box_sizes["Medium (1%-5%)"] += 1
                else:
                    box_sizes["Large (>=5%)"] += 1

            image_rows.append([
                split, stem, width, height, image_box_count
            ])

        except (ValueError, OSError) as error:
            errors.append([split, stem, str(error)])

print("\n========== DATASET AUDIT ==========")

print("Total images:", total_images)
print("Total valid boxes:", total_boxes)
print("Empty labels:", total_empty_labels)
print("Images missing labels:", total_unmatched_images)
print("Orphan labels:", total_orphan_labels)
print("Unreadable images:", total_corrupt_images)
print("Duplicate boxes:", total_duplicate_boxes)

print("\n--- CLASS DISTRIBUTION ---")

for class_id, name in CLASS_NAMES.items():
    print(
        f"{name}: {class_counts[class_id]} boxes"
    )

print("\n--- BOX SIZE DISTRIBUTION ---")

for size, count in box_sizes.items():
    print(f"{size}: {count}")

print("\n--- ERRORS ---")
print("Total reported issues:", len(errors))

for error in errors[:30]:
    print(error)

with open(
    REPORT_DIR / "dataset_quality_images.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:
    writer = csv.writer(file)
    writer.writerow([
        "split", "image", "width", "height", "box_count"
    ])
    writer.writerows(image_rows)

with open(
    REPORT_DIR / "dataset_quality_errors.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:
    writer = csv.writer(file)
    writer.writerow(["split", "image", "issue"])
    writer.writerows(errors)

print("\nReports saved in:", REPORT_DIR)
print("Original dataset was not modified.")
