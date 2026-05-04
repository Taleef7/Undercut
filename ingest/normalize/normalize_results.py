import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_results(db_path: Path, data_dir: Path) -> int:
    data = load_raw_json(data_dir, "jolpica", "2024", "21", "results.json")
    if not data:
        return 0

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return 0

    race = races[0]
    season = int(race.get("season", 0))
    round_num = int(race.get("round", 0))
    session_id = f"{season}_{round_num}_R"

    rows = []
    for r in race.get("Results", []):
        driver = r.get("Driver", {})
        constructor = r.get("Constructor", {})
        time_info = r.get("Time", {})
        driver_ref = driver.get("driverId", "")
        pos_text = r.get("positionText", "")
        position_order = int(r["position"]) if r.get("position", "").isdigit() else -1

        rows.append({
            "session_id": session_id,
            "driver_ref": driver_ref,
            "constructor_ref": constructor.get("constructorId", ""),
            "classified_position": pos_text,
            "position_order": position_order,
            "grid_position": int(r.get("grid", 0)),
            "points": float(r.get("points", 0)),
            "laps_completed": int(r.get("laps", 0)),
            "status": r.get("status", ""),
            "time_millis": int(time_info.get("millis", 0)) if time_info.get("millis") else None,
            "time_gap": time_info.get("time", ""),
            "source_system": "jolpica",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "jolpica", f"{session_id}_{driver_ref}", str(position_order)
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO fact_session_result
            (session_result_id, session_id, driver_id, constructor_id, classified_position,
             position_order, grid_position, points, laps_completed, status,
             time_milliseconds, source_system, data_version, record_hash)
        SELECT session_id || '_' || driver_ref, session_id, driver_ref, constructor_ref, classified_position,
               position_order, grid_position, points, laps_completed, status,
               time_millis, source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
