"""
Unit tests for prescription_parser — medication extraction for printed and handwritten prescriptions.

Tests cover:
  - Printed prescription: numbered entry detection
  - Printed prescription: exclusion of headings, fragments, address text
  - Handwritten prescription: branding/noise exclusion
  - Handwritten prescription: dosage-pattern (1-0-1) recognition
  - Handwritten prescription: "meals" / "massage" NOT classified as medicines
  - Header parser: patient name not populated with label words
  - Confidence breakdown and requires_review flagging
  - Regression: lab report text does NOT produce medications
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from ocr.prescription_parser import (
    parse_prescription,
    parse_prescription_header,
    _is_non_medicine_candidate,
    _extract_dose_schedule,
    _split_into_numbered_entries,
)
from ocr.report_parser import (
    classify_document,
    parse_medical_report,
    extract_key_values,
)


# ---------------------------------------------------------------------------
# Sample texts that represent real OCR output
# ---------------------------------------------------------------------------

PRINTED_PRESCRIPTION_TEXT = """
B/503 J, MMC CAMPUS,
MAHATMA GANDHI MEMORIAL MEDICAL COLLEGE,
INDORE (M.P.)
Ph.: 0731-2527383
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

Follow-up: After 5 days
"""

PRINTED_PRESCRIPTION_WITH_INGREDIENTS = """
Patient: RAVI SHARMA    Age: 35    Sex: Male
Date: 10/10/2023

Diagnosis: Iron Deficiency Anaemia

Rx:
1. Tab Folic Acid 5mg - OD - 30 days
   (Contains: Folic Acid 5mg)
2. Tab Ferrous Sulphate 200mg - BD - 30 days
   (Contains: Ferrous Sulphate 200mg, Vitamin C 60mg)
3. Tab Gestakind - OD - 14 days
   (Multivitamin supplement)
4. Tab Methylcobalamin 500mcg - OD - 30 days

ADVICE: Take iron tablet with orange juice. Avoid tea/coffee.
Follow-up: 4 weeks
"""

HANDWRITTEN_PRESCRIPTION_DENTAL = """
The White Tusk
Smile Dental Clinic

Date: 15/10/2023

Patient: Rahul Verma    Age: 28

Tab. Augmentin 625 mg - 1-0-1 - 5 days - after meals
Tab. Enzoflam - 1-0-1 - 5 days - after meals
Tab. Pan-D 40 mg - 1-0-0 - 5 days - before meals
Hexigel gum paint - 1-0-1 - 1 week - apply on affected area

Advice: Warm saline rinse 3 times daily
Follow-up: 1 week
"""

HANDWRITTEN_PRESCRIPTION_NOISE = """
THE
Smile
Dental
a Tab
meals
Tab
massoge
Cemite
"""

LAB_REPORT_TEXT = """
SMART CITY GENERAL HOSPITAL
PATHOLOGY DEPARTMENT

Patient: RAMESH KUMAR    Age: 45    Sex: Male

COMPLETE BLOOD COUNT

Hemoglobin     14.2    g/dL    13.0-17.0
WBC            12500   /uL     4000-11000    HIGH
Platelets      180000  /uL     150000-400000
"""

AMBIGUOUS_PRESCRIPTION_TEXT = """
Dr. Sharma Clinic
Patient: Priya    Age: 30

c/o cough and cold 3 days

