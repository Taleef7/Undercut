from typing import Tuple, List
from sim.scoring import ScenarioContext

TIRE_CLIFF_THRESHOLDS = {"soft": 18, "medium": 28, "hard": 38, "intermediate": 25, "wet": 30}


def predict_pit_decision(context: ScenarioContext) -> Tuple[str, float, List[str]]:
    """Rule-based pit decision baseline."""
    reasons = []

    # Rule 1: Safety car
    if getattr(context, 'safety_car_active', False):
        reasons.append("Safety car reduces pit loss — good time to pit")
        return "pit_now", 0.85, reasons

    # Rule 2: Rain
    if getattr(context, 'rainfall', False) or getattr(context, 'track_status', '') in ('wet', 'rain_starts'):
        reasons.append("Wet conditions — need intermediate tires")
        return "pit_now", 0.85, reasons

    # Rule 3: Tire cliff
    threshold = TIRE_CLIFF_THRESHOLDS.get(context.compound.lower(), 30)
    if context.stint_age > threshold:
        reasons.append("Tires approaching cliff")
        return "pit_now", 0.8, reasons

    # Rule 4: Undercut threat
    gap_behind = getattr(context, 'gap_behind', 999)
    if 0 < gap_behind < 3.0 and getattr(context, 'opponent_fresher_tires', False):
        reasons.append("Undercut threat from behind")
        return "pit_now", 0.75, reasons

    # Rule 5: Too late
    if getattr(context, 'laps_remaining', 999) < 8:
        reasons.append("Too few laps remaining to benefit from fresh tires")
        return "stay_out", 0.9, reasons

    # Default
    reasons.append("No urgent signal to pit")
    confidence = min(0.95, 0.5 + 0.45 * (len(reasons) / 5))
    return "stay_out", confidence, reasons


def predict_finish_position_band(context: ScenarioContext, sim_result) -> Tuple[str, float, List[str]]:
    """Predict finish position band."""
    reasons = []
    position = getattr(sim_result, 'expected_position', getattr(context, 'position', 10))
    gap_ahead = getattr(context, 'gap_ahead', 0)

    # Rule 1: Pace delta
    if position <= 3 and gap_ahead < 5:
        band = "P1-P3"
        reasons.append("Running in podium positions with small gap to leader")
    elif position <= 6:
        band = "P4-P6"
        reasons.append("Running in midfield top positions")
    elif position <= 10:
        band = "P7-P10"
        reasons.append("Running in lower midfield")
    elif position <= 15:
        band = "P11-P15"
        reasons.append("Running in backmarker positions")
    else:
        band = "P16+"
        reasons.append("Running at the back of the field")

    # Rule 2: Safety car compression
    if getattr(context, 'safety_car_active', False):
        bands = ["P1-P3", "P4-P6", "P7-P10", "P11-P15", "P16+"]
        idx = bands.index(band)
        if idx > 0:
            band = bands[idx - 1]
            reasons.append("Safety car compresses the field — improves position band")

    confidence = min(0.95, 0.5 + 0.1 * len(reasons))
    return band, confidence, reasons
