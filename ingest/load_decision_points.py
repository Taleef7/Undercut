import yaml
import duckdb
import os
from pathlib import Path

def load_decision_points(yaml_path: str, db_path: str):
    """Loads decision points from YAML into DuckDB."""
    # Load YAML
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    
    decision_points = data.get('decision_points', [])
    if not decision_points:
        print("No decision points found in YAML.")
        return

    # Connect to DuckDB
    conn = duckdb.connect(db_path)
    
    # Ensure table exists (running schema.sql first is recommended)
    # For simplicity in this script, we just assume the table was created by schema.sql
    
    for dp in decision_points:
        # available_actions is a list, need to convert to JSON string for the DB
        import json
        actions_json = json.dumps(dp.get('available_actions', []))
        
        conn.execute(
            """
            INSERT INTO race_state_decision_point 
            (decision_point_id, session_id, driver_id, lap_number, decision_type, 
             scenario_title, scenario_description, available_actions_json, 
             actual_decision, actual_outcome_summary, explanation_short, explanation_long)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                dp.get('explanation_long')
            )
        )
    
    print(f"Successfully loaded {len(decision_points)} decision points from {yaml_path}.")
    conn.close()

if __name__ == "__main__":
    # Paths relative to project root
    ROOT = Path(__file__).parent.parent
    YAML_FILE = ROOT / "data" / "decision_points" / "brazil_2024.yaml"
    DB_FILE = ROOT / "data" / "undercut.db"
    
    load_decision_points(str(YAML_FILE), str(DB_FILE))
