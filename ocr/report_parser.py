"""Medical report parser — classifies documents and extracts structured data.

Key changes from original:
- Document-type classification BEFORE extraction (lab, prescription, imaging, etc.)
- Lab extraction is now strict: only known medical tests are matched
- Default status is 'unknown' when no reference range is available
- Prescriptions are delegated to the existing prescription_parser module
- Confidence scoring per extracted value
- Never invents reference ranges or diagnoses
"""
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional


# ---------------------------------------------------------------------------
# Common lab test reference ranges (known tests only)
# ---------------------------------------------------------------------------
REFERENCE_RANGES = {
    'hemoglobin': {'unit': 'g/dL', 'male': (13.0, 17.0), 'female': (12.0, 15.5), 'default': (12.0, 17.0)},
    'hb': {'unit': 'g/dL', 'male': (13.0, 17.0), 'female': (12.0, 15.5), 'default': (12.0, 17.0)},
    'rbc': {'unit': 'million/uL', 'default': (4.5, 5.5)},
    'rbc count': {'unit': 'million/uL', 'default': (4.5, 5.5)},
    'wbc': {'unit': '/uL', 'default': (4000, 11000)},
    'wbc count': {'unit': '/uL', 'default': (4000, 11000)},
    'platelets': {'unit': '/uL', 'default': (150000, 400000)},
    'platelet count': {'unit': '/uL', 'default': (150000, 400000)},
    'hematocrit': {'unit': '%', 'default': (36.0, 48.0)},
    'hct': {'unit': '%', 'default': (36.0, 48.0)},
    'pcv': {'unit': '%', 'default': (36.0, 48.0)},
    'mcv': {'unit': 'fL', 'default': (80.0, 100.0)},
    'mch': {'unit': 'pg', 'default': (27.0, 33.0)},
    'mchc': {'unit': 'g/dL', 'default': (32.0, 36.0)},
    'rdw': {'unit': '%', 'default': (11.5, 14.5)},
    'mpv': {'unit': 'fL', 'default': (7.5, 11.5)},
    'esr': {'unit': 'mm/hr', 'default': (0, 20)},
    'neutrophils': {'unit': '%', 'default': (40, 70)},
    'lymphocytes': {'unit': '%', 'default': (20, 40)},
    'monocytes': {'unit': '%', 'default': (2, 8)},
    'eosinophils': {'unit': '%', 'default': (1, 4)},
    'basophils': {'unit': '%', 'default': (0, 1)},
    'glucose': {'unit': 'mg/dL', 'default': (70, 110)},
    'fasting glucose': {'unit': 'mg/dL', 'default': (70, 100)},
    'fasting blood sugar': {'unit': 'mg/dL', 'default': (70, 100)},
    'fbs': {'unit': 'mg/dL', 'default': (70, 100)},
    'ppbs': {'unit': 'mg/dL', 'default': (70, 140)},
    'random blood sugar': {'unit': 'mg/dL', 'default': (70, 140)},
    'blood sugar': {'unit': 'mg/dL', 'default': (70, 140)},
    'creatinine': {'unit': 'mg/dL', 'default': (0.6, 1.2)},
    'serum creatinine': {'unit': 'mg/dL', 'default': (0.6, 1.2)},
    'urea': {'unit': 'mg/dL', 'default': (15, 40)},
    'blood urea': {'unit': 'mg/dL', 'default': (15, 40)},
    'bun': {'unit': 'mg/dL', 'default': (7, 20)},
    'uric acid': {'unit': 'mg/dL', 'default': (3.5, 7.0)},
    'cholesterol': {'unit': 'mg/dL', 'default': (0, 200)},
    'total cholesterol': {'unit': 'mg/dL', 'default': (0, 200)},
    'hdl': {'unit': 'mg/dL', 'default': (40, 60)},
    'hdl cholesterol': {'unit': 'mg/dL', 'default': (40, 60)},
    'ldl': {'unit': 'mg/dL', 'default': (0, 130)},
    'ldl cholesterol': {'unit': 'mg/dL', 'default': (0, 130)},
    'vldl': {'unit': 'mg/dL', 'default': (5, 40)},
    'triglycerides': {'unit': 'mg/dL', 'default': (0, 150)},
    'sgpt': {'unit': 'U/L', 'default': (7, 56)},
    'alt': {'unit': 'U/L', 'default': (7, 56)},
    'sgot': {'unit': 'U/L', 'default': (10, 40)},
    'ast': {'unit': 'U/L', 'default': (10, 40)},
    'bilirubin': {'unit': 'mg/dL', 'default': (0.1, 1.2)},
    'total bilirubin': {'unit': 'mg/dL', 'default': (0.1, 1.2)},
    'direct bilirubin': {'unit': 'mg/dL', 'default': (0.0, 0.3)},
    'indirect bilirubin': {'unit': 'mg/dL', 'default': (0.1, 1.0)},
    'albumin': {'unit': 'g/dL', 'default': (3.5, 5.0)},
    'serum albumin': {'unit': 'g/dL', 'default': (3.5, 5.0)},
    'globulin': {'unit': 'g/dL', 'default': (2.0, 3.5)},
    'total protein': {'unit': 'g/dL', 'default': (6.0, 8.3)},
    'alkaline phosphatase': {'unit': 'U/L', 'default': (44, 147)},
    'alp': {'unit': 'U/L', 'default': (44, 147)},
    'ggt': {'unit': 'U/L', 'default': (9, 48)},
    'tsh': {'unit': 'mIU/L', 'default': (0.4, 4.0)},
    't3': {'unit': 'ng/dL', 'default': (80, 200)},
    't4': {'unit': 'ug/dL', 'default': (5.0, 12.0)},
    'free t3': {'unit': 'pg/mL', 'default': (2.0, 4.4)},
    'free t4': {'unit': 'ng/dL', 'default': (0.82, 1.77)},
    'hba1c': {'unit': '%', 'default': (4.0, 5.6)},
    'glycated hemoglobin': {'unit': '%', 'default': (4.0, 5.6)},
    'sodium': {'unit': 'mEq/L', 'default': (136, 145)},
    'potassium': {'unit': 'mEq/L', 'default': (3.5, 5.0)},
    'chloride': {'unit': 'mEq/L', 'default': (98, 106)},
    'calcium': {'unit': 'mg/dL', 'default': (8.5, 10.5)},
    'phosphorus': {'unit': 'mg/dL', 'default': (2.5, 4.5)},
    'magnesium': {'unit': 'mg/dL', 'default': (1.7, 2.2)},
    'iron': {'unit': 'ug/dL', 'default': (60, 170)},
    'serum iron': {'unit': 'ug/dL', 'default': (60, 170)},
    'tibc': {'unit': 'ug/dL', 'default': (250, 370)},
    'ferritin': {'unit': 'ng/mL', 'default': (20, 250)},
    'vitamin d': {'unit': 'ng/mL', 'default': (30, 100)},
    'vitamin b12': {'unit': 'pg/mL', 'default': (200, 900)},
    'folate': {'unit': 'ng/mL', 'default': (2.7, 17.0)},
    'crp': {'unit': 'mg/L', 'default': (0, 10)},
    'c-reactive protein': {'unit': 'mg/L', 'default': (0, 10)},
    'psa': {'unit': 'ng/mL', 'default': (0, 4.0)},
    'inr': {'unit': '', 'default': (0.8, 1.2)},
    'pt': {'unit': 'seconds', 'default': (11, 13.5)},
    'aptt': {'unit': 'seconds', 'default': (25, 35)},
    'fibrinogen': {'unit': 'mg/dL', 'default': (200, 400)},
    'd-dimer': {'unit': 'ng/mL', 'default': (0, 500)},
    'amylase': {'unit': 'U/L', 'default': (28, 100)},
    'lipase': {'unit': 'U/L', 'default': (0, 160)},
    'ck': {'unit': 'U/L', 'default': (30, 200)},
    'ck-mb': {'unit': 'U/L', 'default': (0, 25)},
    'ldh': {'unit': 'U/L', 'default': (140, 280)},
    'troponin': {'unit': 'ng/mL', 'default': (0, 0.04)},
    'hcg': {'unit': 'mIU/mL', 'default': (0, 5)},
    'prolactin': {'unit': 'ng/mL', 'default': (2, 18)},
    'cortisol': {'unit': 'ug/dL', 'default': (6, 23)},
}

