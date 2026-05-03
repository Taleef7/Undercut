import duckdb
import pytest
from pathlib import Path
from ingest.normalize import compute_record_hash
from ingest.normalize.normalize_circuits import normalize_circuits
from ingest.normalize.normalize_drivers import normalize_drivers
from ingest.normalize.normalize_constructors import normalize_constructors


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test.db"
    conn = duckdb.connect(str(db))
    schema_sql = Path("tests/fixtures/duckdb/test_schema.sql").read_text()
    for stmt in schema_sql.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.close()
    return db


def test_compute_record_hash_deterministic():
    h1 = compute_record_hash("jolpica", "rec1", "alonso:2024:21")
    h2 = compute_record_hash("jolpica", "rec1", "alonso:2024:21")
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_compute_record_hash_different_input_produces_different_hash():
    h1 = compute_record_hash("jolpica", "rec1", "hamilton:2024:21")
    h2 = compute_record_hash("jolpica", "rec1", "alonso:2024:21")
    assert h1 != h2


def test_normalize_circuits_loads_jolpica_fixture(db_path):
    n = normalize_circuits(db_path, data_dir=Path("tests/fixtures"))
    assert n > 0

    conn = duckdb.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM dim_circuit").fetchone()[0]
    conn.close()
    assert count > 0


def test_normalize_drivers_loads_jolpica_fixture(db_path):
    n = normalize_drivers(db_path, data_dir=Path("tests/fixtures"))
    assert n > 0

    conn = duckdb.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM dim_driver").fetchone()[0]
    conn.close()
    assert count > 0


def test_normalize_constructors_loads_jolpica_fixture(db_path):
    n = normalize_constructors(db_path, data_dir=Path("tests/fixtures"))
    assert n > 0

    conn = duckdb.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM dim_constructor").fetchone()[0]
    conn.close()
    assert count > 0
