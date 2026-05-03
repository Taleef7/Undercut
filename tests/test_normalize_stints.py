import duckdb
import pytest
from pathlib import Path
from ingest.normalize.normalize_stints import normalize_stints


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
        INSERT OR REPLACE INTO dim_tyre_compound VALUES
        (1, 'SOFT', 'slick', 'S', 5, false, false, false),
        (2, 'MEDIUM', 'slick', 'M', 3, false, false, false),
        (3, 'HARD', 'slick', 'H', 1, false, false, false),
        (4, 'INTERMEDIATE', 'inter', 'I', NULL, false, true, false),
        (5, 'WET', 'wet', 'W', NULL, true, false, false),
        (99, 'UNKNOWN', 'slick', 'UNC', NULL, false, false, true)
    """)
    conn.execute("""
        INSERT OR REPLACE INTO dim_driver VALUES
        ('max_verstappen', 'VER', '33', 'Max', 'Verstappen', 'jolpica', NOW(), 'v0.1', 'abc123'),
        ('lewis_hamilton', 'HAM', '44', 'Lewis', 'Hamilton', 'jolpica', NOW(), 'v0.1', 'def456')
    """)
    conn.close()
    return db


def test_normalize_stints_loads_fixture(db_path):
    n = normalize_stints(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    assert n == 3
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT * FROM fact_stint").fetchdf()
    conn.close()
    assert len(df) == 3


def test_normalize_stints_returns_zero_for_missing_data(db_path):
    n = normalize_stints(db_path, data_dir=Path("/nonexistent"), meeting_key=47, session_key=9540)
    assert n == 0


def test_normalize_stints_has_record_hashes(db_path):
    n = normalize_stints(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT record_hash FROM fact_stint").fetchdf()
    conn.close()
    assert df["record_hash"].notna().all()
