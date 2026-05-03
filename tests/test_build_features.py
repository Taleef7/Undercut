import duckdb
import pytest
from pathlib import Path
from ingest.build.build_features import check_prerequisites


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


def test_check_prerequisites_raises_when_empty(db_path):
    with pytest.raises(ValueError, match="race_state_driver_lap_fact"):
        check_prerequisites("2024_21_R", db_path)


def test_check_prerequisites_passes_with_data(db_path):
    conn = duckdb.connect(str(db_path))
    conn.execute("INSERT INTO race_state_driver_lap_fact (session_id, driver_ref, lap_number) VALUES ('2024_21_R', 'max_verstappen', 1)")
    conn.close()
    check_prerequisites("2024_21_R", db_path)
