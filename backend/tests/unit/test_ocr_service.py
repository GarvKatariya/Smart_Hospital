"""
Unit tests for OCRService — the OCR engine abstraction layer.

Tests cover:
  - Mock OCR fallback never fabricates document text or medical values
  - extract_text() returns the expected dict shape
  - document_type and writing_mode are preserved in output
  - Preprocessing dispatch (_preprocess) doesn't crash on missing files
  - Mock output contains an explicit unavailable note and no extracted data
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from ocr.paddleocr_service import OCRService


# ---------------------------------------------------------------------------
# Fixture: fresh OCR service instance (may use mock if no engine available)
# ---------------------------------------------------------------------------

@pytest.fixture
def ocr():
    return OCRService()


# ---------------------------------------------------------------------------
# Engine initialization
# ---------------------------------------------------------------------------

class TestOCRServiceInit:
    def test_engine_type_is_valid(self, ocr):
        assert ocr.engine_type in ('paddleocr', 'tesseract', 'mock')

    def test_mock_engine_has_no_engine_object(self):
        """When engine_type is 'mock', the engine attribute should be None."""
        svc = OCRService()
        if svc.engine_type == 'mock':
            assert svc.engine is None


# ---------------------------------------------------------------------------
# extract_text() — contract tests (shape of returned dict)
# ---------------------------------------------------------------------------

class TestExtractTextContract:
    """Test the shape of the return value regardless of engine backend."""

    @pytest.fixture
    def _create_dummy_image(self, tmp_path):
        """Create a minimal valid PNG for testing."""
        from PIL import Image
        img = Image.new('RGB', (200, 50), color='white')
        path = str(tmp_path / 'dummy.png')
        img.save(path)
        return path

    def test_returns_dict(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image)
        assert isinstance(result, dict)

    def test_has_required_keys(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image)
        required_keys = {'full_text', 'lines', 'average_confidence', 'engine',
                         'document_type', 'writing_mode'}
        assert required_keys.issubset(result.keys()), \
            f"Missing keys: {required_keys - result.keys()}"

    def test_document_type_preserved(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image, document_type='report')
        assert result['document_type'] == 'report'

    def test_writing_mode_preserved(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image, writing_mode='handwritten')
        assert result['writing_mode'] == 'handwritten'

    def test_prescription_type_preserved(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image, document_type='prescription',
                                  writing_mode='printed')
        assert result['document_type'] == 'prescription'
        assert result['writing_mode'] == 'printed'

    def test_lines_is_list(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image)
        assert isinstance(result['lines'], list)

    def test_average_confidence_is_float(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image)
        assert isinstance(result['average_confidence'], float)

    def test_confidence_in_valid_range(self, ocr, _create_dummy_image):
        result = ocr.extract_text(_create_dummy_image)
        assert 0.0 <= result['average_confidence'] <= 1.0


# ---------------------------------------------------------------------------
# Mock OCR engine
# ---------------------------------------------------------------------------

class TestMockOCR:
    def test_mock_extract_does_not_fabricate_document_text(self):
        svc = OCRService()
        # Force mock mode
        svc.engine_type = 'mock'
        svc.engine = None

        # Create a temp image
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (200, 50), 'white')
            img.save(f, format='PNG')
            path = f.name

        try:
            result = svc.extract_text(path)
            assert 'mock' in result['engine'].lower() or result['engine'] == 'mock'
            assert result['full_text'] == ''
            assert result['lines'] == []
            assert result['average_confidence'] == 0.0
        finally:
            os.unlink(path)

    def test_mock_includes_note_field(self):
        svc = OCRService()
        svc.engine_type = 'mock'
        svc.engine = None
        result = svc._mock_extract('/tmp/fake.png')
        assert 'note' in result
        assert 'No OCR engine available' in result['note']
        assert result['full_text'] == ''


# ---------------------------------------------------------------------------
# Preprocessing dispatch
# ---------------------------------------------------------------------------

class TestPreprocessingDispatch:
    def test_preprocess_falls_back_to_original_on_missing_file(self, ocr):
        """If the image file doesn't exist, preprocessing should gracefully
        fall back to the original path."""
        result_path = ocr._preprocess('/tmp/nonexistent_123456789.png', 'report', 'printed')
        assert result_path == '/tmp/nonexistent_123456789.png'

    def test_preprocess_handles_handwritten_mode(self, ocr):
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (400, 200), 'white')
            img.save(f, format='PNG')
            path = f.name
        try:
            result_path = ocr._preprocess(path, 'prescription', 'handwritten')
            assert os.path.exists(result_path)
        finally:
            os.unlink(path)
            if result_path != path and os.path.exists(result_path):
                os.unlink(result_path)

    def test_preprocess_handles_printed_mode(self, ocr):
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (400, 200), 'white')
            img.save(f, format='PNG')
            path = f.name
        try:
            result_path = ocr._preprocess(path, 'report', 'printed')
            assert os.path.exists(result_path)
        finally:
            os.unlink(path)
            if result_path != path and os.path.exists(result_path):
                os.unlink(result_path)
