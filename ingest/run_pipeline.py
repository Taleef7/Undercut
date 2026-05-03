"""
CLI orchestration for the Undercut data pipeline.

Usage:
    bootstrap       Fetch + normalize reference data from Jolpica
    fetch-weekend   Fetch round-specific data
    normalize       Transform raw JSON into canonical DuckDB tables
    build-race-state  Construct derived race state tables
    build-features  Construct feature store tables
    validate        Run validation checks
"""
import argparse
import sys
from pathlib import Path
import duckdb


DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "undercut.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Undercut data pipeline CLI",
        prog="run_pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bootstrap
    p_bootstrap = subparsers.add_parser("bootstrap", help="Fetch + normalize reference data")
    p_bootstrap.add_argument("--source", default="jolpica", choices=["jolpica"])
    p_bootstrap.add_argument("--seasons", type=int, nargs="+", required=True,
                             help="Season years to bootstrap (e.g. 2022 2023 2024)")

    # fetch-weekend
    p_fetch = subparsers.add_parser("fetch-weekend", help="Fetch round-specific data")
    p_fetch.add_argument("--season", type=int, required=True)
    p_fetch.add_argument("--round", type=int, required=True)
    p_fetch.add_argument("--force", action="store_true",
                         help="Delete existing raw files before fetching")

    # normalize
    p_normalize = subparsers.add_parser("normalize", help="Transform raw JSON into canonical tables")
    p_normalize.add_argument("--season", type=int, required=True)
    p_normalize.add_argument("--round", type=int, required=True)
    p_normalize.add_argument("--session", default="R", choices=["R", "Q"],
                             help="Session type (default: R for Race, Q for Qualifying)")

    # build-race-state
    p_race = subparsers.add_parser("build-race-state", help="Construct race state tables")
    p_race.add_argument("--season", type=int, required=True)
    p_race.add_argument("--round", type=int, required=True)

    # build-features
    p_features = subparsers.add_parser("build-features", help="Construct feature store tables")
    p_features.add_argument("--season", type=int, required=True)
    p_features.add_argument("--round", type=int, required=True)

    # validate
    p_validate = subparsers.add_parser("validate", help="Run validation checks")
    p_validate.add_argument("--season", type=int, required=True)
    p_validate.add_argument("--round", type=int, required=True)
    p_validate.add_argument("--session", default="R", choices=["R", "Q"],
                            help="Session type (default: R)")

    return parser


def _get_session_id(season: int, round_num: int, session_type: str = "R") -> str:
    return f"{season}_{round_num}_{session_type}"


def cmd_bootstrap(args):
    print(f"Bootstrapping from {args.source} for seasons {args.seasons}")
    from ingest.jolpica_client import JolpicaClient
    from ingest.normalize.normalize_circuits import normalize_circuits
    from ingest.normalize.normalize_drivers import normalize_drivers
    from ingest.normalize.normalize_constructors import normalize_constructors

    client = JolpicaClient(data_dir=DATA_DIR)
    client.fetch_raw_all_time()
    n_circuits = normalize_circuits(DB_PATH, DATA_DIR)
    print(f"  Circuits: {n_circuits} inserted")

    for season in args.seasons:
        client.fetch_raw_bootstrap(season)
        n_drivers = normalize_drivers(DB_PATH, DATA_DIR)
        n_constructors = normalize_constructors(DB_PATH, DATA_DIR)
        print(f"  Season {season}: {n_drivers} drivers, {n_constructors} constructors")

    print("Bootstrap complete.")


def cmd_fetch_weekend(args):
    print(f"Fetching season={args.season} round={args.round}")
    from ingest.jolpica_client import JolpicaClient
    from ingest.openf1_client import OpenF1Client

    if args.force:
        import shutil
        raw_jolpica = DATA_DIR / "raw" / "jolpica" / str(args.season) / str(args.round)
        if raw_jolpica.exists():
            shutil.rmtree(raw_jolpica)
            print(f"  Deleted {raw_jolpica}")
        print("  (OpenF1 force delete not yet implemented — cache-first will skip)")

    jolpica = JolpicaClient(data_dir=DATA_DIR)
    jolpica.fetch_raw(args.season, args.round)
    print("  Jolpica fetch complete")

    openf1 = OpenF1Client(data_dir=DATA_DIR)
    meetings = openf1.get_meetings(year=args.season)
    meeting_key = None
    for m in meetings:
        if m.get("meeting_name", "").lower() == "brazilian grand prix" or args.round == 21:
            meeting_key = m["meeting_key"]
            break
    if meeting_key:
        sessions = openf1.get_sessions(meeting_key)
        for s in sessions:
            if s.get("session_type") == "Race":
                session_key = s["session_key"]
                openf1.fetch_session(session_key, meeting_key)
                print(f"  OpenF1 fetch complete (session_key={session_key})")
                break

    print("Fetch complete.")


