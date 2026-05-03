import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_laps(db_path: Path, data_dir: Path, meeting_key: int, session_key: int) -> int:
    data = load_raw_json(data_dir, "openf1", str(meeting_key), str(session_key), "laps.json")
    if not data:
        return 0

    conn = duckdb.connect(str(db_path))

    driver_map_df = conn.execute(
        "SELECT driver_number, driver_ref FROM dim_driver"
    ).fetchdf()
    driver_map = dict(zip(driver_map_df["driver_number"], driver_map_df["driver_ref"]))

    compound_map_df = conn.execute(
        "SELECT compound_name, tyre_compound_id FROM dim_tyre_compound"
    ).fetchdf()
    compound_map = dict(zip(
        compound_map_df["compound_name"].str.upper(),
        compound_map_df["tyre_compound_id"]
    ))

    session_id = "2024_21_R"

    rows = []
    for lap in data:
        driver_num = str(lap.get("driver_number", ""))
        driver_ref = driver_map.get(str(driver_num))
        if not driver_ref:
            driver_ref = driver_num

        compound_raw = lap.get("compound", "")
        tyre_compound_id = compound_map.get(compound_raw.upper() if compound_raw else "", 99)

        lap_duration = lap.get("lap_duration")
        lap_time_ms = round(lap_duration * 1000, 3) if lap_duration is not None else None

        rows.append({
            "session_id": session_id,
            "driver_ref": driver_ref,
            "lap_number": int(lap.get("lap_number", 0)),
            "lap_time_ms": lap_time_ms,
            "lap_time_seconds": lap_duration,
            "tyre_compound_id": tyre_compound_id,
            "compound_label_source": compound_raw,
            "stint_number": int(lap.get("stint", 0)),
            "is_pit_out_lap": bool(lap.get("is_pit_out_lap", False)),
            "lap_start_time": lap.get("date_start", ""),
            "source_system": "openf1",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "openf1",
                f"{session_id}_{driver_ref}_{lap.get('lap_number', 0)}",
                str(lap_time_ms or "")
            ),
        })

    df = pd.DataFrame(rows)
    conn.execute("""
        INSERT OR REPLACE INTO fact_lap
            (session_id, driver_ref, lap_number, lap_time_ms, lap_time_seconds,
             tyre_compound_id, compound_label_source, stint_number, is_pit_out_lap,
             lap_start_time, source_system, data_version, record_hash)
        SELECT session_id, driver_ref, lap_number, lap_time_ms, lap_time_seconds,
               tyre_compound_id, compound_label_source, stint_number, is_pit_out_lap,
               lap_start_time, source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
