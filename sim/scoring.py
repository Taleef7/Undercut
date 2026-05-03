"""
Simulator scoring - score user decisions against historical + simulated outcomes.
"""
from dataclasses import dataclass
from typing import Optional


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


def score_decision(
    decision: StrategyDecision,
    context: ScenarioContext,
    historical_decision: str,
    simulated_positions: dict
) -> dict:
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
    
    # Basic scoring logic
    score = 0
    grade = "Poor"
    explanation = ""
    
    # Match historical?
    if user_action == historical_action:
        score = 75
        grade = "Solid call"
        explanation = "You made the same call as the real team!"
    else:
        # Check simulated outcome
        sim_position = simulated_positions.get(user_action, context.position)
        
        if sim_position < context.position:
            score = 90
            grade = "Strong call"
            explanation = f"Simulation suggests you could have gained {context.position - sim_position} position(s)"
        elif sim_position == context.position:
            score = 60
            grade = "Risky"
            explanation = "Simulation suggests similar outcome, but risky given the conditions"
        else:
            score = 40
            grade = "Poor call"
            explanation = "Simulation suggests your choice would have cost positions"
    
    # Bonus for reasonable decisions in gray areas
    if user_action == "pit_now" and context.stint_age > 20:
        score = min(score + 10, 100)
        explanation += " Good timing on the pit stop!"
    
    if user_action == "stay_out" and context.stint_age < 10:
        score = max(score - 10, 0)
        explanation += " Tires still had life, pitting early was aggressive."
    
    return {
        "score": score,
        "grade": grade,
        "explanation": explanation,
        "historical_decision": historical_action,
        "model_recommendation": "pit_now" if sim_position < context.position else "stay_out",
    }


def get_grade_label(score: int) -> str:
    """Get grade label from score."""
    if score >= 85:
        return "Masterful"
    elif score >= 70:
        return "Strong"
    elif score >= 50:
        return "Solid"
    elif score >= 30:
        return "Risky"
    else:
        return "Poor"