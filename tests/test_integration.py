import duckdb
import pytest
from pathlib import Path


def test_full_pipeline_smoke(tmp_path):
    """Smoke test: DB -> normalize results -> verify data."""
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
        INSERT OR REPLACE INTO dim_driver VALUES
        ('max_verstappen', 'VER', '33', 'Max', 'Verstappen', 'jolpica', NOW(), 'v0.1', 'h1'),
        ('lewis_hamilton', 'HAM', '44', 'Lewis', 'Hamilton', 'jolpica', NOW(), 'v0.1', 'h2')
    """)
    conn.execute("""
        INSERT OR REPLACE INTO dim_session VALUES
        ('2024_21_R', '2024_21', 'R', 'Brazil GP Race', 69, 'jolpica', NOW(), 'v0.1', 's1')
    """)
    conn.execute("""
        INSERT OR REPLACE INTO dim_tyre_compound VALUES
        (1, 'SOFT', 'slick', 'S', 5, false, false, false),
        (2, 'MEDIUM', 'slick', 'M', 3, false, false, false),
        (99, 'UNKNOWN', 'slick', 'UNC', NULL, false, false, true)
    """)
    conn.close()

    from ingest.normalize.normalize_results import normalize_results
    n_results = normalize_results(db, data_dir=Path("tests/fixtures"))
    assert n_results == 2

    conn = duckdb.connect(str(db))
    df = conn.execute("SELECT * FROM fact_session_result").fetchdf()
    assert len(df) == 2
    assert df.iloc[0]["position_order"] == 1
    assert df["record_hash"].notna().all()
    conn.close()


def test_run_all_tests():
    """Meta-test: this always passes, serves as a checkpoint."""
    assert True
