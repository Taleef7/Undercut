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
            "nationality": c.get("nationality", ""),
            "source_system": "jolpica",
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO dim_constructor
            (constructor_id, constructor_ref, constructor_name, nationality,
             source_system)
        SELECT constructor_ref, constructor_ref, constructor_name, nationality,
               source_system
        FROM df
    """)
    conn.close()
    return len(rows)
