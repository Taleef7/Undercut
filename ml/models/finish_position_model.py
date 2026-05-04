from typing import Tuple, List, Optional
import json
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb


class FinishPositionModel:
    def __init__(self, model_type: str = "xgboost"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.class_names = ["P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+"]
        self.explainer = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        feature_names: List[str],
    ) -> "FinishPositionModel":
        self.feature_names = feature_names
        X_scaled = self.scaler.fit_transform(X_train)

        if self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42
            )
        else:
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                objective="multi:softprob",
                eval_metric="mlogloss",
                random_state=42,
            )
        self.model.fit(X_scaled, y_train)

        if self.model_type == "xgboost":
            import shap
            self.explainer = shap.TreeExplainer(self.model)

        return self

    def predict(self, X: pd.DataFrame) -> Tuple[str, float]:
        X_scaled = self.scaler.transform(X)
        pred_idx = int(self.model.predict(X_scaled)[0])
        proba = self.model.predict_proba(X_scaled)[0]
        band = self.class_names[pred_idx] if pred_idx < len(self.class_names) else "P16+"
        confidence = round(float(max(proba)), 4)
        return band, confidence

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path / "model.joblib")
        joblib.dump(self.scaler, path / "scaler.joblib")
        with open(path / "feature_names.json", "w") as f:
            json.dump(self.feature_names, f)
        if self.explainer is not None:
            joblib.dump(self.explainer, path / "shap_explainer.joblib")

    @classmethod
    def load(cls, path: Path) -> "FinishPositionModel":
        instance = cls()
        instance.model = joblib.load(path / "model.joblib")
        instance.scaler = joblib.load(path / "scaler.joblib")
        with open(path / "feature_names.json") as f:
            instance.feature_names = json.load(f)
        explainer_path = path / "shap_explainer.joblib"
        if explainer_path.exists():
            instance.explainer = joblib.load(explainer_path)
        return instance
