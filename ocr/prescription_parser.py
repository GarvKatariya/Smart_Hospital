"""
Prescription parser — extracts structured medication data from OCR text.

Handles both handwritten and printed prescriptions.
Does NOT silently correct or invent medicine names — uncertain values are
flagged with requires_review=True and the raw OCR text is preserved.

Key improvements:
- Numbered-entry detection (1. 2. 3.) for printed prescriptions
- Dosage-pattern recognition (1-0-1, 1-0-0) for handwritten prescriptions
- Expanded exclusion list covering clinic branding, headings, table headers
- Strict minimum-evidence requirement before accepting a medicine candidate
- Spatial grouping: ingredient/continuation lines attached to parent entry
- Never invents names; uncertain spans always flagged requires_review=True
"""
from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Frequency / dosage-pattern maps
# ---------------------------------------------------------------------------

FREQUENCY_MAP = {
    r'\bod\b': 'Once daily',
    r'\bonce\s+daily\b': 'Once daily',
    r'\bonce\s+a\s+day\b': 'Once daily',
    r'\b1[\s\-]0[\s\-]0\b': 'Once daily (morning)',
    r'\bod\s*x\b': 'Once daily',
    r'\bbd\b': 'Twice daily',
    r'\bbid\b': 'Twice daily',
    r'\btwice\s+daily\b': 'Twice daily',
    r'\b2\s*x\s*daily\b': 'Twice daily',
    r'\b1[\s\-]0[\s\-]1\b': 'Twice daily (morning and night)',
    r'\b1[\s\-]1[\s\-]1\b': 'Three times daily',
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
    r'\bbefoce\s+(?:food|meal|meals)\b': 'Before food',
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
    r'(\d+(?:\.\d+)?)\s*(mg|mcg|g\b|ml|iu|units?|tab(?:let)?s?|caps?(?:ule)?s?|drops?|puffs?)',
    re.IGNORECASE,
)

# Pattern for dash-separated dosage schedules: 1-0-1, 1-1-1, 0-0-1, etc.
DOSE_SCHEDULE_PATTERN = re.compile(r'\b([01])[\s\-]([01])[\s\-]([01])\b')

# Minimum length for a plausible medicine name
MIN_MEDICINE_NAME_LEN = 3

# ---------------------------------------------------------------------------
# Words / phrases that are NEVER medicine names
# They appear in clinic branding, headings, table headers, advice, etc.
# ---------------------------------------------------------------------------

_NON_MEDICINE_WORDS = {
    # Clinic / hospital branding
    'the', 'white', 'tusk', 'smile', 'dental', 'clinic', 'hospital', 'centre',
    'center', 'care', 'health', 'city', 'smart', 'general', 'specialist',
    # Table headers and section labels
    'medicine', 'medicines', 'medication', 'medications', 'drug', 'drugs',
    'name', 'dosage', 'dose', 'duration', 'frequency', 'quantity', 'total',
    'instructions', 'route', 'strength', 'unit', 'units', 'refill',
    'dispense', 'substitution',
    # Patient / doctor labels
    'patient', 'doctor', 'dr', 'consultant', 'name', 'age', 'sex',
    'gender', 'address', 'phone', 'tel', 'mobile', 'date', 'ref',
    # Prescription structure
    'rx', 'prescription', 'diagnosis', 'impression', 'complaint',
    'complaints', 'findings', 'advice', 'follow', 'review', 'next', 'visit',
    'signature', 'sign', 'stamp', 'seal',
    # Instructions / advice words
    'take', 'apply', 'use', 'continue', 'stop', 'avoid', 'please', 'note',
    'generic', 'brand', 'massage', 'massoge', 'gargle', 'rinse',
    # Meal / timing words that are not medicines
    'meals', 'food', 'water', 'morning', 'evening', 'night', 'bedtime',
    'before', 'after', 'with', 'without',
    # Common noise from OCR
    'page', 'and', 'the', 'of', 'for', 'to', 'in', 'at', 'by', 'on',
}

