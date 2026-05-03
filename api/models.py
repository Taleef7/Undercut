from typing import List, Optional
from pydantic import BaseModel


class ScenarioSummary(BaseModel):
    decision_point_id: str
    scenario_title: str
    scenario_description: str
    driver_id: str
    lap_number: int
    decision_type: str
    available_actions: List[str]
    difficulty_level: Optional[str] = None


class ScenarioDetail(ScenarioSummary):
    actual_decision: str
    actual_outcome_summary: str
    explanation_short: str
    explanation_long: str
    current_position: int
    gap_ahead_seconds: Optional[float]
    gap_behind_seconds: Optional[float]
    compound: str
    stint_age_laps: int
    laps_remaining: int
    track_temperature_c: Optional[float]
    air_temperature_c: Optional[float]
    rainfall: Optional[bool]
    track_status: Optional[str]
    safety_car_active: Optional[bool]
    virtual_safety_car_active: Optional[bool]


class SimulationSummary(BaseModel):
    expected_position: int
    expected_finish_position_band: Optional[str] = None
    risk_score: float
    tire_risk: Optional[str] = None
    track_position_risk: Optional[str] = None


class DecisionResponse(BaseModel):
    scenario_id: str
    user_action: str
    score: int
    grade: str
    historical_decision: str
    model_recommendation: str
    model_confidence: Optional[float] = None
    model_top_features: List[str] = []
    simulation_summary: SimulationSummary
    explanation: str
    tradeoffs: List[str] = []


class DecisionRequest(BaseModel):
    action: str
    compound: Optional[str] = None
