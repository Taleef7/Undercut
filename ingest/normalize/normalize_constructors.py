import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_constructors(db_path: Path, data_dir: Path) -> int:
    data = load_raw_json(data_dir, "jolpica", "2024", "season", "constructors.json")
    if not data:
        data = load_raw_json(data_dir, "jolpica", "all_time", "constructors.json")
    if not data:
        return 0

    constructors = data.get("MRData", {}).get("ConstructorTable", {}).get("Constructors", [])
    if not constructors:
        return 0

    rows = []
    for c in constructors:
        rows.append({
            "constructor_ref": c["constructorId"],
            "constructor_name": c.get("name", ""),
            "constructor_nationality": c.get("nationality", ""),
            "source_system": "jolpica",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "jolpica", c["constructorId"], c.get("name", "")
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO dim_constructor
            (constructor_ref, constructor_name, constructor_nationality,
             source_system, data_version, record_hash)
        SELECT constructor_ref, constructor_name, constructor_nationality,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
