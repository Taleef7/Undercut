"""
Undercut - Data ingestion for Brazil 2024 GP
Uses FastF1 to fetch session data for the vertical slice
"""
import logging
import duckdb
from pathlib import Path
from datetime import datetime
import pandas as pd

import fastf1
from fastf1 import Cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
YEAR = 2024
GRAND_PRIX = "Brazil"
OUTPUT_DIR = Path("data/cache/brazil_2024")


def setup_cache(cache_dir: Path) -> None:
    """Configure FastF1 cache."""
    Cache.enable_cache(cache_dir)
    logger.info(f"FastF1 cache enabled at {cache_dir}")


def load_session(session_name: str, year: int = YEAR, gp: str = GRAND_PRIX):
    """Load a single session."""
    try:
        session = fastf1.get_session(year, gp, session_name)
        session.load()
        logger.info(f"Loaded {session_name} for {gp} {year}")
        return session
    except Exception as e:
        logger.warning(f"Failed to load {session_name}: {e}")
        return None


def session_to_dataframes(session):
    """Convert a FastF1 session to dict of DataFrames."""
    if session is None:
        return {}

    dfs = {}

    # Laps
    try:
        laps = session.laps
        laps["session_name"] = session.name
        laps["session_date"] = session.date
        dfs["laps"] = laps
    except Exception as e:
        logger.warning(f"Failed to get laps: {e}")

    # Results
    try:
        results = session.results.copy()
        results["session_name"] = session.name
        dfs["results"] = results
    except Exception as e:
        logger.warning(f"Failed to get results: {e}")

    # Weather
    try:
        weather = session.weather_data.copy()
        weather["session_name"] = session.name
        dfs["weather"] = weather
    except Exception as e:
        logger.warning(f"Failed to get weather: {e}")

    # Stints
    try:
        stints = []
        for driver in session.results["DriverNumber"]:
            driver_stints = session.laps.pick_driver(driver).pick_stints()
            if not driver_stints.empty:
                driver_stints = driver_stints.copy()
                driver_stints["Driver"] = driver
                stints.append(driver_stints)
        if stints:
            dfs["stints"] = pd.concat(stints, ignore_index=True)
    except Exception as e:
        logger.warning(f"Failed to get stints: {e}")

    # Pit stops
    try:
        pit_stops = session.pit_stops.copy()
        pit_stops["session_name"] = session.name
        dfs["pit_stops"] = pit_stops
    except Exception as e:
        logger.warning(f"Failed to get pit_stops: {e}")

    # Race control messages
    try:
        rc_msgs = session.race_control_messages
        if not rc_msgs.empty:
            rc_msgs = rc_msgs.copy()
            rc_msgs["session_name"] = session.name
            dfs["race_control"] = rc_msgs
    except Exception as e:
        logger.warning(f"Failed to get race_control: {e}")

    return dfs


def save_parquets(dfs: dict, output_dir: Path) -> None:
    """Save DataFrames to Parquet files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in dfs.items():
        if df is not None and not df.empty:
            path = output_dir / f"{name}.parquet"
            df.to_parquet(path, index=True)
            logger.info(f"Saved {name}: {len(df)} rows to {path}")


def load_brazil_2024():
    """Main: Load Brazil 2024 data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    setup_cache(OUTPUT_DIR / "fastf1")

    sessions = ["FP1", "FP2", "FP3", "Qualifying", "Sprint Shootout", "Sprint", "Race"]
    all_dfs = {}

    for sess_name in sessions:
        logger.info(f"Loading {sess_name}...")
        session = load_session(sess_name)
        if session:
            dfs = session_to_dataframes(session)
            all_dfs[sess_name] = dfs

    # Save each session's data
    for sess_name, dfs in all_dfs.items():
        sess_dir = OUTPUT_DIR / sess_name.lower().replace(" ", "_")
        save_parquets(dfs, sess_dir)

    logger.info("Brazil 2024 data load complete!")


if __name__ == "__main__":
    load_brazil_2024()