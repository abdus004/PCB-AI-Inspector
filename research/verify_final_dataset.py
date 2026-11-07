from pathlib import Path

ROOT = Path("datasets/pcb-yolo-final")

total_images = 0
total_labels = 0

for split in ["train", "val", "test"]:
    image_dir = ROOT / "images" / split
    label_dir = ROOT / "labels" / split

    images = {
        p.stem for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png"]
    }

    labels = {
        p.stem for p in label_dir.glob("*.txt")
    }

    missing_labels = images - labels
    orphan_labels = labels - images

    total_images += len(images)
    total_labels += len(labels)

    print(f"\n{split.upper()}")
    print("Images:", len(images))
    print("Labels:", len(labels))
    print("Missing labels:", len(missing_labels))
    print("Orphan labels:", len(orphan_labels))

print("\n========== FINAL VERIFICATION ==========")
print("Total images:", total_images)
print("Total labels:", total_labels)

if total_images == 10668 and total_labels == 10668:
    print("FILE COUNT: PASSED")
else:
    print("FILE COUNT: FAILED")