import pytest
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "undercut.db"


class TestMLE2EPipeline:
    """End-to-end tests for the full ML training pipeline."""

    def test_dataset_builds_from_actual_db(self):
        from ml.datasets.pit_decision_dataset import PitDecisionDataset
        ds = PitDecisionDataset()
        X_train, y_train, X_test, y_test, feature_names = ds.build()
        assert len(X_train) > 0
        assert len(X_test) > 0
        assert len(feature_names) >= 5
        assert set(y_train.unique()).issubset({0, 1})

    def test_trained_model_predicts_within_range(self):
        from ml.datasets.pit_decision_dataset import PitDecisionDataset
        from ml.models.pit_decision_model import PitDecisionModel

        ds = PitDecisionDataset()
        X_train, y_train, _, _, feature_names = ds.build()

        model = PitDecisionModel(model_type="xgboost")
        model.train(X_train, y_train, feature_names)

        rec, conf = model.predict(X_train.iloc[[0]])
        assert rec in ("pit_now", "stay_out")
        assert 0 <= conf <= 1

    def test_trained_model_produces_shap_explanations(self):
        from ml.datasets.pit_decision_dataset import PitDecisionDataset
        from ml.models.pit_decision_model import PitDecisionModel

        ds = PitDecisionDataset()
        X_train, y_train, _, _, feature_names = ds.build()

        model = PitDecisionModel(model_type="xgboost")
        model.train(X_train, y_train, feature_names)

        explanations = model.explain(X_train.iloc[[0]])
        assert len(explanations) == 3
        assert all(isinstance(e, str) for e in explanations)

    def test_model_artifacts_save_and_load(self):
        from ml.datasets.pit_decision_dataset import PitDecisionDataset
        from ml.models.pit_decision_model import PitDecisionModel
        import tempfile, shutil

        ds = PitDecisionDataset()
        X_train, y_train, _, _, feature_names = ds.build()

        model = PitDecisionModel(model_type="logistic_regression")
        model.train(X_train, y_train, feature_names)

        tmpdir = Path(tempfile.mkdtemp())
        try:
            model.save(tmpdir)
            loaded = PitDecisionModel.load(tmpdir)
            rec, conf = loaded.predict(X_train.iloc[[0]])
            assert rec in ("pit_now", "stay_out")
            assert 0 <= conf <= 1
        finally:
            shutil.rmtree(tmpdir)

    def test_finish_position_model_trains(self):
        from ml.datasets.finish_position_dataset import FinishPositionDataset
        from ml.models.finish_position_model import FinishPositionModel

        ds = FinishPositionDataset()
        X_train, y_train, _, _, feature_names = ds.build()
        if X_train.empty:
            pytest.skip("No finish position data available")

        model = FinishPositionModel(model_type="xgboost")
        model.train(X_train, y_train, feature_names)

        band, conf = model.predict(X_train.iloc[[0]])
        assert band in ("P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+")
        assert 0 <= conf <= 1

    def test_registry_write_and_read(self):
        conn = duckdb.connect(str(DB_PATH))
        from ml.registry import register_model, get_latest_model

        metrics = {"accuracy": 0.85, "f1_score": 0.82, "roc_auc": 0.91}
        model_id = register_model(
            conn, "e2e_test_model", "v1", "e2e_test",
            "v0.1", metrics, "/tmp/e2e_test",
        )
        assert model_id == "e2e_test_model_v1"

        latest = get_latest_model(conn, "e2e_test_model")
        assert latest is not None
        assert latest["model_version"] == "v1"
        assert latest["accuracy"] == 0.85
        conn.close()

    def test_registry_multiple_versions(self):
        conn = duckdb.connect(str(DB_PATH))
        from ml.registry import register_model, get_latest_model

        metrics = {"accuracy": 0.8, "f1_score": 0.75, "roc_auc": 0.85}
        register_model(conn, "e2e_version_test", "v1", "test", "v1", metrics, "/tmp/1", notes="original")
        register_model(conn, "e2e_version_test", "v2", "test", "v2", metrics, "/tmp/2", notes="updated")

        latest = get_latest_model(conn, "e2e_version_test")
        assert latest["model_version"] == "v2"
        conn.close()

    def test_trained_model_lists_in_registry(self):
        conn = duckdb.connect(str(DB_PATH))
        df = conn.execute("""
            SELECT model_name, model_version, accuracy, f1_score, roc_auc
            FROM ml_model_registry
            WHERE model_name IN ('pit_decision', 'finish_position')
            ORDER BY model_name
        """).fetchdf()
        conn.close()
        assert len(df) >= 2
        names = set(df["model_name"])
        assert "pit_decision" in names

    def test_model_artifacts_exist_on_disk(self):
        artifacts_dir = Path(__file__).parent.parent / "ml" / "artifacts"
        pit_dir = artifacts_dir / "pit_decision"
        assert pit_dir.exists(), "pit_decision artifacts dir missing"
        versions = list(pit_dir.iterdir())
        assert len(versions) >= 1
        latest = sorted(versions)[-1]
        assert (latest / "model.joblib").exists()
        assert (latest / "scaler.joblib").exists()
        assert (latest / "feature_names.json").exists()
        assert (latest / "shap_explainer.joblib").exists()

    def test_full_training_pipeline_runs(self):
        """End-to-end: build dataset → train → evaluate → save → register."""
        from ml.datasets.pit_decision_dataset import PitDecisionDataset
        from ml.models.pit_decision_model import PitDecisionModel
        from ml.evaluate import evaluate_binary_classification
        from ml.registry import register_model
        import tempfile, shutil, json

        ds = PitDecisionDataset()
        X_train, y_train, X_test, y_test, feature_names = ds.build()

        model = PitDecisionModel(model_type="xgboost")
        model.train(X_train, y_train, feature_names)

        X_test_filtered = X_test[feature_names]
        X_test_filtered = X_test_filtered.dropna()
        y_test_filtered = y_test.loc[X_test_filtered.index]

        y_pred = model.model.predict(model.scaler.transform(X_test_filtered))
        y_proba = model.model.predict_proba(model.scaler.transform(X_test_filtered))[:, 1]
        y_true = y_test_filtered.values
        metrics = evaluate_binary_classification(y_true, y_pred, y_proba)

        tmpdir = Path(tempfile.mkdtemp())
        try:
            model.save(tmpdir)
            assert (tmpdir / "model.joblib").exists()
            assert (tmpdir / "feature_names.json").exists()

            conn = duckdb.connect(str(DB_PATH))
            model_id = register_model(
                conn, "e2e_full_pipeline_test", "v1", "e2e_full",
                "v0.1", metrics, str(tmpdir), notes="E2E test",
            )
            conn.close()
            assert model_id == "e2e_full_pipeline_test_v1"
        finally:
            shutil.rmtree(tmpdir)

    def test_engine_uses_trained_model_fallback(self):
        """Verify the engine gracefully falls back to baselines when model unavailable."""
        from sim.engine import UndercutEngine
        from sim.scoring import StrategyDecision, ScenarioContext

        engine = UndercutEngine(circuit="interlagos")
        context = ScenarioContext(
            driver="VER", lap=32, position=2, compound="medium",
            stint_age=14, gap_ahead=1.2, gap_behind=4.8,
            laps_remaining=39, safety_car_active=False,
            virtual_safety_car_active=False, rainfall=False,
            track_status="green",
        )
        result = engine.evaluate_strategy(
            StrategyDecision(action="stay_out"),
            context,
            historical_decision="stay_out",
        )
        assert "model_recommendation" in result
        assert "model_confidence" in result
        assert "model_top_features" in result
        assert result["model_recommendation"] in ("pit_now", "stay_out")

    def test_predict_endpoint_integration(self):
        """Verify the API predict endpoint works with the trained model."""
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "44",
            "lap_number": 32,
        })
        if resp.status_code == 503:
            pytest.skip("Trained model not available on this machine")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recommendation"] in ("pit_now", "stay_out")
        assert 0 <= data["confidence"] <= 1
        assert abs(data["probability_pit"] + data["probability_stay"] - 1.0) < 0.01
