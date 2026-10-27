"""
Additional edge-case tests for prescription_parser — fills coverage gaps.

Tests cover:
  - _normalise_frequency(): all patterns in FREQUENCY_MAP
  - _normalise_meal(): all patterns in MEAL_MAP
  - _extract_dosage(): various dose formats
  - _extract_duration(): with and without "for" prefix
  - _extract_route(): all route patterns
  - _schedule_to_frequency(): mapping dose schedules to text
  - Freeform parsing with continuation/ingredient lines
  - Multi-word non-medicine phrase detection
  - Very long prescription with many entries
  - Unicode/special characters in OCR output
  - Mixed-case and unusual spacing
  - Prescription with only injections (no Tab/Cap)
  - Single-medicine prescription
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
    _normalise_frequency,
    _normalise_meal,
    _extract_dosage,
    _extract_duration,
    _extract_route,
    _build_medication_record,
)


# ---------------------------------------------------------------------------
# Frequency normalisation
# ---------------------------------------------------------------------------

class TestNormaliseFrequency:
    def test_od(self):
        assert _normalise_frequency("Take OD") == "Once daily"

    def test_once_daily(self):
        assert _normalise_frequency("once daily after food") == "Once daily"

    def test_once_a_day(self):
        assert _normalise_frequency("once a day") == "Once daily"

    def test_bd(self):
        assert _normalise_frequency("give BD") == "Twice daily"

    def test_bid(self):
        assert _normalise_frequency("BID with food") == "Twice daily"

    def test_twice_daily(self):
        assert _normalise_frequency("twice daily") == "Twice daily"

    def test_tds(self):
        assert _normalise_frequency("Tab 500mg TDS") == "Three times daily"

    def test_tid(self):
        assert _normalise_frequency("TID for 5 days") == "Three times daily"

    def test_three_times_daily(self):
        assert _normalise_frequency("three times daily") == "Three times daily"

    def test_qid(self):
        assert _normalise_frequency("QID after meals") == "Four times daily"

    def test_hs(self):
        assert _normalise_frequency("Tab HS") == "At bedtime"

    def test_bedtime(self):
        assert _normalise_frequency("at bedtime") == "At bedtime"

    def test_sos(self):
        assert _normalise_frequency("Tab 650mg SOS") == "As needed"

    def test_prn(self):
        assert _normalise_frequency("PRN for pain") == "As needed"

    def test_stat(self):
        assert _normalise_frequency("give STAT") == "Immediately"

    def test_no_match_returns_none(self):
        assert _normalise_frequency("some random text") is None

    def test_1_0_1_schedule_detected(self):
        result = _normalise_frequency("1-0-1 after meals")
        assert result is not None
        assert 'daily' in result.lower() or 'twice' in result.lower()

    def test_1_1_1_schedule_detected(self):
        result = _normalise_frequency("1-1-1 for 5 days")
        assert result is not None
        assert 'three' in result.lower()


# ---------------------------------------------------------------------------
# Meal normalisation
# ---------------------------------------------------------------------------

class TestNormaliseMeal:
    def test_after_food(self):
        assert _normalise_meal("after food") == "After food"

    def test_after_meals(self):
        assert _normalise_meal("after meals") == "After food"

    def test_before_food(self):
        assert _normalise_meal("before food") == "Before food"

    def test_before_meals(self):
        assert _normalise_meal("before meals") == "Before food"

    def test_with_food(self):
        assert _normalise_meal("with food") == "With food"

    def test_empty_stomach(self):
        assert _normalise_meal("on empty stomach") == "On empty stomach"

    def test_with_water(self):
        assert _normalise_meal("with water") == "With water"

    def test_af_abbreviation(self):
        assert _normalise_meal("take AF") == "After food"

    def test_bf_abbreviation(self):
        assert _normalise_meal("take BF") == "Before food"

    def test_no_match_returns_none(self):
        assert _normalise_meal("some random text") is None


# ---------------------------------------------------------------------------
# Dosage extraction
# ---------------------------------------------------------------------------

class TestExtractDosage:
    def test_mg_dosage(self):
        result = _extract_dosage("500mg after food")
        assert result is not None
        assert '500' in result and 'mg' in result.lower()

    def test_mcg_dosage(self):
        result = _extract_dosage("250 mcg daily")
        assert result is not None
        assert '250' in result

    def test_ml_dosage(self):
        result = _extract_dosage("5ml syrup TDS")
        assert result is not None
        assert '5' in result and 'ml' in result.lower()

    def test_tablet_dosage(self):
        result = _extract_dosage("2 tablets daily")
        assert result is not None
        assert '2' in result

    def test_drops_dosage(self):
        result = _extract_dosage("3 drops in each eye")
        assert result is not None
        assert '3' in result

    def test_decimal_dosage(self):
        result = _extract_dosage("0.5mg daily")
        assert result is not None
        assert '0.5' in result

    def test_no_dosage_returns_none(self):
        assert _extract_dosage("take after food") is None


# ---------------------------------------------------------------------------
# Duration extraction
# ---------------------------------------------------------------------------

class TestExtractDuration:
    def test_days_with_for(self):
        result = _extract_duration("for 5 days")
        assert result is not None
        assert '5' in result and 'day' in result.lower()

    def test_days_without_for(self):
        result = _extract_duration("7 days")
        assert result is not None
        assert '7' in result

    def test_weeks(self):
        result = _extract_duration("for 2 weeks")
        assert result is not None
        assert '2' in result and 'week' in result.lower()

    def test_months(self):
        result = _extract_duration("for 3 months")
        assert result is not None
        assert '3' in result and 'month' in result.lower()

    def test_no_duration_returns_none(self):
        assert _extract_duration("take daily") is None


# ---------------------------------------------------------------------------
# Route extraction
# ---------------------------------------------------------------------------

class TestExtractRoute:
    def test_oral(self):
        assert _extract_route("oral tablet") == "Oral"

    def test_topical(self):
        assert _extract_route("apply topically") == "Topical"

    def test_iv(self):
        assert _extract_route("give iv stat") == "Intravenous"

    def test_intravenous(self):
        assert _extract_route("intravenous drip") == "Intravenous"

    def test_im(self):
        assert _extract_route("im injection") == "Intramuscular"

    def test_sc_subcutaneous(self):
        assert _extract_route("sc injection daily") == "Subcutaneous"

    def test_inhalation(self):
        assert _extract_route("inhalation 2 puffs") == "Inhalation"

    def test_nasal(self):
        assert _extract_route("nasal spray") == "Nasal"

    def test_eye(self):
        assert _extract_route("eye drops") == "Optic/Aural"

    def test_gum_paint(self):
        assert _extract_route("gum paint bd") == "Topical/Dental"

    def test_gel(self):
        assert _extract_route("apply gel locally") == "Topical/Dental"

    def test_no_route_returns_none(self):
        assert _extract_route("some random text") is None


# ---------------------------------------------------------------------------
# Multi-word non-medicine phrase detection
# ---------------------------------------------------------------------------

class TestMultiWordNonMedicinePhrases:
    def test_white_tusk_excluded(self):
        assert _is_non_medicine_candidate("White Tusk") is True

    def test_smile_dental_excluded(self):
        assert _is_non_medicine_candidate("Smile Dental") is True

    def test_after_meals_excluded(self):
        assert _is_non_medicine_candidate("After Meals") is True

    def test_follow_up_excluded(self):
        assert _is_non_medicine_candidate("Follow Up") is True

    def test_medicine_name_excluded(self):
        assert _is_non_medicine_candidate("Medicine Name") is True

    def test_purely_numeric_excluded(self):
        assert _is_non_medicine_candidate("12345") is True
        assert _is_non_medicine_candidate("12-34-56") is True

    def test_very_short_excluded(self):
        assert _is_non_medicine_candidate("AB") is True
        assert _is_non_medicine_candidate("X") is True

    def test_all_exclusion_words(self):
        assert _is_non_medicine_candidate("the clinic") is True


# ---------------------------------------------------------------------------
# _build_medication_record edge cases
# ---------------------------------------------------------------------------

class TestBuildMedicationRecord:
    def test_rejects_non_medicine_name(self):
        result = _build_medication_record(
            "The White Tusk", "The White Tusk clinic", None, [], 'printed'
        )
        assert result is None

    def test_rejects_no_evidence_line(self):
        """A name with no medicine evidence (no dosage, no form, no frequency) is skipped."""
        result = _build_medication_record(
            "Sunshine", "Sunshine morning walk", None, [], 'printed'
        )
        assert result is None

    def test_accepts_name_with_form_prefix(self):
        result = _build_medication_record(
            "Tab. Paracetamol", "Tab. Paracetamol 500mg TDS 5 days", None, [], 'printed'
        )
        assert result is not None
        assert 'paracetamol' in result['name_transcribed'].lower()

    def test_accepts_name_with_dosage_evidence(self):
        result = _build_medication_record(
            "Amoxicillin", "Amoxicillin 500mg twice daily 7 days", None, [], 'printed'
        )
        assert result is not None

    def test_ingredient_notes_preserved(self):
        result = _build_medication_record(
            "Tab. Folic Acid",
            "Tab. Folic Acid 5mg OD 30 days (Contains: Folic Acid 5mg)",
            "Contains: Folic Acid 5mg",
            [], 'printed'
        )
        assert result is not None
        assert result['ingredient_notes'] == "Contains: Folic Acid 5mg"

    def test_requires_review_for_low_confidence(self):
        """Low OCR confidence should flag requires_review."""
        low_conf_lines = [{'text': 'Xyzpqr 500mg', 'confidence': 0.4}]
        result = _build_medication_record(
            "Xyzpqr", "Xyzpqr 500mg OD 5 days", None, low_conf_lines, 'printed'
        )
        assert result is not None
        assert result['requires_review'] is True


# ---------------------------------------------------------------------------
# Freeform parsing with continuation lines
# ---------------------------------------------------------------------------

class TestFreeformWithContinuation:
    def test_continuation_line_merged(self):
        text = """Tab. Metformin 500mg BD 30 days
