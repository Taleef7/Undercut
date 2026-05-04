"""
Simulator scoring - score user decisions against historical + simulated outcomes.
"""
from dataclasses import dataclass
from typing import Optional

ACTION_PIT_NOW = "pit_now"
ACTION_STAY_OUT = "stay_out"
ACTION_EXTEND_STINT = "extend_stint"

GRADE_MASTERFUL = "Masterful"
GRADE_STRONG_CALL = "Strong call"
GRADE_INSPIRED_CALL = "Inspired call"
GRADE_RISKY = "Risky"
GRADE_POOR_CALL = "Poor call"
GRADE_OFF_THE_WALL = "Off the wall"


@dataclass
class StrategyDecision:
    """A strategy decision made by the user."""
    action: str  # pit_now, stay_out, extend_stint, etc.
    compound: Optional[str] = None


@dataclass
class ScenarioContext:
    """Context for a scenario."""
    driver: str
    lap: int
    position: int
    compound: str
    stint_age: int
    gap_ahead: float
    gap_behind: float
    laps_remaining: int
    safety_car_active: bool = False
    virtual_safety_car_active: bool = False
    rainfall: bool = False
    track_status: str = "green"
    modifier_pit_loss_delta: float = 0.0
    modifier_stint_age_delta: int = 0
    opponent_fresher_tires: bool = False
    circuit: str = "interlagos"


def score_decision(
    decision: StrategyDecision,
    context: ScenarioContext,
    historical_decision: str,
    simulated_positions: dict[str, int],
) -> dict[str, object]:
    """
    Score a user decision.
    
    Args:
        decision: User's decision
        context: Scenario context
        historical_decision: What actually happened historically
        simulated_positions: Dict of action -> expected position
    
    Returns:
        Dict with score, grade, explanation
    """
    user_action = decision.action
    historical_action = historical_decision
    sim_position = simulated_positions.get(user_action, context.position)
    
    # Basic scoring logic
    score = 0
    grade = GRADE_POOR_CALL
    explanation = ""
    
    # Match historical?
    if user_action == historical_action:
        score = 75
        grade = GRADE_STRONG_CALL
        explanation = "You made the same call as the real team!"
    else:
        # Check simulated outcome
        if sim_position < context.position:
            score = 90
            grade = GRADE_INSPIRED_CALL
            explanation = f"Simulation suggests you could have gained {context.position - sim_position} position(s)"
        elif sim_position == context.position:
            score = 60
            grade = GRADE_RISKY
            explanation = "Simulation suggests similar outcome, but risky given the conditions"
        else:
            score = 40
            grade = GRADE_POOR_CALL
            explanation = "Simulation suggests your choice would have cost positions"
    
    effective_stint_age = context.stint_age + getattr(context, 'modifier_stint_age_delta', 0)

    # Bonus for reasonable decisions in gray areas
    if user_action.startswith("pit_") and effective_stint_age > 20:
        score = min(score + 10, 100)
        explanation += " Good timing on the pit stop!"

    if user_action == ACTION_STAY_OUT and effective_stint_age < 10:
        score = max(score - 10, 0)
        explanation += " Tires still had life, pitting early was aggressive."
    
    return {
        "score": score,
        "grade": grade,
        "explanation": explanation,
        "historical_decision": historical_action,
        "model_recommendation": ACTION_PIT_NOW if sim_position < context.position else ACTION_STAY_OUT,
    }


def get_grade_label(score: int) -> str:
    """Get grade label from score."""
    if score >= 85:
        return GRADE_MASTERFUL
    elif score >= 70:
        return GRADE_STRONG_CALL
    elif score >= 50:
        return GRADE_INSPIRED_CALL
    elif score >= 30:
        return GRADE_RISKY
    else:
        return GRADE_OFF_THE_WALL
