from typing import Optional, Dict, Any
from pathlib import Path
import duckdb
import json

DB_PATH = Path(__file__).parent.parent / "data" / "undercut.db"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def register_model(
    conn: duckdb.DuckDBPyConnection,
    model_name: str,
    model_version: str,
    target: str,
    data_version: str,
    metrics: Dict[str, Any],
    artifact_path: str,
    notes: str = "",
) -> str:
    model_id = f"{model_name}_{model_version}"
    conn.execute("""
        INSERT OR REPLACE INTO ml_model_registry
        (model_id, model_name, model_version, target_definition,
         training_data_version, training_date, accuracy, f1_score,
         roc_auc, artifact_path, notes)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, [
        model_id, model_name, model_version, target,
        data_version,
        metrics.get("accuracy"), metrics.get("f1_score"),
        metrics.get("roc_auc"), artifact_path, notes,
    ])
    return model_id


def get_latest_model(conn: duckdb.DuckDBPyConnection, model_name: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("""
        SELECT * FROM ml_model_registry
        WHERE model_name = ?
        ORDER BY training_date DESC
        LIMIT 1
    """, [model_name]).fetchdf()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def load_model_artifacts(model_name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
    artifact_path = ARTIFACTS_DIR / model_name
    if not artifact_path.exists():
        return None
    if version == "latest":
        versions = sorted([p for p in artifact_path.iterdir() if p.is_dir()])
        if not versions:
            return None
        artifact_path = versions[-1]
    else:
        artifact_path = artifact_path / version

    if not artifact_path.exists():
        return None

    from ml.models.pit_decision_model import PitDecisionModel
    from ml.models.finish_position_model import FinishPositionModel

    if model_name == "pit_decision":
        model = PitDecisionModel.load(artifact_path)
        return {"model": model, "path": str(artifact_path)}
    elif model_name == "finish_position":
        model = FinishPositionModel.load(artifact_path)
        return {"model": model, "path": str(artifact_path)}

    return None