# Build a set of known lab test names (lower-cased) for strict matching
_KNOWN_LAB_TESTS = set(REFERENCE_RANGES.keys())


# ---------------------------------------------------------------------------
# Document-type classification
# ---------------------------------------------------------------------------

# Weighted keyword lists for each document category
_CLASSIFICATION_PATTERNS = {
    'laboratory_report': {
        'strong': [
            'pathology', 'laboratory', 'lab report', 'hematology', 'biochemistry',
            'complete blood count', 'cbc', 'hemogram', 'blood test', 'lipid profile',
            'liver function', 'kidney function', 'thyroid profile', 'urine analysis',
            'urinalysis', 'serology', 'microbiology', 'culture sensitivity',
            'reference range', 'ref range', 'normal range', 'biological reference',
            'specimen', 'sample type', 'blood sample', 'serum', 'plasma',
            'test name', 'test result', 'investigation',
        ],
        'moderate': [
            'hemoglobin', 'wbc', 'rbc', 'platelets', 'hematocrit', 'mcv', 'mch',
            'creatinine', 'bilirubin', 'sgpt', 'sgot', 'cholesterol', 'triglycerides',
            'tsh', 'hba1c', 'glucose', 'urea', 'albumin', 'esr',
            'g/dl', 'mg/dl', 'u/l', 'meq/l', 'miu/l', '/ul',
            'million/ul', 'cells/cumm',
        ],
    },
    'prescription': {
        'strong': [
            'prescription', 'rx', 'sig:', 'tab.', 'tab ', 'cap.', 'cap ',
            'syrup', 'inj.', 'inj ', 'ointment', 'drops', 'cream',
            'dispense', 'refill', 'substitution', 'pharmacist',
            'take ', 'after food', 'before food', 'after meal', 'before meal',
            'twice daily', 'once daily', 'three times', 'thrice daily',
            'at bedtime', 'hs', 'od', 'bd', 'tid', 'tds', 'qid',
            'chief complaint', 'c/o', 'chief complaints',
            'diagnosis', 'clinical finding', 'follow up', 'follow-up',
            'advice', 'medicine', 'treatment',
        ],
        'moderate': [
            'fever', 'cough', 'cold', 'pain', 'headache', 'vomiting',
            'diarrhea', 'weakness', 'chills', 'swelling',
            'mg ', 'mcg', 'ml ', 'days', 'weeks',
            'opd', 'ipd', 'outpatient', 'consultation',
            'dr.', 'doctor', 'clinic', 'hospital',
            'patient', 'age', 'sex', 'weight',
        ],
    },
    'diagnostic_imaging': {
        'strong': [
            'x-ray', 'xray', 'radiograph', 'mri', 'ct scan', 'computed tomography',
            'magnetic resonance', 'ultrasound', 'usg', 'sonography', 'ecg',
            'electrocardiogram', 'echo', 'echocardiography', 'pet scan',
            'mammography', 'dexa', 'bone density', 'fluoroscopy',
            'impression:', 'findings:', 'technique:', 'clinical history:',
            'radiologist', 'radiology',
        ],
        'moderate': [
            'no abnormality', 'normal study', 'within normal limits',
            'fracture', 'opacity', 'effusion', 'mass', 'lesion',
            'contrast', 'coronal', 'sagittal', 'axial',
        ],
    },
    'discharge_summary': {
        'strong': [
            'discharge summary', 'discharge', 'admitted on', 'discharged on',
            'date of admission', 'date of discharge', 'length of stay',
            'discharge diagnosis', 'discharge medication', 'condition at discharge',
            'hospital course', 'course in hospital',
        ],
        'moderate': [
            'ward', 'bed no', 'inpatient', 'ipd',
            'surgery', 'procedure', 'operation',
        ],
    },
}

