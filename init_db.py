"""Auto-initialize the database on startup if missing or empty."""
import duckdb
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "undercut.db"
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SEEDS_DIR = ROOT / "db" / "seeds"
DECISION_POINTS = ROOT / "data" / "decision_points" / "brazil_2024.yaml"


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


def load_decision_points() -> None:
    print("  Loading decision points...")
    sys.path.insert(0, str(ROOT))
    from ingest.load_decision_points import load_decision_points as load_dp
    load_dp(str(DECISION_POINTS), str(DB_PATH))


def init() -> None:
    if db_exists_with_data():
        print("[init_db] Database already initialized with decision points.")
        return

    print("[init_db] Database missing or empty. Initializing...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_PATH))
    run_migrations(conn)
    run_seeds(conn)
    conn.close()
    load_decision_points()

    print("[init_db] Database initialized successfully!")


if __name__ == "__main__":
    init()
