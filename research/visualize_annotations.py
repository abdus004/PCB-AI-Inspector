
from pathlib import Path
import random
import cv2
import matplotlib.pyplot as plt

DATASET_DIR = Path("datasets/pcb-defect-dataset")
SPLIT = "train"
NUM_IMAGES = 9

CLASS_NAMES = {
    0: "mouse_bite",
    1: "spur",
    2: "missing_hole",
    3: "short",
    4: "open_circuit",
    5: "spurious_copper",
}

image_dir = DATASET_DIR / SPLIT / "images"
label_dir = DATASET_DIR / SPLIT / "labels"

images = list(image_dir.glob("*.jpg"))
random.seed(42)
samples = random.sample(images, min(NUM_IMAGES, len(images)))

fig, axes = plt.subplots(3, 3, figsize=(15, 12))
axes = axes.flatten()

for ax, image_path in zip(axes, samples):
    image = cv2.imread(str(image_path))

    if image is None:
        ax.set_title("Could not read image")
        ax.axis("off")
        continue

    height, width = image.shape[:2]
    label_path = label_dir / f"{image_path.stem}.txt"

    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            values = line.split()

            if len(values) != 5:
                continue

            class_id = int(values[0])
            x_center, y_center, box_w, box_h = map(float, values[1:])

            x1 = int((x_center - box_w / 2) * width)
            y1 = int((y_center - box_h / 2) * height)
            x2 = int((x_center + box_w / 2) * width)
            y2 = int((y_center + box_h / 2) * height)

            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            name = CLASS_NAMES.get(class_id, f"class_{class_id}")
            cv2.putText(
                image, name, (x1, max(20, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1
            )

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    ax.imshow(image)
    ax.set_title(image_path.name, fontsize=8)
    ax.axis("off")

for ax in axes[len(samples):]:
    ax.axis("off")

plt.tight_layout()
plt.show()
