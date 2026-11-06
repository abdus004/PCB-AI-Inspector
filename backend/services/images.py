"""Image validation helpers: checks the real image content, not just the name."""
import struct
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.JpegImagePlugin import JpegImageFile
from PIL.PngImagePlugin import PngImageFile
from PIL.WebPImagePlugin import WebPImageFile

import config


_PLUGINS = {"JPEG": JpegImageFile, "PNG": PngImageFile, "WEBP": WebPImageFile}


class ImageValidationError(Exception):
    """Raised when an upload is not an acceptable image. Carries an HTTP status."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ValidatedImage:
    image: Image.Image      # RGB, EXIF orientation applied (what the model sees)
    raw_bytes: bytes        # exact bytes the user uploaded
    format: str             # "JPEG", "PNG" or "WEBP"
    extension: str          # "jpg", "png" or "webp"
    width: int
    height: int


def _sniff_format(contents: bytes) -> str | None:
    """Identify JPEG / PNG / WEBP from the file's first bytes (not from its name)."""
    if contents[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if contents[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return "WEBP"
    return None


def _open_as(fmt: str, contents: bytes) -> Image.Image:
    """Open with the format-specific Pillow class.

    This deliberately avoids `Image.open`, which Ultralytics monkey-patches (it can try to
    auto-install HEIF support when a file cannot be identified).
    """
    plugin = _PLUGINS[fmt]
    return plugin(BytesIO(contents))


_DECODE_ERRORS = (
    UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError,
    Image.DecompressionBombError, struct.error,
)


def validate_image_bytes(contents: bytes) -> ValidatedImage:
    if not contents:
        raise ImageValidationError("The uploaded file is empty.")
    if len(contents) > config.MAX_UPLOAD_BYTES:
        raise ImageValidationError("Image must be 10 MB or smaller.", 413)

    fmt = _sniff_format(contents)
    if fmt is None:
        raise ImageValidationError(
            "Unsupported or invalid file. Please upload a JPG, JPEG, PNG or WEBP image."
        )

    # Pass 1: read the header and check the dimensions before decoding pixels.
    try:
        probe = _open_as(fmt, contents)
        width, height = probe.size
        if width * height > config.MAX_IMAGE_PIXELS:
            raise ImageValidationError("Image dimensions are too large.", 413)
        probe.close()
    except ImageValidationError:
        raise
    except _DECODE_ERRORS:
        raise ImageValidationError(
            "Invalid or corrupted image file. Please upload a valid JPG, PNG or WEBP image."
        )

    # Pass 2: fully decode (catches truncated or damaged files).
    try:
        img = _open_as(fmt, contents)
        img.load()
        image = ImageOps.exif_transpose(img).convert("RGB")
        img.close()
    except _DECODE_ERRORS:
        raise ImageValidationError("The image appears to be corrupted and could not be decoded.")

    if image.width < 16 or image.height < 16:
        raise ImageValidationError("Image is too small to inspect.")

    return ValidatedImage(
        image=image,
        raw_bytes=contents,
        format=fmt,
        extension=config.ALLOWED_FORMATS[fmt],
        width=image.width,
        height=image.height,
    )


def make_thumbnail_bytes(image: Image.Image, size: int = 256) -> bytes:
    thumb = image.copy()
    thumb.thumbnail((size, size))
    out = BytesIO()
    thumb.save(out, format="JPEG", quality=80)
    return out.getvalue()
