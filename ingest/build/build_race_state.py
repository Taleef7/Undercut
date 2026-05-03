import duckdb
import pandas as pd
from pathlib import Path


def check_prerequisites(session_id: str, db_path: Path) -> list[str]:
    conn = duckdb.connect(str(db_path))
    warnings = []
    hard = ["fact_lap", "fact_stint", "fact_pit_stop"]
    soft = ["fact_interval_sample", "fact_position_sample", "fact_weather_sample", "fact_race_control_event"]
    for table in hard:
        count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE session_id = ?", [session_id]).fetchone()[0]
        if count == 0:
            conn.close()
            raise ValueError(f"No {table} rows for session {session_id}. Run 'normalize' first.")
    for table in soft:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE session_id = ?", [session_id]).fetchone()[0]
            if count == 0:
                warnings.append(f"WARNING: No {table} rows for session {session_id}. Derived columns depending on this table will be NULL.")
        except Exception:
            warnings.append(f"WARNING: Table {table} does not exist. Derived columns depending on this table will be NULL.")
    conn.close()
    return warnings


def build_race_state_driver_lap(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    total_laps_row = conn.execute("SELECT total_laps FROM dim_session WHERE session_id = ?", [session_id]).fetchone()
    total_laps = total_laps_row[0] if total_laps_row else 70
    query = f"""
    INSERT INTO race_state_driver_lap_fact
    SELECT
        fl.session_id, fl.driver_ref, fl.lap_number, fl.lap_time_ms, fl.lap_time_seconds,
        fl.tyre_compound_id, fl.compound_label_source, fl.stint_number,
        fl.lap_number - COALESCE(fs.lap_start, 0) AS stint_age_laps,
        {total_laps} - fl.lap_number AS laps_remaining,
        CASE WHEN fp.lap_number IS NOT NULL OR fp2.lap_number IS NOT NULL THEN TRUE ELSE FALSE END AS is_pit_lap,
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NULL::BOOLEAN, NULL::BOOLEAN, NULL::VARCHAR, NULL::INTEGER, NULL::FLOAT, NULL::FLOAT,
        NULL::VARCHAR, NULL::VARCHAR, NULL::BOOLEAN, NULL::BOOLEAN,
        NOW(), 'v0.1'
    FROM fact_lap fl
    LEFT JOIN fact_stint fs ON fl.session_id = fs.session_id AND fl.driver_ref = fs.driver_ref AND fl.stint_number = fs.stint_number
    LEFT JOIN fact_pit_stop fp ON fl.session_id = fp.session_id AND fl.driver_ref = fp.driver_ref AND fl.lap_number = fp.lap_number
    LEFT JOIN fact_pit_stop fp2 ON fl.session_id = fp2.session_id AND fl.driver_ref = fp2.driver_ref AND fl.lap_number = fp2.lap_number - 1
    WHERE fl.session_id = ?
    """
    result = conn.execute(query, [session_id])
    count = result.fetchall()[0][0] if result else 0
    conn.close()
    return count


def build_race_state_field_lap(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    query = """
    INSERT INTO race_state_field_lap
    SELECT DISTINCT
        rs.session_id, rs.lap_number, NULL::VARCHAR, COUNT(DISTINCT rs.driver_ref),
        NULL::FLOAT, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT, NULL::FLOAT,
        NOW(), 'v0.1'
    FROM race_state_driver_lap_fact rs
    WHERE rs.session_id = ?
    GROUP BY rs.session_id, rs.lap_number
    """
    result = conn.execute(query, [session_id])
    count = result.fetchall()[0][0] if result else 0
    conn.close()
    return count
