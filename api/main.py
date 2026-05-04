from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import duckdb
from pathlib import Path
from sim.engine import UndercutEngine
from sim.scoring import StrategyDecision, ScenarioContext
from sim.chaos import ChaosEngine, ChaosModifier
from api.models import (
    ScenarioSummary,
    ScenarioDetail,
    DecisionResponse,
    DecisionRequest,
    SimulationSummary,
    ChaosModifierRequest,
)

app = FastAPI(title="Undercut API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "undercut.db"


@app.get("/")
def read_root():
    return {"message": "Undercut API is running"}


@app.get("/scenarios", response_model=List[ScenarioSummary])
def get_scenarios():
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute("SELECT * FROM race_state_decision_point").fetchdf()
    conn.close()

    results = []
    for row in df.to_dict(orient="records"):
        results.append(
            ScenarioSummary(
                decision_point_id=row["decision_point_id"],
                scenario_title=row["scenario_title"],
                scenario_description=row["scenario_description"],
                driver_id=row["driver_id"],
                lap_number=int(row["lap_number"] or 0),
                decision_type=row["decision_type"],
                available_actions=json.loads(row["available_actions_json"]),
                difficulty_level=row.get("difficulty_level"),
            )
        )
    return results


@app.get("/scenarios/{decision_id}", response_model=ScenarioDetail)
def get_scenario(decision_id: str):
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?",
        (decision_id,),
    ).fetchdf()
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Scenario not found")

    row = df.to_dict(orient="records")[0]
    return ScenarioDetail(
        decision_point_id=row["decision_point_id"],
        scenario_title=row["scenario_title"],
        scenario_description=row["scenario_description"],
        driver_id=row["driver_id"],
        lap_number=int(row["lap_number"] or 0),
        decision_type=row["decision_type"],
        available_actions=json.loads(row["available_actions_json"]),
        difficulty_level=row.get("difficulty_level"),
        actual_decision=row["actual_decision"],
        actual_outcome_summary=row["actual_outcome_summary"],
        explanation_short=row["explanation_short"],
        explanation_long=row["explanation_long"],
        current_position=int(row.get("current_position") or 1),
        gap_ahead_seconds=row["gap_ahead_seconds"],
        gap_behind_seconds=row["gap_behind_seconds"],
        compound=row["compound"],
        stint_age_laps=int(row.get("stint_age_laps") or 0),
        laps_remaining=int(row.get("laps_remaining") or 0),
        track_temperature_c=row["track_temperature_c"],
        air_temperature_c=row["air_temperature_c"],
        rainfall=row["rainfall"],
        track_status=row["track_status"],
        safety_car_active=row["safety_car_active"],
        virtual_safety_car_active=row["virtual_safety_car_active"],
    )


@app.post("/scenarios/{decision_id}/decision", response_model=DecisionResponse)
def submit_decision(decision_id: str, request: DecisionRequest):
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?",
        (decision_id,),
    ).fetchdf()
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Scenario not found")

    row = df.to_dict(orient="records")[0]

    available_actions = json.loads(row["available_actions_json"])
    if request.action not in available_actions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{request.action}'. Available: {available_actions}",
        )

    gap_ahead = row["gap_ahead_seconds"]
    gap_behind = row["gap_behind_seconds"]
    if gap_ahead is None:
        gap_ahead = 0.0
    if gap_behind is None:
        gap_behind = 0.0

    context = ScenarioContext(
        driver=row["driver_id"],
        lap=int(row["lap_number"] or 0),
        position=int(row.get("current_position") or 1),
        compound=row["compound"],
        stint_age=int(row.get("stint_age_laps") or 0),
        gap_ahead=float(gap_ahead),
        gap_behind=float(gap_behind),
        laps_remaining=int(row.get("laps_remaining") or 0),
        safety_car_active=bool(row.get("safety_car_active", False)),
        virtual_safety_car_active=bool(row.get("virtual_safety_car_active", False)),
        rainfall=bool(row.get("rainfall", False)),
        track_status=str(row.get("track_status", "green") or "green"),
    )

    engine = UndercutEngine(circuit="interlagos")
    sim_result = engine.simulate_decision(
        StrategyDecision(action=request.action, compound=request.compound),
        context,
        row["actual_decision"],
    )

    score_data = engine.evaluate_strategy(
        StrategyDecision(action=request.action, compound=request.compound),
        context,
        row["actual_decision"],
    )

    return DecisionResponse(
        scenario_id=row["decision_point_id"],
        user_action=request.action,
        score=score_data["score"],
        grade=score_data["grade"],
        historical_decision=row["actual_decision"],
        model_recommendation=score_data["model_recommendation"],
        model_confidence=score_data.get("model_confidence"),
        model_top_features=score_data.get("model_top_features", []),
        simulation_summary=SimulationSummary(
            expected_position=sim_result.expected_position,
            expected_finish_position_band=score_data.get("expected_finish_position_band"),
            risk_score=sim_result.risk_score,
        ),
        explanation=score_data["explanation"],
        tradeoffs=[],
    )


