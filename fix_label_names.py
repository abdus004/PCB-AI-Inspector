
from pathlib import Path

BASE = Path("datasets/pcb-defect-dataset")
splits = ("train", "val", "test")

renamed = 0

for split in splits:
    labels_dir = BASE / split / "labels"
    images_dir = BASE / split / "images"

    image_stems = {
        p.stem for p in images_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    }

    for label in labels_dir.glob("*_256.txt"):
        target_stem = label.stem[:-4] + "_600"

        if target_stem not in image_stems:
            raise RuntimeError(f"No matching image for {label}")

        target = labels_dir / f"{target_stem}.txt"

        if target.exists():
            raise RuntimeError(f"Target already exists: {target}")

        label.rename(target)
        renamed += 1

print(f"Renamed {renamed} label files.")
print("Next: rerun check_annotations.py")