(extended release formulation)
Tab. Glimepiride 2mg OD 30 days"""
        meds = parse_prescription(text, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        # The continuation line should not be a separate medicine
        assert not any('extended' in n for n in names)

    def test_ingredient_line_not_separate_medicine(self):
        text = """Tab. Augmentin 625mg 1-0-1 5 days after meals
contains amoxicillin 500mg + clavulanic acid 125mg
Tab. Enzoflam 1-0-1 5 days after meals"""
        meds = parse_prescription(text, writing_mode='handwritten')
        names = [m['name_transcribed'].lower() for m in meds]
        assert not any('contains' in n or 'amoxicillin' in n for n in names)


# ---------------------------------------------------------------------------
# Complex / realistic prescriptions
# ---------------------------------------------------------------------------

class TestComplexPrescriptions:
    INJECTION_PRESCRIPTION = """
Dr. Kumar, General Hospital
Patient: Anita Devi  Age: 55  Sex: Female
Date: 01/10/2023

Diagnosis: Diabetic Ketoacidosis

Rx:
1. Inj Insulin R 8 units SC stat
2. Inj Normal Saline 1000ml IV over 4 hours
3. Inj Ondansetron 4mg IV TDS 3 days
4. Tab Metformin 500mg BD after food 30 days
"""

    def test_injections_detected(self):
        meds = parse_prescription(self.INJECTION_PRESCRIPTION, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('insulin' in n for n in names), f"Insulin not found in {names}"

    def test_mixed_injection_and_tablet(self):
        meds = parse_prescription(self.INJECTION_PRESCRIPTION, writing_mode='printed')
        names = [m['name_transcribed'].lower() for m in meds]
        assert any('metformin' in n for n in names), f"Metformin not found in {names}"
        assert len(meds) >= 2

    SINGLE_MEDICINE = """
