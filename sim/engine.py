"""
Core Simulation Engine - Orchestrates pit, tire, and scoring models.
"""
from typing import Dict, Any
from dataclasses import dataclass
from .circuit_config import CIRCUIT_CONFIG
from .pit_model import get_pit_loss, estimate_pit_delta
from .tire_model import TireState, estimate_lap_time, is_in_tire_cliff_zone
from .scoring import score_decision, StrategyDecision, ScenarioContext

@dataclass
class SimResult:
    expected_position: int
    estimated_lap_time: float
    delta_to_historical: float
    risk_score: float

class UndercutEngine:
    """
    Orchestrates the simulation of a driver's strategy decision.
    """
    def __init__(self, circuit: str = "interlagos"):
        self.circuit = circuit

    def simulate_decision(
        self, 
        decision: StrategyDecision, 
        context: ScenarioContext, 
        historical_decision: str
    ) -> SimResult:
        """
        Simulate the outcome of a user's decision.
        """
        # 1. Estimate lap time for current state
        import warnings
        circuit_config = CIRCUIT_CONFIG.get(self.circuit)
        if circuit_config is None:
            warnings.warn(f"Unknown circuit '{self.circuit}', using default base lap time")
            base_lap_time_ms = 90000
        else:
            base_lap_time_ms = circuit_config["base_lap_time_ms"]

        effective_stint_age = context.stint_age + getattr(context, 'modifier_stint_age_delta', 0)
        tire_state = TireState(compound=context.compound, stint_age=effective_stint_age)
        est_lap_time = estimate_lap_time(
            base_lap_time_ms=base_lap_time_ms,
            tire_state=tire_state
        )

        # 2. Calculate position impact if pitting
        if decision.action.startswith("pit_"):
            pit_loss = get_pit_loss(self.circuit) + getattr(context, 'modifier_pit_loss_delta', 0.0)
            # Safety car / VSC further reduces effective pit loss
            if context.safety_car_active:
                pit_loss = max(0.0, pit_loss - 18.0)
            elif context.virtual_safety_car_active:
                pit_loss = max(0.0, pit_loss - 14.0)

            pos_delta = estimate_pit_delta(
                current_position=context.position,
                gap_ahead=context.gap_ahead,
                gap_behind=context.gap_behind,
                pit_loss_seconds=pit_loss
            )
            expected_pos = int(context.position + pos_delta)
        else:
            # stay_out or extend_stint
            # Simplified: expect to keep position unless tires are in cliff
            if is_in_tire_cliff_zone(context.compound, effective_stint_age):
                expected_pos = context.position + 1
            else:
                expected_pos = context.position

        # 3. Risk assessment with modifier awareness
        risk_score = 0.5  # Neutral
        if decision.action == "stay_out" and effective_stint_age > 25:
            risk_score = 0.8  # High risk of cliff
        elif decision.action.startswith("pit_") and context.gap_ahead < 5.0:
            risk_score = 0.7  # High risk of rejoining in traffic

        # Modifiers dramatically shift risk
        if context.rainfall or context.track_status == "wet":
            if decision.action.startswith("pit_") and ("wet" in decision.action or "inter" in decision.action):
                risk_score = max(risk_score - 0.3, 0.1)  # Much safer
            elif not decision.action.startswith("pit_"):
                risk_score = min(risk_score + 0.3, 1.0)  # Much riskier

        if context.safety_car_active or context.virtual_safety_car_active:
            if decision.action.startswith("pit_"):
                risk_score = max(risk_score - 0.25, 0.1)  # SC pit is safer
            else:
                risk_score = min(risk_score + 0.15, 1.0)

        if context.track_status == "red_flag":
            if decision.action.startswith("pit_"):
                risk_score = 0.05  # Essentially free
            else:
                risk_score = 0.9  # Missing free pit is very risky

        if context.modifier_stint_age_delta > 0 and not decision.action.startswith("pit_"):
            risk_score = min(risk_score + 0.2, 1.0)

        if context.modifier_pit_loss_delta > 0 and decision.action.startswith("pit_"):
            risk_score = min(risk_score + 0.15, 1.0)

        return SimResult(
            expected_position=expected_pos,
            estimated_lap_time=est_lap_time,
            delta_to_historical=0.0,  # Simplified for MVP
            risk_score=round(risk_score, 2)
        )

    def evaluate_strategy(
        self,
        user_decision: StrategyDecision,
        context: ScenarioContext,
        historical_decision: str
    ) -> Dict[str, Any]:
        """
        Full evaluation pipeline: simulation -> scoring.
        """
        # Run simulation for user's choice
        user_sim = self.simulate_decision(user_decision, context, historical_decision)

        # Create simulated outcomes for all possible actions for scoring
        # (Simplified for MVP: just user vs historical)
        sim_outcomes = {
            user_decision.action: user_sim.expected_position,
            historical_decision: context.position  # Assume historical was optimal
        }

        score_data = score_decision(
            user_decision,
            context,
            historical_decision,
            sim_outcomes
        )

        from ml.baselines import predict_pit_decision, predict_finish_position_band
        from ml.registry import load_model_artifacts

        trained_model = None
        try:
            artifacts = load_model_artifacts("pit_decision")
            if artifacts:
                trained_model = artifacts["model"]
        except Exception:
            trained_model = None

        if trained_model and hasattr(trained_model, "feature_names"):
            try:
                import pandas as pd
                feat_dict = {
                    "stint_age_laps": context.stint_age,
                    "compound_hardness": {"soft": 1, "medium": 2, "hard": 3, "intermediate": 4, "wet": 5}.get(context.compound.lower(), 3),
                    "is_wet_compound": 1 if context.compound.lower() in ("intermediate", "wet") else 0,
                    "lap_time_ms": 90000.0,
                    "rolling_3_lap_avg_ms": None,
                    "is_pit_out_lap": 0,
                    "approx_position": context.position,
                    "laps_remaining": context.laps_remaining,
                    "rainfall_flag": 1 if context.rainfall else 0,
                    "air_temperature_c": None,
                    "track_temperature_c": None,
                    "red_flag": 0,
                    "yellow_flag": 0,
                }
                if len([f for f in trained_model.feature_names if f in feat_dict]) == len(trained_model.feature_names):
                    X = pd.DataFrame([{k: feat_dict.get(k) for k in trained_model.feature_names}])
                    model_rec, model_conf = trained_model.predict(X)
                    model_features = trained_model.explain(X)
                else:
                    raise ValueError("Feature mismatch")
            except Exception:
                model_rec, model_conf, model_features = predict_pit_decision(context)
        else:
            model_rec, model_conf, model_features = predict_pit_decision(context)

        finish_band, finish_conf, finish_reasons = predict_finish_position_band(context, user_sim)

        return {
            "score": score_data["score"],
            "grade": score_data["grade"],
            "explanation": score_data["explanation"],
            "model_recommendation": model_rec,
            "model_confidence": round(model_conf, 2),
            "model_top_features": model_features[:3],
            "expected_position": user_sim.expected_position,
            "expected_finish_position_band": finish_band,
            "risk_score": user_sim.risk_score,
            "estimated_lap_time": user_sim.estimated_lap_time,
        }