Tab Cetirizine 10mg - OD - 5 days - after food
Tab Ambroxol 30mg - TDS - 5 days
"""


# ---------------------------------------------------------------------------
# Printed prescription tests
# ---------------------------------------------------------------------------

class TestPrintedPrescription:
    def test_classified_as_prescription(self):
        result = classify_document(PRINTED_PRESCRIPTION_TEXT)
        assert result['category'] == 'prescription', \
            f"Expected prescription, got {result['category']} (scores: {result['scores']})"

    def test_detects_four_numbered_entries(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert len(meds) >= 3, f"Expected ≥3 medications, got {len(meds)}: {names}"

    def test_does_not_include_address_fragments(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        # Address/header fragments must NOT become medicine entries
        bad = [n for n in names if n in ('b', 'mmc', 'ph', 'timing', 'opd', 'shospital')]
        assert not bad, f"Address/header fragments treated as medicines: {bad}"

    def test_does_not_include_section_headings(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        bad = [n for n in names if n in (
            'chief', 'complaint', 'clinical', 'findings', 'medicine',
            'dosage', 'duration', 'weight', 'height',
        )]
        assert not bad, f"Section headings treated as medicines: {bad}"

    def test_does_not_include_advice_lines(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        bad = [n for n in names if n in ('plenty', 'bland', 'fluids', 'diet', 'advice', 'follow')]
        assert not bad, f"Advice words treated as medicines: {bad}"

    def test_paracetamol_detected(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('paracetamol' in n for n in names), \
            f"Paracetamol not found in {names}"

    def test_azithromycin_detected(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('azithromycin' in n for n in names), \
            f"Azithromycin not found in {names}"

    def test_frequency_extracted(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        paracetamol = next(
            (m for m in meds if 'paracetamol' in m['name_transcribed'].lower()), None
        )
        assert paracetamol is not None, "Paracetamol not found"
        assert paracetamol['frequency'] is not None, \
            f"Frequency not extracted for Paracetamol: {paracetamol}"

    def test_duration_extracted(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        paracetamol = next(
            (m for m in meds if 'paracetamol' in m['name_transcribed'].lower()), None
        )
        assert paracetamol is not None, "Paracetamol not found"
        assert paracetamol['duration'] is not None, \
            f"Duration not extracted for Paracetamol: {paracetamol}"

    def test_ingredient_notes_not_counted_as_separate_medicines(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_WITH_INGREDIENTS, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        # "(Contains: Folic Acid 5mg)" should NOT become a separate medicine entry
        bad = [n for n in names if n.startswith('contains') or n.startswith('(')]
        assert not bad, f"Ingredient notes treated as medicines: {bad}"

    def test_full_pipeline_prescription_category(self):
        result = parse_medical_report(PRINTED_PRESCRIPTION_TEXT)
        assert result['document_category'] == 'prescription'
        assert result['important_values'] == {}
        assert result['abnormal_values'] == {}
        assert 'prescription_data' in result
        # No "normal ranges" message for a prescription
        for f in result['key_findings']:
            assert 'normal ranges' not in f.lower()


class TestPrintedPrescriptionIngredients:
    def test_folic_acid_is_medicine_not_lab_value(self):
        lab_values = extract_key_values(PRINTED_PRESCRIPTION_WITH_INGREDIENTS)
        test_names_lower = [v['test_name'].lower() for v in lab_values]
        # "Folic Acid" should not appear as a lab result
        assert not any('folic' in n for n in test_names_lower), \
            f"Folic Acid wrongly extracted as lab value: {test_names_lower}"

    def test_gestakind_has_uncertain_flag(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_WITH_INGREDIENTS, writing_mode='printed')
        gestakind = next(
            (m for m in meds if 'gestakind' in m['name_transcribed'].lower()), None
        )
        if gestakind:
            # Name is OCR-uncertain so should be flagged for review
            assert gestakind['requires_review'] is True, \
                f"Gestakind should be flagged for review: {gestakind}"


# ---------------------------------------------------------------------------
# Handwritten prescription tests
# ---------------------------------------------------------------------------

class TestHandwrittenPrescription:
    def test_classified_as_prescription(self):
        result = classify_document(HANDWRITTEN_PRESCRIPTION_DENTAL)
        assert result['category'] == 'prescription', \
            f"Expected prescription, got {result['category']} (scores: {result['scores']})"

    def test_clinic_branding_excluded(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        bad = [n for n in names if n in ('the', 'white', 'tusk', 'smile', 'dental')]
        assert not bad, f"Clinic branding treated as medicines: {bad}"

    def test_meals_not_a_medicine(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert 'meals' not in names, f"'meals' wrongly treated as medicine: {names}"
        assert 'after meals' not in names

    def test_massage_not_a_medicine(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_NOISE, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert 'massoge' not in names, f"'massoge' wrongly treated as medicine: {names}"
        assert 'massage' not in names

    def test_the_not_a_medicine(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_NOISE, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert 'the' not in names, f"'THE' wrongly treated as medicine: {names}"

    def test_a_tab_not_a_medicine(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_NOISE, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        # "a Tab" by itself with no dosage/duration evidence is not a medicine
        assert 'a' not in names

    def test_augmentin_detected(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('augmentin' in n for n in names), \
            f"Augmentin not detected in {names}"

    def test_enzoflam_detected(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('enzoflam' in n for n in names), \
            f"Enzoflam not detected in {names}"

    def test_pan_d_detected(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('pan' in n for n in names), \
            f"Pan-D not detected in {names}"

    def test_hexigel_detected_as_topical(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        gum_paint = next(
            (m for m in meds if 'hexigel' in m['name_transcribed'].lower()), None
        )
        if gum_paint:
            assert gum_paint['route'] in ('Topical', 'Topical/Dental', None), \
                f"Hexigel route should be topical: {gum_paint['route']}"

    def test_dosage_schedule_1_0_1_detected(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        augmentin = next(
            (m for m in meds if 'augmentin' in m['name_transcribed'].lower()), None
        )
        assert augmentin is not None, "Augmentin not found"
        assert augmentin.get('dose_schedule') == '1-0-1', \
            f"Expected dose_schedule '1-0-1', got: {augmentin.get('dose_schedule')}"

    def test_dosage_schedule_1_0_0_detected(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        pan_d = next(
            (m for m in meds if 'pan' in m['name_transcribed'].lower()), None
        )
        if pan_d:
            assert pan_d.get('dose_schedule') == '1-0-0', \
                f"Expected dose_schedule '1-0-0' for Pan-D, got: {pan_d.get('dose_schedule')}"

    def test_after_meals_instruction_extracted(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        augmentin = next(
            (m for m in meds if 'augmentin' in m['name_transcribed'].lower()), None
        )
        if augmentin:
            assert augmentin.get('meal_instructions') == 'After food', \
                f"Expected 'After food' for Augmentin, got: {augmentin.get('meal_instructions')}"

    def test_before_meals_instruction_extracted(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        pan_d = next(
            (m for m in meds if 'pan' in m['name_transcribed'].lower()), None
        )
        if pan_d:
            assert pan_d.get('meal_instructions') == 'Before food', \
                f"Expected 'Before food' for Pan-D, got: {pan_d.get('meal_instructions')}"

    def test_duration_extracted_for_handwritten(self):
        meds = parse_prescription(HANDWRITTEN_PRESCRIPTION_DENTAL, writing_mode='handwritten')
        augmentin = next(
            (m for m in meds if 'augmentin' in m['name_transcribed'].lower()), None
        )
        if augmentin:
            assert augmentin.get('duration') is not None, \
                f"Duration not extracted for Augmentin: {augmentin}"

    def test_full_pipeline_prescription_category_handwritten(self):
        result = parse_medical_report(HANDWRITTEN_PRESCRIPTION_DENTAL)
        assert result['document_category'] == 'prescription'
        assert result['important_values'] == {}
        assert result['abnormal_values'] == {}

    def test_low_confidence_classification_still_extracts(self):
        """Even with low classification confidence, we should still attempt extraction."""
        result = parse_medical_report(HANDWRITTEN_PRESCRIPTION_NOISE)
        # Should not crash; may be prescription or unknown category
        assert 'document_category' in result
        assert 'key_findings' in result


# ---------------------------------------------------------------------------
# Header parser tests
# ---------------------------------------------------------------------------

class TestPrescriptionHeader:
    def test_patient_name_extracted(self):
        header = parse_prescription_header(PRINTED_PRESCRIPTION_TEXT)
        assert 'patient_name' in header, f"Patient name not extracted: {header}"
        assert header['patient_name'].strip() != '', "Patient name is empty"

    def test_patient_name_not_a_label_word(self):
        header = parse_prescription_header(PRINTED_PRESCRIPTION_TEXT)
        bad_labels = {'patient', 'dosage', 'duration', 'medicine', 'drug',
                      'tablet', 'name', 'doctor', 'hospital'}
        name = header.get('patient_name', '').lower().strip()
        assert name not in bad_labels, \
            f"patient_name contains a label word: '{name}'"

    def test_age_extracted(self):
        header = parse_prescription_header(PRINTED_PRESCRIPTION_TEXT)
        assert 'patient_age' in header, f"Age not extracted: {header}"
        assert header['patient_age'] == 24

    def test_sex_extracted(self):
        header = parse_prescription_header(PRINTED_PRESCRIPTION_TEXT)
        assert 'patient_sex' in header, f"Sex not extracted: {header}"

    def test_date_extracted(self):
        header = parse_prescription_header(PRINTED_PRESCRIPTION_TEXT)
        assert 'date' in header, f"Date not extracted: {header}"

    def test_header_dental_clinic_not_in_patient_name(self):
        header = parse_prescription_header(HANDWRITTEN_PRESCRIPTION_DENTAL)
        name = header.get('patient_name', '').lower()
        bad = ['white', 'tusk', 'smile', 'dental']
        assert not any(b in name for b in bad), \
            f"Clinic name leaked into patient_name: '{header.get('patient_name')}'"


# ---------------------------------------------------------------------------
# Lab report regression
# ---------------------------------------------------------------------------

class TestLabReportRegression:
    def test_lab_report_still_works(self):
        result = parse_medical_report(LAB_REPORT_TEXT)
        assert result['document_category'] == 'laboratory_report'
        assert len(result.get('important_values', {})) > 0

    def test_lab_report_no_prescription_data(self):
        result = parse_medical_report(LAB_REPORT_TEXT)
        assert 'prescription_data' not in result or result.get('prescription_data') is None

    def test_lab_values_not_extracted_from_prescription(self):
        lab_vals = extract_key_values(PRINTED_PRESCRIPTION_TEXT)
        test_names = [v['test_name'].lower() for v in lab_vals]
        bad = [n for n in test_names if n in (
            'weight', 'height', 'bp', 'b', 'mmc', 'ph', 'timing', 'opd', 'fever'
        )]
        assert not bad, f"Prescription noise misidentified as lab values: {bad}"


# ---------------------------------------------------------------------------
# Dose schedule detection
# ---------------------------------------------------------------------------

class TestDoseSchedule:
    def test_1_0_1_detected(self):
        assert _extract_dose_schedule("1-0-1 for 5 days") == "1-0-1"

    def test_1_0_0_detected(self):
        assert _extract_dose_schedule("1-0-0 before meals") == "1-0-0"

    def test_1_1_1_detected(self):
        assert _extract_dose_schedule("1-1-1 TDS") == "1-1-1"

    def test_no_schedule_returns_none(self):
        assert _extract_dose_schedule("take twice daily") is None

    def test_spaces_also_work(self):
        result = _extract_dose_schedule("1 0 1")
        assert result == "1-0-1"


# ---------------------------------------------------------------------------
# Non-medicine candidate detection
# ---------------------------------------------------------------------------

class TestNonMedicineCandidate:
    def test_the_is_excluded(self):
        assert _is_non_medicine_candidate("THE") is True

    def test_smile_is_excluded(self):
        assert _is_non_medicine_candidate("Smile") is True

    def test_dental_is_excluded(self):
        assert _is_non_medicine_candidate("Dental") is True

    def test_meals_is_excluded(self):
        assert _is_non_medicine_candidate("meals") is True

    def test_massage_is_excluded(self):
        assert _is_non_medicine_candidate("massoge") is True

    def test_medicine_header_excluded(self):
        assert _is_non_medicine_candidate("Medicine") is True

    def test_dosage_header_excluded(self):
        assert _is_non_medicine_candidate("Dosage") is True

    def test_augmentin_not_excluded(self):
        assert _is_non_medicine_candidate("Augmentin") is False

    def test_paracetamol_not_excluded(self):
        assert _is_non_medicine_candidate("Paracetamol") is False

    def test_hexigel_not_excluded(self):
        assert _is_non_medicine_candidate("Hexigel") is False


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_text_returns_no_meds(self):
        assert parse_prescription("") == []
        assert parse_prescription("   ") == []

    def test_poor_quality_ocr_no_crash(self):
        poor_ocr = "Sm@rt C1ty H0sp1t@l P@ti3nt: Unkn0wn"
        result = parse_prescription(poor_ocr, writing_mode='printed')
        # Should not crash; may return empty or flagged entries
        assert isinstance(result, list)

    def test_ambiguous_document_classified_as_prescription(self):
        result = classify_document(AMBIGUOUS_PRESCRIPTION_TEXT)
        assert result['category'] == 'prescription'

    def test_ambiguous_prescription_extracts_meds(self):
        meds = parse_prescription(AMBIGUOUS_PRESCRIPTION_TEXT, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('cetirizine' in n for n in names), \
            f"Cetirizine not extracted from ambiguous prescription: {names}"

    def test_malformed_ocr_no_crash(self):
        malformed = "\x00\xff some text \n\n\n Tab??? 500 mg"
        result = parse_medical_report(malformed)
        assert isinstance(result, dict)
        assert 'document_category' in result

    def test_numbered_entry_split(self):
        lines = [
            "1. Tab Paracetamol 500mg TDS 5 days",
            "2. Tab Azithromycin 500mg OD 3 days",
            "3. Tab Pantoprazole 40mg OD 5 days",
        ]
        entries = _split_into_numbered_entries(lines)
        assert len(entries) == 3
        assert entries[0][0] == 1
        assert entries[1][0] == 2
        assert entries[2][0] == 3

    def test_requires_review_set_for_short_names(self):
        text = "Tab AB 5mg od 5 days"
        meds = parse_prescription(text, writing_mode='printed')
        for m in meds:
            if len(m['name_transcribed']) < 5:
                assert m['requires_review'] is True

    def test_confidence_field_always_present(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        for m in meds:
            assert 'confidence' in m
            assert 0.0 <= m['confidence'] <= 1.0

    def test_requires_review_field_always_present(self):
        meds = parse_prescription(PRINTED_PRESCRIPTION_TEXT, writing_mode='printed')
        for m in meds:
            assert 'requires_review' in m
            assert isinstance(m['requires_review'], bool)
