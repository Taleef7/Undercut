import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_drivers(db_path: Path, data_dir: Path) -> int:
    data = load_raw_json(data_dir, "jolpica", "2024", "season", "drivers.json")
    if not data:
        data = load_raw_json(data_dir, "jolpica", "all_time", "drivers.json")
    if not data:
        return 0

    drivers = data.get("MRData", {}).get("DriverTable", {}).get("Drivers", [])
    if not drivers:
        return 0

    rows = []
    for d in drivers:
        rows.append({
            "driver_ref": d["driverId"],
            "driver_code": d.get("code", ""),
            "driver_number": d.get("permanentNumber", ""),
            "driver_forename": d.get("givenName", ""),
            "driver_surname": d.get("familyName", ""),
            "source_system": "jolpica",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "jolpica", d["driverId"], d.get("code", "")
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO dim_driver
            (driver_ref, driver_code, driver_number, driver_forename, driver_surname,
             source_system, data_version, record_hash)
        SELECT driver_ref, driver_code, driver_number, driver_forename, driver_surname,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
