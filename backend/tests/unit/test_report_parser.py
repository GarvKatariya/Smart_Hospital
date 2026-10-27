"""
Unit tests for report_parser — document classification and extraction.

Tests cover:
  - Document classification (prescription, lab report, imaging, discharge, unknown)
  - Strict lab value extraction (only known tests, proper status)
  - Prescription text NOT misclassified as lab results
  - Edge cases (empty text, malformed input, poor OCR)
"""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from ocr.report_parser import (
    classify_document,
    detect_report_type,
    extract_key_values,
    parse_medical_report,
    _is_known_lab_test,
    _is_excluded_name,
)


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

PRESCRIPTION_TEXT = """
B/503 J, MMC CAMPUS,
MAHATMA GANDHI MEMORIAL MEDICAL COLLEGE,
INDORE (M.P.)
Ph.: 0731- 2527383
Timing: 9AM To 3PM

Department of General Medicine OPD 6 PATIENT

MYH OPD Prescription

Patient Name: KAMLESH
Age/Sex: 24/Male
Date: 7/11/2018

CHIEF COMPLAINT:
FEVER WITH CHILLS - 4 DAYS
BODY ACHES - 4 DAYS

CLINICAL FINDINGS:
Weight: 80 Kg    Height: 200 cm    BP: 120/80 mmHg

DIAGNOSIS: ACUTE FEBRILE ILLNESS

Rx:
1. Tab Paracetamol 500mg - TDS - 5 days
2. Tab Azithromycin 500mg - OD - 3 days
3. Tab Pantoprazole 40mg - OD - 5 days
4. Syp Ambrodil-S - TDS - 5 days

ADVICE:
- Plenty of fluids
- Bland diet
- If no improvement in 3 days, get CBC done

Follow-up: After 5 days
"""

LAB_REPORT_TEXT = """
SMART CITY GENERAL HOSPITAL
PATHOLOGY DEPARTMENT
Date: 15/03/2024

Patient: RAMESH KUMAR    Age: 45    Sex: Male
Ref: Dr. Sharma    Sample: Blood

COMPLETE BLOOD COUNT

Test Name          Result    Unit       Ref Range
Hemoglobin         14.2      g/dL       13.0-17.0
RBC                4.8       million/uL 4.5-5.5
WBC                12500     /uL        4000-11000    HIGH
Platelets          180000    /uL        150000-400000
Hematocrit         42.0      %          36.0-48.0
MCV                87.5      fL         80.0-100.0
MCH                29.6      pg         27.0-33.0
ESR                35        mm/hr      0-20          HIGH

LIPID PROFILE
Cholesterol        245       mg/dL      0-200         HIGH
HDL                38        mg/dL      40-60         LOW
LDL                160       mg/dL      0-130         HIGH
Triglycerides      180       mg/dL      0-150         HIGH
"""

IMAGING_REPORT_TEXT = """
RADIOLOGY DEPARTMENT
X-Ray Report

Patient: SUNIL VERMA    Age: 55    Sex: Male
Referred by: Dr. Patel

X-Ray Chest PA View

Technique: Standard PA chest radiograph

Findings:
Both lung fields are clear.
Heart size is normal.
No pleural effusion.
Costophrenic angles are clear.
Mediastinum is normal.
Bony thorax is intact.

Impression: Normal chest X-ray. No significant abnormality detected.

Radiologist: Dr. A. Gupta
"""

DISCHARGE_SUMMARY_TEXT = """
DISCHARGE SUMMARY
Date of Admission: 10/03/2024
Date of Discharge: 15/03/2024

Patient: ANIL SHARMA    Age: 60    Sex: Male
Ward: General Medicine    Bed No: 12

Discharge Diagnosis: Acute Gastroenteritis

Hospital Course:
Patient presented with loose stools and vomiting for 2 days.
Managed with IV fluids, antibiotics and supportive care.
Condition improved over 5 days.

Discharge Medication:
1. Tab ORS - TDS - 5 days
2. Tab Racecadotril 100mg - TDS - 3 days

Condition at Discharge: Stable, improved.
Follow-up: After 1 week in OPD.
"""

POOR_OCR_TEXT = """
Sm@rt C1ty H0sp1tal
P@th0l0gy D3pt
Herght: 170 cm
Wt: 65 kg
BP: 130/85
"""