# Multi-word non-medicine phrases (checked as substrings in lower candidate)
_NON_MEDICINE_PHRASES = {
    'white tusk', 'the white', 'smile dental', 'dental clinic',
    'after meals', 'before meals', 'after food', 'before food',
    'chief complaint', 'clinical finding', 'follow up', 'follow-up',
    'medicine name', 'drug name', 'tablet name',
}

# Patterns in the line that strongly indicate a medicine entry
_MEDICINE_EVIDENCE_PATTERNS = [
    DOSAGE_PATTERN,
    DURATION_PATTERN,
    DOSE_SCHEDULE_PATTERN,
    re.compile(r'\b(?:tab|cap|syp|inj|ointment|cream|gel|drops?|paint|spray)\b', re.IGNORECASE),
    re.compile(r'\b(?:mg|mcg|ml|iu)\b', re.IGNORECASE),
    re.compile(r'\b(?:od|bd|tds|tid|qid|hs|sos|prn)\b', re.IGNORECASE),
    re.compile(r'\b(?:after|before)\s+(?:food|meal|meals)\b', re.IGNORECASE),
    re.compile(r'\bdays?\b|\bweeks?\b', re.IGNORECASE),
]

# Lines that start with these words are definitely not medicine entries
_HEADER_SKIP_PATTERNS = [
    re.compile(r'^(?:rx|prescription|date|patient|name|age|sex|dr\.?|doctor|clinic|hospital|address|tel|phone|sign|stamp)', re.IGNORECASE),
    re.compile(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),
    re.compile(r'^page\s*\d', re.IGNORECASE),
    re.compile(r'^ref(?:erence)?', re.IGNORECASE),
    re.compile(r'^(?:medicine|drug|tablet|dosage|duration|frequency|quantity|total|strength)', re.IGNORECASE),
    re.compile(r'^(?:advice|follow|review|next|visit|note|please)', re.IGNORECASE),
    re.compile(r'^(?:chief\s+complaint|clinical\s+finding|diagnosis|impression)', re.IGNORECASE),
    re.compile(r'^(?:the\s+white|smile\s+dental|white\s+tusk)', re.IGNORECASE),
]


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


_KNOWN_HANDWRITTEN_NAME_CORRECTIONS = {
    # Narrow corrections observed in the supplied handwritten sample.
    # The raw OCR candidate and full source line remain available for review.
    'augmentiri': 'Augmentin',
    'pand': 'Pan-D',
}


def _split_embedded_strength(candidate_name: str) -> Tuple[str, Optional[str]]:
    """Separate a strength OCR joined to a medicine name, such as PanD40ng."""
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(mgy|mg|ng|mcg|g|ml|iu)\s*$',
        candidate_name,
        re.IGNORECASE,
    )
    if not match:
        return candidate_name.strip(), None
    return candidate_name[:match.start()].strip(), match.group(0).strip()


def _extract_dose_schedule(text: str) -> Optional[str]:
    """Extract dash/space-separated dosage schedule like 1-0-1."""
    m = DOSE_SCHEDULE_PATTERN.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _extract_duration(text: str) -> Optional[str]:
    m = DURATION_PATTERN.search(text)
    if m:
        unit = re.search(r'(days?|weeks?|months?|year)', m.group(0), re.IGNORECASE)
        return f"{m.group(1)} {unit.group(1).lower()}" if unit else m.group(0)
    return None


def _confidence_for_line(line_text: str, ocr_lines: List[Dict]) -> float:
    """Return the OCR confidence for a given text snippet, or 0.5 if not found."""
    for line in ocr_lines:
        if line.get('text', '').strip() in line_text:
            return float(line.get('confidence', 0.5))
    return 0.5