@app.post("/scenarios/{decision_id}/chaos", response_model=DecisionResponse)
def submit_chaos_decision(decision_id: str, request: ChaosModifierRequest):
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?",
        (decision_id,),
    ).fetchdf()
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Scenario not found")

    row = df.to_dict(orient="records")[0]

    available_actions = json.loads(row["available_actions_json"])
    if request.action not in available_actions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{request.action}'. Available: {available_actions}",
        )

    gap_ahead = row["gap_ahead_seconds"]
    gap_behind = row["gap_behind_seconds"]
    if gap_ahead is None:
        gap_ahead = 0.0
    if gap_behind is None:
        gap_behind = 0.0

    context = ScenarioContext(
        driver=row["driver_id"],
        lap=int(row["lap_number"] or 0),
        position=int(row.get("current_position") or 1),
        compound=row["compound"],
        stint_age=int(row.get("stint_age_laps") or 0),
        gap_ahead=float(gap_ahead),
        gap_behind=float(gap_behind),
        laps_remaining=int(row.get("laps_remaining") or 0),
        safety_car_active=bool(row.get("safety_car_active", False)),
        virtual_safety_car_active=bool(row.get("virtual_safety_car_active", False)),
        rainfall=bool(row.get("rainfall", False)),
        track_status=str(row.get("track_status", "green") or "green"),
    )

    # Apply chaos modifiers
    chaos_engine = ChaosEngine(circuit="interlagos")
    modifiers = [
        ChaosModifier(
            modifier_type=m.get("modifier_type", ""),
            modifier_value=float(m.get("modifier_value", 0.0)),
        )
        for m in request.modifiers
    ]
    modified_context = chaos_engine.apply_modifiers(context, modifiers)

    # Run simulation with modified context
    engine = UndercutEngine(circuit="interlagos")
    sim_result = engine.simulate_decision(
        StrategyDecision(action=request.action, compound=None),
        modified_context,
        row["actual_decision"],
    )

    score_data = engine.evaluate_strategy(
        StrategyDecision(action=request.action, compound=None),
        modified_context,
        row["actual_decision"],
    )

    return DecisionResponse(
        scenario_id=row["decision_point_id"],
        user_action=request.action,
        score=score_data["score"],
        grade=score_data["grade"],
        historical_decision=row["actual_decision"],
        model_recommendation=score_data["model_recommendation"],
        model_confidence=score_data.get("model_confidence"),
        model_top_features=score_data.get("model_top_features", []),
        simulation_summary=SimulationSummary(
            expected_position=sim_result.expected_position,
            expected_finish_position_band=score_data.get("expected_finish_position_band"),
            risk_score=sim_result.risk_score,
        ),
        explanation=score_data["explanation"],
        tradeoffs=[],
    )
