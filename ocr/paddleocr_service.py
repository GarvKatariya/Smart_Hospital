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
            # Try with orientation model first, fall back to simpler init
            try:
                self.engine = PaddleOCR(
                    lang='en',
                    use_textline_orientation=True,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                )
            except Exception:
                self.engine = PaddleOCR(lang='en')
            self.engine_type = 'paddleocr'
            logger.info('PaddleOCR initialized successfully')
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
                result = self._paddle_extract(preprocessed_path, writing_mode)
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

    def _paddle_result_lines(self, result) -> List[Dict]:
        """Convert PaddleOCR v3 and legacy results into a common line format."""
        lines: List[Dict] = []
        for page in result or []:
            try:
                rec_texts = page['rec_texts']
                rec_scores = page['rec_scores']
                dt_polys = page.get('dt_polys', [None] * len(rec_texts))
            except (KeyError, TypeError):
                # Older PaddleOCR format: [[bbox, (text, confidence)], ...]
                for item in page or []:
                    try:
                        text = item[1][0]
                        confidence = float(item[1][1])
                        bbox = item[0]
                        if hasattr(bbox, 'tolist'):
                            bbox = bbox.tolist()
                        lines.append({'text': text, 'confidence': confidence, 'bbox': bbox})
                    except (IndexError, TypeError):
                        continue
                continue

            for index, text in enumerate(rec_texts):
                confidence = float(rec_scores[index]) if index < len(rec_scores) else 0.0
                bbox = dt_polys[index] if index < len(dt_polys) else None
                if hasattr(bbox, 'tolist'):
                    bbox = bbox.tolist()
                lines.append({'text': text, 'confidence': confidence, 'bbox': bbox})
        return lines

    @staticmethod
    def _line_y_bounds(line: Dict):
        bbox = line.get('bbox')
        try:
            points = [(float(point[0]), float(point[1])) for point in bbox]
            return min(point[1] for point in points), max(point[1] for point in points)
        except (TypeError, ValueError, IndexError):
            return None

    @staticmethod
    def _map_crop_bbox(bbox, crop_left: int, crop_top: int, scale: float):
        if bbox is None:
            return None
        try:
            return [
                [crop_left + float(point[0]) / scale, crop_top + float(point[1]) / scale]
                for point in bbox
            ]
        except (TypeError, ValueError, IndexError):
            return None

    def _handwriting_detail_lines(self, image_path: str, lines: List[Dict]) -> List[Dict]:
        """Retry schedule-adjacent handwriting in small, contrast-enhanced crops.

        Full-page recognition often reads handwritten dose schedules while
        missing the medicine name or the meal note beside it.  This targeted
        pass only revisits rows that contain a dosage pattern, which avoids
        multiplying OCR work for ordinary printed uploads.
        """
        try:
            import re
            import numpy as np
            from PIL import Image, ImageEnhance

            image = Image.open(image_path).convert('RGB')
            width, height = image.size
            schedules = []
            for line in lines:
                if not re.search(r'\b[01]\s*[-–—]\s*[01]\s*[-–—]\s*[01]\b', line.get('text', '')):
                    continue
                bounds = self._line_y_bounds(line)
                if bounds:
                    schedules.append((line, (bounds[0] + bounds[1]) / 2, bounds[0]))

            added: List[Dict] = []
            meal_crops: List[Dict] = []
            for schedule, center_y, top_y in schedules:
                nearby = []
                for line in lines:
                    bounds = self._line_y_bounds(line)
                    if not bounds:
                        continue
                    other_center = (bounds[0] + bounds[1]) / 2
                    if center_y - 290 <= other_center <= center_y + 25:
                        nearby.append((line, other_center))

                advice_nearby = any(
                    re.search(r'\b(?:adv|advice)\b', line.get('text', ''), re.IGNORECASE)
                    for line, _ in nearby
                )
                is_medication_row = any(
                    re.search(r'\b(?:tab|cap|syp|syrup|inj)\b', line.get('text', ''), re.IGNORECASE)
                    for line, _ in nearby
                )

                # The meal note is written in the left margin and can be lost
                # when the full-page recognizer prioritizes the large dose row.
                if not advice_nearby:
                    left, right = 0, max(1, int(width * 0.27))
                    crop_top = max(0, int(center_y - 115))
                    crop_bottom = min(height, int(center_y + 115))
                    if crop_bottom > crop_top:
                        meal_crops.append((left, crop_top, right, crop_bottom))

                # Retry the row label only when the full-page pass found no
                # nearby tablet/capsule header.  Advice dosage lines are not
                # medicine rows and should never create a medication guess.
                if is_medication_row or advice_nearby:
                    continue
                left, right = int(width * 0.15), int(width * 0.94)
                crop_top = max(0, int(center_y - 325))
                crop_bottom = min(height, int(center_y + 5))
                if crop_bottom <= crop_top:
                    continue
                crop = image.crop((left, crop_top, right, crop_bottom))
                crop = ImageEnhance.Sharpness(ImageEnhance.Contrast(crop).enhance(1.45)).enhance(1.4)
                scale = 2.0
                crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
                crop_result = self.engine.ocr(np.asarray(crop))
                for recovered in self._paddle_result_lines(crop_result):
                    if not re.search(r'\b(?:tab|cap|syp|syrup|inj)\b', recovered.get('text', ''), re.IGNORECASE):
                        continue
                    recovered['bbox'] = self._map_crop_bbox(recovered.get('bbox'), left, crop_top, scale)
                    recovered['supplemental_pass'] = 'handwriting_row'
                    added.append(recovered)

            for left, crop_top, right, crop_bottom in meal_crops:
                crop = image.crop((left, crop_top, right, crop_bottom))
                crop = ImageEnhance.Sharpness(ImageEnhance.Contrast(crop).enhance(1.45)).enhance(1.4)
                scale = 2.0
                crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
                crop_result = self.engine.ocr(np.asarray(crop))
                meal_tokens = self._paddle_result_lines(crop_result)
                recognized = ' '.join(line.get('text', '') for line in meal_tokens).lower()
                has_after = bool(re.search(r'\bafter\b', recognized))
                has_before = bool(re.search(r'\b(?:before|befoce)\b', recognized))
                has_meals = bool(re.search(r'\bmeals?\b', recognized))
                if not has_meals or not (has_after or has_before):
                    continue

                direction = 'after' if has_after else 'before'
                word_lines = [
                    line for line in meal_tokens
                    if re.search(r'\b(?:after|before|befoce|meals?)\b', line.get('text', ''), re.IGNORECASE)
                ]
                points = [
                    point
                    for line in word_lines
                    for point in (line.get('bbox') or [])
                    if len(point) >= 2
                ]
                if points:
                    xs = [float(point[0]) for point in points]
                    ys = [float(point[1]) for point in points]
                    composite_bbox = [
                        [left + min(xs) / scale, crop_top + min(ys) / scale],
                        [left + max(xs) / scale, crop_top + min(ys) / scale],
                        [left + max(xs) / scale, crop_top + max(ys) / scale],
                        [left + min(xs) / scale, crop_top + max(ys) / scale],
                    ]
                else:
                    composite_bbox = None
                added.append({
                    'text': f'{direction} meals',
                    'confidence': min((float(line.get('confidence', 0.5)) for line in word_lines), default=0.5),
                    'bbox': composite_bbox,
                    'raw_text': recognized,
                    'supplemental_pass': 'meal_margin',
                })

            # Suppress the page-level "meals" fragment when the detail pass
            # has recovered the complete phrase at the same location.
            composite_meals = [line for line in added if line.get('supplemental_pass') == 'meal_margin']
            kept_lines = []
            for line in lines:
                bounds = self._line_y_bounds(line)
                is_fragment = line.get('text', '').strip().lower() in {'meal', 'meals'}
                if is_fragment and bounds:
                    center = (bounds[0] + bounds[1]) / 2
                    if any(
                        (meal_bounds := self._line_y_bounds(meal))
                        and abs(center - (meal_bounds[0] + meal_bounds[1]) / 2) < 95
                        for meal in composite_meals
                    ):
                        continue
                kept_lines.append(line)

            combined = kept_lines + added
            combined.sort(key=lambda line: (
                (bounds[0] + bounds[1]) / 2 if (bounds := self._line_y_bounds(line)) else float('inf')
            ))
            return combined
        except Exception as exc:
            logger.warning('Handwriting detail OCR pass failed: %s', exc)
            return lines

    def _paddle_extract(self, image_path: str, writing_mode: WritingMode = 'printed') -> Dict:
        """Extract text using PaddleOCR, with a targeted second pass for handwriting."""
        result = self.engine.ocr(image_path)
        lines = self._paddle_result_lines(result)
        if writing_mode == 'handwritten':
            lines = self._handwriting_detail_lines(image_path, lines)

        full_text = '\n'.join(line['text'] for line in lines)
        avg_confidence = (
            sum(float(line.get('confidence', 0.0)) for line in lines) / len(lines)
            if lines else 0.0
        )

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
