import duckdb
import pytest
from pathlib import Path
from ingest.normalize.normalize_results import normalize_results


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
    conn.close()
    return db


def test_normalize_results_loads_fixture(db_path):
    n = normalize_results(db_path, data_dir=Path("tests/fixtures"))
    assert n == 2
    conn = duckdb.connect(str(db_path))
    rows = conn.execute("SELECT * FROM fact_session_result").fetchdf()
    conn.close()
    assert len(rows) == 2
    assert rows.iloc[0]["position_order"] == 1


def test_normalize_results_returns_zero_for_missing_data(db_path):
    n = normalize_results(db_path, data_dir=Path("/nonexistent"))
    assert n == 0


def test_normalize_results_has_record_hashes(db_path):
    n = normalize_results(db_path, data_dir=Path("tests/fixtures"))
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT record_hash FROM fact_session_result").fetchdf()
    conn.close()
    assert df["record_hash"].notna().all()
    assert all(len(h) == 64 for h in df["record_hash"])