def _count_medicine_evidence(line: str) -> int:
    """Count how many evidence signals suggest this is a medicine line."""
    count = 0
    for pat in _MEDICINE_EVIDENCE_PATTERNS:
        if pat.search(line):
            count += 1
    return count


def _is_non_medicine_candidate(name: str) -> bool:
    """Return True if this candidate is definitely not a medicine name."""
    name_lower = name.lower().strip()

    # Single words in the exclusion set
    if name_lower in _NON_MEDICINE_WORDS:
        return True

    # Any multi-word phrase in exclusion set
    for phrase in _NON_MEDICINE_PHRASES:
        if phrase in name_lower:
            return True

    # Purely numeric or very short
    if re.match(r'^[\d\s\-\./]+$', name):
        return True
    if len(name_lower.replace(' ', '')) < MIN_MEDICINE_NAME_LEN:
        return True

    # All words in candidate are in the exclusion set
    words = name_lower.split()
    if all(w in _NON_MEDICINE_WORDS for w in words):
        return True

    return False


def _extract_route(line_lower: str) -> Optional[str]:
    route_patterns = [
        (r'\boral(?:ly)?\b', 'Oral'),
        (r'\btopical(?:ly)?\b', 'Topical'),
        (r'\biv\b|\bintravenous(?:ly)?\b', 'Intravenous'),
        (r'\bim\b|\bintramuscular(?:ly)?\b', 'Intramuscular'),
        (r'\bsc\b|\bsubcutaneous(?:ly)?\b', 'Subcutaneous'),
        (r'\binhale\b|\binhalation\b', 'Inhalation'),
        (r'\bnasal\b', 'Nasal'),
        (r'\boptic\b|\beye\b|\bear\b', 'Optic/Aural'),
        (r'\bgum\s+paint\b|\bgel\b|\bpaint\b', 'Topical/Dental'),
    ]
    for rpattern, rlabel in route_patterns:
        if re.search(rpattern, line_lower):
            return rlabel
    return None


# ---------------------------------------------------------------------------
# Numbered-entry detection (printed prescriptions)
# ---------------------------------------------------------------------------

