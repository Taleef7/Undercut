from fastapi import APIRouter, HTTPException
from pathlib import Path
import os
import duckdb
import pandas as pd

from api.models import PitDecisionRequest, PitDecisionResponse
from ml.registry import load_model_artifacts

router = APIRouter(tags=["prediction"])

ROOT = Path(__file__).parent.parent.parent
DB_PATH = Path(os.environ.get("DUCKDB_PATH", ROOT / "data" / "undercut.db"))

COMPOUND_HARDNESS_MAP = {
    "SOFT": 1, "MEDIUM": 2, "HARD": 3,
    "INTERMEDIATE": 4, "WET": 5,
}

MODEL_CACHE = {}


def _get_pit_model():
    if "pit_decision" in MODEL_CACHE:
        return MODEL_CACHE["pit_decision"]
    artifacts = load_model_artifacts("pit_decision")
    if artifacts is None:
        return None
    model = artifacts["model"]
    MODEL_CACHE["pit_decision"] = model
    return model


def _resolve_driver_number(session_id: str, driver_code: str) -> str:
    """Map a 3-letter driver code (e.g. 'VER') or number to the car number used in fact tables."""
    if driver_code.isdigit():
        return driver_code

    conn = duckdb.connect(str(DB_PATH))
    try:
        result = conn.execute("""
            SELECT DISTINCT fl.driver_ref
            FROM fact_lap fl
            JOIN dim_driver dd ON fl.driver_ref = CAST(dd.driver_number AS VARCHAR)
            WHERE fl.session_id = ? AND dd.code = ?
        """, [session_id, driver_code]).fetchone()
    finally:
        conn.close()

    if result:
        return str(result[0])

    return driver_code


def _build_feature_row(session_id: str, driver_id: str, lap_number: int) -> dict:
    car_number = _resolve_driver_number(session_id, driver_id)

    conn = duckdb.connect(str(DB_PATH))
    try:
        df = conn.execute("""
            SELECT stint_age_laps, lap_time_ms, current_compound_label
            FROM race_state_driver_lap_fact
            WHERE session_id = ? AND driver_id = ? AND lap_number = ?
        """, [session_id, car_number, lap_number]).fetchdf()
    finally:
        conn.close()

    if df.empty:
        return None

    row = df.iloc[0]

    compound = row.get("current_compound_label")
    if pd.isna(compound) or not compound:
        compound = "UNKNOWN"

    stint_age = int(row["stint_age_laps"]) if pd.notna(row["stint_age_laps"]) else 0
    lap_time = float(row["lap_time_ms"]) if pd.notna(row["lap_time_ms"]) else 90000.0

    return {
        "stint_age_laps": stint_age,
        "compound_hardness": COMPOUND_HARDNESS_MAP.get(compound, 3),
        "is_wet_compound": 1 if compound in ("INTERMEDIATE", "WET") else 0,
        "lap_time_ms": lap_time,
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


@router.post("/predict/pit-decision", response_model=PitDecisionResponse)
def predict_pit_decision(request: PitDecisionRequest):
    model = _get_pit_model()
    if model is None:
        raise HTTPException(status_code=503, detail="No trained pit decision model available")

    feat_dict = _build_feature_row(request.session_id, request.driver_id, request.lap_number)
    if feat_dict is None:
        raise HTTPException(status_code=404, detail="No data found for this session/driver/lap")

    common_features = [f for f in model.feature_names if f in feat_dict]
    if len(common_features) < len(model.feature_names):
        raise HTTPException(
            status_code=422,
            detail=f"Feature mismatch: model expects {model.feature_names}, got {list(feat_dict.keys())}",
        )

    X = pd.DataFrame([{k: feat_dict.get(k) for k in model.feature_names}])
    recommendation, confidence = model.predict(X)
    probability_pit = model.predict_proba(X)
    top_features = model.explain(X)

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
