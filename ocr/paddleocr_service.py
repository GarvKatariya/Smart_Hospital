"""
PaddleOCR service with separate pipelines for printed and handwritten documents.

Supports four workflows:
  - Reports    + Printed     → optimised for lab/diagnostic printouts
  - Reports    + Handwritten → clinical notes, handwritten observations
  - Prescriptions + Printed  → typeset/digital prescription tables
  - Prescriptions + Handwritten → doctor handwritten prescriptions

document_type: 'report' | 'prescription'
writing_mode:  'printed' | 'handwritten'
"""
from __future__ import annotations

import io
import os
import logging
import tempfile
from typing import Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

DocumentType = Literal['report', 'prescription']
WritingMode  = Literal['printed', 'handwritten']


class OCRService:
    def __init__(self):
        self.engine = None
        self.engine_type: str = 'mock'
        self._initialize()

    def _initialize(self):
        # Try PaddleOCR first (v3.7+ API)
        try:
            from paddleocr import PaddleOCR
            self.engine = PaddleOCR(
                lang='en',
                use_textline_orientation=True,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
            self.engine_type = 'paddleocr'
            logger.info('PaddleOCR initialized successfully (v3.7+ API)')
            return
        except ImportError:
            logger.info('PaddleOCR not installed, trying Tesseract')
        except Exception as e:
            logger.warning(f'PaddleOCR initialization failed: {e}')

        # Tesseract fallback
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.engine_type = 'tesseract'
            logger.info('Using Tesseract OCR fallback')
            return
        except Exception:
            pass

        self.engine_type = 'mock'
        logger.warning('No OCR engine available, using mock OCR')

    # ------------------------------------------------------------------
    # Public entry point — callers choose document_type + writing_mode
    # ------------------------------------------------------------------

    def extract_text(
        self,
        image_path: str,
        document_type: DocumentType = 'report',
        writing_mode: WritingMode = 'printed',
    ) -> Dict:
        """
        Run OCR with preprocessing selected for the document type and
        writing style.  Returns a dict with:
          full_text, lines, average_confidence, engine,
          document_type, writing_mode
        """
        # Apply the appropriate preprocessing pipeline and save to a temp file
        preprocessed_path = self._preprocess(image_path, document_type, writing_mode)

        try:
            if self.engine_type == 'paddleocr':
                result = self._paddle_extract(preprocessed_path)
            elif self.engine_type == 'tesseract':
                result = self._tesseract_extract(preprocessed_path, writing_mode)
            else:
                result = self._mock_extract(image_path)
        finally:
            # Clean up temp preprocessed file
            if preprocessed_path != image_path:
                try:
                    os.remove(preprocessed_path)
                except OSError:
                    pass

        result['document_type'] = document_type
        result['writing_mode'] = writing_mode
        return result

    # ------------------------------------------------------------------
    # Preprocessing dispatch
    # ------------------------------------------------------------------

    def _preprocess(
        self,
        image_path: str,
        document_type: DocumentType,
        writing_mode: WritingMode,
    ) -> str:
        """
        Apply the correct preprocessing pipeline and save to a temp PNG.
        Returns the path to the preprocessed image (may equal image_path
        if preprocessing fails).
        """
        try:
            from ocr.preprocess import preprocess_printed, preprocess_handwritten

            if writing_mode == 'handwritten':
                img = preprocess_handwritten(image_path)
            else:
                img = preprocess_printed(image_path)

            fd, tmp_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
            img.save(tmp_path, format='PNG', dpi=(300, 300))
            return tmp_path
        except Exception as exc:
            logger.warning(f'Preprocessing failed ({exc}), using original image')
            return image_path

    # ------------------------------------------------------------------
    # Engine implementations
    # ------------------------------------------------------------------

    def _paddle_extract(self, image_path: str) -> Dict:
        """Extract text using PaddleOCR v3.7+ (OCRResult dict-style access)."""
        result = self.engine.ocr(image_path)
        lines: List[Dict] = []
        total_confidence = 0.0
        count = 0

        if result:
            for page in result:
                try:
                    rec_texts = page['rec_texts']
                    rec_scores = page['rec_scores']
                    dt_polys = (
                        page.get('dt_polys', [None] * len(rec_texts))
                        if hasattr(page, 'get')
                        else [None] * len(rec_texts)
                    )
                except (KeyError, TypeError):
                    # Older PaddleOCR format: [[bbox, (text, conf)], ...]
                    if page:
                        for line in page:
                            try:
                                text = line[1][0]
                                confidence = float(line[1][1])
                                bbox = line[0]
                                lines.append({'text': text, 'confidence': confidence, 'bbox': bbox})
                                total_confidence += confidence
                                count += 1
                            except (IndexError, TypeError):
                                continue
                    continue

                for i, text in enumerate(rec_texts):
                    score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                    bbox = (
                        dt_polys[i].tolist()
                        if i < len(dt_polys) and dt_polys[i] is not None and hasattr(dt_polys[i], 'tolist')
                        else None
                    )
                    lines.append({'text': text, 'confidence': score, 'bbox': bbox})
                    total_confidence += score
                    count += 1

        full_text = '\n'.join(l['text'] for l in lines)
        avg_confidence = total_confidence / count if count > 0 else 0.0

        return {
            'full_text': full_text,
            'lines': lines,
            'average_confidence': avg_confidence,
            'engine': 'paddleocr',
            'page_count': len(result) if result else 0,
        }

    def _tesseract_extract(self, image_path: str, writing_mode: WritingMode = 'printed') -> Dict:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)

        # Use different PSM for handwritten vs printed
        # PSM 6: assume uniform block of text (good for printed)
        # PSM 4: assume a single column of text (better for prescriptions)
        # PSM 11: sparse text (may help with handwriting)
        if writing_mode == 'handwritten':
            config = '--oem 3 --psm 6'
        else:
            config = '--oem 3 --psm 6'

        text = pytesseract.image_to_string(img, config=config)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config=config)

        lines = []
        for i, word in enumerate(data['text']):
            if word.strip():
                conf = max(0.0, float(data['conf'][i])) / 100
                lines.append({'text': word, 'confidence': conf})

        avg_conf = sum(l['confidence'] for l in lines) / len(lines) if lines else 0.0

        return {
            'full_text': text,
            'lines': lines,
            'average_confidence': avg_conf,
            'engine': 'tesseract',
        }

    def _mock_extract(self, image_path: str) -> Dict:
        return {
            'full_text': (
                'SMART CITY GENERAL HOSPITAL\n'
                'PATHOLOGY DEPARTMENT\n'
                'Patient: Demo Patient  Age: 45  Sex: Male\n'
                'COMPLETE BLOOD COUNT\n'
                'Hemoglobin 14.2 g/dL\n'
                'WBC 8500 /uL\n'
                'Platelets 250000 /uL\n'
                'Glucose 95 mg/dL\n'
            ),
            'lines': [{'text': '[Mock OCR] Placeholder text', 'confidence': 0.5}],
            'average_confidence': 0.5,
            'engine': 'mock',
            'note': 'No OCR engine available. Install paddleocr or pytesseract.',
        }


ocr_service = OCRService()