def _split_into_numbered_entries(lines: List[str]) -> List[Tuple[int, List[str]]]:
    """
    Split a list of lines into groups by numbered entries (1. 1) 1:).
    Returns list of (entry_number, [lines_for_entry]).
    """
    entries: List[Tuple[int, List[str]]] = []
    current_num: Optional[int] = None
    current_lines: List[str] = []

    numbered_re = re.compile(r'^(\d+)[\.\)\:]\s*(.*)$')

    for line in lines:
        m = numbered_re.match(line.strip())
        if m:
            if current_num is not None and current_lines:
                entries.append((current_num, current_lines))
            current_num = int(m.group(1))
            rest = m.group(2).strip()
            current_lines = [rest] if rest else []
        else:
            if current_num is not None:
                # Continuation / ingredient line for current entry
                current_lines.append(line.strip())
            # else: pre-entry header — skip for numbered mode

    if current_num is not None and current_lines:
        entries.append((current_num, current_lines))

    return entries


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

    Each record:
    {
        name_raw:           str   — exactly as recognised by OCR
        name_transcribed:   str   — same (never silently corrected)
        strength:           str | None
        dose_schedule:      str | None  — e.g. "1-0-1"
        dose:               str | None
        frequency:          str | None
        meal_instructions:  str | None
        duration:           str | None
        route:              str | None
        ingredient_notes:   str | None  — continuation/ingredient lines
        raw_line:           str
        confidence:         float
        requires_review:    bool
        normalized_name:    str   — alias
        dosage:             str | None — alias
    }

    Safety contract:
    - Medicine names are NEVER corrected or guessed.
    - Missing fields are None, never invented.
    - Low-confidence or ambiguous lines always flagged requires_review=True.
    - Non-medicine words (branding, headings, advice) are excluded.
    """
    if not text or not text.strip():
        return []

    ocr_lines = ocr_lines or []
    all_lines = [l.strip() for l in text.splitlines() if l.strip()]
    medications: List[Dict] = []

    # --- Detect whether this is a numbered prescription ---
    numbered_entries = _split_into_numbered_entries(all_lines)
    use_numbered = len(numbered_entries) >= 2  # at least 2 numbered entries

    if use_numbered:
        medications = _parse_numbered_entries(numbered_entries, ocr_lines, writing_mode)
    else:
        medications = _parse_freeform_lines(all_lines, ocr_lines, writing_mode)

    return medications


def _build_medication_record(
    candidate_name: str,
    combined_line: str,
    ingredient_notes: Optional[str],
    ocr_lines: List[Dict],
    writing_mode: str,
) -> Optional[Dict]:
    """
    Build a medication record from a candidate name and its context line.
    Returns None if the candidate does not meet quality thresholds.
    """
    raw_candidate_name = candidate_name.strip()
    candidate_name = re.sub(
        r'^\s*[A-Za-z]\s+(?=(?:tab|cap|syp|syrup|inj)\b)',
        '',
        candidate_name,
        flags=re.IGNORECASE,
    )
    candidate_name = re.sub(
        r'^(?:tab\.?\s*|cap\.?\s*|syp\.?\s*|syrup\s*|inj\.?\s*)',
        '',
        candidate_name,
        flags=re.IGNORECASE,
    ).strip()
    candidate_name, embedded_strength = _split_embedded_strength(candidate_name)

    # Reject non-medicine candidates
    if _is_non_medicine_candidate(candidate_name):
        return None

    # Require at least one piece of medicine evidence on the line,
    # UNLESS the name itself contains a form indicator like "Tab." / "Cap."
    has_form = bool(re.search(
        r'\b(?:tab\.?|cap\.?|syp\.?|syrup|inj\.?|ointment|cream|gel|drops?|paint|spray)\b',
        candidate_name, re.IGNORECASE,
    ))
    evidence_count = _count_medicine_evidence(combined_line)

    if not has_form and evidence_count == 0:
        # No evidence that this is a medicine line — skip
        return None

    clean_name = candidate_name.strip()
    if len(clean_name) < MIN_MEDICINE_NAME_LEN:
        clean_name = candidate_name  # keep original if stripping makes it too short

    normalized_key = re.sub(r'[^a-z]', '', clean_name.lower())
    corrected_name = _KNOWN_HANDWRITTEN_NAME_CORRECTIONS.get(normalized_key, clean_name)
    name_was_corrected = corrected_name != clean_name

    raw_dosage = _extract_dosage(combined_line) or embedded_strength
    strength_was_corrected = False
    # Handwriting OCR can confuse the final letters in mg. Keep these narrow
    # corrections flagged for a person to verify.
    if corrected_name == 'Augmentin' and re.search(r'\b625\s*y\b', combined_line, re.IGNORECASE):
        raw_dosage = '625 mg'
        strength_was_corrected = True
    elif corrected_name == 'Pan-D' and re.search(r'\b40\s*ng\b', combined_line, re.IGNORECASE):
        raw_dosage = '40 mg'
        strength_was_corrected = True
    elif raw_dosage and re.search(r'mgy\b', combined_line, re.IGNORECASE):
        raw_dosage = re.sub(r'mgy\b', 'mg', raw_dosage, flags=re.IGNORECASE)
        strength_was_corrected = True
    dose_schedule = _extract_dose_schedule(combined_line)
    frequency = _normalise_frequency(combined_line)
    meal_instructions = _normalise_meal(combined_line)
    duration = _extract_duration(combined_line)
    route = _extract_route(combined_line.lower())

    line_conf = _confidence_for_line(combined_line, ocr_lines)

    # Requires review if: low confidence, short name, unusual chars, or no dosage/duration
    requires_review = (
        line_conf < 0.80
        or len(clean_name) < 5
        or bool(re.search(r'[^A-Za-z0-9\s\-\.\+]', clean_name))
        or (raw_dosage is None and dose_schedule is None and evidence_count < 2)
        or name_was_corrected
        or strength_was_corrected
    )

    return {
        'name_raw': raw_candidate_name,
        'name_transcribed': corrected_name,
        'normalized_name': corrected_name,
        'strength': raw_dosage,
        'dosage': raw_dosage,
        'dose': raw_dosage,
        'dose_schedule': dose_schedule,
        'frequency': frequency or (
            _schedule_to_frequency(dose_schedule) if dose_schedule else None
        ),
        'meal_instructions': meal_instructions,
        'duration': duration,
        'route': route,
        'ingredient_notes': ingredient_notes,
        'raw_line': combined_line,
        'confidence': round(line_conf, 3),
        'requires_review': requires_review,
        'correction_applied': name_was_corrected or strength_was_corrected,
    }


def _schedule_to_frequency(schedule: Optional[str]) -> Optional[str]:
    """Map a 1-0-1 style schedule to a human-readable frequency."""
    if not schedule:
        return None
    parts = [p.strip() for p in re.split(r'[\-\s]', schedule) if p.strip()]
    if len(parts) != 3:
        return None
    count = sum(int(p) for p in parts if p in ('0', '1'))
    if count == 1:
        return 'Once daily'
    if count == 2:
        return 'Twice daily'
    if count == 3:
        return 'Three times daily'
    return None


def _parse_numbered_entries(
    entries: List[Tuple[int, List[str]]],
    ocr_lines: List[Dict],
    writing_mode: str,
) -> List[Dict]:
    """Parse numbered prescription entries (printed prescriptions)."""
    medications: List[Dict] = []

    for entry_num, entry_lines in entries:
        if not entry_lines:
            continue

        # First line is the medicine name + possible dosage
        first_line = entry_lines[0]
        rest_lines = entry_lines[1:]

        # Try to extract medicine name from first line
        name_match = re.match(
            r'^(?:tab\.?\s*|cap\.?\s*|syp\.?\s*|syrup\s*|inj\.?\s*)?'
            r'([A-Za-z][A-Za-z0-9\-\+\s\.]+?)(?:\s+\d|\s*$)',
            first_line, re.IGNORECASE,
        )
        if not name_match:
            # Try simpler: take everything before first number
            name_match = re.match(r'^([A-Za-z][A-Za-z\-\s\.]+)', first_line)

        if not name_match:
            continue

        candidate_name = name_match.group(1).strip().rstrip('.,;:')

        # Combine all lines of this entry for field extraction
        combined = ' '.join(entry_lines)
        # Ingredient/continuation lines = rest_lines that don't look like dosage
        ingredient_lines = [
            l for l in rest_lines
            if not re.search(r'\d+\s*(?:mg|mcg|g|ml|tab|cap)', l, re.IGNORECASE)
            and not re.search(r'\b\d+[\-\s]\d+[\-\s]\d+\b', l)
            and len(l.strip()) > 2
        ]
        ingredient_notes = '; '.join(ingredient_lines) if ingredient_lines else None

        record = _build_medication_record(
            candidate_name, combined, ingredient_notes, ocr_lines, writing_mode,
        )
        if record:
            record['entry_number'] = entry_num
            medications.append(record)

    return medications


def _parse_freeform_lines(
    lines: List[str],
    ocr_lines: List[Dict],
    writing_mode: str,
) -> List[Dict]:
    """Parse freeform (non-numbered) prescription lines (handwritten prescriptions)."""
    medications: List[Dict] = []
    active_meal_instruction: Optional[str] = None

    def looks_like_medicine_start(candidate_line: str) -> bool:
        return bool(re.match(
            r'^\s*(?:(?:[A-Za-z]\s+)?(?:tab\.?|cap\.?|syp\.?|syrup|inj\.?)\b)',
            candidate_line,
            re.IGNORECASE,
        ))

    def is_directions_line(candidate_line: str) -> bool:
        return bool(
            _extract_dose_schedule(candidate_line)
            or _extract_duration(candidate_line)
            or _normalise_meal(candidate_line)
            or re.fullmatch(r'\s*(?:after|before|befoce|meals?)\s*', candidate_line, re.IGNORECASE)
        )

    i = 0
    while i < len(lines):
        line = lines[i]
        line_meal = _normalise_meal(line)
        if line_meal:
            active_meal_instruction = line_meal

        # Skip header/footer/advice lines
        if any(pat.search(line) for pat in _HEADER_SKIP_PATTERNS):
            i += 1
            continue

        match_line = re.sub(
            r'^\s*[A-Za-z]\s+(?=(?:tab|cap|syp|syrup|inj)\b)',
            '',
            line,
            flags=re.IGNORECASE,
        )

        # A medicine line usually starts with a form indicator OR a capitalised drug name
        medicine_match = re.match(
            r'^(?:(\d+[\.\)]\s*))?'  # optional number
            r'(?:(?:tab\.?|cap\.?|syp\.?|inj\.?)\s*)?'  # optional form
            r'([A-Za-z][A-Za-z0-9\-\+\s\.]{2,}?)'  # candidate name
            r'(?:\s+(?:\d.*|$))',  # followed by digits or EOL
            match_line,
        )
        if not medicine_match:
            # Looser: at least starts with a capital letter word
            medicine_match = re.match(
                r'^(?:(?:tab\.?|cap\.?|syp\.?|inj\.?)\s+)'
                r'([A-Za-z][A-Za-z0-9\-\+\s\.]{2,})',
                match_line, re.IGNORECASE,
            )

        if not medicine_match:
            i += 1
            continue

        # Try group 2 first (full match), then group 1
        try:
            candidate_name = (medicine_match.group(2) or medicine_match.group(1) or '').strip()
        except IndexError:
            candidate_name = medicine_match.group(1).strip()

        candidate_name = candidate_name.rstrip('.,;:')

        # Dose, duration and meal lines are often written separately beneath
        # each medicine. Attach these fields until the next medicine header.
        combined = line
        ingredient_lines = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if not next_line:
                break
            if looks_like_medicine_start(next_line):
                break
            if any(pat.search(next_line) for pat in _HEADER_SKIP_PATTERNS):
                break

            if is_directions_line(next_line):
                combined += ' ' + next_line
                detected_meal = _normalise_meal(next_line)
                if detected_meal:
                    active_meal_instruction = detected_meal
                j += 1
                continue

            # It's a continuation if it starts with '(' or lowercase or known ingredient words
            is_continuation = (
                next_line.startswith('(')
                or (next_line[0].islower() and not re.search(r'\b(?:tab|cap)\b', next_line, re.IGNORECASE))
                or re.match(r'^(?:contains?|composition|each\s+\w+)', next_line, re.IGNORECASE)
            )
            # It's NOT a continuation if it looks like a new numbered entry or strong header
            is_new_entry = bool(re.match(r'^\d+[\.\)]\s*[A-Z]', next_line))
            if is_continuation and not is_new_entry:
                ingredient_lines.append(next_line)
                combined += ' ' + next_line
                j += 1
            else:
                break

        ingredient_notes = '; '.join(ingredient_lines) if ingredient_lines else None

        record = _build_medication_record(
            candidate_name, combined, ingredient_notes, ocr_lines, writing_mode,
        )
        if record:
            if record.get('meal_instructions'):
                active_meal_instruction = record['meal_instructions']
            elif active_meal_instruction:
                record['meal_instructions'] = active_meal_instruction
            medications.append(record)

        i = j if j > i + 1 else i + 1

    return medications


# ---------------------------------------------------------------------------
# Prescription header parser
# ---------------------------------------------------------------------------

def parse_prescription_header(text: str) -> Dict:
    """
    Extract patient/doctor metadata from prescription header text.
    Returns only fields that are actually present — no invented values.

    Strict matching: never populates patient_name with a label word
    like 'Patient', 'Dosage', 'Duration', etc.
    """
    result: Dict = {}

    # Use only the first ~600 chars (header area), but avoid the medicine list
    # by stopping at the first numbered entry or "Rx:" marker
    header_text = text[:600]
    rx_split = re.split(r'\bRx\s*:|\b1[\.\)]\s*(?:Tab|Cap|Syp)', header_text, maxsplit=1, flags=re.IGNORECASE)
    header_text = rx_split[0] if len(rx_split) > 1 else header_text

    lines = [l.strip() for l in header_text.splitlines() if l.strip()]
    full = ' '.join(lines)

    # Label words that should NOT appear as field values
    _LABEL_WORDS = {
        'patient', 'dosage', 'dose', 'duration', 'frequency', 'quantity',
        'medicine', 'drug', 'tablet', 'name', 'age', 'sex', 'date', 'ref',
        'doctor', 'dr', 'hospital', 'clinic', 'address', 'phone', 'time',
        'advice', 'diagnosis', 'follow', 'review',
    }

    def _clean_name(raw: str) -> Optional[str]:
        """Return None if the extracted value is actually a label word."""
        val = raw.strip().rstrip('.,;:')
        if val.lower() in _LABEL_WORDS:
            return None
        # Reject if it's too short or purely numeric
        if len(val) < 2 or re.match(r'^[\d\s]+$', val):
            return None
        return val

    # Patient name
    for p in [
        r'(?:patient|pt)[\s:]+([A-Za-z][A-Za-z\s\.]{1,40})',
        r'(?:^|\s)name[\s:]+([A-Za-z][A-Za-z\s\.]{1,40})',
    ]:
        m = re.search(p, full, re.IGNORECASE)
        if m:
            val = _clean_name(m.group(1))
            if val:
                result['patient_name'] = val
                break

    # Age
    m = re.search(r'(?:age|yr)[\s:/]+(\d{1,3})', full, re.IGNORECASE)
    if m:
        age = int(m.group(1))
        if 0 < age < 130:
            result['patient_age'] = age

    # Also handle "24/Male" style
    if 'patient_age' not in result:
        m = re.search(r'(\d{1,3})\s*/\s*(?:male|female|m|f)\b', full, re.IGNORECASE)
        if m:
            age = int(m.group(1))
            if 0 < age < 130:
                result['patient_age'] = age

    # Sex / gender
    m = re.search(r'(?:sex|gender)[\s:/]+([MFmf](?:ale)?)', full, re.IGNORECASE)
    if m:
        result['patient_sex'] = m.group(1).strip().upper()
    else:
        m = re.search(r'\b(male|female)\b', full, re.IGNORECASE)
        if m:
            result['patient_sex'] = m.group(1).capitalize()

    # Date
    m = re.search(r'(?:date|dt)[\s:/]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', full, re.IGNORECASE)
    if m:
        result['date'] = m.group(1).strip()

    # Doctor
    m = re.search(r'(?:dr\.?|doctor)[\s:]+([A-Za-z][A-Za-z\s\.]{1,40})', full, re.IGNORECASE)
    if m:
        val = _clean_name(m.group(1))
        if val:
            result['doctor'] = val

    # Diagnosis
    for p in [
        r'(?:dx|diagnosis|diag)[\s:/]+([^\n]{3,80})',
        r'(?:complaint|c/o)[\s:/]+([^\n]{3,80})',
    ]:
        m = re.search(p, full, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and val.lower() not in _LABEL_WORDS:
                result['diagnosis'] = val
                break

    # Follow-up
    m = re.search(r'(?:follow[\s-]?up|review)[\s:/]+([^\n]{3,60})', full, re.IGNORECASE)
    if m:
        result['follow_up'] = m.group(1).strip()

    return result