# Words/patterns that should NEVER be treated as lab test names
_NON_LAB_PATTERNS = {
    # Administrative / demographic
    'name', 'patient', 'age', 'sex', 'gender', 'dob', 'date of birth',
    'address', 'phone', 'tel', 'mobile', 'email', 'id', 'reg', 'registration',
    'mrn', 'uhid', 'opd', 'ipd', 'ward', 'bed', 'room',
    # Document structure
    'page', 'sr', 'no', 'date', 'time', 'timing', 'ref', 'reference',
    'test', 'value', 'unit', 'range', 'result', 'status', 'method',
    # Hospital / doctor info
    'hospital', 'clinic', 'centre', 'center', 'lab', 'department',
    'pathology', 'doctor', 'dr', 'consultant', 'technician',
    'city', 'state', 'pin', 'zip', 'general', 'smart',
    # Prescription / clinical
    'height', 'weight', 'bp', 'blood pressure', 'pulse', 'temperature', 'temp',
    'spo2', 'respiratory rate', 'rr', 'hr', 'heart rate', 'bmi',
    'complaint', 'complaints', 'c/o', 'diagnosis', 'fever', 'cough', 'cold',
    'pain', 'headache', 'vomiting', 'chills', 'swelling', 'weakness',
    'advice', 'follow', 'review', 'visit', 'next',
    # Medicine-related
    'tab', 'tablet', 'cap', 'capsule', 'syrup', 'inj', 'injection',
    'ointment', 'cream', 'drops', 'mg', 'mcg', 'ml',
    # Duration / frequency noise
    'days', 'day', 'weeks', 'week', 'months', 'month', 'morning', 'evening',
    'night', 'daily', 'dose', 'total', 'quantity',
    # OCR noise
    'b', 'mmc', 'ph', 'rs', 'rs.', 'sl',
}


def classify_document(text: str) -> Dict:
    """
    Classify a medical document into a category based on keyword analysis.

    Returns:
        {
            'category': str,        # 'laboratory_report', 'prescription', 'diagnostic_imaging',
                                    # 'discharge_summary', 'other_medical_document', 'unknown'
            'confidence': float,    # 0.0 to 1.0
            'scores': dict,         # per-category scores for transparency
        }
    """
    if not text or not text.strip():
        return {'category': 'unknown', 'confidence': 0.0, 'scores': {}}

    text_lower = text.lower()
    scores = {}

    for category, patterns in _CLASSIFICATION_PATTERNS.items():
        score = 0.0
        for kw in patterns.get('strong', []):
            if kw in text_lower:
                score += 3.0
        for kw in patterns.get('moderate', []):
            if kw in text_lower:
                score += 1.0
        scores[category] = score

    if not scores or max(scores.values()) == 0:
        return {'category': 'unknown', 'confidence': 0.0, 'scores': scores}

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    # Compute confidence as ratio of best to total, scaled
    total = sum(scores.values())
    if total > 0:
        dominance = best_score / total
    else:
        dominance = 0.0

    # Map raw score to confidence
    if best_score >= 15:
        base_confidence = 0.9
    elif best_score >= 8:
        base_confidence = 0.7
    elif best_score >= 4:
        base_confidence = 0.5
    else:
        base_confidence = 0.3

    confidence = min(1.0, base_confidence * (0.5 + 0.5 * dominance))

    # Handwritten prescriptions may contain very few of the keyword phrases
    # used by the generic scorer. A prescription marker together with a
    # medicine form and a dose pattern is strong structural evidence.
    has_prescription_marker = bool(re.search(r'\b(?:rx|prescription)\b', text_lower))
    has_medicine_form = bool(re.search(r'\b(?:tab\.?|cap\.?|syp\.?|syrup|inj\.?)\b', text_lower))
    has_dose_pattern = bool(
        re.search(r'\b[01]\s*[-–—]\s*[01]\s*[-–—]\s*[01]\b', text_lower)
        or re.search(r'\b(?:once|twice|three times)\s+(?:a\s+)?daily\b', text_lower)
    )
    if best_category == 'prescription' and has_medicine_form and has_dose_pattern:
        confidence = max(confidence, 0.82 if has_prescription_marker else 0.76)

    # If confidence is too low, return 'other_medical_document' or 'unknown'
    if confidence < 0.25:
        return {'category': 'unknown', 'confidence': confidence, 'scores': scores}
    if confidence < 0.35:
        return {'category': 'other_medical_document', 'confidence': confidence, 'scores': scores}

    return {'category': best_category, 'confidence': round(confidence, 3), 'scores': scores}


# ---------------------------------------------------------------------------
# Report-type detection (more specific sub-type for lab reports)
# ---------------------------------------------------------------------------

REPORT_TYPE_PATTERNS = {
    'Complete Blood Count': ['cbc', 'complete blood count', 'hemogram', 'blood count', 'wbc', 'rbc', 'hemoglobin', 'hematocrit', 'platelets'],
    'Liver Function Test': ['liver function', 'lft', 'sgpt', 'sgot', 'bilirubin', 'alt', 'ast', 'alkaline phosphatase'],
    'Kidney Function Test': ['kidney function', 'kft', 'renal', 'creatinine', 'urea', 'bun'],
    'Lipid Profile': ['lipid profile', 'cholesterol', 'hdl', 'ldl', 'triglycerides'],
    'Thyroid Profile': ['thyroid', 'tsh', 't3', 't4'],
    'Blood Sugar': ['glucose', 'blood sugar', 'fasting', 'hba1c', 'diabetes'],
    'Urine Analysis': ['urine', 'urinalysis'],
    'X-Ray Report': ['x-ray', 'xray', 'radiograph'],
    'MRI Report': ['mri', 'magnetic resonance'],
    'CT Scan': ['ct scan', 'computed tomography'],
}


