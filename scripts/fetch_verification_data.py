"""Fetch real lap data from FastF1 to verify decision point race_state values."""
import fastf1
from pathlib import Path

fastf1.Cache.enable_cache("data/cache")

RACES = [
    (2021, "Abu Dhabi", "R", 58, "abu_dhabi_2021"),
    (2023, "Singapore", "R", 62, "singapore_2023"),
    (2022, "Hungary", "R", 70, "hungary_2022"),
]


def fetch_race_state(year, gp, session_type, total_laps, race_key):
    print(f"\n{'='*60}")
    print(f"=== {year} {gp} ===")
    print(f"{'='*60}")

    session = fastf1.get_session(year, gp, session_type)
    session.load()

    # Target laps for decision points
    target_laps = {
        "abu_dhabi_2021": [14, 53, 56],
        "singapore_2023": [20, 40, 43],
        "hungary_2022": [38, 47, 51],
    }

    for lap_num in target_laps.get(race_key, []):
        if lap_num > total_laps:
            continue

        print(f"\n--- Lap {lap_num} ---")

        # Get lap data
        laps = session.laps[session.laps["LapNumber"] == lap_num]

        # Get weather data for this lap
        try:
            weather = session.weather_data
            if weather is not None and not weather.empty:
                # Find weather sample closest to this lap
                w = weather.iloc[-1]  # approximate - last sample
                track_temp = w.get('TrackTemp', 'N/A') if hasattr(w, 'get') else getattr(w, 'TrackTemp', 'N/A')
                air_temp = w.get('AirTemp', 'N/A') if hasattr(w, 'get') else getattr(w, 'AirTemp', 'N/A')
                rainfall = w.get('Rainfall', 'N/A') if hasattr(w, 'get') else getattr(w, 'Rainfall', 'N/A')
                print(f"  Weather (approx): Track temp {track_temp}°C, Air temp {air_temp}°C, Rainfall {rainfall}")
        except Exception as e:
            print(f"  Weather: could not fetch ({e})")

        # Print driver data
        for _, row in laps.iterrows():
            driver = row["Driver"]
            pos = row["Position"]
            compound = row.get("Compound", "UNKNOWN")
            stint = row.get("Stint", "N/A")
            lap_time = row.get("LapTime", "N/A")

            # Get interval data
            interval = "N/A"
            try:
                intervals = session.laps.pick_driver(driver)[session.laps.pick_driver(driver)["LapNumber"] == lap_num]
                if not intervals.empty:
                    gap = intervals.iloc[0].get("GapToLeader", "N/A")
                    interval_val = intervals.iloc[0].get("IntervalToPositionAhead", "N/A")
                    interval = f"Gap: {gap}, Interval: {interval_val}"
            except Exception:
                pass

            print(f"  {driver}: P{pos}, Compound: {compound}, Stint: {stint}, LapTime: {lap_time}, {interval}")

        # Check for safety car / track status
        try:
            race_control = session.race_control_messages
            if race_control is not None and not race_control.empty:
                rc_at_lap = race_control[race_control["Lap"].notna() & (race_control["Lap"] == lap_num)]
                if not rc_at_lap.empty:
                    for _, msg in rc_at_lap.iterrows():
                        print(f"  Race Control: {msg.get('Message', 'N/A')}")
        except Exception as e:
            print(f"  Could not fetch race control: {e}")


if __name__ == "__main__":
    for args in RACES:
        fetch_race_state(*args)
