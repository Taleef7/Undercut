import yaml
import duckdb
import json
import os
from pathlib import Path


def load_decision_points(yaml_path: str, db_path: str):
    """Loads decision points from a single YAML file into DuckDB."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and 'decision_points' in data:
        decision_points = data.get('decision_points', [])
    else:
        decision_points = data if isinstance(data, list) else []

    if not decision_points:
        print("No decision points found in YAML.")
        return 0

    conn = duckdb.connect(db_path)

    for dp in decision_points:
        actions_json = json.dumps(dp.get('available_actions', []))
        race_state = dp.get('race_state', {})

        conn.execute(
            """
            INSERT OR REPLACE INTO race_state_decision_point
            (decision_point_id, session_id, driver_id, lap_number, decision_type,
             scenario_title, scenario_description, available_actions_json,
             actual_decision, actual_outcome_summary, explanation_short, explanation_long,
             current_position, gap_ahead_seconds, gap_behind_seconds, compound,
             stint_age_laps, laps_remaining, track_temperature_c, air_temperature_c,
             rainfall, track_status, safety_car_active, virtual_safety_car_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dp.get('id'),
                dp.get('session_id'),
                dp.get('driver_id'),
                dp.get('lap_number'),
                dp.get('decision_type'),
                dp.get('scenario_title'),
                dp.get('scenario_description'),
                actions_json,
                dp.get('actual_decision'),
                dp.get('actual_outcome_summary'),
                dp.get('explanation_short'),
                dp.get('explanation_long'),
                race_state.get('current_position'),
                race_state.get('gap_ahead_seconds'),
                race_state.get('gap_behind_seconds'),
                race_state.get('compound'),
                race_state.get('stint_age_laps'),
                race_state.get('laps_remaining'),
                race_state.get('track_temperature_c'),
                race_state.get('air_temperature_c'),
                race_state.get('rainfall'),
                race_state.get('track_status'),
                race_state.get('safety_car_active'),
                race_state.get('virtual_safety_car_active'),
            )
        )

    print(f"Successfully loaded {len(decision_points)} decision points from {yaml_path}.")
    conn.close()
    return len(decision_points)


def load_all_decision_points(db_path: str):
    """Loads all decision point YAML files from data/decision_points/ into DuckDB."""
    dp_dir = Path(__file__).parent.parent / "data" / "decision_points"
    yaml_files = sorted(dp_dir.glob("*.yaml"))

    if not yaml_files:
        print(f"No YAML files found in {dp_dir}")
        return 0

    total = 0
    for yf in yaml_files:
        total += load_decision_points(str(yf), db_path)

    print(f"\nTotal decision points loaded: {total}")
    return total


if __name__ == "__main__":
    ROOT = Path(__file__).parent.parent
    DB_FILE = ROOT / "data" / "undercut.db"

    load_all_decision_points(str(DB_FILE))