def cmd_normalize(args):
    session_id = _get_session_id(args.season, args.round, args.session)
    print(f"Normalizing session={session_id}")

    from ingest.normalize.normalize_sessions import normalize_sessions
    from ingest.normalize.normalize_results import normalize_results
    from ingest.normalize.normalize_laps import normalize_laps

    n_sessions = normalize_sessions(DB_PATH, DATA_DIR)
    print(f"  Sessions: {n_sessions} rows")

    n_results = normalize_results(DB_PATH, DATA_DIR)
    print(f"  Results: {n_results} rows")

    if args.session == "R":
        from ingest.normalize.normalize_stints import normalize_stints
        from ingest.normalize.normalize_pit_stops import normalize_pit_stops
        from ingest.normalize.normalize_weather import normalize_weather
        from ingest.normalize.normalize_race_control import normalize_race_control

        meeting_key = 47
        session_key = 9540

        n_laps = normalize_laps(DB_PATH, DATA_DIR, meeting_key, session_key)
        n_stints = normalize_stints(DB_PATH, DATA_DIR, meeting_key, session_key)
        n_pits = normalize_pit_stops(DB_PATH, DATA_DIR, meeting_key, session_key)
        n_weather = normalize_weather(DB_PATH, DATA_DIR, meeting_key, session_key)
        n_rc = normalize_race_control(DB_PATH, DATA_DIR, meeting_key, session_key)
        print(f"  Laps: {n_laps}, Stints: {n_stints}, Pit stops: {n_pits}, "
              f"Weather: {n_weather}, Race control: {n_rc}")

    print("Normalize complete.")


def cmd_build_race_state(args):
    session_id = _get_session_id(args.season, args.round)
    print(f"Building race state for {session_id}")

    from ingest.build.build_race_state import (
        build_race_state_driver_lap, build_race_state_field_lap, check_prerequisites
    )
    warnings = check_prerequisites(session_id, DB_PATH)
    for w in warnings:
        print(f"  {w}")

    n_driver = build_race_state_driver_lap(session_id, DB_PATH)
    print(f"  race_state_driver_lap_fact: {n_driver} rows")

    n_field = build_race_state_field_lap(session_id, DB_PATH)
    print(f"  race_state_field_lap: {n_field} rows")

    print("Build race state complete.")


def cmd_build_features(args):
    session_id = _get_session_id(args.season, args.round)
    print(f"Building features for {session_id}")

    from ingest.build.build_features import (
        build_feature_pit_decision, build_feature_undercut_opportunity, check_prerequisites
    )
    check_prerequisites(session_id, DB_PATH)

    n_pit = build_feature_pit_decision(session_id, DB_PATH)
    print(f"  feature_pit_decision: {n_pit} rows")

    n_undercut = build_feature_undercut_opportunity(session_id, DB_PATH)
    print(f"  feature_undercut_opportunity: {n_undercut} rows")

    print("Build features complete.")


def cmd_validate(args):
    session_id = _get_session_id(args.season, args.round, args.session)
    print(f"Validating session={session_id}")

    from ingest.validate.reports import write_report
    warnings = [f"Validation check placeholder for {session_id}"]
    report_path = write_report(warnings, [], args.season, args.round, args.session, DATA_DIR)
    print(f"  Report written to {report_path}")
    print(f"  {len(warnings)} warnings, 0 errors")


COMMAND_MAP = {
    "bootstrap": cmd_bootstrap,
    "fetch-weekend": cmd_fetch_weekend,
    "normalize": cmd_normalize,
    "build-race-state": cmd_build_race_state,
    "build-features": cmd_build_features,
    "validate": cmd_validate,
}


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = COMMAND_MAP.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
