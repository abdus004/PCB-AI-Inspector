"""The core inspection workflow: validate -> YOLO once -> annotate -> save."""
import json
import secrets
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import config
import database
from services import model as model_service
from services.images import ValidatedImage, make_thumbnail_bytes

STATUS_DEFECTS = "defects_detected"
STATUS_NONE = "no_visible_defects_detected"
STATUS_INCONCLUSIVE = "inconclusive"

CONCLUSIONS = {
    STATUS_DEFECTS: (
        "Potential Defect Detected",
        "The model found one or more possible defects. Review each detection "
        "and confirm it by physical or manual inspection.",
    ),
    STATUS_NONE: (
        "No Visible Defect Detected",
        "The model did not detect any of its six supported defect types in this "
        "image. This does not prove the board is defect-free.",
    ),
    STATUS_INCONCLUSIVE: (
        "Inconclusive",
        "The result cannot be relied on: the image is low resolution and/or the "
        "model found only low-confidence candidates. Try a sharper, closer image "
        "and inspect manually.",
    ),
}


def conclusion_for(status: str) -> dict:
    label, message = CONCLUSIONS[status]
    return {"status": status, "label": label, "message": message}


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #
def extract_detections(result, conf_threshold: float) -> tuple[list[dict], int]:
    """Turn a YOLO result into (detections, weak_candidate_count)."""
    names = model_service.class_names()
    rows = []
    weak = 0
    for index, box in enumerate(result.boxes):
        confidence = float(box.conf[0])
        if confidence < conf_threshold:
            weak += 1
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        rows.append((index, {
            "defect": names[int(box.cls[0])],
            "confidence": round(confidence, 4),
            "bounding_box": {
                "x1": round(x1, 2), "y1": round(y1, 2),
                "x2": round(x2, 2), "y2": round(y2, 2),
            },
        }))
    rows.sort(key=lambda r: r[1]["confidence"], reverse=True)
    detections = []
    for number, (_, det) in enumerate(rows, start=1):
        detections.append({"id": number, **det})
    return detections, weak


def decide_status(detections: list, weak: int, width: int, height: int) -> str:
    if detections:
        return STATUS_DEFECTS
    if weak > 0 or min(width, height) < config.MIN_RELIABLE_SIDE:
        return STATUS_INCONCLUSIVE
    return STATUS_NONE


def summarise_classes(detections: list) -> list[dict]:
    summary: dict[str, dict] = {}
    for det in detections:
        entry = summary.setdefault(det["defect"], {"defect": det["defect"], "count": 0, "max_confidence": 0.0})
        entry["count"] += 1
        entry["max_confidence"] = max(entry["max_confidence"], det["confidence"])
    return sorted(summary.values(), key=lambda e: e["max_confidence"], reverse=True)


def annotated_jpeg_bytes(result) -> bytes:
    """Legacy /predict/annotated: Ultralytics' own drawing of every box in the result."""
    plotted = result.plot()                      # BGR numpy array
    out = BytesIO()
    Image.fromarray(plotted[:, :, ::-1]).save(out, format="JPEG", quality=92)
    return out.getvalue()


_BOX_COLORS = [
    (79, 214, 230), (242, 176, 76), (129, 230, 120), (236, 112, 140), (160, 140, 255), (250, 226, 90),
]


