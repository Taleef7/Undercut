"""Detailed fetch for stint ages and gaps."""
import fastf1
from pathlib import Path

fastf1.Cache.enable_cache("data/cache")

RACES = [
    (2021, "Abu Dhabi", "R", 58, "abu_dhabi_2021"),
    (2023, "Singapore", "R", 62, "singapore_2023"),
    (2022, "Hungary", "R", 70, "hungary_2022"),
]


def get_stint_age(session, driver, target_lap):
    """Calculate how many laps the current stint has been going."""
    try:
        driver_laps = session.laps.pick_drivers(driver)
        target_row = driver_laps[driver_laps["LapNumber"] == target_lap]
        if target_row.empty:
            return None
        current_stint = target_row.iloc[0]["Stint"]
        # Find first lap of this stint
        stint_laps = driver_laps[driver_laps["Stint"] == current_stint]
        first_lap = stint_laps["LapNumber"].min()
        return int(target_lap - first_lap + 1)
    except Exception as e:
        return f"ERROR: {e}"


def get_gap_data(session, driver, target_lap):
    """Get gap to leader and interval to position ahead."""
    try:
        driver_laps = session.laps.pick_drivers(driver)
        row = driver_laps[driver_laps["LapNumber"] == target_lap]
        if row.empty:
            return None, None
        gap = row.iloc[0].get("GapToLeader", None)
        interval = row.iloc[0].get("IntervalToPositionAhead", None)
        return gap, interval
    except Exception as e:
        return f"ERROR: {e}", None


def fetch_detailed(year, gp, session_type, total_laps, race_key):
    print(f"\n{'='*60}")
    print(f"=== {year} {gp} ===")
    print(f"{'='*60}")

    session = fastf1.get_session(year, gp, session_type)
    session.load()

    target_laps = {
        "abu_dhabi_2021": [(14, "PER"), (53, "VER"), (56, "HAM")],
        "singapore_2023": [(20, "RUS"), (40, "ALO"), (43, "NOR")],
        "hungary_2022": [(38, "SAI"), (47, "LEC"), (51, "VER")],
    }

    for lap_num, driver in target_laps.get(race_key, []):
        print(f"\n--- {race_key} Lap {lap_num}, Driver {driver} ---")

        laps = session.laps[session.laps["LapNumber"] == lap_num]
        row = laps[laps["Driver"] == driver]
        if row.empty:
            print("  No data found")
            continue

        pos = row.iloc[0]["Position"]
        compound = row.iloc[0].get("Compound", "UNKNOWN")
        stint = row.iloc[0].get("Stint", "N/A")

        stint_age = get_stint_age(session, driver, lap_num)
        gap, interval = get_gap_data(session, driver, lap_num)
        laps_remaining = total_laps - lap_num

        print(f"  Position: P{pos}")
        print(f"  Compound: {compound}")
        print(f"  Stint: {stint}")
        print(f"  Stint Age: {stint_age} laps")
        print(f"  Gap to Leader: {gap}")
        print(f"  Interval to Ahead: {interval}")
        print(f"  Laps Remaining: {laps_remaining}")


if __name__ == "__main__":
    for args in RACES:
        fetch_detailed(*args)
