
from pathlib import Path

base = Path("datasets/pcb-defect-dataset")

for split in ("train", "val", "test"):
    images_dir = base / split / "images"
    labels_dir = base / split / "labels"

    print(f"\n========== {split.upper()} ==========")

    images = sorted(
        p for p in images_dir.iterdir()
        if p.suffix.lower() in {
            ".jpg", ".jpeg", ".png", ".bmp", ".webp"
        }
    )
    labels = sorted(labels_dir.glob("*.txt"))

    print("\nFirst 5 image filenames:")
    for p in images[:5]:
        print(repr(p.name), "| stem:", repr(p.stem))

    print("\nFirst 5 label filenames:")
    for p in labels[:5]:
        print(repr(p.name), "| stem:", repr(p.stem))

    image_stems = {p.stem for p in images}
    label_stems = {p.stem for p in labels}

    print("\nExample image with no matching label:")
    for p in images:
        if p.stem not in label_stems:
            print(p.name)
            break

    print("\nExample label with no matching image:")
    for p in labels:
        if p.stem not in image_stems:
            print(p.name)
            break