def detect_report_type(text: str) -> str:
    """Detect the type of medical report from OCR text."""
    text_lower = text.lower()
    scores = {}
    for report_type, keywords in REPORT_TYPE_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[report_type] = score
    if scores:
        return max(scores, key=scores.get)
    return 'General Medical Report'


# ---------------------------------------------------------------------------
# Strict lab value extraction
# ---------------------------------------------------------------------------

def _reconstruct_lines(text: str) -> str:
    """Combine fragmented OCR lines into test-name + value lines.

    PaddleOCR often puts each table cell on its own line, e.g.:
        Hemoglobin
        14.2
        g/dL
        13.0-17.0
    This function reconstructs those into: "Hemoglobin 14.2 g/dL 13.0-17.0"
    """
    raw_lines = [l.strip() for l in text.split('\n') if l.strip()]
    merged = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        # If this line is purely a test name (alpha) and the next is a number,
        # merge them
        if (re.match(r'^[A-Za-z][A-Za-z\s\(\)/\-]+$', line)
                and i + 1 < len(raw_lines)
                and re.match(r'^[\d]+\.?\d*$', raw_lines[i + 1].strip())):
            combined = line
            j = i + 1
            # Grab the numeric value and any following unit/ref-range lines
            while j < len(raw_lines) and j < i + 4:
                next_l = raw_lines[j].strip()
                # Stop if it looks like another test name (alpha only, >3 chars)
                if (re.match(r'^[A-Za-z][A-Za-z\s\(\)/\-]+$', next_l)
                        and len(next_l) > 3
                        and next_l.upper() not in ('G', 'MG', 'UL', 'DL', 'ML')):
                    # But only stop if the NEXT line after this is also a number
                    # (meaning this is a new test name, not a unit)
                    if j + 1 < len(raw_lines) and re.match(r'^[\d]+\.?\d*$', raw_lines[j + 1].strip()):
                        break
                combined += ' ' + next_l
                j += 1
            merged.append(combined)
            i = j
        else:
            merged.append(line)
            i += 1
    return '\n'.join(merged)


def _is_known_lab_test(name: str) -> bool:
    """Check if a candidate name matches a known lab test.

    Strict matching only — substring matches are rejected unless the candidate
    IS a known test name (or contains it as a complete word boundary match).
    This prevents 'folic acid' from matching 'acid' → 'uric acid', and
    'morning' from matching anything in the lab test set.
    """
    name_lower = name.lower().strip()
    # Direct exact match
    if name_lower in _KNOWN_LAB_TESTS:
        return True
    # Whole-word forward match: candidate contains a known test name as a phrase
    for known in _KNOWN_LAB_TESTS:
        # Only accept if both strings are long enough to avoid false positives
        if len(name_lower) < 4 or len(known) < 4:
            continue
        # The known test name must appear as a whole-word phrase in the candidate
        if re.search(r'\b' + re.escape(known) + r'\b', name_lower):
            return True
    return False


def _is_excluded_name(name: str) -> bool:
    """Check if a candidate name should be excluded from lab results."""
    name_lower = name.lower().strip()
    # Direct match against exclusion list
    if name_lower in _NON_LAB_PATTERNS:
        return True
    # Check each word
    words = name_lower.split()
    if len(words) == 1 and name_lower in _NON_LAB_PATTERNS:
        return True
    # Very short single-word names are likely noise
    if len(words) == 1 and len(name_lower) < 3:
        return True
    return False


