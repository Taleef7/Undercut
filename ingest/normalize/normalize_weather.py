import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_weather(db_path: Path, data_dir: Path, meeting_key: int, session_key: int) -> int:
    data = load_raw_json(data_dir, "openf1", str(meeting_key), str(session_key), "weather.json")
    if not data:
        return 0

    session_id = "2024_21_R"

    rows = []
    for i, w in enumerate(data):
        rows.append({
            "session_id": session_id,
            "sample_time": w.get("date", ""),
            "air_temperature_c": float(w.get("air_temperature", 0)),
            "track_temperature_c": float(w.get("track_temperature", 0)),
            "humidity_pct": int(w.get("humidity", 0)),
            "rainfall_flag": bool(w.get("rainfall", False)),
            "source_system": "openf1",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "openf1",
                f"{session_id}_{i}",
                str(w.get("date", ""))
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT INTO fact_weather_sample
            (session_id, sample_time, air_temperature_c, track_temperature_c,
             humidity_pct, rainfall_flag, source_system, data_version, record_hash)
        SELECT session_id, sample_time, air_temperature_c, track_temperature_c,
               humidity_pct, rainfall_flag, source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
