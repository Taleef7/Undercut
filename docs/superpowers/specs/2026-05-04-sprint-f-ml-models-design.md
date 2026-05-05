# Sprint F — Real ML Models Design

**Date:** 2026-05-04
**Status:** Approved design

## Problem

The current ML layer uses rule-based baselines only (`ml/baselines.py`). The feature store tables (`feature_pit_decision`, `feature_undercut_opportunity`) contain 1,137 rows but most feature columns are NaN because the race state builder doesn't populate derived columns (positions, intervals, weather, compound hardness). We need real trained models with proper evaluation, SHAP explainability, model registry, and API integration.

## Approach

Build a self-contained training pipeline (`ml/datasets/`) that constructs training data **directly from base tables** (`fact_lap`, `fact_stint`, `fact_pit_stop`, `fact_driver_session_entry`, `fact_session_result`, `fact_race_control_event`, `fact_weather_sample`) rather than depending on the broken feature store. This gives us clean datasets now, and the feature store can be rebuilt to match the same feature definitions later.

## Design

### 1. Dataset Builders

#### `ml/datasets/__init__.py`
Package marker, exports `PitDecisionDataset` and `FinishPositionDataset`.

#### `ml/datasets/pit_decision_dataset.py`
Builds a binary classification dataset for the question: "Should this driver pit within the next 3 laps?"

**Query logic:**
- Joins `fact_lap` → `fact_stint` (for stint age, compound) → `fact_driver_session_entry` → `fact_session_result` (for final position) → `fact_pit_stop` (for label)
- Joins `fact_race_control_event` (for safety car / VSC / red flag flags at each lap)
- Joins `fact_weather_sample` (for rainfall, temperature at each lap via nearest-sample join)

**Features (12–15):**
| Feature | Source | Type |
|---------|--------|------|
| stint_age_laps | computed: lap_number - stint.lap_start | int |
| laps_remaining | computed: total_session_laps - lap_number | int |
| current_position | fact_lap.position | int |
| compound_hardness | mapped from compound label: soft=1, medium=2, hard=3, inter=4, wet=5 | int |
| lap_time_ms | fact_lap.lap_time_ms | float |
| rolling_3_lap_avg_ms | windowed avg over fact_lap for same driver | float |
| rolling_5_lap_avg_ms | windowed avg over fact_lap for same driver | float |
| pace_delta_to_field | driver rolling avg - field median rolling avg | float |
| safety_car_flag | 1 if SC active at this lap from race_control events | bool |
| vsc_flag | 1 if VSC active at this lap | bool |
| rainfall_flag | 1 if weather sample shows rain near this lap | bool |
| track_temperature | nearest weather sample | float |
| pit_stops_so_far | count of fact_pit_stop rows before this lap | int |
| gap_to_leader | fact_lap (fallback: null if unavailable) | float/null |

**Label:**
- `actual_pitted_within_3_laps`: 1 if `fact_pit_stop` exists for this driver in laps [lap_number, lap_number+3]

**Returns:** `pd.DataFrame` (features), `pd.Series` (labels), `List[str]` (feature names)

**Handling missing data:**
- Rows with >50% NaN features are dropped
- Rolling averages with insufficient window → NaN (not zero)
- Gap columns default to NaN (XGBoost handles natively)

#### `ml/datasets/finish_position_dataset.py`
Builds a multiclass classification dataset.

**Target:** `final_position_band` — binned from `fact_session_result.position_order`:
- P1-P3, P4-P6, P7-P10, P11-P15, P16+

**Features (8–10):**
- current_position, stint_age_laps, compound_hardness, laps_remaining
- rolling_3_lap_avg_ms, pace_delta_to_field_ms
- safety_car_flag, rainfall_flag
- gap_to_leader_seconds (optional)

**Label:** Join to final `fact_session_result.position_order` and bin.

### 2. Model Trainers

#### `ml/models/__init__.py`
Package marker.

#### `ml/models/pit_decision_model.py`

```python
class PitDecisionModel:
    def __init__(self, model_type="xgboost"):
        ...
    
    def train(self, X_train, y_train, feature_names):
        # Scale features
        # Train model (XGBoost or RandomForest)
        # Fit SHAP TreeExplainer
        pass
    
    def predict(self, X) -> Tuple[str, float]:
        # Returns (recommendation, confidence)
        pass
    
    def explain(self, X) -> List[str]:
        # Returns top 3 SHAP features as human-readable strings
        pass
    
    def save(self, path: str):
        # Save model.joblib, scaler.joblib, feature_names.json, shap_explainer.joblib
        pass
    
    @classmethod
    def load(cls, path: str) -> "PitDecisionModel":
        pass
```

**Training pipeline:**
1. Random split: 80/20 train/test
2. Scale features with `StandardScaler`
3. Train models in order:
   - Logistic Regression (baseline to beat)
   - Random Forest (100 trees, max_depth=10)
   - XGBoost (n_estimators=200, max_depth=6, learning_rate=0.1)
4. Optional: `GridSearchCV` with small grid
5. Evaluate on test set
6. Fit SHAP `TreeExplainer` on XGBoost

**Prediction threshold calibration:**
- Default threshold 0.5
- Returns `"pit_now"` if probability >= 0.5, `"stay_out"` otherwise
- Confidence = max(prob, 1-prob)

#### `ml/models/finish_position_model.py`
Same pattern but:
- Multiclass target (5 classes)
- XGBoost with `objective='multi:softprob'`
- SHAP TreeExplainer (multiclass)

### 3. Evaluation

#### `ml/evaluate.py`
```python
def evaluate_classification(y_true, y_pred, y_proba, class_names):
    """Return dict with accuracy, precision, recall, f1, roc_auc, confusion_matrix."""
    pass

def print_evaluation_report(metrics, model_name, target_name):
    """Pretty-print evaluation results."""
    pass
```

