import duckdb
import pytest
from pathlib import Path
from ingest.normalize.normalize_weather import normalize_weather


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


def test_normalize_weather_loads_fixture(db_path):
    n = normalize_weather(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    assert n == 2
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT * FROM fact_weather_sample").fetchdf()
    conn.close()
    assert len(df) == 2


def test_normalize_weather_returns_zero_for_missing_data(db_path):
    n = normalize_weather(db_path, data_dir=Path("/nonexistent"), meeting_key=47, session_key=9540)
    assert n == 0


def test_normalize_weather_has_record_hashes(db_path):
    n = normalize_weather(db_path, data_dir=Path("tests/fixtures"), meeting_key=47, session_key=9540)
    conn = duckdb.connect(str(db_path))
    df = conn.execute("SELECT record_hash FROM fact_weather_sample").fetchdf()
    conn.close()
    assert df["record_hash"].notna().all()
