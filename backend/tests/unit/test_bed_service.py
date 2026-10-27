"""Tests for database-backed bed status fallbacks."""
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from app.db.models.hospital import BedOccupancy, HospitalBed
from app.services.bed_service import BedService


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, beds, occupancy):
        self.rows = {HospitalBed: beds, BedOccupancy: occupancy}

    def query(self, model):
        return FakeQuery(self.rows[model])


def test_forecast_uses_live_capacity_when_history_and_model_are_missing():
    beds = [
        SimpleNamespace(status="occupied"),
        SimpleNamespace(status="available"),
        SimpleNamespace(status="maintenance"),
    ]
    db = FakeDB(beds, [])
    service = BedService()
    service.model.load = Mock(return_value=False)

    result = service.get_forecast(db)

    assert result["total_beds"] == 3
    assert result["predicted_occupied"] == [1] * 7
    assert result["predicted_available"] == [2] * 7
    assert len(result["dates"]) == 7
    assert result["source"] == "Live occupancy baseline (no admission history)"


def test_forecast_uses_trained_model_with_sparse_local_history():
    today = date.today()
    admissions = [
        SimpleNamespace(
            admission_date=datetime.combine(
                today - timedelta(days=offset),
                time(12),
            ),
            actual_discharge_date=None,
        )
        for offset in range(1, 11)
    ]
    db = FakeDB(
        [SimpleNamespace(status="occupied"), SimpleNamespace(status="available")],
        admissions,
    )
    service = BedService()
    service.model.load = Mock(return_value=True)
    service.model.predict_7day = Mock(return_value=[1, 2, 3, 4, 5, 6, 7])

    result = service.get_forecast(db)

    assert result["predicted_occupied"] == [1, 2, 2, 2, 2, 2, 2]
    assert "LSTM trained on Hero DMC" in result["source"]
    assert "Experimental forecast" in result["model_note"]
    service.model.predict_7day.assert_called_once()
