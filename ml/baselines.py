"""
Rule-based ML baselines for pit decision and finish position prediction.
"""
from typing import Tuple, List
from sim.scoring import ScenarioContext

# Thresholds for tire cliff detection (stint_age > threshold triggers pit recommendation)
COMPOUND_CLIFF_THRESHOLDS = {
    "soft": 18,
    "medium": 28,
    "hard": 38,
}

# Finish position bands ordered from best to worst
BANDS: List[str] = ["P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+"]


def _position_to_band(position: int) -> str:
    """Map a current position to a finish position band."""
    if position <= 3:
        return "P1-P3"
    elif position <= 6:
        return "P4-P6"
    elif position <= 10:
        return "P7-P10"
    elif position <= 15:
        return "P11-P15"
    else:
        return "P16+"


def predict_pit_decision(context: ScenarioContext) -> Tuple[str, float, List[str]]:
    """
    Rule-based baseline for pit-stop decisions.

    Rules are evaluated in priority order. The first matching rule determines
    the recommendation. Confidence is drawn from the matching rule. When
    multiple rules match simultaneously, a composite confidence formula is
    applied: 0.5 + 0.45 * (matching_rules / total_rules), capped at 0.95.

    Returns:
        (recommendation, confidence, reasons)
    """
    total_rules = 5
    matching_rules: List[Tuple[int, str, float, str]] = []

    # Rule 1: Safety car active
    if getattr(context, "safety_car_active", False):
        matching_rules.append(
            (0, "stay_out", 0.9, "Safety car on track — pitting now loses track position")
        )

    # Rule 2: Rainfall or wet track conditions
    track_status = getattr(context, "track_status", "green")
    if getattr(context, "rainfall", False) or track_status in ("wet", "rain_starts"):
        matching_rules.append(
            (1, "pit_now", 0.85, "Wet conditions — need intermediate tires")
        )

    # Rule 3: Tire cliff approaching
    threshold = COMPOUND_CLIFF_THRESHOLDS.get(context.compound.lower(), 999)
    if context.stint_age > threshold:
        matching_rules.append(
            (2, "pit_now", 0.8, "Tires approaching cliff")
        )

    # Rule 4: Undercut threat from behind
    if (
        0 < context.gap_behind < 3.0
        and getattr(context, "opponent_fresher_tires", False)
    ):
        matching_rules.append(
            (3, "pit_now", 0.75, "Undercut threat from behind")
        )

    # Rule 5: Too few laps remaining
    if context.laps_remaining < 8:
        matching_rules.append(
            (4, "stay_out", 0.9, "Too few laps remaining to benefit from fresh tires")
        )

    if not matching_rules:
        return "stay_out", 0.6, ["No urgent signal to pit"]

    # Sort by priority (lowest index = highest priority)
    matching_rules.sort(key=lambda r: r[0])
    recommendation = matching_rules[0][1]
    reasons = [matching_rules[0][3]]

    # Apply composite confidence formula when multiple rules match
    if len(matching_rules) > 1:
        confidence = min(0.5 + 0.45 * (len(matching_rules) / total_rules), 0.95)
    else:
        confidence = matching_rules[0][2]

    return recommendation, confidence, reasons


def predict_finish_position_band(
    context: ScenarioContext, sim_result
) -> Tuple[str, float, List[str]]:
    """
    Rule-based baseline for predicting the driver's finish position band.

    Args:
        context: Scenario context.
        sim_result: Simulation result object (expected_position is read from it).

    Returns:
        (band, confidence, reasons)
    """
    reasons: List[str] = []
    band = _position_to_band(context.position)

    # Rule 1: Strong pace and front-running position
    if context.position <= 3 and context.gap_ahead < 5:
        band = "P1-P3"
        reasons.append("Strong pace and front-running position")

    # Rule 3: Large gap to leader pushes band toward midfield/back
    if context.gap_ahead > 30:
        if context.gap_ahead > 90:
            band = "P16+"
            reasons.append("Large gap to leader indicates back of field")
        elif context.gap_ahead > 60:
            band = "P11-P15"
            reasons.append("Significant gap to leader indicates mid-to-back field")
        else:
            band = "P7-P10"
            reasons.append("Substantial gap to leader indicates midfield position")

    # Rule 2: Safety car compresses the field, improving the band by one tier
    if getattr(context, "safety_car_active", False):
        band_index = BANDS.index(band)
        band_index = max(0, band_index - 1)
        band = BANDS[band_index]
        reasons.append("Safety car compresses the field, improving position potential")

    if not reasons:
        reasons.append("Based on current running position")

    confidence = 0.6
    return band, confidence, reasons
