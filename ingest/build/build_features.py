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
        (feature_id, session_id, driver_id, lap_number, laps_remaining,
         current_position, gap_ahead_seconds, gap_behind_seconds,
         stint_age_laps, compound_hardness_order,
         rolling_3_lap_avg_ms, pace_delta_to_field_ms,
         safety_car_active_flag, vsc_active_flag, rainfall_flag,
         track_temperature, pit_loss_estimate_seconds,
         actual_pitted_within_3_laps, feature_version, created_at)
    SELECT
        rs.session_id || '_' || rs.driver_id || '_' || rs.lap_number,
        rs.session_id, rs.driver_id, rs.lap_number, rs.laps_remaining,
        rs.current_position, rs.interval_ahead_seconds, rs.interval_behind_seconds,
        rs.stint_age_laps, NULL,
        rs.rolling_3_lap_avg_ms, rs.pace_delta_to_field_ms,
        rs.safety_car_active_flag, rs.virtual_safety_car_active_flag, rs.rainfall_flag,
        rs.track_temperature, NULL,
        EXISTS (SELECT 1 FROM fact_pit_stop fp WHERE fp.session_id = rs.session_id AND fp.driver_ref = rs.driver_id AND fp.lap_number BETWEEN rs.lap_number AND rs.lap_number + 3),
        'v0.1', NOW()
    FROM race_state_driver_lap_fact rs WHERE rs.session_id = ?
    """
    conn.execute(query, [session_id])
    count = conn.execute("SELECT COUNT(*) FROM feature_pit_decision WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()
    return count


def build_feature_undercut_opportunity(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    query = """
    INSERT INTO feature_undercut_opportunity
        (feature_id, session_id, driver_id, target_driver_id, lap_number,
         gap_to_target_seconds, target_stint_age_laps, own_stint_age_laps,
         own_compound, target_compound, pit_loss_estimate_seconds,
         circuit_overtaking_difficulty, undercut_succeeded,
         feature_version, created_at)
    SELECT
        rs.session_id || '_' || rs.driver_id || '_' || rs.lap_number,
        rs.session_id, rs.driver_id, rs.driver_behind_id, rs.lap_number,
        rs.interval_behind_seconds, NULL, rs.stint_age_laps,
        rs.current_compound_id, NULL, NULL,
        NULL, FALSE,
        'v0.1', NOW()
    FROM race_state_driver_lap_fact rs WHERE rs.session_id = ?
    """
    conn.execute(query, [session_id])
    count = conn.execute("SELECT COUNT(*) FROM feature_undercut_opportunity WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()
    return count
