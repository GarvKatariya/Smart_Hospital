"""
Report Service — processes medical document images through OCR + classification + structured parser.

Supports:
  - writing_mode: 'printed' | 'handwritten'
  - Automatic document classification (lab report, prescription, imaging, etc.)
  - Routes prescriptions to the existing prescription_parser for structured extraction
"""
from __future__ import annotations

import os
import sys
import tempfile
import logging
import json
import re
from typing import Dict

logger = logging.getLogger(__name__)

# Ensure project root is on the path so ocr.* imports work
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ocr.paddleocr_service import ocr_service
from ocr.report_parser import parse_medical_report, classify_document
from app.ai.llm.factory import llm_provider


PATIENT_INSIGHT_PROMPT = """You explain extracted medical report findings to a patient in plain language.
Use only the structured facts provided below. Do not infer or name a disease from lab values,
do not add values or reference ranges, and do not recommend starting, stopping, or changing
treatment. Explain what the flagged results mean relative to the ranges printed on this report,
what the report does and does not establish, and give up to two useful questions for the patient's
clinician. Keep the response to 2-4 short bullets. Do not assign urgency unless the supplied report
explicitly does so. End with a brief reminder that a clinician should interpret the report in context.

Extracted report facts (may contain OCR errors):
{facts}"""


def _basic_patient_insight(parsed: Dict) -> str:
    """Build a conservative, value-grounded explanation if AI is unavailable."""
    category = parsed.get('document_category')
    abnormal = parsed.get('abnormal_values') or {}
    if category == 'laboratory_report':
        lab_values = parsed.get('lab_values') or []
        flagged = [item for item in lab_values if item.get('status') in {'high', 'low'}]
        if flagged:
            details = []
            for item in flagged:
                direction = 'above' if item['status'] == 'high' else 'below'
                value = f"{item.get('value')} {item.get('unit', '')}".strip()
                reference = item.get('reference_range')
                comparison = f"{direction} the printed range {reference}" if reference else f"{direction} the available range"
                details.append(f"{item.get('test_name')}: {value} ({comparison})")
            insight = (
                f"The OCR extracted {len(lab_values)} lab results; {len(flagged)} are outside "
                f"the reference ranges printed on the report. " + '; '.join(details) + '.'
            )
            report_comment = parsed.get('report_comment')
            normalized_comment = (report_comment or '').lower()
            if 'microcytic' in normalized_comment and re.search(r'\b(?:ferritin|forritin)\b', normalized_comment):
                insight += ' The report comment appears to note a microcytic pattern with low ferritin; verify the wording against the original scan.'
            elif report_comment:
                insight += ' The report includes an additional comment; check its exact wording on the original scan.'
            insight += ' These findings are not a diagnosis; ask your clinician to interpret them with your symptoms and medical history.'
            return insight
        if parsed.get('lab_values'):
            return (
                f"The OCR extracted {len(parsed['lab_values'])} lab results, and none were flagged "
                'outside the reference ranges printed on the report. This does not rule out a health '
                'problem; ask your clinician to interpret the results in context.'
            )
        return 'No standard lab values were extracted, so this report cannot be explained reliably.'
    if category == 'diagnostic_imaging':
        impression = (parsed.get('sections') or {}).get('impression')
        if impression:
            return f'The report impression says: {impression} Review its meaning with the clinician who ordered the scan.'
    if category == 'prescription':
        return (
            'This document appears to contain medication instructions. Verify every medicine name, '
            'dose, and schedule against the original document with your prescriber or pharmacist.'
        )
    if category == 'discharge_summary':
        return 'This appears to be a discharge summary. Review the diagnosis, medicines, and follow-up plan with your care team.'
    return 'There is not enough structured information in this document to explain it reliably.'


