
from pathlib import Path
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO

app = FastAPI(
    title="PCB AI Inspector API",
    description="AI-powered PCB defect detection system",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "best.pt"

model = YOLO(str(MODEL_PATH))

CLASS_NAMES = model.names


@app.get("/")
def home():
    return {
        "message": "PCB AI Inspector API is running!",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": True
    }


@app.get("/model-info")
def model_info():
    return {
        "model": "YOLO11n",
        "classes": CLASS_NAMES,
        "number_of_classes": len(CLASS_NAMES)
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG, PNG or WEBP image."
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Empty image uploaded.")

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")

    try:
        image = Image.open(BytesIO(contents)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Invalid image file.")

    results = model.predict(
        source=image,
        imgsz=640,
        conf=0.25,
        verbose=False
    )

    result = results[0]

    detections = []

    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detections.append({
            "defect": CLASS_NAMES[class_id],
            "confidence": round(confidence, 4),
            "bounding_box": {
                "x1": round(x1, 2),
                "y1": round(y1, 2),
                "x2": round(x2, 2),
                "y2": round(y2, 2)
            }
        })

    return {
        "filename": file.filename,
        "status": "defects_detected" if detections else "no_visible_defects_detected",
        "total_defects": len(detections),
        "detections": detections
    }


@app.post("/predict/annotated")
async def predict_annotated(file: UploadFile = File(...)):

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Unsupported image format.")

    contents = await file.read()

    if not contents or len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Invalid or oversized image.")

    try:
        image = Image.open(BytesIO(contents)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Invalid image file.")

    results = model.predict(
        source=image,
        imgsz=640,
        conf=0.25,
        verbose=False
    )

    annotated = results[0].plot()
    output = BytesIO()

    Image.fromarray(annotated[:, :, ::-1]).save(output, format="JPEG")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="image/jpeg"
    )
