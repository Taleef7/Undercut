from typing import Tuple, List, Optional
import json
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb


class PitDecisionModel:
    def __init__(self, model_type: str = "xgboost"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.explainer = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        feature_names: List[str],
    ) -> "PitDecisionModel":
        self.feature_names = [c for c in feature_names if c in X_train.columns and X_train[c].dtype.kind in "iufb"]
        X_numeric = X_train[self.feature_names].copy()
        y_clean = y_train.loc[X_numeric.index]
        X_clean = X_numeric.dropna()
        y_clean = y_clean.loc[X_clean.index]
        X_scaled = self.scaler.fit_transform(X_clean)
        y_clean = y_clean.reset_index(drop=True)

        if self.model_type == "logistic_regression":
            self.model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        elif self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, class_weight="balanced", random_state=42
            )
        else:
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                eval_metric="logloss",
                random_state=42,
            )

        self.model.fit(X_scaled, y_clean)

        if self.model_type == "xgboost":
            import shap
            self.explainer = shap.TreeExplainer(self.model)

        return self

    def predict(self, X: pd.DataFrame) -> Tuple[str, float]:
        X_scaled = self.scaler.transform(X[self.feature_names])
        proba = self.model.predict_proba(X_scaled)[0, 1]
        pred = 1 if proba >= 0.5 else 0
        recommendation = "pit_now" if pred == 1 else "stay_out"
        confidence = round(max(proba, 1 - proba), 4)
        return recommendation, confidence

    def predict_proba(self, X: pd.DataFrame) -> float:
        X_scaled = self.scaler.transform(X[self.feature_names])
        return float(self.model.predict_proba(X_scaled)[0, 1])

    def explain(self, X: pd.DataFrame) -> List[str]:
        if self.explainer is None:
            return ["Model explainer not available"]
        X_scaled = self.scaler.transform(X[self.feature_names])
        shap_values = self.explainer.shap_values(X_scaled)
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        feature_importance = list(zip(self.feature_names, np.abs(shap_values[0])))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        top_features = feature_importance[:3]

        template_map = {
            "stint_age_laps": "Stint age was the key signal",
            "compound_hardness": "Tire compound hardness influenced the recommendation",
            "approx_position": "Track position was a significant factor",
            "laps_remaining": "Remaining laps affected pit urgency",
            "lap_time_ms": "Lap time performance influenced the decision",
            "rolling_3_lap_avg_ms": "Recent lap time trend was considered",
            "rainfall_flag": "Rain conditions changed the pit calculus",
            "is_wet_compound": "Wet tire compound affected the recommendation",
            "red_flag": "Red flag status influenced the decision",
            "is_pit_out_lap": "Pit out lap status was a factor",
            "air_temperature_c": "Air temperature influenced tire degradation assessment",
            "track_temperature_c": "Track temperature influenced tire degradation assessment",
        }

        result = []
        for feat, _ in top_features:
            msg = template_map.get(feat, f"{feat.replace('_', ' ').title()} was considered")
            result.append(msg)

        return result[:3]

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path / "model.joblib")
        joblib.dump(self.scaler, path / "scaler.joblib")
        with open(path / "feature_names.json", "w") as f:
            json.dump(self.feature_names, f)
        if self.explainer is not None:
            joblib.dump(self.explainer, path / "shap_explainer.joblib")

    @classmethod
    def load(cls, path: Path) -> "PitDecisionModel":
        instance = cls()
        instance.model = joblib.load(path / "model.joblib")
        instance.scaler = joblib.load(path / "scaler.joblib")
        with open(path / "feature_names.json") as f:
            instance.feature_names = json.load(f)
        explainer_path = path / "shap_explainer.joblib"
        if explainer_path.exists():
            instance.explainer = joblib.load(explainer_path)
        if hasattr(instance.model, "__class__"):
            model_class_name = instance.model.__class__.__name__
            if "XGB" in model_class_name:
                instance.model_type = "xgboost"
            elif "RandomForest" in model_class_name:
                instance.model_type = "random_forest"
            else:
                instance.model_type = "logistic_regression"
        return instance