def _patient_insight(parsed: Dict, ocr_engine: str) -> Dict[str, str]:
    """Explain parsed facts while preventing mock OCR from being presented as patient data."""
    basic = _basic_patient_insight(parsed)
    if ocr_engine == 'mock':
        return {
            'text': basic,
            'status': 'sample_only',
            'notice': 'Demo insight only: OCR returned placeholder text, so this does not explain your uploaded document.',
        }

    if parsed.get('document_category') == 'prescription':
        return {
            'text': basic,
            'status': 'basic',
            'notice': 'This is an OCR transcription, not a medication recommendation. Verify the extracted details against the original prescription.',
        }

    # The mock provider returns generic demo copy, not an explanation of the
    # extracted report. Use the structured-result explanation instead of
    # labeling that placeholder as AI output.
    if llm_provider.__class__.__name__ == 'MockLLMProvider':
        notice = (
            'The AI explanation is in demo mode. Verify all extracted medication details against the original prescription with your prescriber or pharmacist.'
            if parsed.get('document_category') == 'prescription'
            else 'The AI provider is in demo mode. This explanation is based on values and reference ranges extracted from your report.'
        )
        return {
            'text': basic,
            'status': 'basic',
            'notice': notice,
        }

    sections = parsed.get('sections') or {}
    imaging_sections = {
        key: sections[key]
        for key in ('findings', 'impression')
        if sections.get(key)
    } if parsed.get('document_category') == 'diagnostic_imaging' else {}
    facts = {
        'document_category': parsed.get('document_category'),
        'report_type': parsed.get('report_type'),
        'lab_values': [
            {
                'test': item.get('test_name'),
                'value': item.get('value'),
                'unit': item.get('unit'),
                'reference_range': item.get('reference_range'),
                'status': item.get('status'),
            }
            for item in (parsed.get('lab_values') or [])
        ],
        'key_findings': (parsed.get('key_findings') or [])[:10],
        'abnormal_values': parsed.get('abnormal_values') or {},
        'imaging_sections': imaging_sections,
    }
    try:
        explanation = llm_provider.generate(
            PATIENT_INSIGHT_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False)),
            context={'type': 'patient_report_explanation'},
        )
        if explanation and explanation.strip():
            return {'text': explanation.strip(), 'status': 'ai', 'notice': ''}
    except Exception as exc:
        logger.warning('Patient report insight generation failed: %s', exc)

    return {
        'text': basic,
        'status': 'basic',
        'notice': 'A basic explanation is shown because the AI explanation service was unavailable.',
    }


class ReportService:
    def process_report_image(
        self,
        image_bytes: bytes,
        writing_mode: str = 'printed',
    ) -> Dict:
        """
        Run OCR on image bytes, classify the document, and parse the result.

        writing_mode: 'printed' | 'handwritten'
        Returns:
            {
                'ocr':    { full_text, lines, average_confidence, engine, ... },
                'parsed': { document_category, report_type, summary, key_findings, ... },
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

            full_text = ocr_result.get('full_text', '')
            ocr_confidence = float(ocr_result.get('average_confidence', 0.0))

            # Parse the document (classification happens inside parse_medical_report)
            parsed = parse_medical_report(
                full_text,
                writing_mode=writing_mode,
                ocr_lines=ocr_result.get('lines'),
            )
            insight = _patient_insight(parsed, ocr_result.get('engine', 'unknown'))

            # Add a low-confidence warning if OCR quality is poor
            if ocr_confidence < 0.6 and ocr_confidence > 0:
                if 'key_findings' not in parsed:
                    parsed['key_findings'] = []
                parsed['key_findings'].insert(
                    0,
                    f'⚠ Low OCR confidence ({ocr_confidence:.0%}). '
                    f'Extracted text may contain errors. Manual review recommended.'
                )
                parsed['low_confidence_warning'] = True

            # Add a mode-mismatch hint if handwritten mode produces low confidence
            if writing_mode == 'handwritten' and ocr_confidence < 0.5 and ocr_confidence > 0:
                parsed.setdefault('key_findings', []).append(
                    'Handwriting recognition confidence is low. '
                    'Consider trying "Printed" mode if the document is typed.'
                )

            return {'ocr': ocr_result, 'parsed': parsed, 'patient_insight': insight}

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
