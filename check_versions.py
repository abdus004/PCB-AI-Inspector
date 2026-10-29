
from pathlib import Path
from collections import Counter

base = Path("datasets/pcb-defect-dataset")

for split in ("train", "val", "test"):
    images_dir = base / split / "images"
    labels_dir = base / split / "labels"

    image_stems = {
        p.stem for p in images_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    }

    label_stems = {p.stem for p in labels_dir.glob("*.txt")}

    matched = image_stems & label_stems
    unmatched_images = image_stems - label_stems
    unmatched_labels = label_stems - image_stems

    print(f"\n===== {split.upper()} =====")
    print("Matching image-label pairs:", len(matched))
    print("Images without exact matching labels:", len(unmatched_images))
    print("Labels without exact matching images:", len(unmatched_labels))

    print("\nUnmatched image examples:")
    for name in sorted(unmatched_images)[:5]:
        print(" ", name)

    print("\nUnmatched label examples:")
    for name in sorted(unmatched_labels)[:5]:
        print(" ", name)

    print("\nImage filename suffix counts:")
    print(Counter(name.rsplit("_", 1)[-1] for name in image_stems).most_common(10))

    print("\nLabel filename suffix counts:")
    print(Counter(name.rsplit("_", 1)[-1] for name in label_stems).most_common(10))
