
from pathlib import Path
import cv2

DATASET_DIR = Path("datasets/pcb-defect-dataset")
OUTPUT_DIR = Path("reports/box_crops/mouse_bite")
CLASS_ID = 0

CLASS_NAME = "mouse_bite"
PADDING = 30
SCALE = 4

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

count = 0

for split in ("train", "val", "test"):

    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    for label_path in label_dir.glob("*.txt"):

        image_path = image_dir / f"{label_path.stem}.jpg"

        if not image_path.exists():
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            continue

        height, width = image.shape[:2]

        lines = label_path.read_text(
            encoding="utf-8"
        ).splitlines()

        for box_index, line in enumerate(lines):

            parts = line.split()

            if len(parts) != 5:
                continue

            class_id = int(float(parts[0]))

            if class_id != CLASS_ID:
                continue

            x, y, w, h = map(float, parts[1:])

            x1 = int((x - w / 2) * width)
            y1 = int((y - h / 2) * height)
            x2 = int((x + w / 2) * width)
            y2 = int((y + h / 2) * height)

            left = max(0, x1 - PADDING)
            top = max(0, y1 - PADDING)
            right = min(width, x2 + PADDING)
            bottom = min(height, y2 + PADDING)

            crop = image[top:bottom, left:right]

            if crop.size == 0:
                continue

            enlarged = cv2.resize(
                crop,
                None,
                fx=SCALE,
                fy=SCALE,
                interpolation=cv2.INTER_CUBIC
            )

            # Draw the original annotation boundary.
            cv2.rectangle(
                enlarged,
                (
                    (x1 - left) * SCALE,
                    (y1 - top) * SCALE
                ),
                (
                    (x2 - left) * SCALE,
                    (y2 - top) * SCALE
                ),
                (0, 255, 0),
                2
            )

            count += 1

            filename = (
                f"{split}_{label_path.stem}_"
                f"box{box_index + 1}.jpg"
            )

            cv2.imwrite(
                str(OUTPUT_DIR / filename),
                enlarged
            )

print("Mouse-bite crops created:", count)
print("Output:", OUTPUT_DIR)
print("Original images and labels were not modified.")
