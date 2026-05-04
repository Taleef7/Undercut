import duckdb
import pytest
from pathlib import Path
from ingest.normalize.normalize_laps import normalize_laps


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test.db"
    conn = duckdb.connect(str(db))
    schema_sql = Path("tests/fixtures/duckdb/test_schema.sql").read_text()
    for stmt in schema_sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass
    conn.execute("""
        INSERT OR REPLACE INTO dim_tyre_compound (tyre_compound_id, compound_label, compound_category, compound_code, compound_hardness_order, is_wet, is_intermediate, is_slick) VALUES
        (1, 'SOFT', 'slick', 'S', 5, false, false, false),
        (2, 'MEDIUM', 'slick', 'M', 3, false, false, false),
        (3, 'HARD', 'slick', 'H', 1, false, false, false),
        (4, 'INTERMEDIATE', 'inter', 'I', NULL, false, true, false),
        (5, 'WET', 'wet', 'W', NULL, true, false, false),
        (99, 'UNKNOWN', 'slick', 'UNC', NULL, false, false, true)
    """)
    conn.execute("""
        INSERT OR REPLACE INTO dim_driver (driver_id, driver_ref, code, driver_number, first_name, last_name, full_name, nationality, source_system) VALUES
        ('max_verstappen', 'max_verstappen', 'VER', 33, 'Max', 'Verstappen', 'Max Verstappen', 'Dutch', 'jolpica'),
        ('lewis_hamilton', 'lewis_hamilton', 'HAM', 44, 'Lewis', 'Hamilton', 'Lewis Hamilton', 'British', 'jolpica')
    """)
    conn.close()
    return db


def test_normalize_laps_loads_fixture(db_path):
    n = normalize_laps(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    assert n == 5
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT * FROM fact_lap").fetchdf()
    conn.close()
    assert len(df) == 5
    assert "lap_time_ms" in df.columns


def test_normalize_laps_returns_zero_for_missing_data(db_path):
    n = normalize_laps(db_path, data_dir=Path("/nonexistent"), meeting_key=47, session_key=9540)
    assert n == 0


def test_normalize_laps_has_record_hashes(db_path):
    n = normalize_laps(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT record_hash FROM fact_lap").fetchdf()
    conn.close()
    assert df["record_hash"].notna().all()
