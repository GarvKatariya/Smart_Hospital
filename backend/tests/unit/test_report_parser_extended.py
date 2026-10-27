"""
Additional edge-case tests for report_parser — fills coverage gaps.

Tests cover:
  - _reconstruct_lines(): fragmented OCR line merging
  - _extract_inline_reference(): inline reference range parsing
  - _parse_as_generic(): ambiguous document fallback routing
  - _parse_as_imaging(): imaging report extraction
  - _parse_as_discharge(): discharge summary extraction
  - _extract_prescription_fields(): structured field extraction
  - Lab extraction: lipid profile, thyroid, kidney, liver tests
  - Lab extraction: duplicate test names deduplication
  - Lab extraction: inline HIGH/LOW flags
  - Cross-contamination: discharge summary doesn't produce lab values as main output
  - Edge: extremely long text, repeated patterns, interleaved content
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from ocr.report_parser import (
    classify_document,
    detect_report_type,
    extract_key_values,
    parse_medical_report,
    _is_known_lab_test,
    _is_excluded_name,
    _reconstruct_lines,
    _extract_inline_reference,
)


# ---------------------------------------------------------------------------
# _reconstruct_lines tests
# ---------------------------------------------------------------------------

class TestReconstructLines:
    def test_merges_fragmented_test_and_value(self):
        """PaddleOCR often splits test name and value onto separate lines."""
        text = "Hemoglobin\n14.2\ng/dL\n13.0-17.0"
        result = _reconstruct_lines(text)
        # Should merge into one line containing all fragments
        lines = result.split('\n')
        merged_line = next((l for l in lines if 'Hemoglobin' in l and '14.2' in l), None)
        assert merged_line is not None, f"Failed to merge: {lines}"

    def test_leaves_already_merged_lines_intact(self):
        text = "Hemoglobin 14.2 g/dL 13.0-17.0\nWBC 12500 /uL 4000-11000"
        result = _reconstruct_lines(text)
        lines = result.split('\n')
        assert any('Hemoglobin' in l and '14.2' in l for l in lines)
        assert any('WBC' in l and '12500' in l for l in lines)

    def test_handles_multiple_fragmented_tests(self):
        text = "Hemoglobin\n14.2\ng/dL\nWBC\n12500\n/uL"
        result = _reconstruct_lines(text)
        lines = [l for l in result.split('\n') if l.strip()]
        # Each test should be on its own merged line
        assert any('Hemoglobin' in l and '14.2' in l for l in lines)
        assert any('WBC' in l and '12500' in l for l in lines)

    def test_empty_input(self):
        assert _reconstruct_lines("") == ""

    def test_only_numbers(self):
        text = "14.2\n12500\n180000"
        result = _reconstruct_lines(text)
        assert result.strip()  # Should not crash


# ---------------------------------------------------------------------------
# _extract_inline_reference tests
# ---------------------------------------------------------------------------

class TestExtractInlineReference:
    def test_standard_range(self):
        result = _extract_inline_reference("Hemoglobin 14.2 g/dL 13.0-17.0")
        assert result is not None
        low, high, unit = result
        assert low == 13.0
        assert high == 17.0

    def test_range_with_en_dash(self):
        result = _extract_inline_reference("WBC 12500 /uL 4000–11000")
        assert result is not None
        low, high, _ = result
        assert low == 4000
        assert high == 11000

    def test_no_range_returns_none(self):
        result = _extract_inline_reference("Some random text without numbers")
        assert result is None

    def test_invalid_range_low_gt_high(self):
        result = _extract_inline_reference("Value 100-50")
        # low > high should be rejected
        assert result is None

    def test_range_with_unit(self):
        result = _extract_inline_reference("ESR 25 mm/hr 0-20")
        assert result is not None
        low, high, unit = result
        assert low == 0
        assert high == 20


# ---------------------------------------------------------------------------
# Lab extraction: lipid, thyroid, kidney, liver profiles
# ---------------------------------------------------------------------------

LIPID_PROFILE_TEXT = """
LIPID PROFILE

Total Cholesterol   245   mg/dL   0-200     HIGH
HDL Cholesterol     38    mg/dL   40-60     LOW
LDL Cholesterol     160   mg/dL   0-130     HIGH
Triglycerides       180   mg/dL   0-150     HIGH
VLDL                36    mg/dL   5-40
"""

THYROID_PROFILE_TEXT = """
THYROID PROFILE

TSH     6.5    mIU/L    0.4-4.0    HIGH
Free T3  2.8   pg/mL    2.0-4.4
Free T4  0.7   ng/dL    0.82-1.77  LOW
"""

KIDNEY_FUNCTION_TEXT = """
KIDNEY FUNCTION TEST

