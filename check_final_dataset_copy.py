from pathlib import Path
import pandas as pd

SOURCE = Path("datasets/pcb-defect-dataset")
DEST = Path("datasets/pcb-yolo-final")
MANIFEST = Path("reports/board_split_proposal.csv")

df = pd.read_csv(MANIFEST)

missing_images = []
missing_labels = []
existing_destinations = []

for _, row in df.iterrows():
    original_split = row["split"]
    new_split = row["new_split"]
    filename = row["file"]

    image_src = SOURCE / original_split / "images" / filename
    label_src = SOURCE / original_split / "labels" / (
        Path(filename).stem + ".txt"
    )

    image_dest = DEST / "images" / new_split / filename
    label_dest = DEST / "labels" / new_split / (
        Path(filename).stem + ".txt"
    )

    if not image_src.is_file():
        missing_images.append(str(image_src))

    if not label_src.is_file():
        missing_labels.append(str(label_src))

    if image_dest.exists() or label_dest.exists():
        existing_destinations.append(filename)

print("========== COPY PREFLIGHT ==========")
print("Manifest rows:", len(df))
print("Missing images:", len(missing_images))
print("Missing labels:", len(missing_labels))
print("Existing destination files:", len(existing_destinations))

print("\nImages planned per split:")
print(df["new_split"].value_counts().to_string())

if missing_images or missing_labels or existing_destinations:
    print("\nCHECK FAILED. DO NOT COPY FILES.")
else:
    print("\nPREFLIGHT PASSED. READY FOR COPY.")