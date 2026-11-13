"""PCB AI Inspector API.

Existing endpoints kept:  /  /health  /model-info  /predict  /predict/annotated
New endpoints:            /inspect  /inspections  /inspections/{id}[...]
"""
import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

import config
import database
from services import inspection as inspection_service
from services import model as model_service
from services import report as report_service
from services.images import ImageValidationError, ValidatedImage, validate_image_bytes

logger = logging.getLogger("pcb-ai-inspector")

# Decoding + inference on several large images at once multiplies peak memory, so by default
# requests are processed one at a time (extra requests simply wait their turn).
_gate = asyncio.Semaphore(int(os.environ.get("PCB_MAX_CONCURRENT", "1")))

INSPECTION_ID_PATTERN = re.compile(r"^PCB-\d{8}-[0-9A-F]{6}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    for folder in (config.ORIGINALS_DIR, config.ANNOTATED_DIR, config.REPORTS_DIR, config.THUMBNAILS_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    database.init_db()
    model_service.load_model()      # fails fast with a clear message if best.pt is missing
    yield


app = FastAPI(
    title="PCB AI Inspector API",
    description="AI-powered PCB defect detection system",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def read_and_validate(file: UploadFile) -> ValidatedImage:
    # Read at most limit+1 bytes so a huge upload cannot exhaust memory.
    contents = await file.read(config.MAX_UPLOAD_BYTES + 1)
    try:
        return await run_in_threadpool(validate_image_bytes, contents)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


async def run_safely(func, *args, what: str = "The inspection"):
    """Run blocking work in a thread. Unexpected errors become clean JSON 500s.

    (A bare unhandled exception would skip the CORS headers, and the browser
    would then report a confusing network error instead of the real message.)
    """
    try:
        return await run_in_threadpool(func, *args)
    except HTTPException:
        raise
    except Exception:
        logger.exception("%s failed", what)
        raise HTTPException(
            status_code=500,
            detail=f"{what} failed because of an unexpected server error. Please try again.",
        )


def get_payload_or_404(inspection_id: str) -> dict:
    if not INSPECTION_ID_PATTERN.match(inspection_id):
        raise HTTPException(status_code=404, detail="Inspection not found.")
    payload = inspection_service.get_inspection_payload(inspection_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return payload


# --------------------------------------------------------------------------- #
# Existing endpoints (unchanged response shapes)
# --------------------------------------------------------------------------- #
@app.get("/")
def home():
    return {"message": "PCB AI Inspector API is running!", "status": "success"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": model_service.is_loaded()}


@app.get("/model-info")
def model_info():
    names = model_service.class_names()
    return {
        "model": config.MODEL_NAME,
        "classes": names,
        "number_of_classes": len(names),
        "image_size": config.IMAGE_SIZE,
        "confidence_threshold": config.CONF_THRESHOLD,
        "evaluation": config.EVALUATION,
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    async with _gate:
        validated = await read_and_validate(file)
        return await run_safely(inspection_service.predict_legacy, validated, file.filename, what="The prediction")


@app.post("/predict/annotated")
async def predict_annotated(file: UploadFile = File(...)):
    async with _gate:
        validated = await read_and_validate(file)
        jpeg = await run_safely(inspection_service.predict_annotated_legacy, validated, what="The prediction")
    return StreamingResponse(BytesIO(jpeg), media_type="image/jpeg")


# --------------------------------------------------------------------------- #
# Unified inspection + history
# --------------------------------------------------------------------------- #
@app.post("/inspect", status_code=201)
async def inspect(file: UploadFile = File(...)):
    """Validate -> run YOLO once -> annotate -> save -> return full results."""
    async with _gate:
        validated = await read_and_validate(file)
        return await run_safely(inspection_service.run_inspection, validated, file.filename, what="The inspection")


@app.get("/inspections")
def list_inspections(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)):
    return inspection_service.list_payload(limit, offset)


@app.get("/inspections/{inspection_id}")
def get_inspection(inspection_id: str):
    return get_payload_or_404(inspection_id)


def _image_response(path_value: str, media_type: str) -> FileResponse:
    path = Path(path_value)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored image file is missing.")
    return FileResponse(path, media_type=media_type)


@app.get("/inspections/{inspection_id}/original")
def get_original(inspection_id: str):
    get_payload_or_404(inspection_id)
    row = database.get_inspection(inspection_id)
    media = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    ext = row["original_path"].rsplit(".", 1)[-1].lower()
    return _image_response(row["original_path"], media.get(ext, "application/octet-stream"))


@app.get("/inspections/{inspection_id}/annotated")
def get_annotated(inspection_id: str):
    get_payload_or_404(inspection_id)
    row = database.get_inspection(inspection_id)
    return _image_response(row["annotated_path"], "image/jpeg")


@app.get("/inspections/{inspection_id}/thumbnail")
def get_thumbnail(inspection_id: str):
    get_payload_or_404(inspection_id)
    row = database.get_inspection(inspection_id)
    if not row["thumbnail_path"]:
        raise HTTPException(status_code=404, detail="Thumbnail not available.")
    return _image_response(row["thumbnail_path"], "image/jpeg")


@app.get("/inspections/{inspection_id}/report")
async def get_report(inspection_id: str):
    payload = get_payload_or_404(inspection_id)
    pdf_path = config.REPORTS_DIR / f"{inspection_id}.pdf"
    if not pdf_path.is_file():
        try:
            pdf_path = await run_in_threadpool(report_service.build_report, inspection_id, payload)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Stored inspection images are missing, so the report cannot be created.")
        except Exception:
            logger.exception("Creating the PDF report failed")
            raise HTTPException(status_code=500, detail="The PDF report could not be created. Please try again.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"PCB-Inspection-Report-{inspection_id}.pdf",
    )


@app.delete("/inspections/{inspection_id}")
def delete_inspection(inspection_id: str):
    if not INSPECTION_ID_PATTERN.match(inspection_id):
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if not inspection_service.delete_inspection(inspection_id):
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return {"deleted": True, "inspection_id": inspection_id}