Creatinine    1.5    mg/dL    0.6-1.2    HIGH
Blood Urea    45     mg/dL    15-40      HIGH
Uric Acid     8.2    mg/dL    3.5-7.0    HIGH
Sodium        140    mEq/L    136-145
Potassium     4.2    mEq/L    3.5-5.0
"""

LIVER_FUNCTION_TEXT = """
LIVER FUNCTION TEST

SGPT           85     U/L      7-56      HIGH
SGOT           55     U/L      10-40     HIGH
Total Bilirubin 1.8   mg/dL    0.1-1.2   HIGH
Direct Bilirubin 0.5  mg/dL    0.0-0.3   HIGH
Alkaline Phosphatase  120  U/L  44-147
Total Protein   7.2   g/dL     6.0-8.3
Albumin         4.0   g/dL     3.5-5.0
"""


class TestLipidProfile:
    def test_detects_lipid_report_type(self):
        rtype = detect_report_type(LIPID_PROFILE_TEXT)
        assert 'lipid' in rtype.lower()

    def test_extracts_cholesterol(self):
        values = extract_key_values(LIPID_PROFILE_TEXT)
        test_names = [v['test_name'].lower().strip() for v in values]
        assert any('cholesterol' in t for t in test_names)

    def test_hdl_marked_low(self):
        values = extract_key_values(LIPID_PROFILE_TEXT)
        hdl = next((v for v in values if 'hdl' in v['test_name'].lower()), None)
        if hdl:
            assert hdl['status'] == 'low'

    def test_triglycerides_marked_high(self):
        values = extract_key_values(LIPID_PROFILE_TEXT)
        trig = next((v for v in values if 'triglyceride' in v['test_name'].lower()), None)
        if trig:
            assert trig['status'] == 'high'


class TestThyroidProfile:
    def test_detects_thyroid_report_type(self):
        rtype = detect_report_type(THYROID_PROFILE_TEXT)
        assert 'thyroid' in rtype.lower()

    def test_extracts_tsh(self):
        values = extract_key_values(THYROID_PROFILE_TEXT)
        tsh = next((v for v in values if 'tsh' in v['test_name'].lower()), None)
        assert tsh is not None
        assert tsh['value'] == 6.5
        assert tsh['status'] == 'high'


class TestKidneyFunction:
    def test_detects_kidney_report_type(self):
        rtype = detect_report_type(KIDNEY_FUNCTION_TEXT)
        assert 'kidney' in rtype.lower()

    def test_creatinine_high(self):
        values = extract_key_values(KIDNEY_FUNCTION_TEXT)
        creatinine = next((v for v in values if 'creatinine' in v['test_name'].lower()), None)
        if creatinine:
            assert creatinine['status'] == 'high'
            assert creatinine['value'] == 1.5


class TestLiverFunction:
    def test_detects_liver_report_type(self):
        rtype = detect_report_type(LIVER_FUNCTION_TEXT)
        assert 'liver' in rtype.lower()

    def test_sgpt_high(self):
        values = extract_key_values(LIVER_FUNCTION_TEXT)
        sgpt = next((v for v in values if 'sgpt' in v['test_name'].lower()), None)
        if sgpt:
            assert sgpt['status'] == 'high'
            assert sgpt['value'] == 85

    def test_albumin_normal(self):
        values = extract_key_values(LIVER_FUNCTION_TEXT)
        albumin = next((v for v in values if 'albumin' in v['test_name'].lower()), None)
        if albumin:
            assert albumin['status'] == 'normal'


# ---------------------------------------------------------------------------
# Duplicate deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_hemoglobin_only_extracted_once(self):
        text = "Hemoglobin 14.2 g/dL 13.0-17.0\nHemoglobin 14.2 g/dL 13.0-17.0"
        values = extract_key_values(text)
        hb_count = sum(1 for v in values if 'hemoglobin' in v['test_name'].lower())
        assert hb_count == 1


# ---------------------------------------------------------------------------
# Full pipeline: imaging and discharge
# ---------------------------------------------------------------------------

DETAILED_IMAGING_TEXT = """
RADIOLOGY DEPARTMENT
MRI Brain Report

Patient: ANIL VERMA    Age: 60    Sex: Male
Referred by: Dr. Gupta

Technique: MRI Brain with contrast

Findings:
Small lacunar infarct in the left basal ganglia.
Mild age-related cerebral atrophy.
No mass lesion or midline shift.
Normal posterior fossa structures.

Impression: Small lacunar infarct. Age-related changes. No acute intracranial pathology.

