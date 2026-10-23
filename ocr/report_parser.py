"""Medical report parser - extracts structured information from OCR text."""
import re
from typing import Dict, List, Tuple, Optional


# Common lab test reference ranges
REFERENCE_RANGES = {
    'hemoglobin': {'unit': 'g/dL', 'male': (13.0, 17.0), 'female': (12.0, 15.5), 'default': (12.0, 17.0)},
    'hb': {'unit': 'g/dL', 'male': (13.0, 17.0), 'female': (12.0, 15.5), 'default': (12.0, 17.0)},
    'rbc': {'unit': 'million/uL', 'default': (4.5, 5.5)},
    'wbc': {'unit': '/uL', 'default': (4000, 11000)},
    'platelets': {'unit': '/uL', 'default': (150000, 400000)},
    'hematocrit': {'unit': '%', 'default': (36.0, 48.0)},
    'hct': {'unit': '%', 'default': (36.0, 48.0)},
    'mcv': {'unit': 'fL', 'default': (80.0, 100.0)},
    'mch': {'unit': 'pg', 'default': (27.0, 33.0)},
    'mchc': {'unit': 'g/dL', 'default': (32.0, 36.0)},
    'esr': {'unit': 'mm/hr', 'default': (0, 20)},
    'glucose': {'unit': 'mg/dL', 'default': (70, 110)},
    'fasting glucose': {'unit': 'mg/dL', 'default': (70, 100)},
    'blood sugar': {'unit': 'mg/dL', 'default': (70, 140)},
    'creatinine': {'unit': 'mg/dL', 'default': (0.6, 1.2)},
    'urea': {'unit': 'mg/dL', 'default': (15, 40)},
    'bun': {'unit': 'mg/dL', 'default': (7, 20)},
    'uric acid': {'unit': 'mg/dL', 'default': (3.5, 7.0)},
    'cholesterol': {'unit': 'mg/dL', 'default': (0, 200)},
    'total cholesterol': {'unit': 'mg/dL', 'default': (0, 200)},
    'hdl': {'unit': 'mg/dL', 'default': (40, 60)},
    'ldl': {'unit': 'mg/dL', 'default': (0, 130)},
    'triglycerides': {'unit': 'mg/dL', 'default': (0, 150)},
    'sgpt': {'unit': 'U/L', 'default': (7, 56)},
    'alt': {'unit': 'U/L', 'default': (7, 56)},
    'sgot': {'unit': 'U/L', 'default': (10, 40)},
    'ast': {'unit': 'U/L', 'default': (10, 40)},
    'bilirubin': {'unit': 'mg/dL', 'default': (0.1, 1.2)},
    'total bilirubin': {'unit': 'mg/dL', 'default': (0.1, 1.2)},
    'direct bilirubin': {'unit': 'mg/dL', 'default': (0.0, 0.3)},
    'albumin': {'unit': 'g/dL', 'default': (3.5, 5.0)},
    'total protein': {'unit': 'g/dL', 'default': (6.0, 8.3)},
    'alkaline phosphatase': {'unit': 'U/L', 'default': (44, 147)},
    'alp': {'unit': 'U/L', 'default': (44, 147)},
    'tsh': {'unit': 'mIU/L', 'default': (0.4, 4.0)},
    't3': {'unit': 'ng/dL', 'default': (80, 200)},
    't4': {'unit': 'ug/dL', 'default': (5.0, 12.0)},
    'hba1c': {'unit': '%', 'default': (4.0, 5.6)},
    'sodium': {'unit': 'mEq/L', 'default': (136, 145)},
    'potassium': {'unit': 'mEq/L', 'default': (3.5, 5.0)},
    'calcium': {'unit': 'mg/dL', 'default': (8.5, 10.5)},
    'iron': {'unit': 'ug/dL', 'default': (60, 170)},
    'vitamin d': {'unit': 'ng/mL', 'default': (30, 100)},
    'vitamin b12': {'unit': 'pg/mL', 'default': (200, 900)},
}

