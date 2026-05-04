import pytest
from pathlib import Path
import yaml
import duckdb
import tempfile


VALID_DP = {
    "id": "test_race_lap10",
    "session_id": "R",
    "driver_id": "VER",
    "lap_number": 10,
    "decision_type": "pit_now_vs_stay_out",
    "scenario_title": "Test scenario",
    "scenario_description": "A test scenario for validation.",
    "available_actions": ["pit_now_inter", "stay_out"],
    "actual_decision": "stay_out",
    "actual_outcome_summary": "Stayed out and won.",
    "explanation_short": "Good call.",
    "explanation_long": "Long explanation here.",
    "race_state": {
        "current_position": 1,
        "gap_ahead_seconds": None,
        "gap_behind_seconds": 2.5,
        "compound": "medium",
        "stint_age_laps": 12,
        "laps_remaining": 50,
        "track_temperature_c": 35.0,
        "air_temperature_c": 28.0,
        "rainfall": False,
        "track_status": "green",
        "safety_car_active": False,
        "virtual_safety_car_active": False,
    },
}


def test_validator_accepts_valid_decision_point():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    errors = validator.validate(VALID_DP)
    assert errors == []


def test_validator_rejects_invalid_decision_type():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    bad = dict(VALID_DP)
    bad["decision_type"] = "invalid_type"
    errors = validator.validate(bad)
    assert any("Invalid decision_type" in e for e in errors)


def test_validator_rejects_missing_race_state_field():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    bad = dict(VALID_DP)
    bad["race_state"] = {k: v for k, v in bad["race_state"].items() if k != "compound"}
    errors = validator.validate(bad)
    assert any("Missing race_state field: compound" in e for e in errors)


def test_validator_rejects_actual_decision_not_in_actions():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    bad = dict(VALID_DP)
    bad["actual_decision"] = "not_an_action"
    errors = validator.validate(bad)
    assert any("actual_decision must be one of available_actions" in e for e in errors)


def test_validator_rejects_more_than_four_actions():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    bad = dict(VALID_DP)
    bad["available_actions"] = ["a", "b", "c", "d", "e"]
    errors = validator.validate(bad)
    assert any("must not exceed 4" in e for e in errors)


def test_validator_rejects_empty_actions():
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    bad = dict(VALID_DP)
    bad["available_actions"] = []
    errors = validator.validate(bad)
    assert any("non-empty list" in e for e in errors)


def test_load_all_yaml_files_validate():
    """Integration: all YAML files in data/decision_points/ pass validation."""
    from ingest.validate.decision_points import DecisionPointValidator
    validator = DecisionPointValidator()
    dp_dir = Path("data/decision_points")
    yaml_files = sorted(dp_dir.glob("*.yaml"))
    assert len(yaml_files) >= 1

    for yf in yaml_files:
        with open(yf) as fh:
            dps = yaml.safe_load(fh)
        for dp in dps:
            errors = validator.validate(dp)
            assert errors == [], f"Validation errors in {dp.get('id', 'unknown')} in {yf.name}: {errors}"


def test_load_all_decision_points_into_db():
    """Integration: load all YAML files into DuckDB and verify count."""
    from ingest.load_decision_points import load_decision_points
    from ingest.validate.decision_points import DecisionPointValidator

    validator = DecisionPointValidator()
    dp_dir = Path("data/decision_points")
    yaml_files = sorted(dp_dir.glob("*.yaml"))

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test_dp.db"
        conn = duckdb.connect(str(db))
        schema_sql = Path("tests/fixtures/duckdb/test_schema.sql").read_text()
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass
        conn.close()

        total_loaded = 0
        for yf in yaml_files:
            with open(yf) as fh:
                dps = yaml.safe_load(fh)
            for dp in dps:
                errors = validator.validate(dp)
                assert errors == [], f"Errors in {dp.get('id', 'unknown')}: {errors}"
            load_decision_points(str(yf), str(db))
            total_loaded += len(dps)

        conn = duckdb.connect(str(db))
        count = conn.execute("SELECT COUNT(*) FROM race_state_decision_point").fetchone()[0]
        conn.close()
        assert count == total_loaded, f"Expected {total_loaded} decision points, got {count}"
