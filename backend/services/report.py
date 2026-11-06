"""PDF report generation with ReportLab."""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

import config
import database

NAVY = colors.HexColor("#0B1426")
CYAN = colors.HexColor("#0E8FA3")
GRAY = colors.HexColor("#5B677D")
LIGHT = colors.HexColor("#EEF2F7")
LINE = colors.HexColor("#D3DAE5")

DISCLAIMER = (
    "PCB-AI-Inspector is an experimental decision-support tool. Detections are model "
    "predictions and may include false positives or miss real defects. The model "
    "recognises only six defect types (mouse bite, spur, missing hole, short, open "
    "circuit and spurious copper); other faults are not covered. A result of "
    "\"No Visible Defect Detected\" does not prove a board is defect-free. Confirm "
    "all findings by manual or physical inspection before making any quality, safety "
    "or manufacturing decision."
)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=20, textColor=NAVY, alignment=TA_LEFT, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=base["Normal"], fontSize=10, textColor=GRAY, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12.5, textColor=NAVY, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13.5, textColor=colors.HexColor("#222B3A")),
        "small": ParagraphStyle("sm", parent=base["Normal"], fontSize=8.5, leading=12, textColor=GRAY),
        "cell": ParagraphStyle("c", parent=base["Normal"], fontSize=9, leading=12),
        "cellb": ParagraphStyle("cb", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12),
    }


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _image_for_pdf(path: Path, max_side: int = 1400) -> BytesIO:
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((max_side, max_side))
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
    out.seek(0)
    return out


def _fit(buffer: BytesIO, max_w: float, max_h: float) -> RLImage:
    with Image.open(buffer) as img:
        w, h = img.size
    buffer.seek(0)
    scale = min(max_w / w, max_h / h)
    return RLImage(buffer, width=w * scale, height=h * scale)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(18 * mm, 10 * mm, "PCB-AI-Inspector - experimental AI decision-support report")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report(inspection_id: str, payload: dict) -> Path:
    """Build (or rebuild) the PDF for an inspection and return its path."""
    row = database.get_inspection(inspection_id)
    if row is None:
        raise FileNotFoundError(inspection_id)

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = config.REPORTS_DIR / f"{inspection_id}.pdf"
    st = _styles()
    story = []
    content_w = A4[0] - 36 * mm

    created = datetime.fromisoformat(payload["created_at"])
    created_text = created.strftime("%d %b %Y, %H:%M:%S UTC")

    story += [
        Paragraph("PCB-AI-Inspector", st["title"]),
        Paragraph("PCB Defect Inspection Report", st["sub"]),
    ]

    info = [
        [Paragraph("Inspection ID", st["cellb"]), Paragraph(payload["inspection_id"], st["cell"])],
        [Paragraph("Date and time", st["cellb"]), Paragraph(created_text, st["cell"])],
        [Paragraph("Original filename", st["cellb"]), Paragraph(_escape(payload["filename"]), st["cell"])],
        [Paragraph("Image", st["cellb"]),
         Paragraph(f'{payload["image"]["width"]} x {payload["image"]["height"]} px, {payload["image"]["format"]}', st["cell"])],
        [Paragraph("Model", st["cellb"]),
         Paragraph(f'{payload["model"]["name"]} (weights: {payload["model"]["weights"]})', st["cell"])],
    ]
    t = Table(info, colWidths=[38 * mm, content_w - 38 * mm])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    # Conclusion
    concl = payload["conclusion"]
    box = Table([[Paragraph(f'<b>Inspection conclusion: {concl["label"]}</b>', st["body"])],
                 [Paragraph(concl["message"], st["body"])]], colWidths=[content_w])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 3, CYAN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [Spacer(1, 10), box]

    # Images
    half = (content_w - 6 * mm) / 2
    original = _fit(_image_for_pdf(Path(row["original_path"])), half, 95 * mm)
    annotated = _fit(_image_for_pdf(Path(row["annotated_path"])), half, 95 * mm)
    imgs = Table(
        [[Paragraph("<b>Original PCB image</b>", st["body"]), Paragraph("<b>Annotated PCB image</b>", st["body"])],
         [original, annotated]],
        colWidths=[half + 3 * mm, half + 3 * mm])
    imgs.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("BOTTOMPADDING", (0, 0), (-1, 0), 4)]))
    story += [Paragraph("Images", st["h2"]), imgs]

    # Detections
    story.append(Paragraph("Detected defects", st["h2"]))
    detections = payload["detections"]
    story.append(Paragraph(
        f'Total detections: <b>{payload["total_detections"]}</b> &nbsp;|&nbsp; '
        f'Unique defect classes: <b>{payload["unique_classes"]}</b>', st["body"]))
    story.append(Spacer(1, 4))
    if detections:
        rows = [["#", "Defect", "Confidence", "Bounding box (x1, y1, x2, y2) px"]]
        for d in detections:
            b = d["bounding_box"]
            rows.append([str(d["id"]), _pretty(d["defect"]), f'{d["confidence"] * 100:.1f}%',
                         f'{b["x1"]:.0f}, {b["y1"]:.0f}, {b["x2"]:.0f}, {b["y2"]:.0f}'])
        dt = Table(rows, colWidths=[10 * mm, 45 * mm, 28 * mm, content_w - 83 * mm], repeatRows=1)
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(dt)
    else:
        story.append(Paragraph("No defects from the six supported classes were reported above the "
                               f'{int(config.CONF_THRESHOLD * 100)}% confidence threshold.', st["body"]))
    if payload["low_confidence_candidates"]:
        story += [Spacer(1, 4), Paragraph(
            f'{payload["low_confidence_candidates"]} low-confidence candidate(s) fell below the reporting '
            "threshold and are not listed as detections.", st["small"])]

    # Model + limitations
    ev = payload["evaluation"]
    model_rows = [
        [Paragraph("Model", st["cellb"]), Paragraph(payload["model"]["name"], st["cell"])],
        [Paragraph("Supported classes", st["cellb"]),
         Paragraph(", ".join(_pretty(c) for c in payload["model"]["classes"]), st["cell"])],
        [Paragraph("Settings", st["cellb"]),
         Paragraph(f'Input size {payload["model"]["image_size"]} px, reporting threshold '
                   f'{int(payload["model"]["confidence_threshold"] * 100)}% confidence', st["cell"])],
        [Paragraph("Held-out test results", st["cellb"]),
         Paragraph(f'Precision {ev["precision"] * 100:.1f}%, Recall {ev["recall"] * 100:.1f}%, '
                   f'mAP@50 {ev["map50"] * 100:.1f}%, mAP@50-95 {ev["map50_95"] * 100:.1f}%. '
                   f'{ev["test_set"]}.', st["cell"])],
    ]
    mt = Table(model_rows, colWidths=[38 * mm, content_w - 38 * mm])
    mt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(KeepTogether([
        Paragraph("Model information", st["h2"]), mt, Spacer(1, 4),
        Paragraph(_escape(ev["note"]), st["small"]),
        Paragraph("Limitations and disclaimer", st["h2"]), Paragraph(DISCLAIMER, st["body"]),
    ]))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"PCB Inspection Report {inspection_id}", author="PCB-AI-Inspector")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return pdf_path


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
