from pathlib import Path
import pandas as pd
import shutil

SOURCE = Path("datasets/pcb-defect-dataset")
DEST = Path("datasets/pcb-yolo-final")
MANIFEST = Path("reports/board_split_proposal.csv")

df = pd.read_csv(MANIFEST)

copied_images = 0
copied_labels = 0

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

    shutil.copy2(image_src, image_dest)
    shutil.copy2(label_src, label_dest)

    copied_images += 1
    copied_labels += 1

    if copied_images % 1000 == 0:
        print(f"Copied {copied_images} image-label pairs")

print("\n========== COPY COMPLETED ==========")
print("Images copied:", copied_images)
print("Labels copied:", copied_labels)
print("Destination:", DEST)