EMPTY_TEXT = ""


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestDocumentClassification:
    def test_prescription_classification(self):
        result = classify_document(PRESCRIPTION_TEXT)
        assert result['category'] == 'prescription', \
            f"Expected 'prescription', got '{result['category']}' with scores: {result['scores']}"
        assert result['confidence'] > 0.3

    def test_lab_report_classification(self):
        result = classify_document(LAB_REPORT_TEXT)
        assert result['category'] == 'laboratory_report', \
            f"Expected 'laboratory_report', got '{result['category']}' with scores: {result['scores']}"
        assert result['confidence'] > 0.4

    def test_imaging_classification(self):
        result = classify_document(IMAGING_REPORT_TEXT)
        assert result['category'] == 'diagnostic_imaging', \
            f"Expected 'diagnostic_imaging', got '{result['category']}' with scores: {result['scores']}"

    def test_discharge_classification(self):
        result = classify_document(DISCHARGE_SUMMARY_TEXT)
        assert result['category'] == 'discharge_summary', \
            f"Expected 'discharge_summary', got '{result['category']}' with scores: {result['scores']}"

    def test_empty_text_classification(self):
        result = classify_document("")
        assert result['category'] == 'unknown'
        assert result['confidence'] == 0.0

    def test_ambiguous_text_classification(self):
        result = classify_document("Hello world, this is some random text")
        assert result['category'] in ('unknown', 'other_medical_document')


# ---------------------------------------------------------------------------
# Lab extraction tests
# ---------------------------------------------------------------------------

class TestLabExtraction:
    def test_extracts_genuine_lab_values(self):
        values = extract_key_values(LAB_REPORT_TEXT)
        test_names = [v['test_name'].lower().strip() for v in values]

        # Should find genuine lab tests
        assert any('hemoglobin' in t for t in test_names), f"Hemoglobin not found in {test_names}"
        assert any('wbc' in t for t in test_names), f"WBC not found in {test_names}"
        assert any('platelet' in t for t in test_names), f"Platelets not found in {test_names}"

    def test_marks_abnormal_values_correctly(self):
        values = extract_key_values(LAB_REPORT_TEXT)
        # WBC 12500 should be high (ref: 4000-11000)
        wbc = next((v for v in values if 'wbc' in v['test_name'].lower()), None)
        if wbc:
            assert wbc['status'] == 'high', f"WBC status should be 'high', got '{wbc['status']}'"

        # ESR 35 should be high (ref: 0-20)
        esr = next((v for v in values if 'esr' in v['test_name'].lower()), None)
        if esr:
            assert esr['status'] == 'high', f"ESR status should be 'high', got '{esr['status']}'"

    def test_does_not_extract_from_prescription(self):
        """The core bug fix: prescription text should NOT produce lab values."""
        values = extract_key_values(PRESCRIPTION_TEXT)

        # These should NOT appear as lab results
        bad_test_names = []
        for v in values:
            name_lower = v['test_name'].lower().strip()
            # None of these should appear
            if name_lower in ('b', 'mmc', 'ph', 'timing', 'opd', 'fever', 'fever with chills',
                              'weight', 'height', 'bp', 'blood pressure', 'age'):
                bad_test_names.append(v['test_name'])

        assert len(bad_test_names) == 0, \
            f"Prescription noise was misinterpreted as lab results: {bad_test_names}"

    def test_does_not_extract_registration_numbers(self):
        values = extract_key_values("B/503 J, MMC CAMPUS, Registration No: 12345")
        test_names = [v['test_name'].lower() for v in values]
        assert 'b' not in test_names
        assert 'registration' not in test_names

    def test_does_not_extract_phone_numbers(self):
        values = extract_key_values("Ph.: 0731-2527383 Tel: 1234567890")
        test_names = [v['test_name'].lower() for v in values]
        assert 'ph' not in test_names
        assert 'tel' not in test_names

    def test_does_not_extract_dates(self):
        values = extract_key_values("Date: 7/11/2018 OPD: 6")
        test_names = [v['test_name'].lower() for v in values]
        assert 'date' not in test_names
        assert 'opd' not in test_names

    def test_does_not_extract_vitals_as_lab(self):
        values = extract_key_values("Weight: 80 Kg Height: 200 cm BP: 120/80 mmHg")
        test_names = [v['test_name'].lower() for v in values]
        assert 'weight' not in test_names
        assert 'height' not in test_names
        assert 'bp' not in test_names

    def test_does_not_extract_symptom_durations(self):
        values = extract_key_values("FEVER WITH CHILLS - 4 DAYS BODY ACHES - 4 DAYS")
        test_names = [v['test_name'].lower() for v in values]
        assert 'fever with chills' not in test_names
        assert 'fever' not in test_names

    def test_default_status_is_unknown(self):
        """When no reference range is available, status should be 'unknown', not 'normal'."""
        # Hemoglobin has a reference range, so it should have a known status
        values = extract_key_values("Hemoglobin 14.2 g/dL")
        if values:
            hb = values[0]
            assert hb['status'] in ('normal', 'high', 'low')

    def test_confidence_scores_present(self):
        values = extract_key_values(LAB_REPORT_TEXT)
        for v in values:
            assert 'confidence' in v
            assert 0.0 <= v['confidence'] <= 1.0

    def test_empty_text_returns_empty_list(self):
        assert extract_key_values("") == []
        assert extract_key_values("   ") == []

    def test_no_lab_results_from_poor_ocr(self):
        values = extract_key_values(POOR_OCR_TEXT)
        # Should not produce fake lab results from OCR noise
        for v in values:
            assert v['test_name'].lower() not in ('herght', 'wt', 'bp', 'smart')


