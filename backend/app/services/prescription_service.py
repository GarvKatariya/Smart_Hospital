"""
Prescription Analysis Service — OCR + rule-based parser + optional NER + LLM explanation.

Supports writing_mode: 'printed' | 'handwritten'
"""
from __future__ import annotations

import os
import sys
import importlib.util
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from app.ai.llm.factory import llm_provider
except ImportError:
    class _MockLLM:
        def generate(self, prompt, context=None):
            return (
                "Mock explanation: medications listed require a pharmacist review. "
                "This is AI-generated information. Always follow your doctor's specific "
                "instructions and consult your pharmacist for any questions."
            )
    llm_provider = _MockLLM()

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'models'))

PRESCRIPTION_PROMPT = """\
You are a pharmacist assistant. Explain the following extracted prescription in simple language.

Medications found:
{medications}

For each medication explain:
1. What it is commonly used for
2. Standard usage instructions
3. Common side effects to watch for
4. Any important warnings

Keep explanations simple and patient-friendly.
Always end with: "This is AI-generated information. Always follow your doctor's specific instructions and consult your pharmacist for any questions."
"""


class PrescriptionService:
    def __init__(self):
        self._ner_model = None
        self._ner_loaded = False
        self._ocr_service = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    def _ensure_ocr(self):
        if self._ocr_service is not None:
            return
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            from ocr.paddleocr_service import ocr_service
            self._ocr_service = ocr_service
            logger.info(f'Prescription OCR loaded: engine={ocr_service.engine_type}')
        except Exception as e:
            logger.warning(f'OCR import failed ({e}), using mock')
            class _MockOCR:
                engine_type = 'mock'
                def extract_text(self, path, **kw):
                    return {
                        'full_text': 'Paracetamol 500mg Twice daily after food\nAmoxicillin 250mg 3 times daily for 5 days',
                        'lines': [],
                        'average_confidence': 0.9,
                        'engine': 'mock',
                    }
            self._ocr_service = _MockOCR()

    def _ensure_ner(self):
        """Attempt to load the trained NER model; silently continue if absent."""
        if self._ner_loaded:
            return
        self._ner_loaded = True  # mark so we don't retry on every call
        try:
            inference_path = os.path.join(MODELS_DIR, 'prescription', 'inference.py')
            if not os.path.exists(inference_path):
                logger.info('Prescription NER model not found — using rule-based parser only')
                return
            spec = importlib.util.spec_from_file_location('prescription_inference', inference_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            ModelClass = getattr(mod, 'PrescriptionModel', None) or getattr(mod, 'PrescriptionNER', None)
            if ModelClass:
                artifacts_dir = os.path.join(MODELS_DIR, 'prescription', 'artifacts')
                model = ModelClass(artifacts_dir)
                if model.load():
                    self._ner_model = model
                    logger.info('Prescription NER model loaded')
                else:
                    logger.info('Prescription NER model artifact missing — using rule-based parser only')
        except Exception as e:
            logger.warning(f'Failed to load prescription NER model: {e}')

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        file_path: str,
        writing_mode: str = 'printed',
        document_type: str = 'prescription',
    ) -> Dict:
        """
        Analyze a prescription image.

        writing_mode: 'printed' | 'handwritten'
        Returns structured dict with medications list, raw OCR text, and LLM explanation.
        """
        self._ensure_ocr()
        self._ensure_ner()

        # 1. OCR with mode-appropriate preprocessing
        ocr_result = self._ocr_service.extract_text(
            file_path,
            document_type=document_type,
            writing_mode=writing_mode,
        )
        raw_text = ocr_result.get('full_text', '')
        ocr_lines = ocr_result.get('lines', [])
        ocr_confidence = float(ocr_result.get('average_confidence', 0.0))

        # 2. Extract medications
        #    Prefer NER model when available, fall back to rule-based parser
        medications: List[Dict] = []
        extraction_method = 'rule_based'

        if self._ner_model:
            try:
                medications = self._ner_model.extract(raw_text)
                extraction_method = 'ner_model'
            except Exception as e:
                logger.warning(f'NER extraction failed ({e}), falling back to rule-based parser')

        if not medications:
            from ocr.prescription_parser import parse_prescription
            medications = parse_prescription(raw_text, ocr_lines=ocr_lines, writing_mode=writing_mode)

        # 3. LLM explanation (only when medications were found)
        llm_explanation = ''
        if medications:
            med_lines = []
            for m in medications:
                name = m.get('name_transcribed') or m.get('normalized_name', 'Unknown')
                parts = [f"- {name}"]
                if m.get('strength') or m.get('dosage'):
                    parts.append(m.get('strength') or m.get('dosage'))
                if m.get('frequency'):
                    parts.append(m['frequency'])
                if m.get('duration'):
                    parts.append(m['duration'])
                med_lines.append(' '.join(parts))
            try:
                llm_explanation = llm_provider.generate(
                    PRESCRIPTION_PROMPT.format(medications='\n'.join(med_lines)),
                    context={'type': 'prescription'},
                )
            except Exception as e:
                logger.error(f'LLM explanation failed: {e}')
                llm_explanation = 'Unable to generate explanation. Please consult your pharmacist.'

        # 4. Try to extract header metadata
        from ocr.prescription_parser import parse_prescription_header
        header = parse_prescription_header(raw_text[:500])  # header usually in first 500 chars

        return {
            'document_type': 'prescription',
            'writing_mode': writing_mode,
            'ocr_text': raw_text,
            'ocr_confidence': ocr_confidence,
            'ocr_engine': ocr_result.get('engine', 'unknown'),
            'extraction_method': extraction_method,
            'patient': header,
            'medications': medications,
            'llm_explanation': llm_explanation,
            'review_status': 'pending',
            'disclaimer': (
                'This is AI-assisted analysis for digitisation purposes only. '
                'Always verify extracted medicine names, dosages and instructions '
                'against the original prescription document. '
                'Never change medications without consulting your doctor.'
            ),
        }

    @property
    def is_available(self):
        return True


prescription_service = PrescriptionService()
