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

    # Start at neutral
    score = 50
    grade = GRADE_RISKY
    explanation_parts = []

    # --- UNDER RED FLAG: tire choice, not pit-vs-stay ---
    under_red_flag = context.track_status == "red_flag"
    is_tire_action = any(kw in user_action for kw in ("fresh", "used", "gamble", "inters", "slicks", "soft"))
    
    if under_red_flag and is_tire_action:
        # Red flag — everyone is already in pits. Score the compound choice.
        if "fresh" in user_action and "inter" in user_action:
            score = 75  # Fresh inters — safe, consensus call
            grade = GRADE_STRONG_CALL
            explanation_parts.append("Fresh intermediates are the safe consensus call under the red flag.")
        elif "used" in user_action:
            score = 60  # Conservative — saving tires for later
            grade = GRADE_RISKY
            explanation_parts.append("Re-using worn tires saves a fresh set but compromises pace on restart.")
        elif "gamble" in user_action or "slick" in user_action:
            score = 35  # High risk — track might not be dry enough
            grade = GRADE_RISKY
            explanation_parts.append("Gambling on slicks under red flag is high-risk — the track may not be ready.")
        elif "push" in user_action:
            score = 80
            grade = GRADE_STRONG_CALL
            explanation_parts.append("Pushing now while others are conservative is bold but could pay off.")
        elif "manage" in user_action or "conserve" in user_action:
            score = 60
            grade = GRADE_RISKY
            explanation_parts.append("Managing through the red flag period is safe but doesn't capitalize on free tire change.")
    elif under_red_flag:
        # Under red flag but action doesn't match tire choice pattern
        score = 40
        grade = GRADE_POOR_CALL
        explanation_parts.append("Under a red flag, tire strategy is the key decision point.")

    # --- Position impact from simulation ---
    if not under_red_flag:
        if sim_position < context.position:
            score = min(score + 20, 100)
            if grade not in (GRADE_MASTERFUL, GRADE_STRONG_CALL):
                grade = GRADE_INSPIRED_CALL
            explanation_parts.append(f"Simulation projects a gain to P{sim_position}.")
        elif sim_position == context.position:
            score = max(score, 55)
            explanation_parts.append("Simulation projects holding position.")
        else:
            score = max(score - 15, 15)
            explanation_parts.append(f"Simulation projects dropping to P{sim_position}.")

    # --- Safety Car / VSC bonuses ---
    if context.safety_car_active and user_action.startswith("pit_"):
        score = min(score + 20, 100)
        if grade not in (GRADE_MASTERFUL,):
            grade = GRADE_STRONG_CALL
        explanation_parts.append("Pitting under Safety Car — well timed, minimal time loss.")
    elif context.safety_car_active and not user_action.startswith("pit_"):
        score = max(score - 10, 0)
        explanation_parts.append("Staying out under Safety Car loses a cheap pit opportunity.")

    if context.virtual_safety_car_active and user_action.startswith("pit_"):
        score = min(score + 15, 100)
        explanation_parts.append("Pitting under VSC saves time.")

    # --- Rain adjustments ---
    if context.rainfall or context.track_status == "wet":
        if user_action.startswith("pit_") and ("wet" in user_action or "inter" in user_action):
            score = min(score + 15, 100)
            if grade not in (GRADE_MASTERFUL, GRADE_STRONG_CALL):
                grade = GRADE_STRONG_CALL
            explanation_parts.append("Switching to wet tires in rainy conditions is correct.")
        elif not user_action.startswith("pit_") and context.compound.lower() not in ("intermediate", "wet"):
            score = max(score - 15, 0)
            explanation_parts.append("Staying on dry tires in the rain is risky.")

    # --- Tire cliff effects ---
    if effective_stint_age > 25 and not user_action.startswith("pit_") and not under_red_flag:
        score = max(score - 10, 0)
        explanation_parts.append(f"Tires are {effective_stint_age} laps old — staying out risks the cliff.")
    if effective_stint_age > 25 and user_action.startswith("pit_"):
        score = min(score + 10, 100)
        explanation_parts.append(f"Good call — tires at {effective_stint_age} laps are nearing the cliff.")

    # --- Historical alignment (significant bonus for matching the actual decision) ---
    if user_action == historical_action:
        score = min(score + 20, 100)
        if grade not in (GRADE_MASTERFUL, GRADE_POOR_CALL):
            grade = GRADE_STRONG_CALL
        explanation_parts.append("You matched the real team decision — which actually worked in the race.")
    else:
        explanation_parts.append("You chose differently from the real team.")

    # --- Modifier-specific adjustments ---
    if context.modifier_stint_age_delta > 0:
        if not user_action.startswith("pit_") and effective_stint_age > 25:
            score = max(score - 10, 0)
            explanation_parts.append(f"Chaos: tires effectively {effective_stint_age} laps old.")
        elif user_action.startswith("pit_") and effective_stint_age > 25:
            score = min(score + 10, 100)
            explanation_parts.append("Chaos: pitting with effectively aged tires is well-timed.")

    if context.modifier_pit_loss_delta > 0 and user_action.startswith("pit_"):
        score = max(score - 10, 0)
        explanation_parts.append(f"Chaos: slow pit stop adds {context.modifier_pit_loss_delta:.0f}s penalty.")

    # Clamp
    score = max(0, min(100, score))

    # Build explanation
    explanation = " ".join(explanation_parts)
    if not explanation:
        explanation = "Decision evaluated against simulation and historical context."

    model_rec = context.compound.lower() if under_red_flag else (
        ACTION_PIT_NOW if sim_position < context.position else ACTION_STAY_OUT
    )

    return {
        "score": score,
        "grade": grade,
        "explanation": explanation,
        "historical_decision": historical_action,
        "model_recommendation": model_rec,
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