def render_annotated_jpeg(image: Image.Image, detections: list[dict]) -> bytes:
    """Draw the reported detections onto a copy of the image.

    Uses only Pillow and the detections already extracted from the single YOLO run,
    so it does not depend on Ultralytics plotting internals and works for zero detections.
    """
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    line = max(2, round(min(canvas.size) / 220))
    font_size = max(12, round(min(canvas.size) / 38))
    try:
        font = ImageFont.load_default(size=font_size)
    except TypeError:                              # very old Pillow
        font = ImageFont.load_default()

    class_order: dict[str, int] = {}
    for det in detections:
        color = _BOX_COLORS[class_order.setdefault(det["defect"], len(class_order)) % len(_BOX_COLORS)]
        b = det["bounding_box"]
        box = (b["x1"], b["y1"], b["x2"], b["y2"])
        draw.rectangle(box, outline=color, width=line)
        text = f'#{det["id"]} {det["defect"].replace("_", " ")} {det["confidence"] * 100:.0f}%'
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        tw, th = right - left, bottom - top
        pad = max(2, font_size // 5)
        label_h = th + 2 * pad
        ty = box[1] - label_h if box[1] - label_h >= 0 else box[1]
        tx = min(max(0, box[0]), max(0, canvas.width - tw - 2 * pad))
        draw.rectangle((tx, ty, tx + tw + 2 * pad, ty + label_h), fill=color)
        draw.text((tx + pad - left, ty + pad - top), text, fill=(8, 12, 24), font=font)

    out = BytesIO()
    canvas.save(out, format="JPEG", quality=92)
    return out.getvalue()


def model_description() -> dict:
    return {
        "name": config.MODEL_NAME,
        "weights": config.MODEL_PATH.name,
        "image_size": config.IMAGE_SIZE,
        "confidence_threshold": config.CONF_THRESHOLD,
        "classes": [v for _, v in sorted(model_service.class_names().items())],
    }


# --------------------------------------------------------------------------- #
# Legacy endpoints (/predict and /predict/annotated) -- behaviour preserved
# --------------------------------------------------------------------------- #
def predict_legacy(validated: ValidatedImage, filename: str) -> dict:
    result = model_service.run_inference(validated.image, config.CONF_THRESHOLD)
    detections, _ = extract_detections(result, config.CONF_THRESHOLD)
    return {
        "filename": filename,
        "status": STATUS_DEFECTS if detections else STATUS_NONE,
        "total_defects": len(detections),
        "detections": [
            {"defect": d["defect"], "confidence": d["confidence"], "bounding_box": d["bounding_box"]}
            for d in detections
        ],
    }


def predict_annotated_legacy(validated: ValidatedImage) -> bytes:
    result = model_service.run_inference(validated.image, config.CONF_THRESHOLD)
    return annotated_jpeg_bytes(result)


# --------------------------------------------------------------------------- #
# Unified inspection
# --------------------------------------------------------------------------- #
def _new_inspection_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"PCB-{stamp}-{secrets.token_hex(3).upper()}"


def _safe_name(name: Optional[str]) -> str:
    cleaned = Path(name or "").name.strip()
    return (cleaned or "uploaded-image")[:200]


def run_inspection(validated: ValidatedImage, filename: Optional[str]) -> dict:
    # 1) YOLO runs exactly once. A lower threshold lets us notice weak candidates;
    #    only detections >= CONF_THRESHOLD are reported (same as /predict).
    result = model_service.run_inference(validated.image, config.WEAK_CONF_THRESHOLD)
    detections, weak = extract_detections(result, config.CONF_THRESHOLD)
    status = decide_status(detections, weak, validated.width, validated.height)

    # 2) Annotated image drawn from the same detections (no second model run).
    annotated_bytes = render_annotated_jpeg(validated.image, detections)
    thumb_bytes = make_thumbnail_bytes(validated.image)

    # 3) Save files, then the database row. Clean up files if anything fails.
    for folder in (config.ORIGINALS_DIR, config.ANNOTATED_DIR, config.THUMBNAILS_DIR):
        folder.mkdir(parents=True, exist_ok=True)

    inspection_id = _new_inspection_id()
    original_path = config.ORIGINALS_DIR / f"{inspection_id}.{validated.extension}"
    annotated_path = config.ANNOTATED_DIR / f"{inspection_id}.jpg"
    thumb_path = config.THUMBNAILS_DIR / f"{inspection_id}.jpg"
    written = [original_path, annotated_path, thumb_path]

    try:
        original_path.write_bytes(validated.raw_bytes)
        annotated_path.write_bytes(annotated_bytes)
        thumb_path.write_bytes(thumb_bytes)

        database.insert_inspection({
            "id": inspection_id,
            "original_filename": _safe_name(filename),
            "original_path": str(original_path),
            "annotated_path": str(annotated_path),
            "thumbnail_path": str(thumb_path),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "detections_json": json.dumps(detections),
            "total_detections": len(detections),
            "unique_classes": len({d["defect"] for d in detections}),
            "status": status,
            "model_json": json.dumps(model_description()),
            "image_json": json.dumps({
                "width": validated.width,
                "height": validated.height,
                "format": validated.format,
                "size_bytes": len(validated.raw_bytes),
            }),
            "low_confidence": weak,
        })
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise

    return get_inspection_payload(inspection_id)


# --------------------------------------------------------------------------- #
# Reading stored inspections
# --------------------------------------------------------------------------- #
def _urls(inspection_id: str) -> dict:
    base = f"/inspections/{inspection_id}"
    return {
        "original": f"{base}/original",
        "annotated": f"{base}/annotated",
        "thumbnail": f"{base}/thumbnail",
        "report": f"{base}/report",
    }


def get_inspection_payload(inspection_id: str) -> Optional[dict]:
    row = database.get_inspection(inspection_id)
    if row is None:
        return None
    detections = row["detections"]
    return {
        "inspection_id": row["id"],
        "filename": row["original_filename"],
        "created_at": row["created_at"],
        "status": row["status"],
        "conclusion": conclusion_for(row["status"]),
        "total_detections": row["total_detections"],
        "total_defects": row["total_detections"],       # compatibility with /predict
        "unique_classes": row["unique_classes"],
        "class_summary": summarise_classes(detections),
        "detections": detections,
        "low_confidence_candidates": row["low_confidence"],
        "image": row["image"],
        "model": row["model"],
        "evaluation": config.EVALUATION,
        "urls": _urls(row["id"]),
    }


def list_payload(limit: int, offset: int) -> dict:
    rows, total = database.list_inspections(limit, offset)
    items = []
    for row in rows:
        detections = json.loads(row["detections_json"])
        items.append({
            "inspection_id": row["id"],
            "filename": row["original_filename"],
            "created_at": row["created_at"],
            "status": row["status"],
            "conclusion": conclusion_for(row["status"]),
            "total_detections": row["total_detections"],
            "unique_classes": row["unique_classes"],
            "defects": sorted({d["defect"] for d in detections}),
            "urls": _urls(row["id"]),
        })
    return {"total": total, "items": items}


def _inside_storage(path: Path) -> bool:
    try:
        path.resolve().relative_to(config.STORAGE_DIR.resolve())
        return True
    except ValueError:
        return False


def delete_inspection(inspection_id: str) -> bool:
    """Remove the DB row and its files (only files inside the storage folder)."""
    row = database.get_inspection(inspection_id)
    if row is None:
        return False
    database.delete_inspection(inspection_id)
    candidates = [
        Path(row["original_path"]),
        Path(row["annotated_path"]),
        Path(row["thumbnail_path"]) if row["thumbnail_path"] else None,
        config.REPORTS_DIR / f"{inspection_id}.pdf",
    ]
    for path in candidates:
        if path is not None and _inside_storage(path):
            path.unlink(missing_ok=True)
    return True
