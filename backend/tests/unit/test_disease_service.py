"""Unit tests for disease service."""
from unittest.mock import MagicMock

import numpy as np

from app.services.disease_service import DiseaseService, FEATURE_NAMES


def test_disease_prediction_uses_ordered_features_and_reports_risk():
    service = DiseaseService()
    service.model = MagicMock()
    service.model.predict.return_value = [1]
    service.model.predict_proba.return_value = [[0.1, 0.9]]
    service.model.feature_importances_ = np.ones(len(FEATURE_NAMES)) / len(FEATURE_NAMES)
    service._loaded = True

    features = {
        "age": 50, "sex": 1, "cp": 2, "trestbps": 120, "chol": 200,
        "fbs": 0, "restecg": 1, "thalach": 150, "exang": 0,
        "oldpeak": 1.0, "slope": 1, "ca": 0, "thal": 2,
    }

    result = service.predict(features)

    service.model.predict.assert_called_once()
    np.testing.assert_array_equal(
        service.model.predict.call_args.args[0][0],
        [features[name] for name in FEATURE_NAMES],
    )
    assert result["prediction"] == 1
    assert result["probability"] == 0.9
    assert result["risk_category"] == "High"
