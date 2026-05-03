import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_circuits(db_path: Path, data_dir: Path) -> int:
    data = load_raw_json(data_dir, "jolpica", "all_time", "circuits.json")
    if not data:
        return 0

    circuits = data.get("MRData", {}).get("CircuitTable", {}).get("Circuits", [])
    if not circuits:
        return 0

    rows = []
    for c in circuits:
        loc = c.get("Location", {})
        rows.append({
            "circuit_ref": c["circuitId"],
            "circuit_name": c["circuitName"],
            "location": loc.get("locality", ""),
            "country": loc.get("country", ""),
            "lat": float(loc.get("lat", 0)),
            "lng": float(loc.get("long", 0)),
            "source_system": "jolpica",
            "data_version": "v0.1",
            "record_hash": compute_record_hash(
                "jolpica", c["circuitId"], c.get("circuitName", "")
            ),
        })

    df = pd.DataFrame(rows)
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO dim_circuit
            (circuit_ref, circuit_name, location, country, lat, lng,
             source_system, data_version, record_hash)
        SELECT circuit_ref, circuit_name, location, country, lat, lng,
               source_system, data_version, record_hash
        FROM df
    """)
    conn.close()
    return len(rows)