def _extract_inline_reference(line: str) -> Optional[Tuple[float, float, str]]:
    """Try to extract a reference range from the same line, e.g. '13.0-17.0 g/dL'."""
    # Pattern: number-number (with optional unit after)
    m = re.search(r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*([A-Za-z/%]+(?:/[A-Za-z]+)?)?', line)
    if m:
        try:
            low = float(m.group(1))
            high = float(m.group(2))
            unit = m.group(3) or ''
            if low < high:
                return (low, high, unit)
        except ValueError:
            pass
    return None


def _extract_key_values_legacy(text: str) -> List[Dict]:
    """Extract lab test values from OCR text — STRICT mode.

    Only extracts values that match known medical lab tests.
    Returns 'unknown' status when no reference range is available.
    Never treats arbitrary numbers as lab results.
    """
    results = []

    # First, reconstruct fragmented OCR lines
    text = _reconstruct_lines(text)
    lines = text.split('\n')

    # Pattern for "TestName Value Unit" on a single reconstructed line
    pattern = re.compile(
        r'([A-Za-z][A-Za-z\s/\(\)\-]+?)\s*[:=\-]?\s*([\d]+\.?\d*)\s*([A-Za-z/%]+(?:/[A-Za-z]+)?)?'
    )

    seen_tests = set()  # avoid duplicates

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        matches = pattern.findall(line)
        for match in matches:
            test_name = match[0].strip().rstrip(':=-')
            value_str = match[1].strip()
            unit = match[2].strip() if len(match) > 2 else ''

            # --- STRICT FILTERING ---

            # Skip if excluded
            if _is_excluded_name(test_name):
                continue

            # Skip if not a known lab test
            if not _is_known_lab_test(test_name):
                continue

            # Skip if too short
            if len(test_name) < 2:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            # Avoid duplicate test names
            test_key = test_name.lower().strip()
            if test_key in seen_tests:
                continue
            seen_tests.add(test_key)

            # Check against reference ranges
            status = 'unknown'  # DEFAULT IS UNKNOWN, not 'normal'
            ref_range = None
            confidence = 0.7  # base confidence for known test match

            if test_key in REFERENCE_RANGES:
                ref = REFERENCE_RANGES[test_key]
                low, high = ref.get('default', (None, None))
                if low is not None and high is not None:
                    ref_range = f"{low}-{high} {ref.get('unit', '')}".strip()
                    confidence = 0.85
                    if value < low:
                        status = 'low'
                        confidence = 0.9
                    elif value > high:
                        status = 'high'
                        confidence = 0.9
                    else:
                        status = 'normal'
                        confidence = 0.85

            # Also try to extract inline reference range from the line
            inline_ref = _extract_inline_reference(line)
            if inline_ref and ref_range is None:
                low, high, ref_unit = inline_ref
                ref_range = f"{low}-{high} {ref_unit}".strip()
                if value < low:
                    status = 'low'
                    confidence = 0.8
                elif value > high:
                    status = 'high'
                    confidence = 0.8
                else:
                    status = 'normal'
                    confidence = 0.75

            # Check for abnormal flags in the original line
            line_upper = line.upper()
            if any(flag in line_upper for flag in ['HIGH', 'ELEVATED', 'H ', ' H', '*H']):
                if status == 'normal' or status == 'unknown':
                    status = 'high'
                    confidence = max(confidence, 0.85)
            elif any(flag in line_upper for flag in ['LOW', 'DECREASED', 'L ', ' L', '*L']):
                if status == 'normal' or status == 'unknown':
                    status = 'low'
                    confidence = max(confidence, 0.85)

            results.append({
                'test_name': test_name,
                'value': value,
                'unit': unit or (REFERENCE_RANGES.get(test_key, {}).get('unit', '')),
                'status': status,
                'reference_range': ref_range,
                'confidence': round(confidence, 3),
            })

    return results


# PaddleOCR commonly emits each table cell on a separate line. Keep aliases
# explicit so table rows such as "White blood cells" and "Hemoglobin A1c"
# are associated with their correct test instead of matching a partial name.
_TABLE_LAB_ALIASES = {
    **{name: name for name in REFERENCE_RANGES},
    'white blood cells': 'wbc',
    'white blood cell': 'wbc',
    'red blood cells': 'rbc',
    'red blood cell': 'rbc',
    'hemoglobin a1c': 'hba1c',
    'haemoglobin a1c': 'hba1c',
    'glycated hemoglobin': 'hba1c',
    'glycated haemoglobin': 'hba1c',
    'glucose fasting': 'fasting glucose',
    'glucose fasting blood': 'fasting glucose',
}
_TABLE_CANONICAL_DISPLAY = {
    'wbc': 'White blood cells',
    'rbc': 'Red blood cells',
    'hba1c': 'Hemoglobin A1c',
    'fasting glucose': 'Glucose, fasting',
    'potassium': 'Potassium',
}


def _match_table_test(line: str) -> Optional[Tuple[str, str, str]]:
    """Return (display name, reference key, text after name) for a known test row."""
    tokens = list(re.finditer(r'[A-Za-z0-9]+', line))
    if not tokens:
        return None
    line_tokens = [token.group(0).lower() for token in tokens]

    aliases = sorted(
        _TABLE_LAB_ALIASES.items(),
        key=lambda item: (len(item[0].split()), len(item[0])),
        reverse=True,
    )
    for alias, reference_key in aliases:
        alias_tokens = re.findall(r'[A-Za-z0-9]+', alias.lower())
        if line_tokens[:len(alias_tokens)] != alias_tokens:
            continue
        name_end = tokens[len(alias_tokens) - 1].end()
        display_name = line[:name_end].strip(' \t:=-')
        return display_name, reference_key, line[name_end:].strip()

    # Printed lab labels are sometimes misread by one character (for example,
    # PaddleOCR can read "Potassium" as "Potasslum"). Permit a single close
    # token match for longer known test names only; this avoids turning random
    # prose or short abbreviations into lab results.
    for alias, reference_key in aliases:
        alias_tokens = re.findall(r'[A-Za-z0-9]+', alias.lower())
        if len(alias_tokens) != 1 or len(line_tokens[0]) < 6 or len(alias_tokens[0]) < 6:
            continue
        similarity = SequenceMatcher(None, line_tokens[0], alias_tokens[0]).ratio()
        if similarity < 0.86:
            continue
        name_end = tokens[0].end()
        display_name = _TABLE_CANONICAL_DISPLAY.get(reference_key, alias.title())
        return display_name, reference_key, line[name_end:].strip()
    return None


def _first_lab_number(text: str) -> Optional[Tuple[float, str, str]]:
    """Read the first result number and return (value, unit tail, original line)."""
    candidate = text.strip()
    # A duplicated OCR punctuation mark can turn 5.8 into .5.8. Correct only
    # that two-decimal pattern; preserve legitimate leading-decimal values such
    # as .82.
    candidate = re.sub(r'^[\s]*[.,](?=\d+\.\d)', '', candidate)
    match = re.search(r'(?<![A-Za-z0-9])([+-]?(?:\d+\.\d*|\.\d+|\d+))', candidate)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value, candidate[match.end():].strip(), text


def _reference_from_lines(lines: List[str]) -> Optional[Tuple[float, Optional[float], str]]:
    """Extract a printed two-sided or one-sided reference range."""
    for line in lines:
        match = re.search(
            r'(?<![\d.])([+-]?\d+(?:\.\d+)?)\s*[-–—]\s*([+-]?\d+(?:\.\d+)?)',
            line,
        )
        if match:
            low, high = float(match.group(1)), float(match.group(2))
            if low < high:
                return low, high, f'{match.group(1)}-{match.group(2)}'
        match = re.search(r'(<=|<|≤)\s*([+-]?\d+(?:\.\d+)?)', line)
        if match:
            return float('-inf'), float(match.group(2)), f'<{match.group(2)}'
        match = re.search(r'(>=|>|≥)\s*([+-]?\d+(?:\.\d+)?)', line)
        if match:
            return float(match.group(2)), None, f'>{match.group(2)}'
    return None


def _row_flag(lines: List[str], value_line: str) -> Optional[str]:
    """Read an explicit H/L flag without mistaking units such as /uL for flags."""
    for line in lines:
        token = line.strip().upper().replace('*', '').strip()
        if token in {'H', 'HIGH', 'L', 'LOW'}:
            return 'high' if token in {'H', 'HIGH'} else 'low'
    match = re.search(r'\s(?:HIGH|LOW|H|L)\s*$', value_line, re.IGNORECASE)
    if match:
        token = match.group(0).strip().upper()
        return 'high' if token in {'H', 'HIGH'} else 'low'
    return None


def _fallback_reference(reference_key: str) -> Optional[Tuple[float, float, str]]:
    ref = REFERENCE_RANGES.get(reference_key)
    if not ref:
        return None
    bounds = ref.get('default')
    if not bounds or bounds[0] is None or bounds[1] is None:
        return None
    low, high = bounds
    return float(low), float(high), f'{low}-{high}'


def _extract_table_key_values(text: str) -> List[Dict]:
    """Extract lab results from line-oriented OCR, including separated table cells."""
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    row_starts = []
    for index, line in enumerate(raw_lines):
        matched = _match_table_test(line)
        if matched:
            row_starts.append((index, matched))

    results = []
    seen = set()
    for position, (line_index, (test_name, reference_key, inline_tail)) in enumerate(row_starts):
        next_index = row_starts[position + 1][0] if position + 1 < len(row_starts) else len(raw_lines)
        row_lines = raw_lines[line_index + 1:next_index]
        candidate_lines = [inline_tail] if inline_tail else []
        candidate_lines.extend(row_lines)

        value_info = None
        value_line_index = -1
        for candidate_index, candidate in enumerate(candidate_lines):
            if not candidate:
                continue
            # Do not mistake a standalone reference range for a result value.
            if re.match(r'^\s*[<>≤≥]?\s*\d+(?:\.\d+)?\s*[-–—]\s*\d', candidate):
                continue
            parsed_number = _first_lab_number(candidate)
            if parsed_number:
                value_info = parsed_number
                value_line_index = candidate_index
                break
        if not value_info:
            continue

        value, unit_tail, original_value_line = value_info
        remaining_lines = candidate_lines[value_line_index + 1:]
        row_context = [original_value_line, *remaining_lines]
        report_reference = _reference_from_lines(row_context)
        reference = report_reference or _fallback_reference(reference_key)
        reference_text = report_reference[2] if report_reference else (
            f'{reference[2]} {REFERENCE_RANGES.get(reference_key, {}).get("unit", "")}'.strip()
            if reference else None
        )

        unit_text = re.split(
            r'(?<![\d.])(?:[+-]?\d+(?:\.\d+)?)\s*[-–—]\s*(?:[+-]?\d+(?:\.\d+)?)|[<>≤≥]\s*\d',
            unit_tail,
            maxsplit=1,
        )[0]
        unit_text = re.sub(r'\s+(?:HIGH|LOW|H|L)\s*$', '', unit_text, flags=re.IGNORECASE)
        unit_text = unit_text.strip(' \t,:;–—-')
        if 'x10' in unit_text.lower() and reference_key in {'wbc', 'white blood cells', 'platelets'}:
            unit_text = 'x10³/µL'
        elif 'x10' in unit_text.lower() and reference_key in {'rbc', 'red blood cells'}:
            unit_text = 'x10⁶/µL'
        else:
            unit_text = unit_text.replace('μ', 'µ')
        if not unit_text:
            unit_text = REFERENCE_RANGES.get(reference_key, {}).get('unit', '')

        explicit_flag = _row_flag(remaining_lines, original_value_line)
        if reference:
            low, high, _ = reference
            if value < low:
                status = 'low'
            elif high is not None and value > high:
                status = 'high'
            else:
                status = 'normal'
        elif explicit_flag:
            status = explicit_flag
        else:
            status = 'unknown'
        # If the report gives no range, retain its explicit flag. A printed
        # range takes precedence over a possibly noisy H/L mark.
        if not report_reference and explicit_flag:
            status = explicit_flag

        dedupe_key = reference_key
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        results.append({
            'test_name': test_name,
            'value': value,
            'unit': unit_text,
            'status': status,
            'reference_range': reference_text,
            'confidence': 0.9 if report_reference else 0.82 if reference else 0.7,
        })
    return results


def extract_key_values(text: str) -> List[Dict]:
    """Extract recognized lab values from inline or multi-line OCR table layouts."""
    if not text or not text.strip():
        return []
    table_values = _extract_table_key_values(text)
    if table_values:
        return table_values
    return _extract_key_values_legacy(text)


# ---------------------------------------------------------------------------
# Main parser entry point
# ---------------------------------------------------------------------------

def parse_medical_report(
    text: str,
    writing_mode: str = 'printed',
    ocr_lines: Optional[List[Dict]] = None,
) -> Dict:
    """Parse OCR text from a medical report into structured data.

    This function now:
    1. Classifies the document type first
    2. Only extracts lab values for actual lab reports
    3. Delegates prescriptions to the prescription_parser
    4. Returns appropriate structures per document type
    """
    if not text or text.strip() == '':
        return {
            'document_category': 'unknown',
            'report_type': 'Unknown',
            'summary': 'No text could be extracted from the image.',
            'key_findings': [],
            'important_values': {},
            'abnormal_values': {},
            'sections': {'raw': ''},
            'classification_confidence': 0.0,
        }

    # Step 1: Classify the document
    classification = classify_document(text)
    category = classification['category']
    class_confidence = classification['confidence']

    # Step 2: Branch based on classification
    if category == 'prescription':
        return _parse_as_prescription(text, writing_mode, classification, ocr_lines)
    elif category == 'diagnostic_imaging':
        return _parse_as_imaging(text, classification)
    elif category == 'discharge_summary':
        return _parse_as_discharge(text, classification)
    elif category == 'laboratory_report':
        return _parse_as_lab_report(text, writing_mode, classification)
    else:
        # For 'other_medical_document' or 'unknown', try lab extraction first
        # but only keep results if we actually find known lab tests.
        # If the text also looks partially like a prescription, prefer that.
        return _parse_as_generic(text, writing_mode, classification, ocr_lines)


def _parse_as_lab_report(text: str, writing_mode: str, classification: Dict) -> Dict:
    """Parse a document classified as a laboratory report."""
    report_type = detect_report_type(text)
    extracted_values = extract_key_values(text)

    important_values = {}
    abnormal_values = {}
    key_findings = []

    for item in extracted_values:
        key = item['test_name']
        val_str = f"{item['value']} {item['unit']}"
        status_str = f" [{item['status'].upper()}]" if item['status'] != 'normal' else ''
        important_values[key] = val_str

        if item['status'] == 'high':
            abnormal_values[key] = f"{val_str} (HIGH - ref: {item['reference_range']})"
            key_findings.append(f"{key} is elevated at {val_str}")
        elif item['status'] == 'low':
            abnormal_values[key] = f"{val_str} (LOW - ref: {item['reference_range']})"
            key_findings.append(f"{key} is below normal at {val_str}")
        elif item['status'] == 'unknown':
            key_findings.append(f"{key}: {val_str} — status unknown (no reference range available)")

    if not key_findings:
        if extracted_values:
            key_findings.append('All extracted lab values appear within normal ranges')
        else:
            key_findings.append('No standard laboratory values could be identified in this document')

    # Build summary
    summary_parts = [f"Report Type: {report_type}"]
    summary_parts.append(f"Lab values extracted: {len(extracted_values)}")
    if abnormal_values:
        summary_parts.append(f"Abnormal values found: {len(abnormal_values)}")
    elif extracted_values:
        summary_parts.append("No abnormal values detected")
    else:
        summary_parts.append("No laboratory values detected in this document")
    summary = '. '.join(summary_parts) + '.'

    return {
        'document_category': 'laboratory_report',
        'report_type': report_type,
        'summary': summary,
        'key_findings': key_findings,
        'important_values': important_values,
        'abnormal_values': abnormal_values,
        'lab_values': extracted_values,  # full structured list with confidence
        'report_comment': next((
            match.group(1).strip()
            for line in text.splitlines()
            if (match := re.match(r'^\s*(?:comment|interpretation|clinical correlation)\s*:\s*(.+)$', line, re.IGNORECASE))
        ), None),
        'sections': {'raw': text},
        'classification_confidence': classification['confidence'],
    }


def _parse_as_prescription(
    text: str,
    writing_mode: str,
    classification: Dict,
    ocr_lines: Optional[List[Dict]] = None,
) -> Dict:
    """Parse a document classified as a medical prescription.

    Delegates to the existing prescription_parser module for medication extraction.
    """
    from ocr.prescription_parser import parse_prescription, parse_prescription_header

    header = parse_prescription_header(text)
    medications = parse_prescription(text, ocr_lines=ocr_lines, writing_mode=writing_mode)

    # Extract additional prescription-specific fields
    prescription_data = _extract_prescription_fields(text)

    key_findings = []
    if header.get('diagnosis'):
        key_findings.append(f"Diagnosis: {header['diagnosis']}")
    if medications:
        key_findings.append(f"{len(medications)} medication(s) identified")
        review_count = sum(1 for m in medications if m.get('requires_review', False))
        if review_count > 0:
            key_findings.append(f"{review_count} medication(s) flagged for manual review")
    else:
        key_findings.append("No medications could be extracted — manual review recommended")

    summary_parts = ["Document Type: Medical Prescription"]
    if header.get('patient_name'):
        summary_parts.append(f"Patient: {header['patient_name']}")
    if header.get('doctor'):
        summary_parts.append(f"Doctor: {header['doctor']}")
    summary_parts.append(f"Medications found: {len(medications)}")
    summary = '. '.join(summary_parts) + '.'

    return {
        'document_category': 'prescription',
        'report_type': 'Medical Prescription',
        'summary': summary,
        'key_findings': key_findings,
        'important_values': {},  # No lab values for prescriptions
        'abnormal_values': {},   # No lab values for prescriptions
        'prescription_data': {
            'patient_info': header,
            'medications': medications,
            'clinical_info': prescription_data,
        },
        'sections': {'raw': text},
        'classification_confidence': classification['confidence'],
        'confidence_breakdown': {
            'document_classification': classification['confidence'],
            'ocr_transcription': None,   # filled in by service layer when available
            'field_extraction': 0.7 if header else 0.3,
            'medicine_name': (
                round(sum(m.get('confidence', 0.5) for m in medications) / len(medications), 3)
                if medications else None
            ),
            'dosage_duration': (
                round(sum(
                    0.9 if (m.get('strength') or m.get('dose_schedule')) else 0.4
                    for m in medications
                ) / len(medications), 3)
                if medications else None
            ),
        },
    }


def _extract_prescription_fields(text: str) -> Dict:
    """Extract structured prescription fields beyond medications."""
    result = {}
    full_text = text
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Chief complaints
    for pattern in [
        r'(?:chief\s+complaint|c/o|complaints?)[s:\s]+(.+?)(?:\n|$)',
        r'(?:presenting\s+complaint)[s:\s]+(.+?)(?:\n|$)',
    ]:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            result['chief_complaints'] = m.group(1).strip()
            break

    # Clinical findings
    for pattern in [
        r'(?:clinical\s+finding|examination|o/e)[s:\s]+(.+?)(?:\n|$)',
        r'(?:on\s+examination)[:\s]+(.+?)(?:\n|$)',
    ]:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            result['clinical_findings'] = m.group(1).strip()
            break

    # Diagnosis
    for pattern in [
        r'(?:diagnosis|dx|provisional\s+diagnosis|final\s+diagnosis)[:\s]+(.+?)(?:\n|$)',
    ]:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            result['diagnosis'] = m.group(1).strip()
            break

    # Advice can span several handwritten lines (product, application method,
    # dose pattern and duration). Keep the complete block until the footer or
    # another labelled section begins.
    advice_start = next((
        index for index, line in enumerate(lines)
        if re.match(r'^\s*(?:adv(?:ice)?|instructions?)\s*[:\-]?\s*', line, re.IGNORECASE)
    ), None)
    if advice_start is not None:
        first = re.sub(
            r'^\s*(?:adv(?:ice)?|instructions?)\s*[:\-]?\s*',
            '',
            lines[advice_start],
            flags=re.IGNORECASE,
        ).strip()
        advice_parts = [first] if first else []
        for line in lines[advice_start + 1:advice_start + 6]:
            if re.search(r'\b(?:patient|phone|email|www\.|follow[- ]?up|review)\b', line, re.IGNORECASE):
                break
            if re.match(r'^\s*(?:tab\.?|cap\.?|syp\.?|inj\.?)\b', line, re.IGNORECASE):
                break
            if re.search(r'\b(?:signature|sign|stamp|web|email|phone)\b', line, re.IGNORECASE):
                break
            advice_parts.append(line)
            if re.search(r'\d+\s*(?:days?|weeks?|months?)\b', line, re.IGNORECASE):
                break
        advice = ' '.join(part for part in advice_parts if part)
        advice = re.sub(r'\bgumpart\b|\bgum\s+po\b', 'gum paint', advice, flags=re.IGNORECASE)
        advice = re.sub(r'\bmassoge\b', 'massage', advice, flags=re.IGNORECASE)
        advice = re.sub(r'\bx\s*(\d+)\s*(days?|weeks?|months?)\b', r'for \1 \2', advice, flags=re.IGNORECASE)
        advice = re.sub(r'\s+', ' ', advice).strip(' .;')
        if advice:
            result['advice'] = advice

    # Follow-up
    m = re.search(r'(?:follow[- ]?up|review|next\s+visit)[:\s]+(.+?)(?:\n|$)', full_text, re.IGNORECASE)
    if m:
        result['follow_up'] = m.group(1).strip()

    # Date
    m = re.search(r'(?:date|dt)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', full_text, re.IGNORECASE)
    if m:
        result['date'] = m.group(1).strip()

    return result


def _parse_as_imaging(text: str, classification: Dict) -> Dict:
    """Parse a document classified as a diagnostic imaging report."""
    report_type = detect_report_type(text)

    # Extract findings/impression sections
    findings = []
    impression = ''

    m = re.search(r'(?:findings?|observations?)[:\s]+(.+?)(?=impression|conclusion|$)',
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        findings_text = m.group(1).strip()
        findings = [f.strip() for f in findings_text.split('\n') if f.strip()]

    m = re.search(r'(?:impression|conclusion)[:\s]+(.+?)$', text, re.IGNORECASE | re.DOTALL)
    if m:
        impression = m.group(1).strip()

    key_findings = findings[:10] if findings else ['Imaging findings — see extracted text']
    if impression:
        key_findings.insert(0, f"Impression: {impression}")

    summary = f"Document Type: {report_type}. {impression or 'See extracted text for findings.'}"

    return {
        'document_category': 'diagnostic_imaging',
        'report_type': report_type,
        'summary': summary,
        'key_findings': key_findings,
        'important_values': {},
        'abnormal_values': {},
        'sections': {'raw': text, 'findings': findings, 'impression': impression},
        'classification_confidence': classification['confidence'],
    }


def _parse_as_discharge(text: str, classification: Dict) -> Dict:
    """Parse a document classified as a discharge summary."""
    key_findings = []

    m = re.search(r'(?:discharge\s+diagnosis|diagnosis)[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m:
        key_findings.append(f"Diagnosis: {m.group(1).strip()}")

    m = re.search(r'(?:discharge\s+medication|medications?)[:\s]+(.+?)(?:\n\n|$)', text, re.IGNORECASE | re.DOTALL)
    if m:
        key_findings.append(f"Discharge medications noted")

    if not key_findings:
        key_findings.append('Discharge summary — see extracted text for details')

    return {
        'document_category': 'discharge_summary',
        'report_type': 'Discharge Summary',
        'summary': 'Document Type: Discharge Summary. Review extracted text for details.',
        'key_findings': key_findings,
        'important_values': {},
        'abnormal_values': {},
        'sections': {'raw': text},
        'classification_confidence': classification['confidence'],
    }


def _parse_as_generic(
    text: str,
    writing_mode: str,
    classification: Dict,
    ocr_lines: Optional[List[Dict]] = None,
) -> Dict:
    """Parse an unclassified or low-confidence document.

    Attempts lab extraction but only keeps results if genuine lab values found.
    Also checks if the text looks like a prescription before falling back to lab.
    Otherwise returns a generic "manual review required" result.
    """
    # If there is any prescription evidence, route to prescription parser
    # instead of falsely extracting lab values
    text_lower = text.lower()
    prescription_signals = [
        'tab ', 'tab.', 'cap ', 'cap.', 'syp ', 'syrup', 'chief complaint',
        'c/o', 'diagnosis', 'follow up', 'follow-up', 'advice', 'rx',
        'after food', 'before food', 'after meal', 'before meal',
        'od', 'bd', 'tds', 'tid',
    ]
    presc_count = sum(1 for s in prescription_signals if s in text_lower)
    if presc_count >= 3:
        result = _parse_as_prescription(text, writing_mode, classification, ocr_lines)
        result['document_category'] = 'other_medical_document'
        result.setdefault('key_findings', []).insert(
            0,
            '⚠ Document type could not be determined with high confidence. '
            'Treated as a prescription based on content signals. Manual verification recommended.',
        )
        return result

    # Try lab extraction
    extracted_values = extract_key_values(text)

    if extracted_values:
        # We found actual lab values, treat as lab report
        result = _parse_as_lab_report(text, writing_mode, classification)
        result['document_category'] = 'other_medical_document'
        result['key_findings'].insert(
            0, '⚠ Document type could not be determined with high confidence. '
               'Results shown may need manual verification.'
        )
        return result

    # No lab values found — generic document
    report_type = detect_report_type(text)

    return {
        'document_category': classification['category'],
        'report_type': report_type,
        'summary': f"Document processed. Category: {classification['category'].replace('_', ' ').title()}. "
                   f"No standard laboratory values detected.",
        'key_findings': [
            'No laboratory results detected in this document.',
            'Manual review of the extracted text is recommended.',
        ],
        'important_values': {},
        'abnormal_values': {},
        'sections': {'raw': text},
        'classification_confidence': classification['confidence'],
    }
