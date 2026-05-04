import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_stints(db_path: Path, data_dir: Path, meeting_key: int, session_key: int) -> int:
    data = load_raw_json(data_dir, "openf1", str(meeting_key), str(session_key), "stints.json")
    if not data:
        return 0

    conn = duckdb.connect(str(db_path))

    driver_map_df = conn.execute(
        "SELECT driver_number, driver_ref FROM dim_driver"
    ).fetchdf()
    driver_map = dict(zip(driver_map_df["driver_number"], driver_map_df["driver_ref"]))

    compound_map_df = conn.execute(
        "SELECT compound_label, tyre_compound_id FROM dim_tyre_compound"
    ).fetchdf()
    compound_map = dict(zip(
        compound_map_df["compound_label"].str.upper(),
        compound_map_df["tyre_compound_id"]
    ))

    session_id = "2024_21_R"

    rows = []
    for stint in data:
        driver_num = str(stint.get("driver_number", ""))
        driver_ref = driver_map.get(str(driver_num))
        if not driver_ref:
            driver_ref = driver_num

        compound_raw = stint.get("compound", "")
        tyre_compound_id = compound_map.get(compound_raw.upper() if compound_raw else "", 99)
        stint_number = int(stint.get("stint_number", 0))

        rows.append({
            "session_id": session_id,
            "driver_ref": driver_ref,
            "stint_number": stint_number,
            "tyre_compound_id": tyre_compound_id,
            "compound_label_source": compound_raw,
            "lap_start": int(stint.get("lap_start") or 0),
            "lap_end": int(stint.get("lap_end") or 0),
            "tyre_age_at_start": int(stint.get("tyre_age_at_start") or 0),
            "source_system": "openf1",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "openf1",
                f"{session_id}_{driver_ref}_{stint_number}",
                str(tyre_compound_id)
            ),
        })

    df = pd.DataFrame(rows)
    conn.execute("""
        INSERT OR REPLACE INTO fact_stint
            (session_id, driver_ref, stint_number, tyre_compound_id,
             compound_label_source, lap_start, lap_end, tyre_age_at_start,
             source_system, data_version, record_hash)
        SELECT session_id, driver_ref, stint_number, tyre_compound_id,
               compound_label_source, lap_start, lap_end, tyre_age_at_start,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
