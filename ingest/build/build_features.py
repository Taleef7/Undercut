import duckdb
from pathlib import Path


def check_prerequisites(session_id: str, db_path: Path) -> None:
    conn = duckdb.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM race_state_driver_lap_fact WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()
    if count == 0:
        raise ValueError(f"No race_state_driver_lap_fact rows for session {session_id}. Run 'build-race-state' first.")


def build_feature_pit_decision(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    query = """
    INSERT INTO feature_pit_decision
    SELECT
        rs.session_id, rs.driver_ref, rs.lap_number, rs.stint_age_laps, rs.laps_remaining,
        rs.current_position, rs.tyre_compound_id, rs.gap_ahead_seconds, rs.gap_behind_seconds,
        rs.safety_car_active_flag, rs.rainfall_flag,
        NULL::FLOAT, NULL::FLOAT,
        EXISTS (SELECT 1 FROM fact_pit_stop fp WHERE fp.session_id = rs.session_id AND fp.driver_ref = rs.driver_ref AND fp.lap_number BETWEEN rs.lap_number AND rs.lap_number + 3),
        NOW(), 'v0.1'
    FROM race_state_driver_lap_fact rs WHERE rs.session_id = ?
    """
    result = conn.execute(query, [session_id])
    count = result.fetchall()[0][0] if result else 0
    conn.close()
    return count


def build_feature_undercut_opportunity(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    query = """
    INSERT INTO feature_undercut_opportunity
    SELECT
        rs.session_id, rs.driver_ref, rs.lap_number, rs.driver_behind_id,
        rs.gap_behind_seconds, rs.stint_age_laps, NULL::INTEGER,
        rs.tyre_compound_id, NULL::INTEGER, NULL::FLOAT, NULL::FLOAT, FALSE,
        NOW(), 'v0.1'
    FROM race_state_driver_lap_fact rs WHERE rs.session_id = ?
    """
    result = conn.execute(query, [session_id])
    count = result.fetchall()[0][0] if result else 0
    conn.close()
    return count
