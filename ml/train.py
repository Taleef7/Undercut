#!/usr/bin/env python3
"""CLI to train ML models.

Usage:
    uv run python -m ml.train --target pit_decision --data-version v0.1
    uv run python -m ml.train --target finish_position --data-version v0.1
"""

import argparse
import sys
from pathlib import Path
import duckdb

from ml.datasets.pit_decision_dataset import PitDecisionDataset
from ml.datasets.finish_position_dataset import FinishPositionDataset
from ml.models.pit_decision_model import PitDecisionModel
from ml.models.finish_position_model import FinishPositionModel
from ml.evaluate import evaluate_binary_classification, evaluate_multiclass_classification
from ml.registry import register_model

DB_PATH = Path(__file__).parent.parent / "data" / "undercut.db"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def train_pit_decision(data_version: str):
    print("Building pit decision dataset...")
    ds = PitDecisionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()

    if X_train.empty:
        print("ERROR: No training data available")
        sys.exit(1)

    print(f"  Training samples: {len(X_train)}, Test samples: {len(X_test)}")
    print(f"  Features: {feature_names}")

    numeric_cols = X_train.select_dtypes(include=["number"]).columns.tolist()
    keep_cols = [c for c in feature_names if c in numeric_cols]
    if len(keep_cols) < len(feature_names):
        print(f"  Dropped non-numeric features: {set(feature_names) - set(keep_cols)}")
    X_train = X_train[keep_cols]
    X_test = X_test[keep_cols]
    feature_names = keep_cols

    train_mask = ~X_train.isna().any(axis=1)
    test_mask = ~X_test.isna().any(axis=1)
    X_train = X_train[train_mask]
    y_train = y_train[train_mask]
    X_test = X_test[test_mask]
    y_test = y_test[test_mask]

    pit_model = PitDecisionModel(model_type="xgboost")
    print("  Training XGBoost model...")
    pit_model.train(X_train, y_train, feature_names)

    print("Evaluating...")
    y_pred = pit_model.model.predict(pit_model.scaler.transform(X_test))
    y_proba = pit_model.model.predict_proba(pit_model.scaler.transform(X_test))[:, 1]
    metrics = evaluate_binary_classification(
        y_test.values, y_pred, y_proba, model_name="pit_decision_xgboost"
    )
    print(f"  Accuracy: {metrics['accuracy']}, F1: {metrics['f1_score']}, ROC-AUC: {metrics['roc_auc']}")

    version = data_version
    artifact_path = ARTIFACTS_DIR / "pit_decision" / version
    pit_model.save(artifact_path)
    print(f"  Artifacts saved to {artifact_path}")

    conn = duckdb.connect(str(DB_PATH))
    model_id = register_model(
        conn, "pit_decision", version, "pit_decision_binary",
        data_version, metrics, str(artifact_path), "Trained on Brazil 2024 race data"
    )
    conn.close()
    print(f"  Model registered: {model_id}")
    print("Done!")


def train_finish_position(data_version: str):
    print("Building finish position dataset...")
    ds = FinishPositionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()

    if X_train.empty:
        print("ERROR: No training data available")
        sys.exit(1)

    print(f"  Training samples: {len(X_train)}, Test samples: {len(X_test)}")

    train_mask = ~X_train.isna().any(axis=1)
    test_mask = ~X_test.isna().any(axis=1)
    X_train = X_train[train_mask]
    y_train = y_train[train_mask]
    X_test = X_test[test_mask]
    y_test = y_test[test_mask]

    fp_model = FinishPositionModel(model_type="xgboost")
    print("  Training XGBoost model...")
    fp_model.train(X_train, y_train, feature_names)

    print("Evaluating...")
    y_pred = fp_model.model.predict(fp_model.scaler.transform(X_test))
    metrics = evaluate_multiclass_classification(
        y_test.values, y_pred, fp_model.class_names, model_name="finish_position_xgboost"
    )
    print(f"  Accuracy: {metrics['accuracy']}, F1-weighted: {metrics['f1_weighted']}")

    version = data_version
    artifact_path = ARTIFACTS_DIR / "finish_position" / version
    fp_model.save(artifact_path)
    print(f"  Artifacts saved to {artifact_path}")

    conn = duckdb.connect(str(DB_PATH))
    model_id = register_model(
        conn, "finish_position", version, "finish_position_multiclass",
        data_version, metrics, str(artifact_path), "Trained on Brazil 2024 race data"
    )
    conn.close()
    print(f"  Model registered: {model_id}")
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Train ML models for Undercut")
    parser.add_argument("--target", choices=["pit_decision", "finish_position"], required=True)
    parser.add_argument("--data-version", default="v0.1")
    args = parser.parse_args()

    if args.target == "pit_decision":
        train_pit_decision(args.data_version)
    else:
        train_finish_position(args.data_version)


if __name__ == "__main__":
    main()
