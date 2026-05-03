import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_pit_stops(db_path: Path, data_dir: Path, meeting_key: int, session_key: int) -> int:
    data = load_raw_json(data_dir, "openf1", str(meeting_key), str(session_key), "pit.json")
    if not data:
        return 0

    conn = duckdb.connect(str(db_path))

    driver_map_df = conn.execute(
        "SELECT driver_number, driver_ref FROM dim_driver"
    ).fetchdf()
    driver_map = dict(zip(driver_map_df["driver_number"], driver_map_df["driver_ref"]))

    session_id = "2024_21_R"

    rows = []
    for pit in data:
        driver_num = str(pit.get("driver_number", ""))
        driver_ref = driver_map.get(str(driver_num))
        if not driver_ref:
            driver_ref = driver_num

        lap_number = int(pit.get("lap_number", 0))

        rows.append({
            "session_id": session_id,
            "driver_ref": driver_ref,
            "lap_number": lap_number,
            "pit_duration_seconds": float(pit.get("pit_duration", 0)),
            "pit_time": pit.get("date", ""),
            "source_system": "openf1",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "openf1",
                f"{session_id}_{driver_ref}_{lap_number}",
                str(pit.get("pit_duration", ""))
            ),
        })

    df = pd.DataFrame(rows)
    conn.execute("""
        INSERT OR REPLACE INTO fact_pit_stop
            (session_id, driver_ref, lap_number, pit_duration_seconds, pit_time,
             source_system, data_version, record_hash)
        SELECT session_id, driver_ref, lap_number, pit_duration_seconds, pit_time,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
