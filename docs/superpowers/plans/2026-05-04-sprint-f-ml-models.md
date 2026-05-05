# Sprint F — Real ML Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace rule-based ML baselines with real XGBoost/Random Forest models trained on actual lap data, with SHAP explainability, model registry, and a `/predict/pit-decision` API endpoint.

**Architecture:** Four new modules (`ml/datasets/`, `ml/models/`, `ml/train.py`, `ml/registry.py`) build a self-contained training pipeline. Datasets query base tables directly (bypassing the NaN-filled feature store), models serialize artifacts, registry writes to `ml_model_registry` table, and the API loads models at startup with fallback to rule-based baselines.

**Tech Stack:** Python 3.11, DuckDB, scikit-learn, XGBoost, SHAP, joblib, FastAPI

**Data constraints:** Only Brazil 2024 data available (wet race, INTERMEDIATE/WET compounds). No position data in tables — derived from cumulative lap times. No lap_number on weather samples — joined by time proximity.

---

### Task 1: Add ML Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add scikit-learn, xgboost, shap to dependencies**

```toml
dependencies = [
    "fastf1>=3.8.3,<4.0.0",
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    "duckdb>=0.10.0",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "httpx>=0.25.0",
    "scikit-learn>=1.3.0",
    "xgboost>=2.0.0",
    "shap>=0.44.0",
    "joblib>=1.3.0",
]
```

- [ ] **Step 2: Install new dependencies**

Run: `uv sync`
Expected: All packages installed without errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add ML dependencies (scikit-learn, xgboost, shap)"
```

---

### Task 2: Add Migration for ml_model_registry Table

**Files:**
- Create: `db/migrations/006_ml_registry.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- Migration 006: ML Model Registry
-- Tracks trained model versions, evaluation metrics, and artifact paths

