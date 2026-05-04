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

# Search for decision points YAML in multiple locations
# (Railway volumes may shadow the data/ directory)
DECISION_POINTS_PATHS = [
    ROOT / "data" / "decision_points" / "brazil_2024.yaml",
    ROOT / "db" / "seeds" / "brazil_2024.yaml",
    Path("brazil_2024.yaml"),
]


def find_decision_points_yaml() -> Path:
    """Find the decision points YAML file, checking multiple locations."""
    for path in DECISION_POINTS_PATHS:
        if path.exists():
            print(f"  Found decision points at: {path}")
            return path
    
    # Debug: print what we found
    print("  ERROR: Could not find brazil_2024.yaml in any of these locations:")
    for path in DECISION_POINTS_PATHS:
        print(f"    - {path} (exists={path.exists()})")
    
    # List contents of relevant directories for debugging
    for dirname in [ROOT / "data", ROOT / "db", ROOT / "db" / "seeds"]:
        if dirname.exists():
            print(f"  Contents of {dirname}:")
            try:
                for item in dirname.iterdir():
                    print(f"    {item.name} {'(dir)' if item.is_dir() else '(file)'}")
            except Exception as e:
                print(f"    Error listing: {e}")
        else:
            print(f"  Directory does not exist: {dirname}")
    
    raise FileNotFoundError("brazil_2024.yaml not found in any expected location")


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
    yaml_path = find_decision_points_yaml()
    
    sys.path.insert(0, str(ROOT))
    from ingest.load_decision_points import load_decision_points as load_dp
    load_dp(str(yaml_path), str(DB_PATH))


def init() -> None:
    print(f"[init_db] DB_PATH={DB_PATH}")
    
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
