"""
Prescription parser — extracts structured medication data from OCR text.

Handles both handwritten and printed prescriptions.
Does NOT silently correct or invent medicine names — uncertain values are
flagged with requires_review=True and the raw OCR text is preserved.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common medical abbreviations
# ---------------------------------------------------------------------------
FREQUENCY_MAP = {
    r'\bod\b': 'Once daily',
    r'\bonce\s+daily\b': 'Once daily',
    r'\bonce\s+a\s+day\b': 'Once daily',
    r'\bod\s*x\b': 'Once daily',
    r'\bbd\b': 'Twice daily',
    r'\bbid\b': 'Twice daily',
    r'\btwice\s+daily\b': 'Twice daily',
    r'\b2\s*x\s*daily\b': 'Twice daily',
    r'\btds\b': 'Three times daily',
    r'\btid\b': 'Three times daily',
    r'\bthree\s+times\s+daily\b': 'Three times daily',
    r'\b3\s*x\s*daily\b': 'Three times daily',
    r'\bqid\b': 'Four times daily',
    r'\bfour\s+times\s+daily\b': 'Four times daily',
    r'\bhs\b': 'At bedtime',
    r'\bbedtime\b': 'At bedtime',
    r'\bnight\b': 'At night',
    r'\bmorning\b': 'In the morning',
    r'\bsos\b': 'As needed',
    r'\bprn\b': 'As needed',
    r'\bas\s+needed\b': 'As needed',
    r'\bstat\b': 'Immediately',
    r'\bimmediately\b': 'Immediately',
}

MEAL_MAP = {
    r'\bafter\s+(?:food|meal|meals|eating)\b': 'After food',
    r'\bbefore\s+(?:food|meal|meals|eating)\b': 'Before food',
    r'\bwith\s+(?:food|meal|meals)\b': 'With food',
    r'\bempty\s+stomach\b': 'On empty stomach',
    r'\bwith\s+water\b': 'With water',
    r'\baf\b': 'After food',
    r'\bbf\b': 'Before food',
}

DURATION_PATTERN = re.compile(
    r'(?:for\s+)?(\d+)\s*(days?|weeks?|months?|year)',
    re.IGNORECASE,
)

DOSAGE_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units?|tab(?:let)?s?|caps?(?:ule)?s?|drops?|puffs?)',
    re.IGNORECASE,
)

# Minimum length for a plausible medicine name
MIN_MEDICINE_NAME_LEN = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_frequency(text: str) -> Optional[str]:
    t = text.lower()
    for pattern, label in FREQUENCY_MAP.items():
        if re.search(pattern, t):
            return label
    return None


def _normalise_meal(text: str) -> Optional[str]:
    t = text.lower()
    for pattern, label in MEAL_MAP.items():
        if re.search(pattern, t):
            return label
    return None


def _extract_dosage(text: str) -> Optional[str]:
    m = DOSAGE_PATTERN.search(text)
    if m:
        return m.group(0)
    return None


def _extract_duration(text: str) -> Optional[str]:
    m = DURATION_PATTERN.search(text)
    if m:
        return m.group(0)
    return None


def _confidence_for_line(line_text: str, ocr_lines: List[Dict]) -> float:
    """Return the OCR confidence for a given text snippet, or 0.5 if not found."""
    for l in ocr_lines:
        if l.get('text', '').strip() in line_text:
            return float(l.get('confidence', 0.5))
    return 0.5


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_prescription(
    text: str,
    ocr_lines: Optional[List[Dict]] = None,
    writing_mode: str = 'printed',
) -> List[Dict]:
    """
    Parse OCR text from a prescription into a list of medication records.

    Each record follows this schema:
    {
        name_raw:         str   — exactly as recognised by OCR
        name_transcribed: str   — same as name_raw (never silently corrected)
        strength:         str | None
        dose:             str | None
        frequency:        str | None
        meal_instructions: str | None
        duration:         str | None
        route:            str | None
        raw_line:         str   — full original OCR line
        confidence:       float — OCR confidence (0–1), 0.5 if unavailable
        requires_review:  bool  — True when confidence < 0.8 or name is short/ambiguous
        normalized_name:  str   — alias for name_transcribed (keeps old callers working)
        dosage:           str | None — alias for strength (keeps old callers working)
    }

    Safety contract:
    - Medicine names are NEVER corrected or guessed.
    - Missing fields are None, never invented.
    - Low-confidence lines are always flagged requires_review=True.
    """
    if not text or not text.strip():
        return []

    ocr_lines = ocr_lines or []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    medications: List[Dict] = []

    for line in lines:
        line_lower = line.lower()

        # Skip obvious header / footer lines
        skip_patterns = [
            r'^(?:rx|prescription|date|patient|name|age|sex|dr\.|doctor|clinic|hospital|address|tel|phone|sign)',
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # dates
            r'^page\s*\d',
            r'^ref(?:erence)?',
            r'^\s*$',
        ]
        if any(re.match(p, line_lower) for p in skip_patterns):
            continue

        # A medicine line usually starts with a capitalised word (the drug name)
        # or a number (for numbered prescription lines like "1. Amoxicillin 500mg")
        medicine_match = re.match(
            r'^(?:\d+[\.\)]\s*)?([A-Za-z][A-Za-z\-\s\.]+?)(?:\s+(\d[\d\.]*\s*(?:mg|mcg|g|ml|iu|tab|cap)[a-z]*))?(?:\s+(.*))?$',
            line,
            re.IGNORECASE,
        )
        if not medicine_match:
            continue

        candidate_name = medicine_match.group(1).strip().rstrip('.,;:')
        if len(candidate_name) < MIN_MEDICINE_NAME_LEN:
            continue

        # Skip lines that are clearly not drug names
        non_drug_words = {
            'take', 'apply', 'use', 'continue', 'stop', 'avoid', 'follow',
            'please', 'note', 'total', 'quantity', 'refill', 'dispense',
            'substitution', 'generic', 'brand', 'diagnosis', 'impression',
            'follow', 'advice', 'review', 'next', 'visit',
        }
        if candidate_name.lower() in non_drug_words:
            continue

        # Extract fields
        raw_dosage = _extract_dosage(line)
        frequency = _normalise_frequency(line)
        meal_instructions = _normalise_meal(line)
        duration = _extract_duration(line)

        # Route extraction
        route = None
        route_patterns = [
            (r'\boral(?:ly)?\b', 'Oral'),
            (r'\btopical(?:ly)?\b', 'Topical'),
            (r'\biv\b|\bintravenous(?:ly)?\b', 'Intravenous'),
            (r'\bim\b|\bintramuscular(?:ly)?\b', 'Intramuscular'),
            (r'\bsc\b|\bsubcutaneous(?:ly)?\b', 'Subcutaneous'),
            (r'\binhale\b|\binhalation\b', 'Inhalation'),
            (r'\bnasal\b', 'Nasal'),
            (r'\boptic\b|\beye\b|\bear\b', 'Optic/Aural'),
        ]
        for rpattern, rlabel in route_patterns:
            if re.search(rpattern, line_lower):
                route = rlabel
                break

        # OCR confidence for this line
        line_conf = _confidence_for_line(line, ocr_lines)

        # Flag for review: low confidence OR very short name OR ambiguous
        requires_review = (
            line_conf < 0.80
            or len(candidate_name) < 5
            or bool(re.search(r'[^A-Za-z0-9\s\-\.]', candidate_name))
        )

        medications.append({
            'name_raw': candidate_name,
            'name_transcribed': candidate_name,   # never silently corrected
            'normalized_name': candidate_name,     # backward-compat alias
            'strength': raw_dosage,
            'dosage': raw_dosage,                  # backward-compat alias
            'dose': raw_dosage,
            'frequency': frequency,
            'meal_instructions': meal_instructions,
            'duration': duration,
            'route': route,
            'raw_line': line,
            'confidence': round(line_conf, 3),
            'requires_review': requires_review,
        })

    return medications


def parse_prescription_header(text: str) -> Dict:
    """
    Extract patient/doctor metadata from prescription header text.
    Returns only fields that are actually present — no invented values.
    """
    result: Dict = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full = ' '.join(lines)

    # Patient name
    for p in [r'(?:patient|pt)[\s:]+([A-Za-z][A-Za-z\s\.]+)', r'name[\s:]+([A-Za-z][A-Za-z\s\.]+)']:
        m = re.search(p, full, re.IGNORECASE)
        if m:
            result['patient_name'] = m.group(1).strip()
            break

    # Age
    m = re.search(r'age[\s:]+(\d+)', full, re.IGNORECASE)
    if m:
        result['patient_age'] = int(m.group(1))

    # Sex / gender
    m = re.search(r'(?:sex|gender)[\s:]+([MF](?:ale)?)', full, re.IGNORECASE)
    if m:
        result['patient_sex'] = m.group(1).strip().upper()

    # Date
    m = re.search(r'(?:date|dt)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', full, re.IGNORECASE)
    if m:
        result['date'] = m.group(1).strip()

    # Doctor
    m = re.search(r'(?:dr\.?|doctor)[\s:]+([A-Za-z][A-Za-z\s\.]+)', full, re.IGNORECASE)
    if m:
        result['doctor'] = m.group(1).strip()

    # Diagnosis (if written)
    for p in [r'(?:dx|diagnosis|diag)[\s:]+([^\n]+)', r'(?:complaint|c/o)[\s:]+([^\n]+)']:
        m = re.search(p, full, re.IGNORECASE)
        if m:
            result['diagnosis'] = m.group(1).strip()
            break

    # Follow-up
    m = re.search(r'(?:follow[\s-]?up|review)[\s:]+([^\n]+)', full, re.IGNORECASE)
    if m:
        result['follow_up'] = m.group(1).strip()

    return result
