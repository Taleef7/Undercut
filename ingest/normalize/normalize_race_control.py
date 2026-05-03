import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_race_control(db_path: Path, data_dir: Path, meeting_key: int, session_key: int) -> int:
    data = load_raw_json(data_dir, "openf1", str(meeting_key), str(session_key), "race_control.json")
    if not data:
        return 0

    session_id = "2024_21_R"

    rows = []
    for i, rc in enumerate(data):
        rows.append({
            "session_id": session_id,
            "event_time": rc.get("date", ""),
            "category": rc.get("category", ""),
            "flag": rc.get("flag", ""),
            "scope": rc.get("scope", ""),
            "message": rc.get("message", ""),
            "lap_number": int(rc.get("lap_number", 0)),
            "source_system": "openf1",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "openf1",
                f"{session_id}_{i}",
                str(rc.get("date", ""))
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT INTO fact_race_control_event
            (session_id, event_time, category, flag, scope, message, lap_number,
             source_system, data_version, record_hash)
        SELECT session_id, event_time, category, flag, scope, message, lap_number,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
