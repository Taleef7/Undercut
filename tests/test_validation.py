import json
import duckdb
import pandas as pd
import pytest
from pathlib import Path
from ingest.validate.checks import (
    validate_rows, check_not_null, check_unique, check_lap_range,
    check_record_hash_not_null,
)
from ingest.validate.reports import write_report


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "driver_ref": ["max_verstappen", "lewis_hamilton", None],
        "lap_number": [1, 1, 100],
        "record_hash": ["abc123", "def456", None],
    })


def test_check_not_null_flags_missing(sample_df):
    warnings = check_not_null(sample_df, ["driver_ref"])
    assert len(warnings) == 1
    assert "Row 2" in warnings[0]


def test_check_unique_flags_duplicates(sample_df):
    warnings = check_unique(sample_df, ["lap_number"])
    assert len(warnings) == 1
    assert "lap_number" in warnings[0]


def test_check_lap_range_flags_out_of_range(sample_df):
    warnings = check_lap_range(sample_df, total_laps=70)
    assert any("Row 2" in w for w in warnings)


def test_check_record_hash_not_null(sample_df):
    warnings = check_record_hash_not_null(sample_df)
    assert len(warnings) == 1


def test_validate_rows_returns_clean_and_warnings(sample_df):
    clean, warnings = validate_rows(sample_df, "fact_lap")
    assert len(clean) <= 3
    assert len(warnings) >= 1


def test_write_report_creates_file(tmp_path):
    report_path = write_report(
        warnings=["w1"], errors=[], season=2024,
        round_num=21, session_type="R", output_dir=tmp_path
    )
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["season"] == 2024
    assert data["round"] == 21
    assert "timestamp" in data


def test_write_report_follows_naming_convention(tmp_path):
    report_path = write_report(
        warnings=[], errors=[], season=2024,
        round_num=21, session_type="R", output_dir=tmp_path
    )
    name = report_path.name
    assert name.startswith("validation_report_2024_21_")
    assert name.endswith(".json")