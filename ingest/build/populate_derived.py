"""
Populate all derived columns in race_state tables that were previously NULL.
Computes positions, gaps, rolling averages, track status flags, and weather
from base fact tables.

Usage:
    uv run python -m ingest.build.populate_derived --session 2024_21_R
"""

import argparse
import hashlib
from pathlib import Path
from datetime import datetime

import duckdb
import pandas as pd
import numpy as np

DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"
SOURCE_SYSTEM = "derived"
DATA_VERSION = "v0.1"


def connect():
    return duckdb.connect(str(DB_PATH))


def create_position_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_position_sample (
            position_sample_id VARCHAR PRIMARY KEY,
            session_id VARCHAR,
            driver_id VARCHAR,
            lap_number INT,
            position INT,
            source_system VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def compute_positions(conn, session_id: str) -> pd.DataFrame:
    print("  Computing positions from cumulative lap times...")
    
    drivers = conn.execute(
        "SELECT DISTINCT driver_ref FROM fact_lap WHERE session_id = ? ORDER BY driver_ref",
        [session_id]
    ).fetchdf()["driver_ref"].tolist()
    
    total_laps = int(conn.execute(
        "SELECT MAX(lap_number) FROM fact_lap WHERE session_id = ?", [session_id]
    ).fetchone()[0])
    
    lap_times = conn.execute("""
        SELECT driver_ref, lap_number, lap_time_ms
        FROM fact_lap
        WHERE session_id = ? AND lap_time_ms IS NOT NULL
        ORDER BY driver_ref, lap_number
    """, [session_id]).fetchdf()
    
    pit_stops = conn.execute("""
        SELECT driver_ref, lap_number, pit_duration_seconds
        FROM fact_pit_stop
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    
    cum_times = {d: 0.0 for d in drivers}
    positions = []
    
    for lap in range(1, total_laps + 1):
        for d in drivers:
            lt = lap_times[(lap_times["driver_ref"] == d) & (lap_times["lap_number"] == lap)]
            if not lt.empty and pd.notna(lt["lap_time_ms"].iloc[0]):
                cum_times[d] += lt["lap_time_ms"].iloc[0]
            ps = pit_stops[(pit_stops["driver_ref"] == d) & (pit_stops["lap_number"] == lap)]
            if not ps.empty:
                cum_times[d] += ps["pit_duration_seconds"].iloc[0] * 1000
        
        lap_drivers = [(d, cum_times[d]) for d in drivers
                       if not lap_times[(lap_times["driver_ref"] == d) & (lap_times["lap_number"] == lap)].empty]
        lap_drivers.sort(key=lambda x: x[1])
        
        for pos, (d, ct) in enumerate(lap_drivers, 1):
            rid = hashlib.sha256(
                f"{session_id}:{d}:{lap}".encode()
            ).hexdigest()[:16]
            positions.append({
                "position_sample_id": f"pos_{session_id}_{d}_{lap}",
                "session_id": session_id,
                "driver_id": str(d),
                "lap_number": lap,
                "position": pos,
                "source_system": SOURCE_SYSTEM,
            })
    
    result = pd.DataFrame(positions)
    print(f"    Computed {len(result)} position records for {len(drivers)} drivers across {total_laps} laps")
    return result


def populate_positions(conn, df: pd.DataFrame):
    print("  Inserting into fact_position_sample...")
    conn.execute("DELETE FROM fact_position_sample WHERE session_id = ?", [df["session_id"].iloc[0]])
    conn.execute("""
        INSERT INTO fact_position_sample
        SELECT position_sample_id, session_id, driver_id, lap_number, position,
               source_system, CURRENT_TIMESTAMP
        FROM df
    """)


def compute_intervals(conn, session_id: str, pos_df: pd.DataFrame) -> pd.DataFrame:
    print("  Computing gaps (gap_to_leader, interval_to_ahead)...")
    
    lap_times = conn.execute("""
        SELECT driver_ref, lap_number, lap_time_ms
        FROM fact_lap
        WHERE session_id = ? AND lap_time_ms IS NOT NULL
    """, [session_id]).fetchdf()
    
    pit_stops = conn.execute("""
        SELECT driver_ref, lap_number, pit_duration_seconds
        FROM fact_pit_stop
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    
    total_laps = int(pos_df["lap_number"].max())
    drivers = pos_df["driver_id"].unique()
    
    cum_times = {d: 0.0 for d in drivers}
    intervals = []
    
    for lap in range(1, total_laps + 1):
        for d in drivers:
            lt = lap_times[(lap_times["driver_ref"] == d) & (lap_times["lap_number"] == lap)]
            if not lt.empty and pd.notna(lt["lap_time_ms"].iloc[0]):
                cum_times[d] += lt["lap_time_ms"].iloc[0]
            ps = pit_stops[(pit_stops["driver_ref"] == d) & (pit_stops["lap_number"] == lap)]
            if not ps.empty:
                cum_times[d] += ps["pit_duration_seconds"].iloc[0] * 1000
        
        lap_pos = pos_df[pos_df["lap_number"] == lap].copy()
        if lap_pos.empty:
            continue
        
        lap_pos = lap_pos.merge(
            pd.DataFrame([(d, cum_times[d]) for d in drivers if d in lap_pos["driver_id"].values],
                         columns=["driver_id", "cum_time_ms"]),
            on="driver_id"
        )
        lap_pos = lap_pos.sort_values("position")
        
        leader_time = lap_pos["cum_time_ms"].min()
        
        for _, row in lap_pos.iterrows():
            gap_to_leader = (row["cum_time_ms"] - leader_time) / 1000.0
            
            pos = int(row["position"])
            if pos > 1:
                ahead_row = lap_pos[lap_pos["position"] == pos - 1]
                if not ahead_row.empty:
                    interval_ahead = (row["cum_time_ms"] - ahead_row["cum_time_ms"].iloc[0]) / 1000.0
                else:
                    interval_ahead = None
            else:
                interval_ahead = None
            
            intervals.append({
                "interval_sample_id": f"int_{session_id}_{row['driver_id']}_{lap}",
                "session_id": session_id,
                "driver_id": str(row["driver_id"]),
                "lap_number": lap,
                "gap_to_leader_seconds": round(gap_to_leader, 3),
                "interval_to_ahead_seconds": round(interval_ahead, 3) if interval_ahead is not None else None,
                "source_system": SOURCE_SYSTEM,
            })
    
    result = pd.DataFrame(intervals)
    print(f"    Computed {len(result)} interval records")
    return result


def populate_intervals(conn, df: pd.DataFrame):
    print("  Inserting into fact_interval_sample...")
    conn.execute("DELETE FROM fact_interval_sample WHERE session_id = ?", [df["session_id"].iloc[0]])
    conn.execute("""
        INSERT INTO fact_interval_sample
        SELECT interval_sample_id, session_id, driver_id, lap_number,
               gap_to_leader_seconds, interval_to_ahead_seconds,
               source_system, CURRENT_TIMESTAMP, ?, ?
        FROM df
    """, [DATA_VERSION, None])


def derive_track_status(conn, session_id: str) -> pd.DataFrame:
    print("  Deriving track status flags per lap...")
    
    events = conn.execute("""
        SELECT lap_number, flag, category, message
        FROM fact_race_control_event
        WHERE session_id = ? AND flag IN ('RED', 'YELLOW', 'SC', 'VSC')
        ORDER BY lap_number
    """, [session_id]).fetchdf()
    
    total_laps = int(conn.execute(
        "SELECT MAX(lap_number) FROM fact_lap WHERE session_id = ?", [session_id]
    ).fetchone()[0])
    
    result = pd.DataFrame({"lap_number": range(1, total_laps + 1)})
    result["safety_car_active_flag"] = False
    result["virtual_safety_car_active_flag"] = False
    result["red_flag_active_flag"] = False
    result["yellow_flag_active_flag"] = False
    result["track_status_normalized"] = "green"
    
    # Track active SC periods (SC deployed until SC ended)
    # For simplicity: flag persists for the lap and next lap for SC/VSC
    active_sc = False
    active_vsc = False
    sc_end_lap = 0
    vsc_end_lap = 0
    
    for _, ev in events.iterrows():
        lap = int(ev["lap_number"])
        flag = ev["flag"]
        
        if flag == "SC":
            active_sc = True
            sc_end_lap = lap + 2
        elif flag == "VSC":
            active_vsc = True
            vsc_end_lap = lap + 2
        elif flag == "RED":
            result.loc[result["lap_number"] == lap, "red_flag_active_flag"] = True
            result.loc[result["lap_number"] == lap, "track_status_normalized"] = "red_flag"
        elif flag == "YELLOW":
            result.loc[result["lap_number"] == lap, "yellow_flag_active_flag"] = True
    
    for lap in range(1, total_laps + 1):
        if lap <= sc_end_lap and active_sc:
            result.loc[result["lap_number"] == lap, "safety_car_active_flag"] = True
            result.loc[result["lap_number"] == lap, "track_status_normalized"] = "safety_car"
        if lap <= vsc_end_lap and active_vsc:
            result.loc[result["lap_number"] == lap, "virtual_safety_car_active_flag"] = True
    
    print(f"    Derived track status for {len(result)} laps")
    return result


def compute_rolling_averages(lap_times: pd.DataFrame, window: int) -> pd.Series:
    return lap_times.rolling(window, min_periods=2).mean()


def rebuild_race_state(conn, session_id: str):
    print("Rebuilding race_state_driver_lap_fact with all columns...")
    
    laps = conn.execute("""
        SELECT fl.session_id, fl.driver_ref AS driver_id, fl.lap_number, fl.lap_time_ms,
               fl.stint_number, fl.is_pit_out_lap
        FROM fact_lap fl
        WHERE fl.session_id = ?
        ORDER BY fl.driver_ref, fl.lap_number
    """, [session_id]).fetchdf()
    
    # Get session metadata
    session_meta = conn.execute("""
        SELECT meeting_id, season_id FROM dim_session WHERE session_id = ?
    """, [session_id]).fetchone()
    meeting_id = session_meta[0] if session_meta else None
    season_id = session_meta[1] if session_meta else None
    
    # Get constructor mapping: driver_number -> constructor_id from session result
    constructor_map = {}
    const_rows = conn.execute("""
        SELECT CAST(driver_number AS VARCHAR) as driver_id, constructor_id
        FROM fact_driver_session_entry WHERE session_id = ?
    """, [session_id]).fetchdf()
    if not const_rows.empty:
        for _, r in const_rows.iterrows():
            constructor_map[str(r["driver_id"])] = r["constructor_id"]
    
    total_laps = int(laps["lap_number"].max())
    laps["laps_remaining"] = total_laps - laps["lap_number"]
    
    stints = conn.execute("""
        SELECT driver_ref, stint_number, tyre_compound_id, compound_label_source,
               lap_start, lap_end
        FROM fact_stint
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    
    positions = conn.execute("""
        SELECT driver_id, lap_number, position
        FROM fact_position_sample
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    positions["driver_id"] = positions["driver_id"].astype(str)
    
    intervals = conn.execute("""
        SELECT driver_id, lap_number, gap_to_leader_seconds, interval_to_ahead_seconds
        FROM fact_interval_sample
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    intervals["driver_id"] = intervals["driver_id"].astype(str)
    
    track_status = derive_track_status(conn, session_id)
    
    weather = conn.execute("""
        SELECT sample_time, air_temperature_c, track_temperature_c, rainfall_flag
        FROM fact_weather_sample
        WHERE session_id = ?
        ORDER BY sample_time
    """, [session_id]).fetchdf()
    
    # Map lap numbers to approximate start times for weather join
    lap_times_map = conn.execute("""
        SELECT lap_number, MIN(lap_start_time) as start_time
        FROM fact_lap
        WHERE session_id = ? AND lap_start_time IS NOT NULL
        GROUP BY lap_number
        ORDER BY lap_number
    """, [session_id]).fetchdf()
    if not lap_times_map.empty:
        lap_times_map["start_time"] = pd.to_datetime(lap_times_map["start_time"], format="mixed")
    
    weather["sample_time"] = pd.to_datetime(weather["sample_time"], format="mixed")
    
    pit_stops = conn.execute("""
        SELECT driver_ref, lap_number, pit_duration_seconds
        FROM fact_pit_stop
        WHERE session_id = ?
    """, [session_id]).fetchdf()
    
    pit_counts = pit_stops.groupby("driver_ref").size().reset_index(name="total_pit_stops")
    last_pit = pit_stops.groupby("driver_ref")["lap_number"].max().reset_index(name="last_pit_lap")
    
    rows = []
    
    for _, lap in laps.iterrows():
        d = lap["driver_id"]
        lap_num = lap["lap_number"]
        
        stint = stints[(stints["driver_ref"] == d) &
                       (stints["lap_start"] <= lap_num) &
                       (stints["lap_end"] >= lap_num)]
        
        compound = stint["tyre_compound_id"].iloc[0] if not stint.empty else "UNKNOWN"
        compound_label = stint["compound_label_source"].iloc[0] if not stint.empty else "UNKNOWN"
        stint_num = int(stint["stint_number"].iloc[0]) if not stint.empty else 0
        stint_start = int(stint["lap_start"].iloc[0]) if not stint.empty else lap_num
        stint_age = lap_num - stint_start if stint_start else 0
        
        pos_row = positions[(positions["driver_id"] == d) & (positions["lap_number"] == lap_num)]
        pos = int(pos_row["position"].iloc[0]) if not pos_row.empty else None
        
        interval_row = intervals[(intervals["driver_id"] == d) & (intervals["lap_number"] == lap_num)]
        gap_leader = float(interval_row["gap_to_leader_seconds"].iloc[0]) if not interval_row.empty else None
        gap_ahead = float(interval_row["interval_to_ahead_seconds"].iloc[0]) if not interval_row.empty else None
        gap_behind = None
        if pos and pos > 1:
            behind = intervals[(intervals["driver_id"] != d) &
                               (intervals["lap_number"] == lap_num) &
                               (intervals["gap_to_leader_seconds"].notna())]
            if not behind.empty:
                pos_behind = positions[(positions["lap_number"] == lap_num) &
                                       (positions["position"] == pos + 1)]
                if not pos_behind.empty:
                    d_behind = str(pos_behind["driver_id"].iloc[0])
                    gap_behind_row = intervals[(intervals["driver_id"] == d_behind) &
                                                (intervals["lap_number"] == lap_num)]
                    if not gap_behind_row.empty:
                        gap_behind = round(
                            float(gap_behind_row["gap_to_leader_seconds"].iloc[0]) -
                            float(interval_row["gap_to_leader_seconds"].iloc[0]), 3
                        )
        
        # Driver ahead/behind IDs
        driver_ahead = None
        driver_behind = None
        if pos:
            ahead = positions[(positions["lap_number"] == lap_num) & (positions["position"] == pos - 1)]
            if not ahead.empty:
                driver_ahead = str(ahead["driver_id"].iloc[0])
            behind_p = positions[(positions["lap_number"] == lap_num) & (positions["position"] == pos + 1)]
            if not behind_p.empty:
                driver_behind = str(behind_p["driver_id"].iloc[0])
        
        # Rolling averages
        driver_laps = laps[laps["driver_id"] == d].sort_values("lap_number")
        lt_series = driver_laps[driver_laps["lap_number"] <= lap_num].tail(5)["lap_time_ms"]
        rolling_3 = lt_series.tail(3).mean() if len(lt_series.tail(3)) >= 2 else None
        rolling_5 = lt_series.mean() if len(lt_series) >= 3 else None
        
        # Pace delta: driver rolling 3 - field median at this lap
        field_laps = laps[laps["lap_number"] == lap_num]["lap_time_ms"]
        field_median = field_laps.median()
        pace_delta = (rolling_3 - field_median) if rolling_3 and pd.notna(field_median) else None
        
        # Pit stop counts
        driver_pits = pit_stops[pit_stops["driver_ref"] == d]
        pit_count = len(driver_pits[driver_pits["lap_number"] < lap_num])
        last_pit_lap = int(driver_pits[driver_pits["lap_number"] < lap_num]["lap_number"].max()) if not driver_pits[driver_pits["lap_number"] < lap_num].empty else None
        
        # Track status for this lap
        ts = track_status[track_status["lap_number"] == lap_num]
        sc_flag = bool(ts["safety_car_active_flag"].iloc[0]) if not ts.empty else False
        vsc_flag = bool(ts["virtual_safety_car_active_flag"].iloc[0]) if not ts.empty else False
        red_flag = bool(ts["red_flag_active_flag"].iloc[0]) if not ts.empty else False
        track_norm = ts["track_status_normalized"].iloc[0] if not ts.empty else "green"
        
        # Weather: join by nearest lap start time
        rain_flag = False
        air_temp = None
        track_temp = None
        if not lap_times_map.empty and not weather.empty:
            lt_row = lap_times_map[lap_times_map["lap_number"] == lap_num]
            if not lt_row.empty and pd.notna(lt_row["start_time"].iloc[0]):
                lap_time = lt_row["start_time"].iloc[0]
                weather["time_diff"] = abs(weather["sample_time"] - lap_time)
                nearest = weather.loc[weather["time_diff"].idxmin()]
                rain_flag = bool(nearest["rainfall_flag"]) if pd.notna(nearest["rainfall_flag"]) else False
                air_temp = float(nearest["air_temperature_c"]) if pd.notna(nearest["air_temperature_c"]) else None
                track_temp = float(nearest["track_temperature_c"]) if pd.notna(nearest["track_temperature_c"]) else None
        else:
            rain_flag = weather["rainfall_flag"].mode().iloc[0] if not weather.empty and not weather["rainfall_flag"].empty else False
            air_temp = float(weather["air_temperature_c"].mean()) if not weather.empty else None
            track_temp = float(weather["track_temperature_c"].mean()) if not weather.empty else None
        
        is_pit = bool(lap["is_pit_out_lap"]) if pd.notna(lap["is_pit_out_lap"]) else False
        
        rid = f"{session_id}_{d}_{lap_num}"
        
        # Pit window: stint_age > 8 for softs, > 12 for mediums, > 18 for hards
        # Undercut threat: gap_behind < 2.0
        # Overcut opportunity: gap_ahead < 1.5 and driver behind has older tires
        compound_hardness_map = {"SOFT": 1, "MEDIUM": 2, "HARD": 3, "INTERMEDIATE": 4, "WET": 5}
        compound_hardness = compound_hardness_map.get(compound.upper(), 3)
        pit_window_open = stint_age > [8, 12, 18, 15, 20][min(compound_hardness - 1, 4)]
        undercut_threat = (gap_behind is not None and gap_behind < 2.0)
        overcut_opportunity = (gap_ahead is not None and gap_ahead < 1.5)
        
        constructor_id = constructor_map.get(str(d))
        
        rows.append({
            "race_state_driver_lap_id": rid,
            "session_id": session_id,
            "meeting_id": meeting_id,
            "season_id": season_id,
            "driver_id": d,
            "constructor_id": constructor_id,
            "lap_number": lap_num,
            "race_lap_pct": round(lap_num / total_laps, 4) if total_laps else None,
            "laps_remaining": total_laps - lap_num,
            "current_position": pos,
            "starting_position": None,
            "positions_gained_lost": None,
            "gap_to_leader_seconds": gap_leader,
            "interval_ahead_seconds": gap_ahead,
            "interval_behind_seconds": gap_behind,
            "driver_ahead_id": driver_ahead,
            "driver_behind_id": driver_behind,
            "current_compound_id": compound,
            "current_compound_label": compound_label,
            "stint_number": stint_num,
            "stint_age_laps": stint_age,
            "total_pit_stops": pit_count,
            "last_pit_lap": last_pit_lap,
            "lap_time_ms": float(lap["lap_time_ms"]) if pd.notna(lap["lap_time_ms"]) else None,
            "rolling_3_lap_avg_ms": round(rolling_3, 3) if rolling_3 else None,
            "rolling_5_lap_avg_ms": round(rolling_5, 3) if rolling_5 else None,
            "pace_delta_to_field_ms": round(pace_delta, 3) if pace_delta else None,
            "track_status_normalized": track_norm,
            "safety_car_active_flag": sc_flag,
            "virtual_safety_car_active_flag": vsc_flag,
            "red_flag_active_flag": red_flag,
            "rainfall_flag": rain_flag,
            "air_temperature": air_temp,
            "track_temperature": track_temp,
            "pit_window_open_flag": pit_window_open,
            "is_pit_lap": is_pit,
            "undercut_threat_flag": undercut_threat,
            "overcut_opportunity_flag": overcut_opportunity,
            "source_coverage_quality": "enriched",
            "created_at": datetime.now(),
        })
    
    df = pd.DataFrame(rows)
    
    print(f"  Deleting old race_state rows for session {session_id}...")
    conn.execute("DELETE FROM race_state_driver_lap_fact WHERE session_id = ?", [session_id])
    
    print(f"  Inserting {len(df)} enriched rows into race_state_driver_lap_fact...")
    conn.execute(
        "INSERT INTO race_state_driver_lap_fact SELECT * FROM df"
    )
    
    # Rebuild field lap summary
    print("  Rebuilding race_state_field_lap...")
    conn.execute("DELETE FROM race_state_field_lap WHERE session_id = ?", [session_id])
    
    for lap_num in range(1, total_laps + 1):
        fl = laps[laps["lap_number"] == lap_num]
        pl = positions[positions["lap_number"] == lap_num]
        ts = track_status[track_status["lap_number"] == lap_num]
        running = len(fl)
        retired = len(positions["driver_id"].unique()) - running
        
        field_lap_times = fl["lap_time_ms"].dropna()
        avg_lap = field_lap_times.mean() if not field_lap_times.empty else None
        med_lap = field_lap_times.median() if not field_lap_times.empty else None
        fast_lap = field_lap_times.min() if not field_lap_times.empty else None
        
        # Compound counts
        stints_at_lap = stints[(stints["lap_start"] <= lap_num) & (stints["lap_end"] >= lap_num)]
        n_soft = len(stints_at_lap[stints_at_lap["tyre_compound_id"] == "SOFT"])
        n_medium = len(stints_at_lap[stints_at_lap["tyre_compound_id"] == "MEDIUM"])
        n_hard = len(stints_at_lap[stints_at_lap["tyre_compound_id"] == "HARD"])
        n_inter = len(stints_at_lap[stints_at_lap["tyre_compound_id"] == "INTERMEDIATE"])
        n_wet = len(stints_at_lap[stints_at_lap["tyre_compound_id"] == "WET"])
        
        # Field spread: gap from leader to last
        lap_intervals = intervals[intervals["lap_number"] == lap_num]
        field_spread = lap_intervals["gap_to_leader_seconds"].max() if not lap_intervals.empty else None
        
        lid = f"field_{session_id}_{lap_num}"
        conn.execute("""
            INSERT INTO race_state_field_lap (
                race_state_field_lap_id, session_id, lap_number,
                total_running_drivers, total_retired_drivers,
                average_lap_time_ms, median_lap_time_ms, fastest_lap_time_ms,
                number_on_soft, number_on_medium, number_on_hard,
                number_on_intermediate, number_on_wet,
                field_spread_seconds, safety_car_active_flag,
                virtual_safety_car_active_flag, red_flag_active_flag, rainfall_flag,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            lid, session_id, lap_num,
            running, retired,
            avg_lap, med_lap, fast_lap,
            n_soft, n_medium, n_hard, n_inter, n_wet,
            field_spread,
            bool(ts["safety_car_active_flag"].iloc[0]) if not ts.empty else False,
            bool(ts["virtual_safety_car_active_flag"].iloc[0]) if not ts.empty else False,
            bool(ts["red_flag_active_flag"].iloc[0]) if not ts.empty else False,
            None,  # rainfall from weather
        ])
    
    print(f"    Built field summary for {total_laps} laps")
    print(f"  race_state_driver_lap_fact: {len(df)} rows")
    print(f"  race_state_field_lap: {total_laps} rows")


def rebuild_feature_store(conn, session_id: str):
    print("Rebuilding feature store...")
    
    # Delete old features for this session
    conn.execute("DELETE FROM feature_pit_decision WHERE session_id = ?", [session_id])
    conn.execute("DELETE FROM feature_undercut_opportunity WHERE session_id = ?", [session_id])
    
    # feature_pit_decision
    rs = conn.execute("""
        SELECT * FROM race_state_driver_lap_fact
        WHERE session_id = ? AND stint_age_laps > 0
    """, [session_id]).fetchdf()
    
    if rs.empty:
        print("  WARNING: No race state data available for feature building")
        return
    
    # Compound hardness map
    compound_map = conn.execute("SELECT * FROM dim_tyre_compound").fetchdf()
    hardness_map = {}
    for _, row in compound_map.iterrows():
        hardness_map[row["compound_label"]] = row.get("compound_hardness_order")
    
    pit_stops = conn.execute("""
        SELECT driver_ref, lap_number FROM fact_pit_stop WHERE session_id = ?
    """, [session_id]).fetchdf()
    
    for _, row in rs.iterrows():
        d = row["driver_id"]
        lap = row["lap_number"]
        compound = row["current_compound_label"]
        hardness = hardness_map.get(compound, 0) if compound else 0
        
        pit_loss = 22.0  # Interlagos default
        if row["safety_car_active_flag"]:
            pit_loss = max(0.0, pit_loss - 18.0)
        elif row["virtual_safety_car_active_flag"]:
            pit_loss = max(0.0, pit_loss - 14.0)
        
        # Label: pitted within 3 laps?
        pit_mask = (pit_stops["driver_ref"] == d) & \
                   (pit_stops["lap_number"] >= lap - 3) & \
                   (pit_stops["lap_number"] <= lap)
        pitted = int(pit_mask.any())
        
        fid = f"{session_id}_{d}_{lap}"
        
        conn.execute("""
            INSERT INTO feature_pit_decision
            (feature_id, session_id, driver_id, lap_number,
             laps_remaining, current_position, gap_ahead_seconds, gap_behind_seconds,
             stint_age_laps, compound_hardness_order,
             rolling_3_lap_avg_ms, pace_delta_to_field_ms,
             safety_car_active_flag, vsc_active_flag,
             rainfall_flag, track_temperature,
             pit_loss_estimate_seconds,
             actual_pitted_within_3_laps,
             feature_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            fid, session_id, d, lap,
            int(row["laps_remaining"]) if pd.notna(row["laps_remaining"]) else 0,
            int(row["current_position"]) if pd.notna(row["current_position"]) else None,
            float(row["interval_ahead_seconds"]) if pd.notna(row["interval_ahead_seconds"]) else None,
            float(row["interval_behind_seconds"]) if pd.notna(row["interval_behind_seconds"]) else None,
            int(row["stint_age_laps"]) if pd.notna(row["stint_age_laps"]) else 0,
            hardness,
            float(row["rolling_3_lap_avg_ms"]) if pd.notna(row["rolling_3_lap_avg_ms"]) else None,
            float(row["pace_delta_to_field_ms"]) if pd.notna(row["pace_delta_to_field_ms"]) else None,
            bool(row["safety_car_active_flag"]) if pd.notna(row["safety_car_active_flag"]) else False,
            bool(row["virtual_safety_car_active_flag"]) if pd.notna(row["virtual_safety_car_active_flag"]) else False,
            bool(row["rainfall_flag"]) if pd.notna(row["rainfall_flag"]) else False,
            float(row["track_temperature"]) if pd.notna(row["track_temperature"]) else None,
            pit_loss,
            bool(pitted),
            DATA_VERSION,
        ])
    
    print(f"  feature_pit_decision: {len(rs)} rows")
    
    # feature_undercut_opportunity (simplified: pairs drivers who are close)
    for _, row in rs.iterrows():
        if pd.notna(row["driver_ahead_id"]) and pd.notna(row["interval_ahead_seconds"]):
            gap = float(row["interval_ahead_seconds"])
            if gap < 5.0:
                uid = f"und_{session_id}_{row['driver_id']}_{row['driver_ahead_id']}_{row['lap_number']}"
                target_stint = rs[(rs["driver_id"] == row["driver_ahead_id"]) & 
                                   (rs["lap_number"] == row["lap_number"])]
                target_age = int(target_stint["stint_age_laps"].iloc[0]) if not target_stint.empty else None
                
                conn.execute("""
                    INSERT INTO feature_undercut_opportunity
                    (feature_id, session_id, driver_id, target_driver_id, lap_number,
                     gap_to_target_seconds, target_stint_age_laps,
                     own_stint_age_laps, own_compound, target_compound,
                     pit_loss_estimate_seconds, circuit_overtaking_difficulty,
                     undercut_succeeded, feature_version, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, [
                    uid, session_id, row["driver_id"], row["driver_ahead_id"], row["lap_number"],
                    gap, target_age,
                    int(row["stint_age_laps"]) if pd.notna(row["stint_age_laps"]) else None,
                    row["current_compound_label"],
                    target_stint["current_compound_label"].iloc[0] if not target_stint.empty else None,
                    22.0, 0.6,  # pit_loss, overtaking_difficulty (interlagos defaults)
                    False, DATA_VERSION,
                ])
    
    print(f"  feature_undercut_opportunity: built from close driver pairs")


def populate(session_id: str = "2024_21_R"):
    conn = connect()
    
    print(f"=== Populating derived data for session {session_id} ===")
    
    # Step 1: Create + populate position table
    print("\n[Step 1] Position data...")
    create_position_table(conn)
    pos_df = compute_positions(conn, session_id)
    populate_positions(conn, pos_df)
    
    # Step 2: Create + populate interval data
    print("\n[Step 2] Interval/gap data...")
    int_df = compute_intervals(conn, session_id, pos_df)
    populate_intervals(conn, int_df)
    
    # Step 3: Rebuild race_state tables
    print("\n[Step 3] Race state tables...")
    rebuild_race_state(conn, session_id)
    
    # Step 4: Rebuild feature store
    print("\n[Step 4] Feature store...")
    rebuild_feature_store(conn, session_id)
    
    conn.close()
    
    # Verify
    conn = connect()
    rs = conn.execute(
        "SELECT COUNT(*) as cnt, COUNT(current_position) as pos, "
        "COUNT(interval_ahead_seconds) as gaps, COUNT(rolling_3_lap_avg_ms) as roll, "
        "COUNT(rainfall_flag) as rain, COUNT(track_status_normalized) as track "
        "FROM race_state_driver_lap_fact WHERE session_id = ?",
        [session_id]
    ).fetchdf()
    conn.close()
    
    print("\n=== Verification ===")
    print(rs.to_string())
    
    # Summary of non-null counts
    conn = connect()
    cols = [
        "current_position", "gap_to_leader_seconds", "interval_ahead_seconds",
        "interval_behind_seconds", "driver_ahead_id", "driver_behind_id",
        "rolling_3_lap_avg_ms", "pace_delta_to_field_ms", "track_status_normalized",
        "safety_car_active_flag", "rainfall_flag", "pit_window_open_flag",
        "undercut_threat_flag", "overcut_opportunity_flag",
    ]
    print("\nNon-null counts:")
    for c in cols:
        cnt = conn.execute(
            f'SELECT COUNT(*) FROM race_state_driver_lap_fact WHERE session_id = ? AND "{c}" IS NOT NULL',
            [session_id]
        ).fetchone()[0]
        print(f"  {c:35s}: {cnt}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate derived race state data")
    parser.add_argument("--session", default="2024_21_R", help="Session ID (default: 2024_21_R)")
    args = parser.parse_args()
    populate(args.session)
