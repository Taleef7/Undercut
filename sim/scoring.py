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


def has_active_modifiers(context: ScenarioContext) -> bool:
    """Check if any chaos modifiers are active."""
    return (
        context.modifier_pit_loss_delta != 0
        or context.modifier_stint_age_delta != 0
        or context.safety_car_active
        or context.virtual_safety_car_active
        or context.rainfall
        or context.track_status in ("wet", "red_flag")
    )


def score_decision(
    decision: StrategyDecision,
    context: ScenarioContext,
    historical_decision: str,
    simulated_positions: dict[str, int],
) -> dict[str, object]:
    """
    Score a user decision with full context awareness including chaos modifiers.
    """
    user_action = decision.action
    historical_action = historical_decision
    sim_position = simulated_positions.get(user_action, context.position)
    effective_stint_age = context.stint_age + context.modifier_stint_age_delta
    modifiers_active = has_active_modifiers(context)

    # Start with simulation-based base score
    score = 50
    grade = GRADE_RISKY
    explanation_parts = []

    # --- Position impact from simulation ---
    if sim_position < context.position:
        score = 70
        grade = GRADE_INSPIRED_CALL
        explanation_parts.append(f"Simulation projects a gain to P{sim_position}.")
    elif sim_position == context.position:
        score = 55
        grade = GRADE_RISKY
        explanation_parts.append("Simulation projects holding position.")
    else:
        score = 35
        grade = GRADE_POOR_CALL
        explanation_parts.append(f"Simulation projects dropping to P{sim_position}.")

    # --- Chaos modifier impact (these are the big differentiators) ---
    modifier_explanations = []

    # Safety Car / VSC: pitting is highly advantageous
    if context.safety_car_active and user_action.startswith("pit_"):
        score = min(score + 25, 100)
        grade = GRADE_MASTERFUL
        modifier_explanations.append("Pitting under Safety Car is a masterful call — minimal time loss.")
    elif context.safety_car_active and not user_action.startswith("pit_"):
        score = max(score - 20, 0)
        grade = GRADE_POOR_CALL
        modifier_explanations.append("Staying out under Safety Car wastes a free pit opportunity.")

    if context.virtual_safety_car_active and user_action.startswith("pit_"):
        score = min(score + 15, 100)
        if grade not in (GRADE_MASTERFUL,):
            grade = GRADE_STRONG_CALL
        modifier_explanations.append("Pitting under VSC saves significant time.")

    # Red Flag: free pit window
    if context.track_status == "red_flag" and user_action.startswith("pit_"):
        score = min(score + 30, 100)
        grade = GRADE_MASTERFUL
        modifier_explanations.append("Red flag pit stop is effectively free — brilliant timing.")
    elif context.track_status == "red_flag" and not user_action.startswith("pit_"):
        score = max(score - 25, 0)
        grade = GRADE_POOR_CALL
        modifier_explanations.append("Missing a free pit under red flag is a major strategic error.")

    # Rain: pitting for wets/inters is usually correct
    if context.rainfall or context.track_status == "wet":
        if user_action.startswith("pit_") and ("wet" in user_action or "inter" in user_action):
            score = min(score + 20, 100)
            if grade not in (GRADE_MASTERFUL,):
                grade = GRADE_STRONG_CALL
            modifier_explanations.append("Switching to wet-weather tires as rain starts is the right call.")
        elif user_action.startswith("pit_") and not ("wet" in user_action or "inter" in user_action):
            score = max(score - 15, 0)
            modifier_explanations.append("Pitting for dry tires in the rain is a risky move.")
        elif not user_action.startswith("pit_"):
            score = max(score - 20, 0)
            grade = GRADE_POOR_CALL
            modifier_explanations.append("Staying on dry tires in wet conditions is dangerous.")

    # Tire cliff: staying out is very risky
    if context.modifier_stint_age_delta > 0:
        if not user_action.startswith("pit_") and effective_stint_age > 25:
            score = max(score - 20, 0)
            modifier_explanations.append(f"Tires are effectively {effective_stint_age} laps old — staying out risks a cliff.")
        elif user_action.startswith("pit_") and effective_stint_age > 25:
            score = min(score + 15, 100)
            modifier_explanations.append(f"Pitting with effectively {effective_stint_age}-lap-old tires is well-timed.")

    # Slow pit stop: penalty for pitting
    if context.modifier_pit_loss_delta > 0 and user_action.startswith("pit_"):
        score = max(score - 15, 0)
        modifier_explanations.append(f"A slow stop (+{context.modifier_pit_loss_delta:.0f}s) hurts the pit strategy.")

    # Rival pits: not covering is risky
    if context.gap_behind < 3.0 and not user_action.startswith("pit_"):
        score = max(score - 10, 0)
        modifier_explanations.append("A close rival pitting this lap puts you at risk of being undercut.")

    # --- Historical alignment bonus (diminished when modifiers change the game) ---
    if user_action == historical_action:
        if modifiers_active:
            # With modifiers, historical decision might not be optimal anymore
            score = min(score + 5, 100)
            explanation_parts.append("Same call as the real team, but conditions have changed.")
        else:
            score = min(score + 15, 100)
            if grade not in (GRADE_MASTERFUL, GRADE_OFF_THE_WALL):
                grade = GRADE_STRONG_CALL
            explanation_parts.append("You made the same call as the real team!")
    else:
        if not modifiers_active:
            explanation_parts.append("You chose differently from the real team.")

    # --- Tire age bonuses (generic) ---
    if user_action.startswith("pit_") and effective_stint_age > 20:
        score = min(score + 8, 100)
        explanation_parts.append("Good timing on the pit stop given tire age.")

    if user_action == ACTION_STAY_OUT and effective_stint_age < 10:
        score = max(score - 10, 0)
        explanation_parts.append("Tires still had plenty of life — pitting early was aggressive.")

    # Clamp score
    score = max(0, min(100, score))

    # Build final explanation
    if modifier_explanations:
        explanation = " ".join(modifier_explanations + explanation_parts)
    else:
        explanation = " ".join(explanation_parts)

    if not explanation:
        explanation = "Decision evaluated against simulation and historical context."

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
