import duckdb
import pandas as pd
from pathlib import Path
from . import compute_record_hash, load_raw_json


def normalize_sessions(db_path: Path, data_dir: Path) -> int:
    data = load_raw_json(data_dir, "jolpica", "2024", "21", "results.json")
    if not data:
        return 0

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return 0

    race = races[0]
    season = int(race.get("season", 0))
    round_num = int(race.get("round", 0))
    race_name = race.get("raceName", "")
    circuit_ref = race.get("Circuit", {}).get("circuitId", "")
    circuit = race.get("Circuit", {})
    loc = circuit.get("Location", {})
    laps_str = race.get("Results", [{}])[0].get("laps", "0") if race.get("Results") else "0"
    total_laps = int(laps_str)

    conn = duckdb.connect(str(db_path))

    season_id = str(season)
    rows_season = [{
        "season_id": season_id,
        "year": season,
    }]
    df_season = pd.DataFrame(rows_season)
    conn.execute("""
        INSERT OR REPLACE INTO dim_season (season_id, year)
        SELECT season_id, year FROM df_season
    """)

    meeting_id = f"{season}_{round_num}"
    rows_meeting = [{
        "meeting_id": meeting_id,
        "season_id": season_id,
        "round_number": round_num,
        "meeting_name": race_name,
        "official_event_name": race_name,
        "country": loc.get("country", ""),
        "location": loc.get("locality", ""),
        "circuit_id": circuit_ref,
        "source_system": "jolpica",
    }]
    df_meeting = pd.DataFrame(rows_meeting)
    conn.execute("""
        INSERT OR REPLACE INTO dim_meeting
            (meeting_id, season_id, round_number, meeting_name, official_event_name,
             country, location, circuit_id, source_system)
        SELECT meeting_id, season_id, round_number, meeting_name, official_event_name,
               country, location, circuit_id, source_system
        FROM df_meeting
    """)

    session_id = f"{season}_{round_num}_R"
    rows_session = [{
        "session_id": session_id,
        "meeting_id": meeting_id,
        "season_id": season_id,
        "session_name": f"{race_name} Race",
        "session_type": "R",
        "is_race": True,
        "is_qualifying": False,
        "is_sprint": False,
        "total_laps": total_laps,
        "source_system": "jolpica",
    }]
    df_session = pd.DataFrame(rows_session)
    conn.execute("""
        INSERT OR REPLACE INTO dim_session
            (session_id, meeting_id, season_id, session_name, session_type,
             is_race, is_qualifying, is_sprint, total_laps, source_system)
        SELECT session_id, meeting_id, season_id, session_name, session_type,
               is_race, is_qualifying, is_sprint, total_laps, source_system
        FROM df_session
    """)

    conn.close()
    return 3
