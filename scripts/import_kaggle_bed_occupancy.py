"""Download and aggregate the public Hero DMC Kaggle admissions dataset.

Only daily date/count aggregates are written to the project. Patient-level rows
and identifiers remain in memory and are discarded with the temporary archive.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import os
import re
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/ashishsahani/hospital-admissions-data"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/real/beds/hero_dmc_daily.csv"
ADMISSION_FILE = "HDHI Admission data.csv"


def parse_date_candidates(raw: str) -> list[dt.date]:
    match = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", raw or "")
    if not match:
        return []
    first, second, year = map(int, match.groups())
    candidates = []
    # The source mixes MM/DD/YYYY and DD/MM/YYYY. Keep both interpretations
    # when the values are ambiguous; admission month and length of stay disambiguate.
    for month, day in ((first, second), (second, first)):
        try:
            candidate = dt.date(year, month, day)
        except ValueError:
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def aggregate_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, int | str]], int]:
    encounters: list[tuple[dt.date, dt.date]] = []
    dropped = 0
    for row in rows:
        try:
            month_year = dt.datetime.strptime(row["month year"].strip(), "%b-%y")
            admissions = [
                value
                for value in parse_date_candidates(row["D.O.A"])
                if value.month == month_year.month and value.year == month_year.year
            ]
            discharges = parse_date_candidates(row["D.O.D"])
            stay_days = float(row["DURATION OF STAY"])
            if not admissions or not discharges:
                raise ValueError("unparseable date")

            choices = [
                (admission, discharge)
                for admission in admissions
                for discharge in discharges
                if discharge >= admission
            ]
            if not choices:
                raise ValueError("discharge precedes admission")

            admission, discharge = min(
                choices,
                key=lambda pair: (
                    abs((pair[1] - pair[0]).days - stay_days),
                    pair[0],
                    pair[1],
                ),
            )
            encounters.append((admission, discharge))
        except (KeyError, TypeError, ValueError, OverflowError):
            dropped += 1

    if not encounters:
        raise ValueError("No valid admission/discharge rows were found")

    first_day = min(admission for admission, _ in encounters)
    last_day = max(discharge for _, discharge in encounters)
    day_count = (last_day - first_day).days + 1
    occupancy_delta = [0] * (day_count + 1)
    admissions_by_day: Counter[int] = Counter()
    discharges_by_day: Counter[int] = Counter()
    for admission, discharge in encounters:
        admission_index = (admission - first_day).days
        discharge_index = (discharge - first_day).days
        admissions_by_day[admission_index] += 1
        discharges_by_day[discharge_index] += 1
        # Date-only records do not contain admission/discharge times. Count a
        # stay on both its admission and discharge dates as a daily census proxy.
        occupancy_delta[admission_index] += 1
        occupancy_delta[discharge_index + 1] -= 1

    daily_rows: list[dict[str, int | str]] = []
    occupied = 0
    for index in range(day_count):
        occupied += occupancy_delta[index]
        daily_rows.append(
            {
                "date": (first_day + dt.timedelta(days=index)).isoformat(),
                "admissions": admissions_by_day[index],
                "discharges": discharges_by_day[index],
                "occupied_beds": occupied,
            }
        )
    return daily_rows, dropped


def download_archive() -> bytes:
    request = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "SmartHospitalManagementSystem/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an already downloaded Kaggle ZIP")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    archive_data = args.archive.read_bytes() if args.archive else download_archive()
    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
        with archive.open(ADMISSION_FILE) as file:
            rows = list(csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig")))
    daily_rows, dropped = aggregate_rows(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["date", "admissions", "discharges", "occupied_beds"])
        writer.writeheader()
        writer.writerows(daily_rows)

    print(
        f"Wrote {len(daily_rows)} daily aggregates from {len(rows)} Kaggle source rows; "
        f"excluded {dropped} rows with inconsistent or unparseable date fields."
    )
    print(f"Output: {os.path.relpath(args.output, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
