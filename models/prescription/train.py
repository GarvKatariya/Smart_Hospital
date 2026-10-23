"""
Prescription Understanding - Medical Entity Extraction

Rule-based prescription extraction designed to work with OCR output.

The OCR engine may not preserve the visual table structure of a prescription.
Therefore, this extractor:
1. Locates the medication section.
2. Identifies medicine names using a controlled vocabulary.
3. Groups nearby OCR lines belonging to the same medication.
4. Extracts dosage, frequency, duration, route, and instructions.
"""

import json
import os
import re
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

DOSAGE_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*(?:mg|g|ml|mcg|µg|iu|units?)\b",
    r"\b\d+(?:\.\d+)?\s*[-/]\s*\d+(?:\.\d+)?\s*(?:mg|g|ml|mcg|µg)\b",
    r"\b\d+\s*(?:tablet|tablets|tab|tabs|capsule|capsules|cap|caps)\b",
]

FREQUENCY_PATTERNS = [
    (r"\b(?:once|1\s*time)\s+(?:daily|a\s*day|per\s*day)\b", "Once daily"),
    (r"\b(?:twice|2\s*times?|bid|b\.i\.d)\s*(?:daily|a\s*day|per\s*day)?\b", "Twice daily"),
    (r"\b(?:thrice|3\s*times?|tid|t\.i\.d)\s*(?:daily|a\s*day|per\s*day)?\b", "Three times daily"),
    (r"\b(?:four\s*times?|qid|q\.i\.d)\s*(?:daily|a\s*day|per\s*day)?\b", "Four times daily"),
    (r"\bevery\s+\d+\s+hours?\b", None),
    (r"\b(?:morning|evening|night|bedtime)\b", None),
    (r"\b(?:daily|od|o\.d\.)\b", "Once daily"),
    (r"\b(?:sos|as\s*needed|prn|p\.r\.n)\b", "As needed"),
]

DURATION_PATTERNS = [
    r"\b(?:for|x)\s*\d+\s*(?:day|days|week|weeks|month|months)\b",
    r"\b\d+\s*(?:day|days|week|weeks|month|months)\s*(?:course|supply)?\b",
]

ROUTE_PATTERNS = [
    (r"\b(?:orally|oral|by\s+mouth|p\.?o\.?)\b", "Oral"),
    (r"\b(?:topical|topically|external|apply)\b", "Topical"),
    (r"\b(?:injection|injectable|intramuscular|i\.?m\.?|intravenous|i\.?v\.?|subcutaneous|s\.?c\.?)\b", "Injectable"),
    (r"\b(?:inhalation|inhaler|nebulizer|nebulise|nebulize)\b", "Inhalation"),
    (r"\b(?:eye\s+drop|ophthalmic)\b", "Ophthalmic"),
    (r"\b(?:ear\s+drop|otic)\b", "Otic"),
]


# ---------------------------------------------------------------------------
# Controlled medicine vocabulary
# ---------------------------------------------------------------------------

COMMON_MEDICINES = {
    "paracetamol": "Paracetamol (Acetaminophen)",
    "acetaminophen": "Paracetamol (Acetaminophen)",
    "amoxicillin": "Amoxicillin",
    "azithromycin": "Azithromycin",
    "ibuprofen": "Ibuprofen",
    "metformin": "Metformin",
    "atorvastatin": "Atorvastatin",
    "omeprazole": "Omeprazole",
    "pantoprazole": "Pantoprazole",
    "amlodipine": "Amlodipine",
    "lisinopril": "Lisinopril",
    "losartan": "Losartan",
    "metoprolol": "Metoprolol",
    "aspirin": "Aspirin",
    "clopidogrel": "Clopidogrel",
    "ciprofloxacin": "Ciprofloxacin",
    "doxycycline": "Doxycycline",
    "cetirizine": "Cetirizine",
    "montelukast": "Montelukast",
    "salbutamol": "Salbutamol (Albuterol)",
    "prednisolone": "Prednisolone",
    "insulin": "Insulin",
    "levothyroxine": "Levothyroxine",
    "warfarin": "Warfarin",
    "diclofenac": "Diclofenac",
    "ranitidine": "Ranitidine",
    "ceftriaxone": "Ceftriaxone",
    "gabapentin": "Gabapentin",
    "tramadol": "Tramadol",
    "fluconazole": "Fluconazole",

    # Useful additions for the current test prescription
    "multivitamin": "Multivitamin",
    "b-complex": "Vitamin B-Complex",
    "vitamin b-complex": "Vitamin B-Complex",
}


