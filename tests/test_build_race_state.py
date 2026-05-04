import duckdb
import pytest
from pathlib import Path
from ingest.build.build_race_state import check_prerequisites, build_race_state_driver_lap


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


@pytest.fixture
def seeded_db(db_path):
    conn = duckdb.connect(str(db_path))
    session_id = "2024_21_R"
    conn.execute("INSERT OR REPLACE INTO dim_driver (driver_id, driver_ref, code, driver_number, first_name, last_name, full_name, nationality, source_system) VALUES ('max_verstappen', 'max_verstappen', 'VER', 33, 'Max', 'Verstappen', 'Max Verstappen', 'Dutch', 'jolpica')")
    conn.execute("INSERT OR REPLACE INTO dim_driver (driver_id, driver_ref, code, driver_number, first_name, last_name, full_name, nationality, source_system) VALUES ('lewis_hamilton', 'lewis_hamilton', 'HAM', 44, 'Lewis', 'Hamilton', 'Lewis Hamilton', 'British', 'jolpica')")
    for lap in range(1, 4):
        for dr in [('max_verstappen', 1), ('lewis_hamilton', 2)]:
            conn.execute("""INSERT OR REPLACE INTO fact_lap (session_id, driver_ref, lap_number, lap_time_ms, tyre_compound_id, stint_number) VALUES (?, ?, ?, ?, 1, 1)""", [session_id, dr[0], lap, 75000 + lap * 10])
    conn.execute("INSERT OR REPLACE INTO fact_stint (session_id, driver_ref, stint_number, tyre_compound_id, lap_start, lap_end, tyre_age_at_start) VALUES ('2024_21_R', 'max_verstappen', 1, 1, 1, 3, 0)")
    conn.execute("INSERT OR REPLACE INTO fact_stint (session_id, driver_ref, stint_number, tyre_compound_id, lap_start, lap_end, tyre_age_at_start) VALUES ('2024_21_R', 'lewis_hamilton', 1, 2, 1, 3, 0)")
    conn.execute("INSERT OR REPLACE INTO fact_pit_stop (session_id, driver_ref, lap_number, pit_duration_seconds, pit_time) VALUES ('2024_21_R', 'max_verstappen', 3, 22.5, '2024-11-03T17:30:00Z')")
    conn.execute("INSERT OR REPLACE INTO dim_session (session_id, meeting_id, session_name, session_type, total_laps, source_system) VALUES ('2024_21_R', '2024_21', 'Brazil GP Race', 'R', 69, 'jolpica')")
    conn.close()
    return db_path


def test_check_prerequisites_passes_with_hard_data(seeded_db):
    warnings = check_prerequisites("2024_21_R", seeded_db)
    assert isinstance(warnings, list)
    assert len(warnings) >= 1  # Soft prereqs missing


def test_check_prerequisites_raises_without_laps(db_path):
    conn = duckdb.connect(str(db_path))
    conn.execute("INSERT OR REPLACE INTO dim_session (session_id, meeting_id, session_name, session_type, total_laps, source_system) VALUES ('2024_21_R', '2024_21', 'test', 'R', 69, 'jolpica')")
    conn.close()
    with pytest.raises(ValueError, match="fact_lap"):
        check_prerequisites("2024_21_R", db_path)


def test_build_race_state_driver_lap_produces_rows(seeded_db):
    count = build_race_state_driver_lap("2024_21_R", seeded_db)
    assert count > 0
    conn = duckdb.connect(str(seeded_db))
    df = conn.execute("SELECT * FROM race_state_driver_lap_fact").fetchdf()
    conn.close()
    assert "stint_age_laps" in df.columns
    assert "laps_remaining" in df.columns
    assert "is_pit_lap" in df.columns


def test_build_race_state_field_lap_produces_rows(seeded_db):
    from ingest.build.build_race_state import build_race_state_field_lap
    build_race_state_driver_lap("2024_21_R", seeded_db)
    count = build_race_state_field_lap("2024_21_R", seeded_db)
    assert count > 0
    conn = duckdb.connect(str(seeded_db))
    df = conn.execute("SELECT * FROM race_state_field_lap").fetchdf()
    conn.close()
    assert "total_running_drivers" in df.columns
