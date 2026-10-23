"""
Prescription Understanding - Inference Service

Loads PrescriptionNER from the exact prescription/train.py file.
This avoids conflicts with other train.py files in the project.
"""

from typing import Dict, List
import importlib.util
import os


class PrescriptionModel:
    def __init__(self, model_dir="artifacts"):
        self.model_dir = model_dir
        self.ner = None
        self._loaded = False

    def load(self) -> bool:
        """Load PrescriptionNER from models/prescription/train.py."""

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            train_path = os.path.join(current_dir, "train.py")

            if not os.path.exists(train_path):
                raise FileNotFoundError(
                    f"Prescription train.py not found: {train_path}"
                )

            spec = importlib.util.spec_from_file_location(
                "prescription_train_module",
                train_path,
            )

            if spec is None or spec.loader is None:
                raise ImportError(
                    f"Could not load module from: {train_path}"
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            PrescriptionNER = getattr(module, "PrescriptionNER", None)

            if PrescriptionNER is None:
                raise ImportError(
                    "PrescriptionNER class not found in prescription/train.py"
                )

            self.ner = PrescriptionNER()
            self._loaded = True

            print(
                f"Successfully loaded PrescriptionNER from: {train_path}"
            )

            return True

        except Exception as e:
            print(f"Failed to load prescription model: {e}")
            self.ner = None
            self._loaded = False
            return False

    def extract(self, text: str) -> List[Dict]:
        """Extract structured medication information from OCR text."""

        if not self._loaded:
            self.load()

        if not self.ner:
            return []

        return self.ner.extract_medications(text)
