
from pathlib import Path
from ultralytics import YOLO

# Find one image from the training dataset
image_dir = Path("datasets/pcb-defect-dataset/train/images")
images = list(image_dir.glob("*.jpg"))

if not images:
    raise FileNotFoundError(f"No JPG images found in {image_dir.resolve()}")

image_path = images[0]

print("Test image:", image_path)

# Load a small pretrained YOLO detection model
model = YOLO("yolo11n.pt")

# Run inference
results = model.predict(
    source=str(image_path),
    imgsz=640,
    device="cpu",
    save=True,
    verbose=True,
)

print("\nInference completed.")
print("Annotated results saved under the runs/detect folder.")
