from pathlib import Path
import yaml

# Dataset location
DATASET_DIR = Path("datasets/pcb-defect-dataset")
CONFIG_FILE = DATASET_DIR / "data.yaml"

print("Checking PCB-AI-Inspector dataset...\n")

# Check configuration file
if not CONFIG_FILE.exists():
    raise FileNotFoundError(
        f"Cannot find dataset config: {CONFIG_FILE.resolve()}"
    )

with open(CONFIG_FILE, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Check paths and classes
print("Defect classes:")
for class_id, class_name in config["names"].items():
    print(f"  {class_id}: {class_name}")

print("\nDataset split summary:")

for split in ("train", "val", "test"):
    image_dir = DATASET_DIR / split / "images"
    label_dir = DATASET_DIR / split / "labels"

    if not image_dir.is_dir() or not label_dir.is_dir():
        print(f"{split}: FOLDERS MISSING")
        continue

    images = [
        p for p in image_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    ]
    labels = list(label_dir.glob("*.txt"))

    print(f"{split}: {len(images)} images, {len(labels)} label files")

print("\nDataset path:", DATASET_DIR.resolve())
print("Check complete.")