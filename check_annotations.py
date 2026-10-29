
from pathlib import Path

DATASET_DIR = Path("datasets/pcb-defect-dataset")
NUM_CLASSES = 6
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

total_images = 0
total_boxes = 0
empty_labels = 0
missing_labels = []
invalid_labels = []

for split in ("train", "val", "test"):
    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    images = [
        p for p in image_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    image_stems = {p.stem for p in images}
    label_stems = {p.stem for p in label_dir.glob("*.txt")}

    missing = image_stems - label_stems
    orphaned = label_stems - image_stems

    missing_labels.extend(
        f"{split}/{name}" for name in sorted(missing)
    )

    print(f"\n--- {split.upper()} ---")
    print("Images:", len(images))
    print("Label files:", len(label_stems))
    print("Images without labels:", len(missing))
    print("Labels without images:", len(orphaned))

    total_images += len(images)

    for label_path in label_dir.glob("*.txt"):
        try:
            lines = label_path.read_text(
                encoding="utf-8"
            ).splitlines()

            if not lines:
                empty_labels += 1
                continue

            for line_number, line in enumerate(lines, start=1):
                parts = line.split()

                if len(parts) != 5:
                    raise ValueError(
                        f"Expected 5 values, got {len(parts)}"
                    )

                class_value = float(parts[0])
                coords = [float(v) for v in parts[1:]]

                if not class_value.is_integer():
                    raise ValueError("Class ID is not an integer")

                class_id = int(class_value)

                if not 0 <= class_id < NUM_CLASSES:
                    raise ValueError(f"Invalid class ID: {class_id}")

                x, y, width, height = coords

                if not all(0 <= v <= 1 for v in coords):
                    raise ValueError("Coordinate outside 0–1")

                if width <= 0 or height <= 0:
                    raise ValueError("Box width/height must be positive")

                if not (0 <= x - width / 2 and x + width / 2 <= 1):
                    raise ValueError("Box extends beyond image horizontally")

                if not (0 <= y - height / 2 and y + height / 2 <= 1):
                    raise ValueError("Box extends beyond image vertically")

                total_boxes += 1

        except (ValueError, OSError) as error:
            invalid_labels.append(
                f"{split}/{label_path.name}: {error}"
            )

print("\n========== SUMMARY ==========")
print("Total images:", total_images)
print("Valid boxes checked:", total_boxes)
print("Empty label files:", empty_labels)
print("Images missing labels:", len(missing_labels))
print("Invalid annotation files:", len(invalid_labels))

if missing_labels:
    print("\nExamples of missing labels:")
    for item in missing_labels[:10]:
        print(" -", item)

if invalid_labels:
    print("\nExamples of invalid annotations:")
    for item in invalid_labels[:20]:
        print(" -", item)

if not missing_labels and not invalid_labels:
    print("\nStructural annotation checks passed.")
    print("Visual inspection is still required.")
