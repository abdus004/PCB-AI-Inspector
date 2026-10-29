
from pathlib import Path

BASE = Path("datasets/pcb-defect-dataset")
splits = ("train", "val", "test")

ready = []
conflicts = []
unmatched = []

for split in splits:
    images_dir = BASE / split / "images"
    labels_dir = BASE / split / "labels"

    image_stems = {
        p.stem for p in images_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    }

    for label in labels_dir.glob("*_256.txt"):
        target_stem = label.stem[:-4] + "_600"

        if target_stem not in image_stems:
            unmatched.append((split, label.name, "No matching image"))
            continue

        target_label = labels_dir / f"{target_stem}.txt"

        if target_label.exists():
            conflicts.append((split, label.name, target_label.name))
        else:
            ready.append((split, label.name, target_label.name))

print("========== DRY RUN ==========")
print("Labels safe to rename:", len(ready))
print("Conflicts (target already exists):", len(conflicts))
print("Labels without matching images:", len(unmatched))

print("\nExamples of proposed renames:")
for split, old, new in ready[:10]:
    print(f"{split}: {old} -> {new}")

if conflicts:
    print("\nExamples of conflicts:")
    for item in conflicts[:10]:
        print(item)

if unmatched:
    print("\nExamples without matching images:")
    for item in unmatched[:10]:
        print(item)

print("\nNo files were changed.")
