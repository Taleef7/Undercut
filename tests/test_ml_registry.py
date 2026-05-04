import duckdb
from pathlib import Path
from ml.registry import register_model, get_latest_model

DB_PATH = Path(__file__).parent.parent / "data" / "undercut.db"


def test_register_model_inserts_row():
    conn = duckdb.connect(str(DB_PATH))
    metrics = {"accuracy": 0.85, "f1_score": 0.82, "roc_auc": 0.91}
    model_id = register_model(
        conn, "pit_decision", "v0.1", "pit_decision_binary",
        "v0.1", metrics, "/tmp/test_artifact", "test run"
    )
    assert model_id == "pit_decision_v0.1"
    row = conn.execute("SELECT * FROM ml_model_registry WHERE model_id = ?", [model_id]).fetchone()
    assert row is not None
    assert row[3] == "pit_decision_binary"  # target_definition (index 3 based on CREATE TABLE order)
    conn.close()


def test_get_latest_model_returns_most_recent():
    conn = duckdb.connect(str(DB_PATH))
    metrics = {"accuracy": 0.8, "f1_score": 0.75, "roc_auc": 0.85}
    register_model(conn, "test_model", "v0.1", "test", "v1", metrics, "/tmp/1")
    register_model(conn, "test_model", "v0.2", "test", "v1", metrics, "/tmp/2")
    latest = get_latest_model(conn, "test_model")
    assert latest is not None
    assert latest["model_version"] == "v0.2"
    conn.close()
