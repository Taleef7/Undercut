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
        (race_state_driver_lap_id, session_id, driver_id, lap_number, lap_time_ms,
         current_compound_id, current_compound_label, stint_number, stint_age_laps,
         laps_remaining, is_pit_lap,
         race_lap_pct, current_position, starting_position, positions_gained_lost,
         gap_to_leader_seconds, interval_ahead_seconds, interval_behind_seconds,
         driver_ahead_id, driver_behind_id,
         total_pit_stops, last_pit_lap,
         rolling_3_lap_avg_ms, rolling_5_lap_avg_ms, pace_delta_to_field_ms,
         track_status_normalized, safety_car_active_flag, virtual_safety_car_active_flag,
         red_flag_active_flag, rainfall_flag,
         air_temperature, track_temperature,
         pit_window_open_flag, undercut_threat_flag, overcut_opportunity_flag,
         source_coverage_quality, created_at)
    SELECT
        fl.session_id || '_' || fl.driver_ref || '_' || fl.lap_number,
        fl.session_id, fl.driver_ref, fl.lap_number, fl.lap_time_ms,
        fl.tyre_compound_id, fl.compound_label_source, fl.stint_number,
        fl.lap_number - COALESCE(fs.lap_start, 0),
        {total_laps} - fl.lap_number,
        CASE WHEN fp.lap_number IS NOT NULL OR fp2.lap_number IS NOT NULL THEN TRUE ELSE FALSE END,
        NULL, NULL, NULL, NULL,
        NULL, NULL, NULL,
        NULL, NULL,
        NULL, NULL,
        NULL, NULL, NULL,
        NULL, NULL, NULL,
        NULL, NULL,
        NULL, NULL,
        NULL, NULL, NULL,
        'partial', NOW()
    FROM fact_lap fl
    LEFT JOIN fact_stint fs ON fl.session_id = fs.session_id AND fl.driver_ref = fs.driver_ref AND fl.stint_number = fs.stint_number
    LEFT JOIN fact_pit_stop fp ON fl.session_id = fp.session_id AND fl.driver_ref = fp.driver_ref AND fl.lap_number = fp.lap_number
    LEFT JOIN fact_pit_stop fp2 ON fl.session_id = fp2.session_id AND fl.driver_ref = fp2.driver_ref AND fl.lap_number = fp2.lap_number - 1
    WHERE fl.session_id = ?
    """
    conn.execute(query, [session_id])
    count = conn.execute("SELECT COUNT(*) FROM race_state_driver_lap_fact WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()
    return count


def build_race_state_field_lap(session_id: str, db_path: Path) -> int:
    conn = duckdb.connect(str(db_path))
    query = """
    INSERT INTO race_state_field_lap
        (race_state_field_lap_id, session_id, lap_number, leader_driver_id,
         total_running_drivers, total_retired_drivers,
         safety_car_active_flag, virtual_safety_car_active_flag, red_flag_active_flag,
         rainfall_flag, average_lap_time_ms, median_lap_time_ms, fastest_lap_time_ms,
         number_on_soft, number_on_medium, number_on_hard, number_on_intermediate, number_on_wet,
         field_spread_seconds, created_at)
    SELECT DISTINCT
        rs.session_id || '_' || rs.lap_number,
        rs.session_id, rs.lap_number, NULL,
        COUNT(DISTINCT rs.driver_id), NULL,
        NULL, NULL, NULL,
        NULL, NULL, NULL, NULL,
        NULL, NULL, NULL, NULL, NULL,
        NULL, NOW()
    FROM race_state_driver_lap_fact rs
    WHERE rs.session_id = ?
    GROUP BY rs.session_id, rs.lap_number
    """
    conn.execute(query, [session_id])
    count = conn.execute("SELECT COUNT(*) FROM race_state_field_lap WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()
    return count
