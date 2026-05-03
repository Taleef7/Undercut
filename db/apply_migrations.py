"""Apply DuckDB migrations in numeric order."""
from pathlib import Path
import duckdb


ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "undercut.db"
MIGRATIONS_DIR = ROOT / "db" / "migrations"


def apply_migrations() -> None:
    conn = duckdb.connect(str(DB_PATH))
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        print(f"Applying: {path.name}")
        conn.execute(path.read_text(encoding="utf-8"))
    conn.close()
    print("All migrations applied.")


if __name__ == "__main__":
    apply_migrations()