# Report type detection patterns
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
        if (re.match(r'^[A-Za-z][A-Za-z\s\(\)/]+$', line)
                and i + 1 < len(raw_lines)
                and re.match(r'^[\d]+\.?\d*$', raw_lines[i + 1].strip())):
            combined = line
            j = i + 1
            # Grab the numeric value and any following unit/ref-range lines
            while j < len(raw_lines) and j < i + 4:
                next_l = raw_lines[j].strip()
                # Stop if it looks like another test name (alpha only, >3 chars)
                if (re.match(r'^[A-Za-z][A-Za-z\s\(\)/]+$', next_l) 
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


def extract_key_values(text: str) -> List[Dict]:
    """Extract test name: value pairs from OCR text."""
    results = []
    
    # First, reconstruct fragmented OCR lines
    text = _reconstruct_lines(text)
    lines = text.split('\n')

    # Patterns for "TestName Value Unit" on a single reconstructed line
    patterns = [
        # "Hemoglobin 14.2 g/dL" or "Hemoglobin: 14.2 g/dL"
        r'([A-Za-z][A-Za-z\s/\(\)]+?)\s*[:=\-]?\s*([\d]+\.?\d*)\s*([A-Za-z/%]+(?:/[A-Za-z]+)?)?',
    ]

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                test_name = match[0].strip().rstrip(':=-')
                value_str = match[1].strip()
                unit = match[2].strip() if len(match) > 2 else ''

                # Skip noise words
                skip_words = ('page', 'date', 'age', 'no', 'sr', 'id', 'ref',
                              'test', 'value', 'unit', 'range', 'sep', 'patient',
                              'smart', 'city', 'general', 'hospital', 'pathology',
                              'department', 'complete', 'blood', 'count', 'profile',
                              'sugar', 'lipid')
                if len(test_name) < 2 or test_name.lower() in skip_words:
                    continue

                try:
                    value = float(value_str)
                except ValueError:
                    continue

                # Check against reference ranges
                status = 'normal'
                ref_range = None
                test_key = test_name.lower().strip()
                if test_key in REFERENCE_RANGES:
                    ref = REFERENCE_RANGES[test_key]
                    low, high = ref.get('default', (None, None))
                    if low is not None and high is not None:
                        ref_range = f"{low}-{high} {ref.get('unit', '')}"
                        if value < low:
                            status = 'low'
                        elif value > high:
                            status = 'high'

                results.append({
                    'test_name': test_name,
                    'value': value,
                    'unit': unit or (REFERENCE_RANGES.get(test_key, {}).get('unit', '')),
                    'status': status,
                    'reference_range': ref_range,
                })

    return results


def parse_medical_report(text: str, writing_mode: str = 'printed') -> Dict:
    """Parse OCR text from a medical report into structured data."""
    if not text or text.strip() == '':
        return {
            'report_type': 'Unknown',
            'summary': 'No text could be extracted from the image.',
            'key_findings': [],
            'important_values': {},
            'abnormal_values': {},
            'sections': {'raw': ''},
        }

    report_type = detect_report_type(text)
    extracted_values = extract_key_values(text)

    # Separate normal and abnormal values
    important_values = {}
    abnormal_values = {}
    key_findings = []

    for item in extracted_values:
        key = item['test_name']
        val_str = f"{item['value']} {item['unit']}"
        important_values[key] = val_str

        if item['status'] == 'high':
            abnormal_values[key] = f"{val_str} (HIGH - ref: {item['reference_range']})"
            key_findings.append(f"{key} is elevated at {val_str}")
        elif item['status'] == 'low':
            abnormal_values[key] = f"{val_str} (LOW - ref: {item['reference_range']})"
            key_findings.append(f"{key} is below normal at {val_str}")

    if not key_findings:
        if extracted_values:
            key_findings.append('All extracted values appear within normal ranges')
        else:
            key_findings.append('Report text extracted but no standard lab values detected')

    # Build summary
    summary_parts = [f"Report Type: {report_type}"]
    summary_parts.append(f"Values extracted: {len(extracted_values)}")
    if abnormal_values:
        summary_parts.append(f"Abnormal values found: {len(abnormal_values)}")
    else:
        summary_parts.append("No abnormal values detected")
    summary = '. '.join(summary_parts) + '.'

    return {
        'report_type': report_type,
        'summary': summary,
        'key_findings': key_findings,
        'important_values': important_values,
        'abnormal_values': abnormal_values,
        'sections': {'raw': text},
    }