# ---------------------------------------------------------------------------
# Lines that should never be interpreted as medicines
# ---------------------------------------------------------------------------

NON_MEDICATION_PREFIXES = (
    "city care hospital",
    "smart city general hospital",
    "patient",
    "patient name",
    "patient id",
    "department",
    "consulting doctor",
    "age",
    "age / gender",
    "date",
    "reg.",
    "registration",
    "chief complaint",
    "diagnosis",
    "sr. no",
    "medicine name",
    "dosage",
    "duration",
    "instructions",
    "additional advice",
    "next appointment",
    "wishing you good health",
    "drink plenty of fluids",
    "take rest",
    "if symptoms persist",
    "consultant physician",
    "ph:",
    "email:",
)


class PrescriptionNER:
    """
    Structured medication extraction from OCR text.

    This is rule-based extraction rather than a trained neural NER model.
    The public interface remains `extract_medications(text)` so the rest
    of the application does not need to change.
    """

    def __init__(self):
        self.medicine_vocab = COMMON_MEDICINES

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def extract_medications(self, text: str) -> List[Dict]:
        """
        Extract medications from OCR text.

        The OCR engine may produce table contents as separate lines, e.g.:

            Paracetamol 500 mg
            1 tablet
            3 days
            After food, thrice daily

        These lines are merged into a single medication record.
        """

        if not text or not text.strip():
            return []

        lines = self._clean_lines(text)

        # Find where medication table begins.
        start_index = self._find_medication_section(lines)

        if start_index is not None:
            candidate_lines = lines[start_index:]
        else:
            # Fallback for plain prescriptions without an explicit table header.
            candidate_lines = lines

        # Stop at sections that clearly indicate the medication table is over.
        candidate_lines = self._trim_after_medication_section(candidate_lines)

        medication_records = []
        current = None

        for line in candidate_lines:
            medicine_match = self._find_known_medicine(line)

            if medicine_match:
                # If we're already processing a medicine, finish it first.
                if current:
                    medication_records.append(self._finalize_record(current))

                normalized_name, confidence = medicine_match

                current = {
                    "raw_parts": [line],
                    "normalized_name": normalized_name,
                    "dosage": self._extract_dosage(line),
                    "frequency": self._extract_frequency(line),
                    "duration": self._extract_duration(line),
                    "route": self._extract_route(line) or "Oral",
                    "instructions": self._extract_instructions(line),
                    "confidence": confidence,
                    "needs_verification": confidence < 0.8,
                }

                continue

            # If this is not a medicine line, attach useful information
            # to the currently active medication.
            if current:
                if self._looks_like_metadata(line):
                    continue

                current["raw_parts"].append(line)

                if not current["dosage"]:
                    current["dosage"] = self._extract_dosage(line)

                if not current["frequency"]:
                    current["frequency"] = self._extract_frequency(line)

                if not current["duration"]:
                    current["duration"] = self._extract_duration(line)

                route = self._extract_route(line)
                if route:
                    current["route"] = route

                instructions = self._extract_instructions(line)
                if instructions:
                    if current["instructions"]:
                        current["instructions"] = (
                            current["instructions"] + "; " + instructions
                        )
                    else:
                        current["instructions"] = instructions

        if current:
            medication_records.append(self._finalize_record(current))

        # Remove accidental duplicates while preserving order.
        return self._deduplicate(medication_records)

    # -----------------------------------------------------------------------
    # OCR cleanup
    # -----------------------------------------------------------------------

    def _clean_lines(self, text: str) -> List[str]:
        """Normalize OCR text into useful non-empty lines."""

        lines = []

        for raw_line in text.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip()

            if not line:
                continue

            # Remove repeated separators around table cells.
            line = line.strip("|")

            if len(line) < 2:
                continue

            lines.append(line)

        return lines

    # -----------------------------------------------------------------------
    # Medication section detection
    # -----------------------------------------------------------------------

    def _find_medication_section(self, lines: List[str]) -> Optional[int]:
        """
        Find the line after the prescription table header.

        Example:
            Sr. No.
            Medicine Name
            Dosage
            Duration
            Instructions
            1
            Paracetamol 500 mg

        We start collecting around the first medicine name.
        """

        for i, line in enumerate(lines):
            lower = line.lower()

            if "medicine name" in lower:
                return i + 1

        # If no header exists, locate first known medicine.
        for i, line in enumerate(lines):
            if self._find_known_medicine(line):
                return i

        return None

    def _trim_after_medication_section(self, lines: List[str]) -> List[str]:
        """
        Stop processing when clearly non-medication sections begin.
        """

        stop_markers = (
            "additional advice",
            "next appointment",
            "wishing you good health",
            "consultant physician",
        )

        result = []

        for line in lines:
            lower = line.lower()

            if any(marker in lower for marker in stop_markers):
                break

            result.append(line)

        return result

    # -----------------------------------------------------------------------
    # Medicine identification
    # -----------------------------------------------------------------------

    def _find_known_medicine(
        self, line: str
    ) -> Optional[tuple[str, float]]:
        """
        Identify a known medicine in the line.

        Only a controlled vocabulary is treated as a high-confidence medicine.
        This prevents words such as "Patient", "Date", "Diagnosis", etc. from
        being incorrectly classified as medications.
        """

        line_lower = line.lower()

        for key, normalized in sorted(
            self.medicine_vocab.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if re.search(rf"\b{re.escape(key)}\b", line_lower):
                confidence = 0.92

                # The generic "multivitamin" entry is slightly less specific.
                if key == "multivitamin":
                    confidence = 0.82

                return normalized, confidence

        return None

    # -----------------------------------------------------------------------
    # Field extraction
    # -----------------------------------------------------------------------

    def _extract_dosage(self, text: str) -> Optional[str]:
        for pattern in DOSAGE_PATTERNS:
            match = re.search(pattern, text.lower())

            if match:
                return match.group(0)

        return None

    def _extract_frequency(self, text: str) -> Optional[str]:
        text_lower = text.lower()

        for pattern, normalized in FREQUENCY_PATTERNS:
            match = re.search(pattern, text_lower)

            if match:
                if normalized is not None:
                    return normalized

                value = match.group(0).strip()
                return value.capitalize()

        return None

    def _extract_duration(self, text: str) -> Optional[str]:
        text_lower = text.lower()

        for pattern in DURATION_PATTERNS:
            match = re.search(pattern, text_lower)

            if match:
                value = match.group(0).strip()

                # Normalize common "x 5 days" wording.
                value = re.sub(r"^x\s*", "", value)

                return value

        return None

    def _extract_route(self, text: str) -> Optional[str]:
        text_lower = text.lower()

        for pattern, route in ROUTE_PATTERNS:
            if re.search(pattern, text_lower):
                return route

        return None

    def _extract_instructions(self, text: str) -> Optional[str]:
        text_lower = text.lower()

        instruction_fragments = []

        if "after food" in text_lower:
            instruction_fragments.append("After food")

        elif "after meal" in text_lower:
            instruction_fragments.append("After meal")

        elif "before food" in text_lower:
            instruction_fragments.append("Before food")

        elif "before meal" in text_lower:
            instruction_fragments.append("Before meal")

        if "at night" in text_lower:
            instruction_fragments.append("At night")

        elif "at bedtime" in text_lower:
            instruction_fragments.append("At bedtime")

        elif "in the morning" in text_lower:
            instruction_fragments.append("In the morning")

        if instruction_fragments:
            return ", ".join(instruction_fragments)

        return None

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _looks_like_metadata(self, line: str) -> bool:
        """
        Detect lines that are clearly not part of a medication entry.
        """

        lower = line.lower().strip()

        if any(lower.startswith(prefix) for prefix in NON_MEDICATION_PREFIXES):
            return True

        # Doctor/registration/contact information.
        if lower.startswith("dr."):
            return True

        if "@" in line:
            return True

        if re.search(r"\b(?:ph|phone|tel)\s*:", lower):
            return True

        # Pure numbering or table headings.
        if re.fullmatch(r"\d+", lower):
            return True

        return False

    def _finalize_record(self, record: Dict) -> Dict:
        raw_parts = record.pop("raw_parts", [])

        raw_text = " ".join(raw_parts)
        raw_text = re.sub(r"\s+", " ", raw_text).strip()

        # Clean obvious OCR duplication.
        instructions = record.get("instructions")
        if instructions:
            instructions = re.sub(r"\s+", " ", instructions).strip()

        return {
            "raw_text": raw_text,
            "normalized_name": record["normalized_name"],
            "dosage": record.get("dosage"),
            "frequency": record.get("frequency"),
            "duration": record.get("duration"),
            "route": record.get("route") or "Oral",
            "instructions": instructions,
            "confidence": record.get("confidence", 0.8),
            "needs_verification": record.get("needs_verification", False),
        }

    def _deduplicate(self, records: List[Dict]) -> List[Dict]:
        seen = set()
        result = []

        for record in records:
            key = (
                record.get("normalized_name", "").lower(),
                record.get("dosage", "") or "",
                record.get("duration", "") or "",
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(record)

        return result


# ---------------------------------------------------------------------------
# Existing model config generation
# ---------------------------------------------------------------------------

def save_model(output_dir="artifacts"):
    """Save the NER model configuration."""

    os.makedirs(output_dir, exist_ok=True)

    config = {
        "model_name": "prescription-ner-v2",
        "type": "rule_based_ner",
        "medicine_vocab_size": len(COMMON_MEDICINES),
        "note": (
            "Rule-based medical entity extraction with OCR-aware "
            "prescription section parsing."
        ),
    }

    with open(os.path.join(output_dir, "model_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    print(f"Prescription NER config saved to {output_dir}")


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_text = """
    City Care Hospital
    123 Health Avenue, Green Park
    New Delhi - 110016
    Ph: +91 11 2345 6789
    Your Health Our Priority
    Email: care@citycarehospital.com
    Patient Name
    : Kshitij Sharma
    Department: General Medicine
    Patient ID
    : PAT001234
    Consulting Doctor:
    Dr. Garv Katariya
    : 24 Years / Male
    MBBS, MD (Internal Medicine)
    Date
    : 08 Sep 2026
    Reg. No.: DMC20261234
    Chief Complaint: Fever, sore throat and body ache since 3 days.
    Diagnosis: Acute Viral Upper Respiratory Tract Infection (URTI)
    Sr. No.
    Medicine Name
    Dosage
    Duration
    Instructions
    1
    Paracetamol 500 mg
    1 tablet
    3 days
    After food, thrice daily
    2
    Azithromycin 500 mg
    1 tablet
    5 days
    After food, once daily
    3
    Cetirizine 10 mg
    1 tablet
    5 days
    At night
    4
    Multivitamin (B-Complex)
    1 tablet
    10 days
    After food, once daily
    Additional Advice:
    Drink plenty of fluids.
    Take rest and avoid strenuous activity.
    If symptoms persist or worsen, consult immediately.
    Next Appointment: 15 Sep 2026
    Dr. Garv Katariya
    Consultant Physician
    Wishing You Good Health
    """

    ner = PrescriptionNER()
    results = ner.extract_medications(test_text)

    print(json.dumps(results, indent=2))
