"""
Core Simulation Engine - Orchestrates pit, tire, and scoring models.
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from .circuit_config import CIRCUIT_CONFIG
from .pit_model import get_pit_loss, estimate_pit_delta
from .tire_model import TireState, estimate_lap_time, get_degradation_multiplier, is_in_tire_cliff_zone
from .scoring import score_decision, StrategyDecision, ScenarioContext
from ml.baselines import predict_pit_decision, predict_finish_position_band

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
        tire_state = TireState(compound=context.compound, stint_age=context.stint_age)
        est_lap_time = estimate_lap_time(
            base_lap_time_ms=base_lap_time_ms,
            tire_state=tire_state
        )

        # 2. Calculate position impact if pitting
        if decision.action.startswith("pit_"):
            pit_loss = get_pit_loss(self.circuit)
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
            if is_in_tire_cliff_zone(context.compound, context.stint_age):
                expected_pos = context.position + 1
            else:
                expected_pos = context.position

        # 3. Simple risk assessment
        risk_score = 0.5 # Neutral
        if decision.action == "stay_out" and context.stint_age > 25:
            risk_score = 0.8 # High risk of cliff
        elif decision.action.startswith("pit_") and context.gap_ahead < 5.0:
            risk_score = 0.7 # High risk of rejoining in traffic

        return SimResult(
            expected_position=expected_pos,
            estimated_lap_time=est_lap_time,
            delta_to_historical=0.0, # Simplified for MVP
            risk_score=risk_score
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

        # ML baseline predictions
        model_recommendation, model_confidence, model_top_features = predict_pit_decision(context)
        expected_band, _, _ = predict_finish_position_band(context, user_sim)

        return {
            "score": score_data["score"],
            "grade": score_data["grade"],
            "explanation": score_data["explanation"],
            "model_recommendation": model_recommendation,
            "model_confidence": model_confidence,
            "model_top_features": model_top_features,
            "expected_position": user_sim.expected_position,
            "expected_finish_position_band": expected_band,
            "risk_score": user_sim.risk_score,
            "estimated_lap_time": user_sim.estimated_lap_time,
        }