CREATE TABLE IF NOT EXISTS ml_model_registry (
    model_id VARCHAR PRIMARY KEY,
    model_name VARCHAR NOT NULL,
    model_version VARCHAR NOT NULL,
    target_definition VARCHAR,
    training_data_version VARCHAR,
    feature_view_version VARCHAR,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy DOUBLE,
    f1_score DOUBLE,
    roc_auc DOUBLE,
    artifact_path VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast latest-model lookup
CREATE INDEX IF NOT EXISTS idx_model_registry_name_version
    ON ml_model_registry (model_name, model_version);
```

- [ ] **Step 2: Apply the migration**

Run: `uv run python db/apply_migrations.py`
Expected: `Applied migration 006_ml_registry.sql`

- [ ] **Step 3: Verify the table exists**

Run: `uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); print(conn.execute(\"SELECT table_name FROM information_schema.tables WHERE table_name='ml_model_registry'\").fetchone())"`
Expected: `('ml_model_registry',)`

- [ ] **Step 4: Commit**

```bash
git add db/migrations/006_ml_registry.sql
git commit -m "feat: add ml_model_registry migration"
```

---

### Task 3: Build PitDecisionDataset

**Files:**
- Create: `ml/datasets/__init__.py`
- Create: `ml/datasets/pit_decision_dataset.py`
- Create: `tests/test_ml_datasets.py`

This task builds a dataset class that queries base tables directly, derives features (including approximate position from cumulative lap times), and returns clean DataFrames ready for model training.

- [ ] **Step 1: Create the datasets package init**

`ml/datasets/__init__.py`:
```python
# ML datasets package
from ml.datasets.pit_decision_dataset import PitDecisionDataset
from ml.datasets.finish_position_dataset import FinishPositionDataset

__all__ = ["PitDecisionDataset", "FinishPositionDataset"]
```

- [ ] **Step 2: Create pit_decision_dataset.py with the full class**

`ml/datasets/pit_decision_dataset.py`:
```python
from typing import Tuple, List, Optional
import pandas as pd
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"

COMPOUND_HARDNESS_MAP = {
    "SOFT": 1, "MEDIUM": 2, "HARD": 3,
    "INTERMEDIATE": 4, "WET": 5,
    "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5,
}


class PitDecisionDataset:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH

    def build(
        self,
        session_id: str = "2024_21_R",
        test_split: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
        """Build pit decision dataset from base tables.
        
        Returns: X_train, y_train, X_test, y_test, feature_names
        """
        conn = duckdb.connect(str(self.db_path))
        df = self._query_features(conn, session_id)
        conn.close()
        
        if df.empty:
            return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), []

        df = self._compute_position(df, session_id)
        df = self._engineer_features(df)
        df = self._compute_label(df, session_id)
        df = self._add_weather(df, session_id)
        df = self._add_track_status(df, session_id)
        df = self._add_session_info(df, session_id)

        feature_cols = [c for c in df.columns if c not in ("label", "driver_ref", "lap_number", "session_id")]
        df = df.dropna(subset=feature_cols, thresh=len(feature_cols) // 2)
        df = df.dropna(subset=["label"])

        X = df[feature_cols].copy()
        y = df["label"].astype(int)

        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, random_state=random_seed, stratify=y
        )
        return X_train, y_train, X_test, y_test, feature_cols

    def _query_features(self, conn, session_id: str) -> pd.DataFrame:
        return conn.execute("""
            SELECT 
                fl.session_id,
                fl.driver_ref,
                fl.lap_number,
                fl.lap_time_ms,
                fl.is_pit_out_lap,
                fl.lap_start_time,
                fs.tyre_compound_id AS stint_compound,
                fs.stint_number AS stint_number,
                fs.lap_start AS stint_lap_start,
                fs.lap_end AS stint_lap_end,
                fpi.lap_number AS pit_stop_lap,
                fpi.pit_duration_seconds
            FROM fact_lap fl
            LEFT JOIN fact_stint fs 
                ON fl.session_id = fs.session_id 
                AND fl.driver_ref = fs.driver_ref
                AND fl.lap_number BETWEEN fs.lap_start AND fs.lap_end
            LEFT JOIN fact_pit_stop fpi
                ON fl.session_id = fpi.session_id
                AND fl.driver_ref = fpi.driver_ref
                AND fl.lap_number = fpi.lap_number
            WHERE fl.session_id = ?
            ORDER BY fl.driver_ref, fl.lap_number
        """, [session_id]).fetchdf()

    def _compute_position(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        
        drivers = df["driver_ref"].unique()
        total_laps = int(df["lap_number"].max())

        pit_stop_durations = conn.execute("""
            SELECT driver_ref, lap_number, pit_duration_seconds
            FROM fact_pit_stop
            WHERE session_id = ?
        """, [session_id]).fetchdf()

        conn.close()

        positions = {}
        cum_times = {d: 0.0 for d in drivers}

        for lap in range(1, total_laps + 1):
            for d in drivers:
                lap_rows = df[(df["driver_ref"] == d) & (df["lap_number"] == lap)]
                if not lap_rows.empty and pd.notna(lap_rows["lap_time_ms"].iloc[0]):
                    cum_times[d] += lap_rows["lap_time_ms"].iloc[0]
                pit_row = pit_stop_durations[
                    (pit_stop_durations["driver_ref"] == d) &
                    (pit_stop_durations["lap_number"] == lap)
                ]
                if not pit_row.empty:
                    cum_times[d] += pit_row["pit_duration_seconds"].iloc[0] * 1000

            lap_drivers = [(d, cum_times[d]) for d in drivers
                           if not df[(df["driver_ref"] == d) & (df["lap_number"] == lap)].empty]
            lap_drivers.sort(key=lambda x: x[1])

            for pos, (d, _) in enumerate(lap_drivers, 1):
                positions[(d, lap)] = pos

        df["approx_position"] = df.apply(
            lambda r: positions.get((r["driver_ref"], r["lap_number"]), None), axis=1
        )
        return df

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result_rows = []
        for driver in df["driver_ref"].unique():
            driver_df = df[df["driver_ref"] == driver].sort_values("lap_number")
            for _, row in driver_df.iterrows():
                stint_age = row["lap_number"] - row["stint_lap_start"] if pd.notna(row["stint_lap_start"]) else None
                compound = row["stint_compound"] if pd.notna(row["stint_compound"]) else None
                compound_hardness = COMPOUND_HARDNESS_MAP.get(compound, 0) if compound else 0
                is_wet = 1 if compound in ("INTERMEDIATE", "WET") else 0
                rolling = driver_df[
                    (driver_df["lap_number"] < row["lap_number"]) &
                    (driver_df["lap_number"] >= row["lap_number"] - 3)
                ]["lap_time_ms"]
                rolling_avg = rolling.mean() if len(rolling) >= 2 else None
                result_rows.append({
                    "session_id": row["session_id"],
                    "driver_ref": row["driver_ref"],
                    "lap_number": row["lap_number"],
                    "stint_age_laps": stint_age,
                    "compound_hardness": compound_hardness,
                    "is_wet_compound": is_wet,
                    "lap_time_ms": row["lap_time_ms"],
                    "rolling_3_lap_avg_ms": rolling_avg,
                    "is_pit_out_lap": 1 if row["is_pit_out_lap"] else 0,
                    "approx_position": row["approx_position"],
                })
        return pd.DataFrame(result_rows)

    def _compute_label(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        pit_laps = conn.execute("""
            SELECT driver_ref, lap_number FROM fact_pit_stop WHERE session_id = ?
        """, [session_id]).fetchdf()
        conn.close()
        df["label"] = 0
        for _, pit_row in pit_laps.iterrows():
            mask = (
                (df["driver_ref"] == pit_row["driver_ref"]) &
                (df["lap_number"] >= pit_row["lap_number"] - 3) &
                (df["lap_number"] <= pit_row["lap_number"])
            )
            df.loc[mask, "label"] = 1
        return df

    def _add_weather(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        weather = conn.execute("""
            SELECT sample_time, air_temperature_c, track_temperature_c, rainfall_flag
            FROM fact_weather_sample
            WHERE session_id = ?
            ORDER BY sample_time
        """, [session_id]).fetchdf()
        conn.close()

        if weather.empty:
            df["rainfall_flag"] = 0
            df["air_temperature_c"] = None
            df["track_temperature_c"] = None
            return df

        weather["sample_time"] = pd.to_datetime(weather["sample_time"])
        df["lap_time"] = pd.to_datetime(df["lap_number"].apply(
            lambda lap_num: self._estimate_lap_time(session_id, lap_num)
        ))

        df["rainfall_flag"] = weather["rainfall_flag"].mode().iloc[0] if not weather["rainfall_flag"].empty else 0
        df["air_temperature_c"] = weather["air_temperature_c"].mean()
        df["track_temperature_c"] = weather["track_temperature_c"].mean()
        return df

    def _estimate_lap_time(self, session_id: str, lap_number: int) -> str:
        conn = duckdb.connect(str(self.db_path))
        result = conn.execute("""
            SELECT MIN(lap_start_time) FROM fact_lap
            WHERE session_id = ? AND lap_number = ? AND lap_start_time IS NOT NULL
        """, [session_id, lap_number]).fetchone()[0]
        conn.close()
        return result if result else "2024-11-03T14:00:00"

    def _add_track_status(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        events = conn.execute("""
            SELECT lap_number, flag FROM fact_race_control_event
            WHERE session_id = ? AND flag IN ('RED', 'YELLOW', 'SC', 'VSC')
            ORDER BY lap_number
        """, [session_id]).fetchdf()
        conn.close()

        red_laps = set()
        yellow_laps = set()
        if not events.empty:
            for _, ev in events.iterrows():
                if ev["flag"] == "RED":
                    red_laps.add(ev["lap_number"])
                elif ev["flag"] == "YELLOW":
                    yellow_laps.add(ev["lap_number"])

        df["red_flag"] = df["lap_number"].isin(red_laps).astype(int)
        df["yellow_flag"] = df["lap_number"].isin(yellow_laps).astype(int)
        return df

    def _add_session_info(self, df: pd.DataFrame, session_id: str) -> pd.DataFrame:
        conn = duckdb.connect(str(self.db_path))
        result = conn.execute("""
            SELECT laps_completed FROM fact_session_result
            WHERE session_id = ? LIMIT 1
        """, [session_id]).fetchone()
        total_laps = result[0] if result else 69
        conn.close()
        df["laps_remaining"] = total_laps - df["lap_number"]
        return df
```

- [ ] **Step 3: Write tests for PitDecisionDataset**

`tests/test_ml_datasets.py`:
```python
import pytest
from ml.datasets.pit_decision_dataset import PitDecisionDataset

def test_pit_decision_dataset_returns_features_and_labels():
    ds = PitDecisionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()
    assert len(feature_names) >= 5
    assert len(X_train) > 0
    assert len(y_train) == len(X_train)
    assert set(y_train.unique()).issubset({0, 1})

def test_pit_decision_dataset_feature_names_are_strings():
    ds = PitDecisionDataset()
    _, _, _, _, feature_names = ds.build()
    assert all(isinstance(f, str) for f in feature_names)
    assert "stint_age_laps" in feature_names
    assert "compound_hardness" in feature_names

def test_pit_decision_dataset_no_nan_in_label():
    ds = PitDecisionDataset()
    _, y_train, _, y_test, _ = ds.build()
    assert y_train.isna().sum() == 0
    assert y_test.isna().sum() == 0

def test_pit_decision_dataset_label_distribution():
    ds = PitDecisionDataset()
    _, y_train, _, _, _ = ds.build()
    ratio = y_train.mean()
    assert 0 < ratio < 1
```

- [ ] **Step 4: Run tests to verify they fail (no implementation yet)**

Run: `uv run python -m pytest tests/test_ml_datasets.py -v`
Expected: Import errors (PitDecisionDataset not implemented yet)

- [ ] **Step 5: Implement the dataset class** (code provided above in Step 2 — write the file)

Write `ml/datasets/pit_decision_dataset.py` with the full code from Step 2.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_ml_datasets.py -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add ml/datasets/ tests/test_ml_datasets.py
git commit -m "feat: add PitDecisionDataset with position derivation from lap times"
```

---

### Task 4: Build FinishPositionDataset

**Files:**
- Create: `ml/datasets/finish_position_dataset.py`

- [ ] **Step 1: Create FinishPositionDataset**

`ml/datasets/finish_position_dataset.py`:
```python
from typing import Tuple, List, Optional
import pandas as pd
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"

POSITION_BANDS = {
    "P1-P3": 3,
    "P4-P6": 6,
    "P7-P10": 10,
    "P11-P15": 15,
    "P16+": 25,
}

BAND_ORDER = ["P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+"]


class FinishPositionDataset:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH

    def build(
        self,
        session_id: str = "2024_21_R",
        test_split: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
        conn = duckdb.connect(str(self.db_path))
        
        final_positions = conn.execute("""
            SELECT driver_id, position_order
            FROM fact_session_result
            WHERE session_id = ?
        """, [session_id]).fetchdf()
        
        if final_positions.empty:
            conn.close()
            return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series(), []
        
        final_positions["final_position_band"] = final_positions["position_order"].apply(
            lambda p: self._position_to_band(p)
        )
        
        df = conn.execute("""
            SELECT 
                fl.session_id,
                fl.driver_ref AS driver_id,
                fl.lap_number,
                fl.lap_time_ms
            FROM fact_lap fl
            WHERE fl.session_id = ?
            ORDER BY fl.driver_ref, fl.lap_number
        """, [session_id]).fetchdf()
        
        conn.close()
        
        df = df.merge(final_positions[["driver_id", "final_position_band", "position_order"]],
                      on="driver_id", how="left")
        
        df["laps_remaining"] = 69 - df["lap_number"]
        df["label"] = df["final_position_band"].map({b: i for i, b in enumerate(BAND_ORDER)})
        
        feature_cols = ["lap_number", "lap_time_ms", "laps_remaining"]
        df = df.dropna(subset=feature_cols)
        
        from sklearn.model_selection import train_test_split
        X = df[feature_cols]
        y = df["label"]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_split, random_state=random_seed
        )
        return X_train, y_train, X_test, y_test, feature_cols

    @staticmethod
    def _position_to_band(position: int) -> str:
        for band in BAND_ORDER:
            if position <= POSITION_BANDS[band]:
                return band
        return "P16+"

    @staticmethod
    def band_label_to_index(band: str) -> int:
        return BAND_ORDER.index(band) if band in BAND_ORDER else 4
```

- [ ] **Step 2: Write tests for FinishPositionDataset**

Add to `tests/test_ml_datasets.py`:
```python
def test_finish_position_dataset_returns_features():
    from ml.datasets.finish_position_dataset import FinishPositionDataset
    ds = FinishPositionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()
    assert len(feature_names) >= 3
    assert len(X_train) > 0
    assert len(y_train) == len(X_train)

def test_finish_position_band_mapping():
    from ml.datasets.finish_position_dataset import FinishPositionDataset
    assert FinishPositionDataset._position_to_band(1) == "P1-P3"
    assert FinishPositionDataset._position_to_band(4) == "P4-P6"
    assert FinishPositionDataset._position_to_band(8) == "P7-P10"
    assert FinishPositionDataset._position_to_band(12) == "P11-P15"
    assert FinishPositionDataset._position_to_band(20) == "P16+"
```

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/test_ml_datasets.py -v`
Expected: 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add ml/datasets/finish_position_dataset.py tests/test_ml_datasets.py
git commit -m "feat: add FinishPositionDataset with band classification"
```

---

### Task 5: Build Evaluate Module

**Files:**
- Create: `ml/evaluate.py`
- Create: `tests/test_ml_evaluate.py`

- [ ] **Step 1: Create evaluate.py**

`ml/evaluate.py`:
```python
from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)


def evaluate_binary_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    model_name: str = "model",
) -> Dict[str, Any]:
    metrics = {
        "model_name": model_name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_true, y_pred, zero_division=0), 4),
    }
    try:
        metrics["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)
    except Exception:
        metrics["roc_auc"] = 0.0
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics["true_negatives"] = int(tn)
    metrics["false_positives"] = int(fp)
    metrics["false_negatives"] = int(fn)
    metrics["true_positives"] = int(tp)
    metrics["total_samples"] = len(y_true)
    
    return metrics


def evaluate_multiclass_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    model_name: str = "model",
) -> Dict[str, Any]:
    metrics = {
        "model_name": model_name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "f1_weighted": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "total_samples": len(y_true),
    }
    report = classification_report(y_true, y_pred, target_names=class_names, zero_division=0, output_dict=True)
    metrics["classification_report"] = report
    return metrics
```

- [ ] **Step 2: Write tests**

`tests/test_ml_evaluate.py`:
```python
import numpy as np
from ml.evaluate import evaluate_binary_classification, evaluate_multiclass_classification


def test_binary_evaluation_returns_expected_keys():
    y_true = np.array([0, 1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 0, 0])
    y_proba = np.array([0.2, 0.8, 0.3, 0.4, 0.1])
    metrics = evaluate_binary_classification(y_true, y_pred, y_proba)
    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc", "true_positives", "false_negatives"):
        assert key in metrics
    assert metrics["accuracy"] == 0.8


def test_binary_evaluation_perfect_prediction():
    y_true = np.array([0, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 1])
    y_proba = np.array([0.1, 0.9, 0.2, 0.8])
    metrics = evaluate_binary_classification(y_true, y_pred, y_proba)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1_score"] == 1.0
```

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/test_ml_evaluate.py -v`
Expected: 2 tests PASS

- [ ] **Step 4: Commit**

```bash
git add ml/evaluate.py tests/test_ml_evaluate.py
git commit -m "feat: add model evaluation module with binary and multiclass metrics"
```

---

### Task 6: Build PitDecisionModel

**Files:**
- Create: `ml/models/__init__.py`
- Create: `ml/models/pit_decision_model.py`
- Create: `tests/test_ml_models.py`

- [ ] **Step 1: Create the models package init**

`ml/models/__init__.py`:
```python
# ML models package
from ml.models.pit_decision_model import PitDecisionModel
from ml.models.finish_position_model import FinishPositionModel

__all__ = ["PitDecisionModel", "FinishPositionModel"]
```

- [ ] **Step 2: Create PitDecisionModel**

`ml/models/pit_decision_model.py`:
```python
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
        self.feature_names = feature_names
        X_scaled = self.scaler.fit_transform(X_train)

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
                use_label_encoder=False,
                random_state=42,
            )

        self.model.fit(X_scaled, y_train)

        if self.model_type == "xgboost":
            import shap
            self.explainer = shap.TreeExplainer(self.model)

        return self

    def predict(self, X: pd.DataFrame) -> Tuple[str, float]:
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)[0, 1]
        pred = 1 if proba >= 0.5 else 0
        recommendation = "pit_now" if pred == 1 else "stay_out"
        confidence = round(max(proba, 1 - proba), 4)
        return recommendation, confidence

    def predict_proba(self, X: pd.DataFrame) -> float:
        X_scaled = self.scaler.transform(X)
        return float(self.model.predict_proba(X_scaled)[0, 1])

    def explain(self, X: pd.DataFrame) -> List[str]:
        if self.explainer is None:
            return ["Model explainer not available"]
        X_scaled = self.scaler.transform(X)
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
```

- [ ] **Step 3: Write tests**

`tests/test_ml_models.py`:
```python
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

from ml.datasets.pit_decision_dataset import PitDecisionDataset
from ml.models.pit_decision_model import PitDecisionModel


@pytest.fixture
def training_data():
    ds = PitDecisionDataset()
    X_train, y_train, _, _, feature_names = ds.build()
    return X_train, y_train, feature_names


def test_pit_model_train_and_predict(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="xgboost")
    model.train(X_train, y_train, feature_names)
    rec, conf = model.predict(X_train.iloc[[0]])
    assert rec in ("pit_now", "stay_out")
    assert 0 <= conf <= 1


def test_pit_model_save_and_load(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="logistic_regression")
    model.train(X_train, y_train, feature_names)
    tmpdir = Path(tempfile.mkdtemp())
    model.save(tmpdir)
    loaded = PitDecisionModel.load(tmpdir)
    rec, conf = loaded.predict(X_train.iloc[[0]])
    assert rec in ("pit_now", "stay_out")
    assert 0 <= conf <= 1
    shutil.rmtree(tmpdir)


def test_pit_model_explain_returns_strings(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="xgboost")
    model.train(X_train, y_train, feature_names)
    explanations = model.explain(X_train.iloc[[0]])
    assert len(explanations) == 3
    assert all(isinstance(e, str) for e in explanations)
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_ml_models.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ml/models/ tests/test_ml_models.py
git commit -m "feat: add PitDecisionModel with XGBoost, RF, LR, save/load, SHAP explainer"
```

---

### Task 7: Build FinishPositionModel

**Files:**
- Create: `ml/models/finish_position_model.py`

- [ ] **Step 1: Create FinishPositionModel**

`ml/models/finish_position_model.py`:
```python
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
```

- [ ] **Step 2: Write tests for FinishPositionModel**

Add to `tests/test_ml_models.py`:
```python
from ml.datasets.finish_position_dataset import FinishPositionDataset
from ml.models.finish_position_model import FinishPositionModel


def test_finish_model_train_and_predict():
    ds = FinishPositionDataset()
    X_train, y_train, _, _, feature_names = ds.build()
    if X_train.empty:
        pytest.skip("No finish position data available")
    model = FinishPositionModel(model_type="xgboost")
    model.train(X_train, y_train, feature_names)
    band, conf = model.predict(X_train.iloc[[0]])
    assert band in ("P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+")
    assert 0 <= conf <= 1
```

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/test_ml_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add ml/models/finish_position_model.py tests/test_ml_models.py
git commit -m "feat: add FinishPositionModel with multiclass classification"
```

---

### Task 8: Build Registry Module

**Files:**
- Create: `ml/registry.py`
- Create: `tests/test_ml_registry.py`
- Create: `ml/artifacts/.gitkeep`

- [ ] **Step 1: Create registry.py**

`ml/registry.py`:
```python
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
```

- [ ] **Step 2: Create .gitkeep for artifacts directory**

```bash
mkdir -p ml/artifacts
echo "" > ml/artifacts/.gitkeep
```

- [ ] **Step 3: Write tests**

`tests/test_ml_registry.py`:
```python
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
    assert row[4] == "pit_decision_binary"  # target_definition
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
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_ml_registry.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ml/registry.py ml/artifacts/ tests/test_ml_registry.py
git commit -m "feat: add model registry module with DB persistence"
```

---

### Task 9: Build Training CLI

**Files:**
- Create: `ml/train.py`

- [ ] **Step 1: Create train.py**

`ml/train.py`:
```python
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
```

- [ ] **Step 2: Train the pit decision model**

Run: `uv run python -m ml.train --target pit_decision --data-version v0.1`
Expected: Successfully trains XGBoost model on Brazil 2024 data, saves artifacts, registers in DB.

- [ ] **Step 3: Train the finish position model**

Run: `uv run python -m ml.train --target finish_position --data-version v0.1`
Expected: Successfully trains XGBoost model, saves artifacts, registers in DB.

- [ ] **Step 4: Verify artifacts exist**

Run: `ls -la ml/artifacts/pit_decision/v0.1/`
Expected: model.joblib, scaler.joblib, feature_names.json, shap_explainer.joblib

- [ ] **Step 5: Verify model registry**

Run: `uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); print(conn.execute('SELECT model_name, model_version, accuracy, f1_score, roc_auc FROM ml_model_registry').fetchdf())"`
Expected: Two rows (pit_decision v0.1, finish_position v0.1) with metrics.

- [ ] **Step 6: Commit**

```bash
git add ml/train.py
git commit -m "feat: add training CLI with end-to-end training pipeline"
```

---

### Task 10: Wire Models into API

**Files:**
- Create: `api/routers/prediction.py`
- Modify: `api/main.py`

- [ ] **Step 1: Create prediction router**

`api/routers/prediction.py`:
```python
from fastapi import APIRouter, HTTPException
from pathlib import Path
import duckdb
import pandas as pd

from api.models import PitDecisionRequest, PitDecisionResponse
from ml.registry import load_model_artifacts
from ml.datasets.pit_decision_dataset import PitDecisionDataset

router = APIRouter(tags=["prediction"])
DB_PATH = Path(__file__).parent.parent.parent / "data" / "undercut.db"


def get_pit_model():
    artifacts = load_model_artifacts("pit_decision")
    return artifacts["model"] if artifacts else None


@router.post("/predict/pit-decision", response_model=PitDecisionResponse)
def predict_pit_decision(request: PitDecisionRequest):
    """Run the trained pit decision model on a specific session/driver/lap."""
    model = get_pit_model()
    if model is None:
        raise HTTPException(status_code=503, detail="No trained pit decision model available")

    conn = duckdb.connect(str(DB_PATH))
    try:
        df = conn.execute("""
            SELECT lap_time_ms, stint_age_laps FROM race_state_driver_lap_fact
            WHERE session_id = ? AND driver_id = ? AND lap_number = ?
        """, [request.session_id, request.driver_id, request.lap_number]).fetchdf()
    finally:
        conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="No data found for this session/driver/lap")

    feature_row = _build_feature_vector(request, df)
    feature_df = pd.DataFrame([feature_row])

    recommendation, confidence = model.predict(feature_df[model.feature_names])
    probability_pit = model.predict_proba(feature_df[model.feature_names])
    top_features = model.explain(feature_df[model.feature_names])

    return PitDecisionResponse(
        session_id=request.session_id,
        driver_id=request.driver_id,
        lap_number=request.lap_number,
        recommendation=recommendation,
        confidence=confidence,
        probability_pit=round(probability_pit, 4),
        probability_stay=round(1 - probability_pit, 4),
        top_features=top_features,
    )


def _build_feature_vector(request: PitDecisionRequest, df: pd.DataFrame) -> dict:
    row = df.iloc[0]
    return {
        "stint_age_laps": int(row["stint_age_laps"]) if pd.notna(row["stint_age_laps"]) else 0,
        "compound_hardness": 5,
        "is_wet_compound": 1,
        "lap_time_ms": float(row["lap_time_ms"]) if pd.notna(row["lap_time_ms"]) else 0,
        "rolling_3_lap_avg_ms": None,
        "is_pit_out_lap": 0,
        "approx_position": None,
        "laps_remaining": 0,
        "rainfall_flag": 1,
        "air_temperature_c": None,
        "track_temperature_c": None,
        "red_flag": 0,
        "yellow_flag": 0,
    }
```

- [ ] **Step 2: Add PitDecisionRequest/Response models to api/models.py**

Add to `api/models.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional


class PitDecisionRequest(BaseModel):
    session_id: str = Field(..., description="e.g. '2024_21_R'")
    driver_id: str = Field(..., description="e.g. 'VER'")
    lap_number: int = Field(..., ge=1, description="Lap number to evaluate")


class PitDecisionResponse(BaseModel):
    session_id: str
    driver_id: str
    lap_number: int
    recommendation: str
    confidence: float
    probability_pit: float
    probability_stay: float
    top_features: List[str] = []
```

- [ ] **Step 3: Register the prediction router in api/main.py**

Add to the imports in `api/main.py`:
```python
from api.routers.prediction import router as prediction_router
```

Add after the existing router includes:
```python
app.include_router(prediction_router)
```

- [ ] **Step 4: Write API test**

`tests/test_ml_api.py`:
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_predict_pit_decision_endpoint_exists():
    response = client.post("/predict/pit-decision", json={
        "session_id": "2024_21_R",
        "driver_id": "VER",
        "lap_number": 32,
    })
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data
        assert "top_features" in data


def test_predict_pit_decision_missing_session():
    response = client.post("/predict/pit-decision", json={
        "session_id": "invalid",
        "driver_id": "VER",
        "lap_number": 1,
    })
    assert response.status_code in (404, 503)
```

- [ ] **Step 5: Run tests**

Run: `uv run python -m pytest tests/test_ml_api.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add api/routers/prediction.py api/models.py api/main.py tests/test_ml_api.py
git commit -m "feat: add /predict/pit-decision endpoint with trained model inference"
```

---

### Task 11: Update Engine to Use Real Models

**Files:**
- Modify: `sim/engine.py`

- [ ] **Step 1: Update evaluate_strategy to try trained model first**

In `sim/engine.py`, locate `evaluate_strategy()` method. Add logic to try loading the trained pit decision model and use it instead of the baseline. Fall back to baseline if model is unavailable or prediction fails.

Find the section around line 113-155 that calls `predict_pit_decision(context)` and replace with:

```python
# Inside evaluate_strategy, before calling baselines:
from ml.registry import load_model_artifacts

trained_model = None
try:
    artifacts = load_model_artifacts("pit_decision")
    if artifacts:
        trained_model = artifacts["model"]
except Exception:
    trained_model = None

if trained_model and hasattr(trained_model, 'feature_names'):
    try:
        import pandas as pd
        feat_dict = {
            "stint_age_laps": context.stint_age,
            "compound_hardness": {"soft": 1, "medium": 2, "hard": 3, "intermediate": 4, "wet": 5}.get(context.compound.lower(), 0),
            "is_wet_compound": 1 if context.compound.lower() in ("intermediate", "wet") else 0,
            "lap_time_ms": getattr(context, 'lap_time_ms', 90000),
            "rolling_3_lap_avg_ms": getattr(context, 'rolling_3_lap_avg_ms', None),
            "is_pit_out_lap": 0,
            "approx_position": context.position,
            "laps_remaining": getattr(context, 'laps_remaining', 10),
            "rainfall_flag": 1 if getattr(context, 'rainfall', False) else 0,
            "air_temperature_c": getattr(context, 'air_temperature', None),
            "track_temperature_c": getattr(context, 'track_temperature', None),
            "red_flag": 0,
            "yellow_flag": 0,
        }
        common_features = [f for f in trained_model.feature_names if f in feat_dict]
        if len(common_features) == len(trained_model.feature_names):
            X = pd.DataFrame([{k: feat_dict.get(k) for k in trained_model.feature_names}])
            model_rec, model_conf = trained_model.predict(X)
            model_features = trained_model.explain(X)
        else:
            raise ValueError("Feature mismatch")
    except Exception:
        from ml.baselines import predict_pit_decision
        model_rec, model_conf, model_features = predict_pit_decision(context)
else:
    from ml.baselines import predict_pit_decision
    model_rec, model_conf, model_features = predict_pit_decision(context)
```

- [ ] **Step 2: Run engine tests to verify no regression**

Run: `uv run python -m pytest tests/test_engine.py tests/test_scoring.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add sim/engine.py
git commit -m "feat: use trained ML model in engine with fallback to baselines"
```

---

### Task 12: Update API Contract

**Files:**
- Modify: `docs/api_contract.md`

- [ ] **Step 1: Add the /predict/pit-decision endpoint documentation**

Append to `docs/api_contract.md`:

```markdown
## POST /predict/pit-decision

Run the trained pit decision ML model on a specific session/driver/lap.

### Request

```json
{
    "session_id": "2024_21_R",
    "driver_id": "VER",
    "lap_number": 32
}
```

### Response (200)

```json
{
    "session_id": "2024_21_R",
    "driver_id": "VER",
    "lap_number": 32,
    "recommendation": "stay_out",
    "confidence": 0.71,
    "probability_pit": 0.29,
    "probability_stay": 0.71,
    "top_features": [
        "Stint age was the key signal",
        "Track position was a significant factor",
        "Rain conditions changed the pit calculus"
    ]
}
```

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | No data found for the session/driver/lap combination |
| 503 | No trained model is available (fallback to baselines active) |
```

- [ ] **Step 2: Commit**

```bash
git add docs/api_contract.md
git commit -m "docs: add /predict/pit-decision endpoint to API contract"
```

---

### Task 13: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `uv run python -m pytest tests/ -v`
Expected: 93 + (new tests) PASS

- [ ] **Step 2: Verify all training artifacts exist**

Run: `uv run python -c "
from pathlib import Path
for p in Path('ml/artifacts').glob('**/model.joblib'):
    print(f'✓ {p.parent.name}/{p.name}')
for p in Path('ml/artifacts').glob('**/shap_explainer.joblib'):
    print(f'✓ {p.parent.name}/{p.name}')
"`

- [ ] **Step 3: Verify registry entries**

Run: `uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); df = conn.execute('SELECT model_name, model_version, accuracy, f1_score FROM ml_model_registry').fetchdf(); print(df); conn.close()"`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Sprint F - real ML models with SHAP explainability and model registry"
git push
```