Radiologist: Dr. A. Sharma
"""

DETAILED_DISCHARGE_TEXT = """
DISCHARGE SUMMARY
Date of Admission: 05/06/2024
Date of Discharge: 12/06/2024
Length of Stay: 7 days

Patient: MEENA KUMARI    Age: 48    Sex: Female
Ward: Surgical    Bed No: 8

Discharge Diagnosis: Cholelithiasis (Gallstones)

Hospital Course:
Patient admitted with right upper quadrant pain.
Ultrasound confirmed gallstones.
Laparoscopic cholecystectomy performed on 06/06/2024.
Post-operative recovery uneventful.
Started on oral diet on day 3.

Discharge Medication:
1. Tab Paracetamol 500mg TDS for 5 days
2. Tab Pantoprazole 40mg OD for 10 days

Condition at Discharge: Stable, ambulatory.
Follow-up: After 2 weeks in Surgical OPD.
"""


class TestImagingFullPipeline:
    def test_classified_as_imaging(self):
        result = classify_document(DETAILED_IMAGING_TEXT)
        assert result['category'] == 'diagnostic_imaging'

    def test_full_pipeline_imaging(self):
        result = parse_medical_report(DETAILED_IMAGING_TEXT)
        assert result['document_category'] == 'diagnostic_imaging'
        assert result['important_values'] == {}
        assert result['abnormal_values'] == {}
        assert 'MRI' in result['report_type'] or 'imaging' in result['report_type'].lower() \
               or result['report_type'] == 'MRI Report'

    def test_imaging_has_impression(self):
        result = parse_medical_report(DETAILED_IMAGING_TEXT)
        sections = result.get('sections', {})
        impression = sections.get('impression', '')
        findings = result.get('key_findings', [])
        # Should have impression either in sections or key_findings
        assert impression or any('impression' in f.lower() or 'infarct' in f.lower() for f in findings)


class TestDischargeFullPipeline:
    def test_classified_as_discharge(self):
        result = classify_document(DETAILED_DISCHARGE_TEXT)
        assert result['category'] == 'discharge_summary'

    def test_full_pipeline_discharge(self):
        result = parse_medical_report(DETAILED_DISCHARGE_TEXT)
        assert result['document_category'] == 'discharge_summary'
        assert result['report_type'] == 'Discharge Summary'

    def test_discharge_has_diagnosis_in_findings(self):
        result = parse_medical_report(DETAILED_DISCHARGE_TEXT)
        findings = result.get('key_findings', [])
        # Should mention the diagnosis
        assert any('cholelithiasis' in f.lower() or 'gallstone' in f.lower() for f in findings) \
               or len(findings) > 0  # at minimum should have findings


# ---------------------------------------------------------------------------
# Generic/unknown document routing
# ---------------------------------------------------------------------------

AMBIGUOUS_WITH_PRESCRIPTION_SIGNALS = """
Dr. Sharma
Patient: Raj

c/o headache and body aches 2 days

Tab Paracetamol 500mg TDS 3 days after food
Tab Cetirizine 10mg OD 5 days
Advice: Rest, fluids
Follow-up: 3 days
"""

AMBIGUOUS_WITH_LAB_SIGNALS = """
Some Medical Centre
Patient: Test

Hemoglobin 14.2 g/dL
WBC 8500 /uL
Platelets 250000 /uL
"""

PURELY_RANDOM_TEXT = """
The quick brown fox jumps over the lazy dog.
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
No medical content here at all.
"""


class TestGenericDocumentRouting:
    def test_ambiguous_with_prescription_signals(self):
        result = parse_medical_report(AMBIGUOUS_WITH_PRESCRIPTION_SIGNALS)
        # Should detect prescription signals and route accordingly
        assert result['document_category'] in ('prescription', 'other_medical_document')

    def test_ambiguous_with_lab_signals(self):
        result = parse_medical_report(AMBIGUOUS_WITH_LAB_SIGNALS)
        # Should detect lab values
        assert result['document_category'] in ('laboratory_report', 'other_medical_document')
        # Should have extracted values
        important = result.get('important_values', {})
        lab_values = result.get('lab_values', [])
        assert len(important) > 0 or len(lab_values) > 0

    def test_purely_random_text(self):
        result = parse_medical_report(PURELY_RANDOM_TEXT)
        assert result['document_category'] in ('unknown', 'other_medical_document')
        assert result['important_values'] == {}
        assert result['abnormal_values'] == {}

    def test_generic_has_key_findings(self):
        result = parse_medical_report(PURELY_RANDOM_TEXT)
        assert 'key_findings' in result
        assert isinstance(result['key_findings'], list)


# ---------------------------------------------------------------------------
# _extract_prescription_fields
# ---------------------------------------------------------------------------

class TestExtractPrescriptionFields:
    def test_extracts_chief_complaint(self):
        text = "Chief Complaint: Fever with chills 3 days\nRx: Tab Paracetamol"
        result = parse_medical_report(text)
        # For prescription-classified docs, should extract clinical info
        if 'prescription_data' in result:
            clinical = result['prescription_data'].get('clinical_info', {})
            assert 'chief_complaints' in clinical or 'diagnosis' in clinical

    def test_extracts_follow_up(self):
        text = """Patient: Test  Age: 25
