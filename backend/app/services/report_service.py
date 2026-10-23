"""
Report Service — processes medical report images through OCR + structured parser.
Supports writing_mode: 'printed' | 'handwritten'
"""
from __future__ import annotations

import os
import sys
import tempfile
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Ensure project root is on the path so ocr.* imports work
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ocr.paddleocr_service import ocr_service
from ocr.report_parser import parse_medical_report


class ReportService:
    def process_report_image(
        self,
        image_bytes: bytes,
        writing_mode: str = 'printed',
    ) -> Dict:
        """
        Run OCR on image bytes and parse the result.

        writing_mode: 'printed' | 'handwritten'
        Returns:
            {
                'ocr':    { full_text, lines, average_confidence, engine, ... },
                'parsed': { report_type, summary, key_findings, ... },
            }
        """
        tmp_path = None
        try:
            # Write bytes to a temp file so the OCR engine can read it
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            ocr_result = ocr_service.extract_text(
                tmp_path,
                document_type='report',
                writing_mode=writing_mode,
            )
            parsed = parse_medical_report(
                ocr_result['full_text'],
                writing_mode=writing_mode,
            )

            return {'ocr': ocr_result, 'parsed': parsed}

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
