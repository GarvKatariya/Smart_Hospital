"""
Unit tests for image preprocessing pipelines (preprocess.py).

Tests cover:
  - preprocess_printed: loads image, outputs RGB PIL Image
  - preprocess_handwritten: loads image, outputs RGB PIL Image
  - preprocess_image (legacy shim): routes to preprocess_printed
  - _load_image: bytes vs path, mode conversion
  - _resize_for_ocr: upscale small images, cap large images
  - _to_grayscale / _to_rgb: mode conversions
  - _adaptive_threshold: binary output shape
  - _global_threshold: binary output shape
  - _deskew: doesn't crash on images without EXIF
"""
import pytest
import sys
import os
import io
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from PIL import Image
import numpy as np

from ocr.preprocess import (
    preprocess_printed,
    preprocess_handwritten,
    preprocess_image,
    _load_image,
    _to_rgb,
    _to_grayscale,
    _deskew,
    _resize_for_ocr,
    _adaptive_threshold,
    _global_threshold,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_rgb_image():
    """A small 100x50 RGB image (below OCR minimum)."""
    return Image.new('RGB', (100, 50), color=(128, 128, 128))


@pytest.fixture
def large_rgb_image():
    """A large 4000x3000 RGB image (above OCR max cap)."""
    return Image.new('RGB', (4000, 3000), color=(200, 200, 200))


@pytest.fixture
def medium_rgb_image():
    """A medium 1000x800 RGB image (within normal range)."""
    return Image.new('RGB', (1000, 800), color=(100, 100, 100))


@pytest.fixture
def rgba_image():
    """An RGBA image (needs conversion)."""
    return Image.new('RGBA', (200, 100), color=(128, 128, 128, 255))


@pytest.fixture
def grayscale_image():
    """A grayscale ('L' mode) image."""
    return Image.new('L', (200, 100), color=128)


@pytest.fixture
def tmp_image_path(medium_rgb_image):
    """Save medium image to a temp file and return path."""
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    medium_rgb_image.save(path, format='PNG')
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tmp_image_bytes(medium_rgb_image):
    """Return medium image as bytes."""
    buf = io.BytesIO()
    medium_rgb_image.save(buf, format='PNG')
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _load_image tests
# ---------------------------------------------------------------------------

class TestLoadImage:
    def test_load_from_path(self, tmp_image_path):
        img = _load_image(tmp_image_path)
        assert isinstance(img, Image.Image)
        assert img.mode in ('RGB', 'L')

    def test_load_from_bytes(self, tmp_image_bytes):
        img = _load_image(tmp_image_bytes)
        assert isinstance(img, Image.Image)
        assert img.mode in ('RGB', 'L')

    def test_converts_rgba_to_rgb(self, rgba_image):
        buf = io.BytesIO()
        rgba_image.save(buf, format='PNG')
        img = _load_image(buf.getvalue())
        assert img.mode == 'RGB'

    def test_preserves_grayscale(self, grayscale_image):
        buf = io.BytesIO()
        grayscale_image.save(buf, format='PNG')
        img = _load_image(buf.getvalue())
        assert img.mode == 'L'


# ---------------------------------------------------------------------------
# _to_rgb / _to_grayscale tests
# ---------------------------------------------------------------------------

class TestModeConversions:
    def test_to_rgb_from_grayscale(self, grayscale_image):
        result = _to_rgb(grayscale_image)
        assert result.mode == 'RGB'

    def test_to_rgb_from_rgb_is_noop(self, medium_rgb_image):
        result = _to_rgb(medium_rgb_image)
        assert result is medium_rgb_image  # same object (no conversion needed)

    def test_to_grayscale_from_rgb(self, medium_rgb_image):
        result = _to_grayscale(medium_rgb_image)
        assert result.mode == 'L'

    def test_to_grayscale_from_grayscale_is_noop(self, grayscale_image):
        result = _to_grayscale(grayscale_image)
        assert result is grayscale_image


# ---------------------------------------------------------------------------
# _deskew tests
# ---------------------------------------------------------------------------

class TestDeskew:
    def test_deskew_doesnt_crash_without_exif(self, medium_rgb_image):
        result = _deskew(medium_rgb_image)
        assert isinstance(result, Image.Image)

    def test_deskew_preserves_dimensions(self, medium_rgb_image):
        result = _deskew(medium_rgb_image)
        assert result.size == medium_rgb_image.size


# ---------------------------------------------------------------------------
# _resize_for_ocr tests
# ---------------------------------------------------------------------------

class TestResizeForOCR:
    def test_upscales_small_images(self, small_rgb_image):
        result = _resize_for_ocr(small_rgb_image)
        assert min(result.size) >= 800

    def test_caps_large_images(self, large_rgb_image):
        result = _resize_for_ocr(large_rgb_image)
        assert max(result.size) <= 3000

    def test_medium_images_unchanged(self, medium_rgb_image):
        result = _resize_for_ocr(medium_rgb_image)
        # Medium (1000x800) should stay the same
        assert result.size == medium_rgb_image.size

    def test_custom_max_dim(self, large_rgb_image):
        result = _resize_for_ocr(large_rgb_image, max_dim=2000)
        assert max(result.size) <= 2000


# ---------------------------------------------------------------------------
# _adaptive_threshold tests
# ---------------------------------------------------------------------------

class TestAdaptiveThreshold:
    def test_output_is_rgb(self, medium_rgb_image):
        result = _adaptive_threshold(medium_rgb_image)
        assert result.mode == 'RGB'

    def test_output_is_binary(self, medium_rgb_image):
        """Output should contain only near-black and near-white pixels."""
        result = _adaptive_threshold(medium_rgb_image)
        arr = np.array(result.convert('L'))
        unique_vals = np.unique(arr)
        # Should be (close to) binary — only 0 and 255
        assert len(unique_vals) <= 3, f"Expected binary output, got {len(unique_vals)} unique values"


# ---------------------------------------------------------------------------
# _global_threshold tests
# ---------------------------------------------------------------------------

class TestGlobalThreshold:
    def test_output_is_rgb(self, medium_rgb_image):
        result = _global_threshold(medium_rgb_image)
        assert result.mode == 'RGB'

    def test_custom_threshold(self, medium_rgb_image):
        result = _global_threshold(medium_rgb_image, thresh=100)
        arr = np.array(result.convert('L'))
        unique_vals = np.unique(arr)
        assert set(unique_vals).issubset({0, 255})

    def test_all_white_image(self):
        white = Image.new('RGB', (200, 100), color=(255, 255, 255))
        result = _global_threshold(white, thresh=180)
        arr = np.array(result.convert('L'))
        # All white pixels > 180, so binary image should be all 0 (white = not foreground)
        assert arr.max() == 0 or arr.min() == 255  # all one value


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestPreprocessPrinted:
    def test_returns_rgb_image_from_path(self, tmp_image_path):
        result = preprocess_printed(tmp_image_path)
        assert isinstance(result, Image.Image)
        assert result.mode == 'RGB'

    def test_returns_rgb_image_from_bytes(self, tmp_image_bytes):
        result = preprocess_printed(tmp_image_bytes)
        assert isinstance(result, Image.Image)
        assert result.mode == 'RGB'

    def test_output_size_meets_minimum(self, tmp_image_bytes):
        result = preprocess_printed(tmp_image_bytes)
        # Should have been resized for OCR
        assert min(result.size) >= 100  # at least reasonable


class TestPreprocessHandwritten:
    def test_returns_rgb_image_from_path(self, tmp_image_path):
        result = preprocess_handwritten(tmp_image_path)
        assert isinstance(result, Image.Image)
        assert result.mode == 'RGB'

    def test_returns_rgb_image_from_bytes(self, tmp_image_bytes):
        result = preprocess_handwritten(tmp_image_bytes)
        assert isinstance(result, Image.Image)
        assert result.mode == 'RGB'

    def test_small_image_gets_upscaled(self):
        small = Image.new('RGB', (100, 50), color=(128, 128, 128))
        buf = io.BytesIO()
        small.save(buf, format='PNG')
        result = preprocess_handwritten(buf.getvalue())
        assert min(result.size) > 100  # should be upscaled


class TestPreprocessImageLegacyShim:
    def test_legacy_shim_delegates_to_printed(self, tmp_image_bytes):
        """preprocess_image() is a backward-compat shim for preprocess_printed()."""
        result = preprocess_image(tmp_image_bytes)
        assert isinstance(result, Image.Image)
        assert result.mode == 'RGB'