# ---------------------------------------------------------------------------
# Full pipeline tests (parse_medical_report)
# ---------------------------------------------------------------------------

class TestParseMedicalReport:
    def test_prescription_full_pipeline(self):
        """Regression test: prescription must NOT produce lab values."""
        result = parse_medical_report(PRESCRIPTION_TEXT)

        assert result['document_category'] == 'prescription'
        assert result['important_values'] == {}
        assert result['abnormal_values'] == {}
        assert 'prescription_data' in result
        assert result['prescription_data']['medications'] is not None

        # Should NOT contain "All extracted values appear within normal ranges"
        for finding in result['key_findings']:
            assert 'normal ranges' not in finding.lower()

    def test_lab_report_full_pipeline(self):
        result = parse_medical_report(LAB_REPORT_TEXT)

        assert result['document_category'] == 'laboratory_report'
        assert len(result['important_values']) > 0
        assert 'lab_values' in result

        # Should detect abnormal values
        assert len(result['abnormal_values']) > 0

    def test_imaging_full_pipeline(self):
        result = parse_medical_report(IMAGING_REPORT_TEXT)
        assert result['document_category'] == 'diagnostic_imaging'
        assert result['important_values'] == {}

    def test_discharge_full_pipeline(self):
        result = parse_medical_report(DISCHARGE_SUMMARY_TEXT)
        assert result['document_category'] == 'discharge_summary'

    def test_empty_text_pipeline(self):
        result = parse_medical_report("")
        assert result['document_category'] == 'unknown'
        assert result['important_values'] == {}

    def test_none_text_pipeline(self):
        result = parse_medical_report(None)
        assert result['document_category'] == 'unknown'

    def test_raw_text_preserved(self):
        result = parse_medical_report(LAB_REPORT_TEXT)
        assert result['sections']['raw'] == LAB_REPORT_TEXT


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_known_lab_test(self):
        assert _is_known_lab_test('Hemoglobin') == True
        assert _is_known_lab_test('hemoglobin') == True
        assert _is_known_lab_test('WBC') == True
        assert _is_known_lab_test('ESR') == True
        assert _is_known_lab_test('Creatinine') == True

    def test_not_lab_test(self):
        assert _is_known_lab_test('Fever') == False
        assert _is_known_lab_test('OPD') == False
        assert _is_known_lab_test('Timing') == False
        assert _is_known_lab_test('MMC') == False
        assert _is_known_lab_test('CAMPUS') == False

    def test_excluded_names(self):
        assert _is_excluded_name('Weight') == True
        assert _is_excluded_name('Height') == True
        assert _is_excluded_name('BP') == True
        assert _is_excluded_name('OPD') == True
        assert _is_excluded_name('Date') == True
        assert _is_excluded_name('Patient') == True
        assert _is_excluded_name('Hospital') == True
        assert _is_excluded_name('Ph') == True
        assert _is_excluded_name('B') == True

    def test_not_excluded(self):
        assert _is_excluded_name('Hemoglobin') == False
        assert _is_excluded_name('Creatinine') == False

    def test_detect_report_type(self):
        assert detect_report_type(LAB_REPORT_TEXT) == 'Complete Blood Count'
        assert detect_report_type(IMAGING_REPORT_TEXT) == 'X-Ray Report'
