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
    laps_str = race.get("Results", [{}])[0].get("laps", "0") if race.get("Results") else "0"
    total_laps = int(laps_str)

    conn = duckdb.connect(str(db_path))

    rows_season = [{
        "year": season,
        "wiki_url": race.get("url", ""),
        "source_system": "jolpica",
        "data_version": "v0.1",
        "record_hash": compute_record_hash("jolpica", str(season), str(season)),
    }]
    df_season = pd.DataFrame(rows_season)
    conn.execute("""
        INSERT OR REPLACE INTO dim_season
            (year, wiki_url, source_system, data_version, record_hash)
        SELECT year, wiki_url, source_system, data_version, record_hash
        FROM df_season
    """)

    meeting_key = f"{season}_{round_num}"
    rows_meeting = [{
        "meeting_key": meeting_key,
        "season": season,
        "round": round_num,
        "meeting_name": race_name,
        "meeting_official_name": race_name,
        "circuit_ref": circuit_ref,
        "source_system": "jolpica",
        "data_version": "v0.1",
        "record_hash": compute_record_hash("jolpica", meeting_key, race_name),
    }]
    df_meeting = pd.DataFrame(rows_meeting)
    conn.execute("""
        INSERT OR REPLACE INTO dim_meeting
            (meeting_key, season, round, meeting_name, meeting_official_name,
             circuit_ref, source_system, data_version, record_hash)
        SELECT meeting_key, season, round, meeting_name, meeting_official_name,
               circuit_ref, source_system, data_version, record_hash
        FROM df_meeting
    """)

    session_id = f"{season}_{round_num}_R"
    rows_session = [{
        "session_id": session_id,
        "meeting_key": meeting_key,
        "session_type": "R",
        "session_name": f"{race_name} Race",
        "total_laps": total_laps,
        "source_system": "jolpica",
        "data_version": "v0.1",
        "record_hash": compute_record_hash("jolpica", session_id, "Race"),
    }]
    df_session = pd.DataFrame(rows_session)
    conn.execute("""
        INSERT OR REPLACE INTO dim_session
            (session_id, meeting_key, session_type, session_name, total_laps,
             source_system, data_version, record_hash)
        SELECT session_id, meeting_key, session_type, session_name, total_laps,
               source_system, data_version, record_hash
        FROM df_session
    """)

    conn.close()
    return 3  # season + meeting + session
