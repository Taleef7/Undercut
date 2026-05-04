"""Auto-initialize the database on startup if missing or empty."""
import duckdb
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
# Allow overriding DB path via env var (useful for Railway volume mounts)
DB_PATH = Path(os.environ.get("DUCKDB_PATH", ROOT / "data" / "undercut.db"))
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SEEDS_DIR = ROOT / "db" / "seeds"
DECISION_POINTS_DIR = ROOT / "data" / "decision_points"


def db_exists_with_data() -> bool:
    if not DB_PATH.exists():
        return False
    try:
        conn = duckdb.connect(str(DB_PATH))
        result = conn.execute(
            "SELECT COUNT(*) FROM race_state_decision_point"
        ).fetchone()
        conn.close()
        return result[0] > 0
    except Exception:
        return False


def get_db_scenario_count() -> int:
    if not DB_PATH.exists():
        return 0
    try:
        conn = duckdb.connect(str(DB_PATH))
        result = conn.execute(
            "SELECT COUNT(*) FROM race_state_decision_point"
        ).fetchone()
        conn.close()
        return result[0]
    except Exception:
        return 0


def run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for sql_file in sql_files:
        print(f"  Running {sql_file.name}...")
        conn.execute(open(sql_file).read())


def run_seeds(conn: duckdb.DuckDBPyConnection) -> None:
    seed_files = sorted(SEEDS_DIR.glob("*.sql"))
    for seed_file in seed_files:
        print(f"  Seeding {seed_file.name}...")
        conn.execute(open(seed_file).read())


def load_all_decision_points() -> int:
    """Load all decision point YAML files into the DB."""
    dp_dir = DECISION_POINTS_DIR
    if not dp_dir.exists():
        print(f"  WARNING: Decision points directory not found: {dp_dir}")
        return 0

    yaml_files = sorted(dp_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"  WARNING: No YAML files found in {dp_dir}")
        return 0

    sys.path.insert(0, str(ROOT))
    from ingest.load_decision_points import load_decision_points as load_dp

    total = 0
    for yf in yaml_files:
        count = load_dp(str(yf), str(DB_PATH))
        total += count

    return total


def init() -> None:
    print(f"[init_db] DB_PATH={DB_PATH}")
    db_count = get_db_scenario_count()
    print(f"[init_db] Current scenarios in DB: {db_count}")

    if not DB_PATH.exists():
        print("[init_db] Database missing. Creating...")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(DB_PATH))
        run_migrations(conn)
        run_seeds(conn)
        conn.close()
    else:
        print("[init_db] Database exists.")

    # Always load/update decision points (INSERT OR REPLACE handles duplicates)
    print("[init_db] Loading decision points from YAML files...")
    loaded = load_all_decision_points()
    new_count = get_db_scenario_count()
    print(f"[init_db] Loaded {loaded} scenarios from YAML. Total in DB: {new_count}")

    if new_count == 0:
        print("[init_db] WARNING: No scenarios loaded! Check data/decision_points/")


if __name__ == "__main__":
    init()
