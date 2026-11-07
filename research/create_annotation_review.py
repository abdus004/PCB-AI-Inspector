
from pathlib import Path
from collections import defaultdict
import random
import cv2

DATASET_DIR = Path("datasets/pcb-defect-dataset")
OUTPUT_DIR = Path("reports/annotation_review")

SPLITS = ["train", "val", "test"]
SAMPLES_PER_CLASS = 8
SEED = 42

CLASS_NAMES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

random.seed(SEED)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for split in SPLITS:

    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    candidates = defaultdict(list)

    for label_path in label_dir.glob("*.txt"):

        image_path = image_dir / f"{label_path.stem}.jpg"

        if not image_path.exists():
            continue

        try:
            lines = label_path.read_text(
                encoding="utf-8"
            ).splitlines()

            classes = set()

            for line in lines:
                parts = line.split()

                if len(parts) == 5:
                    class_id = int(float(parts[0]))

                    if class_id in CLASS_NAMES:
                        classes.add(class_id)

            for class_id in classes:
                candidates[class_id].append(image_path)

        except (ValueError, OSError):
            continue

    for class_id, class_name in CLASS_NAMES.items():

        available = candidates[class_id]

        selected = random.sample(
            available,
            min(SAMPLES_PER_CLASS, len(available))
        )

        for index, image_path in enumerate(selected, start=1):

            image = cv2.imread(str(image_path))

            if image is None:
                continue

            height, width = image.shape[:2]
            label_path = label_dir / f"{image_path.stem}.txt"

            for line in label_path.read_text(
                encoding="utf-8"
            ).splitlines():

                parts = line.split()

                if len(parts) != 5:
                    continue

                class_id_box = int(float(parts[0]))
                x, y, w, h = map(float, parts[1:])

                x1 = int((x - w / 2) * width)
                y1 = int((y - h / 2) * height)
                x2 = int((x + w / 2) * width)
                y2 = int((y + h / 2) * height)

                # Target class: green. Other classes: orange.
                color = (
                    (0, 255, 0)
                    if class_id_box == class_id
                    else (0, 165, 255)
                )

                cv2.rectangle(
                    image, (x1, y1), (x2, y2), color, 2
                )

                name = CLASS_NAMES[class_id_box]

                cv2.putText(
                    image,
                    name,
                    (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1
                )

            output_path = (
                OUTPUT_DIR /
                f"{split}_{class_name}_{index}.jpg"
            )

            cv2.imwrite(str(output_path), image)

        print(
            f"{split} | {class_name}: "
            f"{len(selected)} images selected"
        )

print("\nVisual annotation review created.")
print("Location:", OUTPUT_DIR)
print("Original dataset was not modified.")