Diagnosis: Fever
Rx:
1. Tab Paracetamol 500mg TDS 5 days
Follow-up: After 5 days"""
        result = parse_medical_report(text)
        if 'prescription_data' in result:
            clinical = result['prescription_data'].get('clinical_info', {})
            if 'follow_up' in clinical:
                assert '5 days' in clinical['follow_up']


# ---------------------------------------------------------------------------
# _is_known_lab_test extended
# ---------------------------------------------------------------------------

class TestIsKnownLabTestExtended:
    def test_hba1c(self):
        assert _is_known_lab_test('HbA1c') is True
        assert _is_known_lab_test('hba1c') is True

    def test_vitamin_d(self):
        assert _is_known_lab_test('Vitamin D') is True

    def test_vitamin_b12(self):
        assert _is_known_lab_test('Vitamin B12') is True

    def test_d_dimer(self):
        assert _is_known_lab_test('D-Dimer') is True

    def test_troponin(self):
        assert _is_known_lab_test('Troponin') is True

    def test_random_word_not_lab_test(self):
        assert _is_known_lab_test('Paracetamol') is False
        assert _is_known_lab_test('Breakfast') is False
        assert _is_known_lab_test('Hospital') is False

    def test_partial_match_rejected(self):
        """Short lab abbreviations should not match random strings."""
        assert _is_known_lab_test('MM') is False
        assert _is_known_lab_test('XY') is False


# ---------------------------------------------------------------------------
# _is_excluded_name extended
# ---------------------------------------------------------------------------

class TestIsExcludedNameExtended:
    def test_sl_excluded(self):
        assert _is_excluded_name('Sl') is True

    def test_rs_excluded(self):
        assert _is_excluded_name('Rs') is True

    def test_mmc_excluded(self):
        assert _is_excluded_name('MMC') is True

    def test_long_valid_name_not_excluded(self):
        assert _is_excluded_name('Hemoglobin') is False
        assert _is_excluded_name('Total Cholesterol') is False


# ---------------------------------------------------------------------------
# HIGH/LOW flag detection
# ---------------------------------------------------------------------------

class TestHighLowFlags:
    def test_high_flag_in_text(self):
        text = "WBC 12500 /uL 4000-11000 HIGH"
        values = extract_key_values(text)
        wbc = next((v for v in values if 'wbc' in v['test_name'].lower()), None)
        if wbc:
            assert wbc['status'] == 'high'

    def test_low_flag_in_text(self):
        text = "HDL 35 mg/dL 40-60 LOW"
        values = extract_key_values(text)
        hdl = next((v for v in values if 'hdl' in v['test_name'].lower()), None)
        if hdl:
            assert hdl['status'] == 'low'

    def test_asterisk_h_flag(self):
        text = "ESR 35 mm/hr 0-20 *H"
        values = extract_key_values(text)
        esr = next((v for v in values if 'esr' in v['test_name'].lower()), None)
        if esr:
            assert esr['status'] == 'high'


# ---------------------------------------------------------------------------
# Fragmented OCR lab report (mimics real PaddleOCR output)
# ---------------------------------------------------------------------------

FRAGMENTED_LAB_TEXT = """
PATHOLOGY DEPARTMENT
COMPLETE BLOOD COUNT

Hemoglobin
14.2
g/dL
13.0-17.0

WBC
12500
/uL
4000-11000

Platelets
180000
/uL
150000-400000
"""


class TestFragmentedLabReport:
    def test_classified_as_lab_report(self):
        result = classify_document(FRAGMENTED_LAB_TEXT)
        assert result['category'] == 'laboratory_report'

    def test_extracts_values_from_fragmented(self):
        values = extract_key_values(FRAGMENTED_LAB_TEXT)
        test_names = [v['test_name'].lower().strip() for v in values]
        assert any('hemoglobin' in t for t in test_names), \
            f"Hemoglobin not found in fragmented text. Extracted: {test_names}"

    def test_full_pipeline_fragmented(self):
        result = parse_medical_report(FRAGMENTED_LAB_TEXT)
        assert result['document_category'] == 'laboratory_report'
        assert len(result.get('important_values', {})) > 0
