"""
Image preprocessing pipelines for medical document OCR.

Two separate pipelines:
  - preprocess_printed(image_bytes) → for lab reports, printed prescriptions
  - preprocess_handwritten(image_bytes) → for handwritten prescriptions, clinical notes

Neither pipeline is applied universally — the caller selects based on document_type.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_image(source: bytes | str) -> Image.Image:
    """Load an image from bytes or a file path."""
    if isinstance(source, (bytes, bytearray)):
        img = Image.open(io.BytesIO(source))
    else:
        img = Image.open(source)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _to_grayscale(img: Image.Image) -> Image.Image:
    if img.mode != "L":
        return img.convert("L")
    return img


def _deskew(img: Image.Image) -> Image.Image:
    """
    Attempt to deskew via the image's EXIF orientation (rotation artifacts
    from mobile cameras).  Full warp-based deskew would require cv2 which is
    optional, so we do a best-effort PIL-only version.
    """
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img


def _resize_for_ocr(img: Image.Image, max_dim: int = 3000) -> Image.Image:
    """Upscale small images (< 800 px on either side) for better OCR accuracy,
    and cap extremely large images to avoid memory issues."""
    w, h = img.size
    # Upscale if too small
    min_dim = min(w, h)
    if min_dim < 800:
        scale = 800 / min_dim
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        w, h = new_w, new_h
    # Cap if too large
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def _adaptive_threshold(img: Image.Image) -> Image.Image:
    """
    Apply adaptive (local) binarisation via numpy — suitable for printed
    documents with uneven lighting.  Falls back to global Otsu-style
    threshold if numpy is not available.
    """
    gray = _to_grayscale(img)
    arr = np.array(gray, dtype=np.uint8)

    # Block-size for local mean (must be odd)
    block = max(31, (arr.shape[1] // 40) | 1)
    # Pad to handle borders
    pad = block // 2
    padded = np.pad(arr, pad, mode='reflect')

    # Compute local mean using a uniform filter (fast approximation)
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(padded.astype(np.float32), size=block)
    local_mean = local_mean[pad:-pad, pad:-pad]

    # Binarise with dark text as black (0) and the paper as white (255).
    C = 10  # constant subtracted from mean
    binary = (arr >= (local_mean - C)).astype(np.uint8) * 255

    return Image.fromarray(binary, mode='L').convert('RGB')


def _global_threshold(img: Image.Image, thresh: int = 180) -> Image.Image:
    """Simple global threshold — faster fallback for adaptive threshold."""
    gray = np.array(_to_grayscale(img), dtype=np.uint8)
    # Keep the conventional black-text-on-white-paper polarity expected by OCR.
    binary = ((gray >= thresh) * 255).astype(np.uint8)
    return Image.fromarray(binary, mode='L').convert('RGB')


# ---------------------------------------------------------------------------
# Public pipelines
# ---------------------------------------------------------------------------

def preprocess_printed(source: bytes | str) -> Image.Image:
    """
    Pipeline optimised for printed medical documents:
    lab reports, diagnostic printouts, typeset prescriptions.

    Steps:
    1. Load + EXIF-correct rotation
    2. Resize for OCR resolution
    3. Convert to grayscale
    4. Boost contrast moderately
    5. Apply adaptive binarisation (handles uneven lighting / shadows)
    6. Mild sharpening

    Why: Printed text has clear, uniform strokes.  Adaptive thresholding
    removes background gradients from phone photography without harming
    the characters.  We do NOT apply heavy blur or noise reduction because
    that blurs thin printed characters.
    """
    img = _load_image(source)
    img = _deskew(img)
    img = _resize_for_ocr(img)
    img = _to_grayscale(img)

    # Moderate contrast boost
    img = ImageEnhance.Contrast(img.convert('RGB')).enhance(1.3)
    img = _to_grayscale(img)

    # Adaptive threshold
    try:
        img = _adaptive_threshold(img.convert('RGB'))
    except Exception as exc:
        logger.warning(f"Adaptive threshold failed ({exc}), falling back to global")
        img = _global_threshold(img)

    # Light sharpening
    img = img.filter(ImageFilter.SHARPEN)
    return img.convert('RGB')


def preprocess_handwritten(source: bytes | str) -> Image.Image:
    """
    Pipeline optimised for handwritten prescriptions and clinical notes.

    Steps:
    1. Load + EXIF-correct rotation
    2. Resize for OCR resolution
    3. Convert to grayscale
    4. Gentle contrast enhancement (NOT aggressive — preserves thin strokes)
    5. Very mild Gaussian blur to reduce noise WITHOUT binarising
       (binarisation destroys cursive stroke connectivity)
    6. Brightness normalisation

    Why: Handwritten strokes vary in width, pressure and direction.
    Aggressive thresholding breaks connected letters into fragments.
    Instead we enhance contrast softly and let PaddleOCR handle the
    recognition without forcing a binary image.
    """
    img = _load_image(source)
    img = _deskew(img)
    img = _resize_for_ocr(img)
    img = _to_grayscale(img)

    # Gentle contrast — 1.2× only
    img_rgb = img.convert('RGB')
    img_rgb = ImageEnhance.Contrast(img_rgb).enhance(1.2)
    img_rgb = ImageEnhance.Sharpness(img_rgb).enhance(1.1)

    # Reduce small noise with a very light smooth (not blur)
    img_rgb = img_rgb.filter(ImageFilter.SMOOTH)

    # Normalise brightness so dark-background photos don't confuse OCR
    gray = _to_grayscale(img_rgb)
    arr = np.array(gray, dtype=np.float32)
    p5, p95 = np.percentile(arr, 5), np.percentile(arr, 95)
    if p95 > p5:
        arr = np.clip((arr - p5) / (p95 - p5) * 255, 0, 255).astype(np.uint8)
        gray = Image.fromarray(arr, mode='L')
        img_rgb = gray.convert('RGB')

    return img_rgb


# ---------------------------------------------------------------------------
# Legacy shim — keeps old callers working
# ---------------------------------------------------------------------------

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """Backward-compatible shim — defaults to printed pipeline."""
    return preprocess_printed(image_bytes)