Dr. Patel
Patient: Raj
Rx:
1. Tab Paracetamol 500mg SOS for fever
"""

    def test_single_medicine_prescription(self):
        meds = parse_prescription(self.SINGLE_MEDICINE, writing_mode='printed')
        assert len(meds) >= 1
        assert any('paracetamol' in m['name_transcribed'].lower() for m in meds)

    LONG_PRESCRIPTION = """
Patient: Test Patient    Age: 40    Date: 01/01/2024

Rx:
1. Tab Amlodipine 5mg OD 30 days
2. Tab Atorvastatin 10mg HS 30 days
3. Tab Metformin 500mg BD 30 days after food
4. Tab Losartan 50mg OD 30 days
5. Tab Aspirin 75mg OD 30 days after food
6. Tab Clopidogrel 75mg OD 30 days
7. Cap Omeprazole 20mg OD before food 14 days
8. Tab Metoprolol 25mg BD 30 days
"""

    def test_many_entries_all_detected(self):
        meds = parse_prescription(self.LONG_PRESCRIPTION, writing_mode='printed')
        assert len(meds) >= 6, f"Expected ≥6 meds, got {len(meds)}"

    def test_each_med_has_required_fields(self):
        meds = parse_prescription(self.LONG_PRESCRIPTION, writing_mode='printed')
        for m in meds:
            assert 'name_raw' in m
            assert 'name_transcribed' in m
            assert 'confidence' in m
            assert 'requires_review' in m
            assert 'raw_line' in m


# ---------------------------------------------------------------------------
# Header parser edge cases
# ---------------------------------------------------------------------------

class TestHeaderEdgeCases:
    def test_header_with_female_patient(self):
        text = "Patient: Anita Devi  Age: 55  Sex: Female\nDate: 01/10/2023"
        header = parse_prescription_header(text)
        assert header.get('patient_sex', '').upper() in ('F', 'FEMALE')

    def test_header_with_slash_format(self):
        text = "Name: Raj Kumar\nAge/Sex: 30/Male\nDate: 15/05/2024"
        header = parse_prescription_header(text)
        assert header.get('patient_age') == 30

    def test_header_with_doctor(self):
        text = "Patient: Ram\nDr. Sharma\nDiagnosis: Fever"
        header = parse_prescription_header(text)
        assert 'doctor' in header or 'diagnosis' in header

    def test_header_with_diagnosis(self):
        text = "Patient: Ram  Age: 25\nDiagnosis: Acute Bronchitis"
        header = parse_prescription_header(text)
        assert header.get('diagnosis') is not None
        assert 'bronchitis' in header['diagnosis'].lower()

    def test_header_with_complaint_format(self):
        text = "Patient: Test\nc/o fever and body aches\nRx:"
        header = parse_prescription_header(text)
        # May or may not extract as diagnosis, but shouldn't crash
        assert isinstance(header, dict)

    def test_empty_header(self):
        header = parse_prescription_header("")
        assert isinstance(header, dict)
        assert len(header) == 0

    def test_header_no_structured_fields(self):
        header = parse_prescription_header("Hello world random text")
        assert isinstance(header, dict)


# ---------------------------------------------------------------------------
# Unicode and special character handling
# ---------------------------------------------------------------------------

class TestUnicodeHandling:
    def test_unicode_in_ocr_text(self):
        text = "Tab. Paracétamol 500mg TDS 5 days"
        meds = parse_prescription(text, writing_mode='printed')
        assert isinstance(meds, list)  # shouldn't crash

    def test_newlines_and_tabs(self):
        text = "1.\tTab Paracetamol 500mg\tTDS\t5 days\n2.\tTab Azithromycin 500mg\tOD\t3 days"
        meds = parse_prescription(text, writing_mode='printed')
        assert isinstance(meds, list)

    def test_null_bytes_dont_crash(self):
        text = "Tab\x00Paracetamol\x00500mg\x00TDS"
        meds = parse_prescription(text, writing_mode='printed')
        assert isinstance(meds, list)  # shouldn't crash