### 4. Model Registry

#### New migration `db/migrations/006_ml_registry.sql`
```sql
CREATE TABLE IF NOT EXISTS ml_model_registry (
    model_id VARCHAR PRIMARY KEY,
    model_name VARCHAR,
    model_version VARCHAR,
    target_definition VARCHAR,
    training_data_version VARCHAR,
    feature_view_version VARCHAR,
    training_date TIMESTAMP,
    accuracy DOUBLE,
    f1_score DOUBLE,
    roc_auc DOUBLE,
    artifact_path VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `ml/registry.py`
```python
def register_model(
    conn: duckdb.DuckDBPyConnection,
    model_name: str,
    model_version: str,
    target: str,
    data_version: str,
    metrics: dict,
    artifact_path: str,
    notes: str = ""
) -> str:
    """Insert a row into ml_model_registry, return model_id."""
    pass

def get_latest_model(conn, model_name: str) -> dict:
    """Return the latest registered model by created_at."""
    pass

def load_model_artifacts(model_name: str, version: str = "latest") -> dict:
    """Load model + scaler + feature_names + explainer from artifacts directory."""
    pass
```

**Artifact directory structure:**
```
ml/artifacts/
  pit_decision/
    v0.1/
      model.joblib
      scaler.joblib
      feature_names.json
      shap_explainer.joblib
      metrics.json
  finish_position/
    v0.1/
      model.joblib
      scaler.joblib
      feature_names.json
      shap_explainer.joblib
      metrics.json
```

### 5. CLI

#### `ml/train.py`
```bash
uv run python -m ml.train --target pit_decision --data-version v0.1
uv run python -m ml.train --target finish_position --data-version v0.1
```

**CLI flow:**
1. Build dataset (calls PitDecisionDataset or FinishPositionDataset)
2. Train/test split
3. Train model
4. Evaluate
5. Fit SHAP explainer
6. Save artifacts
7. Register in ml_model_registry

### 6. API Integration

#### Model loading at startup (`api/main.py`)
```python
# Try to load trained models, fall back to baselines
app.state.pit_model = try_load_model("pit_decision")
app.state.finish_model = try_load_model("finish_position")
```

#### `POST /predict/pit-decision`
New endpoint:
```python
@router.post("/predict/pit-decision")
def predict_pit_decision(request: PitDecisionRequest):
    """Direct ML model inference endpoint."""
    # Build feature vector for the given session/driver/lap
    # Run through trained model
    # Return recommendation, confidence, top SHAP features
```

Request body:
```json
{
    "session_id": "2024_21_R",
    "driver_id": "VER", 
    "lap_number": 32
}
```

Response:
```json
{
    "recommendation": "stay_out",
    "confidence": 0.71,
    "top_features": [
        "Stint age was the key signal",
        "Gap ahead reduced pit urgency",
        "Rain flag increased track position value"
    ],
    "probability_pit": 0.29,
    "probability_stay": 0.71
}
```

#### Engine integration (`sim/engine.py`)
- `evaluate_strategy()` tries trained model first
- Falls back to baselines if model not available or prediction fails
- Model recommendations + SHAP features returned in response

### 7. Tests

| File | Tests | Purpose |
|------|-------|---------|
| `tests/test_ml_datasets.py` | 6 | dataset returns correct shape, no NaN in features, label distribution, valid feature names |
| `tests/test_ml_models.py` | 4 | train/predict roundtrip, save/load, SHAP explain returns strings, confidence range [0,1] |
| `tests/test_ml_registry.py` | 4 | register model, read back, get latest, non-existent returns None |
| `tests/test_ml_api.py` | 3 | /predict/pit-decision returns correct shape, handles missing session, validates request |

## Files to Create

```
ml/__init__.py                          (exists, minimal)
ml/datasets/__init__.py                 (new)
ml/datasets/pit_decision_dataset.py     (new)
ml/datasets/finish_position_dataset.py  (new)
ml/models/__init__.py                   (new)
ml/models/pit_decision_model.py         (new)
ml/models/finish_position_model.py      (new)
ml/train.py                             (new)
ml/evaluate.py                          (new)
ml/registry.py                          (new)
db/migrations/006_ml_registry.sql       (new)
api/routers/prediction.py               (new)
tests/test_ml_datasets.py               (new)
tests/test_ml_models.py                 (new)
tests/test_ml_registry.py               (new)
tests/test_ml_api.py                    (new)
```

## Files to Modify

```
api/main.py             — add /predict/pit-decision router, model loading at startup
sim/engine.py           — try trained model before baseline in evaluate_strategy()
sim/scoring.py          — ensure model_top_features from real model passed through
docs/api_contract.md    — document new endpoint
```

## Key Design Decisions

1. **Self-contained datasets** — Build training data from base tables rather than fixing the feature store. The dataset builder becomes the canonical feature engineering reference.

2. **XGBoost over Random Forest** — XGBoost has native NaN handling, better performance, and SHAP TreeExplainer support. Random Forest is trained as a comparison baseline.

3. **Logistic Regression as floor** — Must beat logistic regression. If XGBoost doesn't outperform LR significantly, the features are likely insufficient.

4. **Fallback to baselines** — If model loading fails (file not found, version mismatch), the API silently falls back to rule-based baselines. No hard dependency on trained artifacts.

5. **Separate artifact directory** — `ml/artifacts/{model_name}/{version}/` keeps artifacts organized. Gitignore the artifacts but keep the directory structure.

## Out of Scope

- Feature store data quality fix (separate initiative)
- PyTorch / deep learning models
- Online training or model updates
- Tire degradation model (deferred to later sprint)
- Hyperparameter optimization at scale
