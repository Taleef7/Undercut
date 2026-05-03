"""
Tire degradation model - estimates tire performance by compound and age.
"""
from dataclasses import dataclass
from typing import Tuple


# Degradation curves: (compound -> (stint_age -> pace_multiplier))
# Values are approximate pace loss per lap vs fresh tire
TIRE_DEGRADATION = {
    "soft": [0.0, 0.001, 0.002, 0.003, 0.005, 0.007, 0.010, 0.012, 0.015, 0.018],
    "medium": [0.0, 0.001, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.010],
    "hard": [0.0, 0.0005, 0.001, 0.001, 0.002, 0.002, 0.003, 0.003, 0.004, 0.005],
    "intermediate": [0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.010, 0.012],
    "wet": [0.0, 0.001, 0.002, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.008],
}


# Tire cliff thresholds (laps before cliff starts)
TIRE_CLIFF_THRESHOLDS = {
    "soft": 20,
    "medium": 25,
    "hard": 30,
    "intermediate": 999,  # No cliff
    "wet": 999,
}


@dataclass
class TireState:
    """Current tire state."""
    compound: str  # soft, medium, hard, intermediate, wet
    stint_age: int   # laps on this tire


def get_degradation_multiplier(compound: str, stint_age: int) -> float:
    """
    Get pace multiplier from tire degradation.
    
    Args:
        compound: Tire compound name
        stint_age: Laps on current tire
    
    Returns:
        Pace multiplier (1.0 = fresh, >1.0 = slower)
    """
    compound = compound.lower()
    if compound not in TIRE_DEGRADATION:
        return 1.0
    
    deg_curve = TIRE_DEGRADATION[compound]
    if stint_age >= len(deg_curve):
        return deg_curve[-1]
    return 1.0 + deg_curve[stint_age]


def is_in_tire_cliff_zone(compound: str, stint_age: int) -> bool:
    """Check if running in tire cliff zone."""
    threshold = TIRE_CLIFF_THRESHOLDS.get(compound.lower(), 999)
    return stint_age >= (threshold - 5)


def estimate_lap_time(
    base_lap_time_ms: float,
    tire_state: TireState,
    is_traffic: bool = False,
    track_temp_factor: float = 0.0
) -> float:
    """
    Estimate lap time given tire state and conditions.
    
    Args:
        base_lap_time_ms: Base lap time in milliseconds
        tire_state: Current tire compound and age
        is_traffic: Is the driver in traffic?
        track_temp_factor: Temperature adjustment (-1 to +1)
    
    Returns:
        Estimated lap time in milliseconds
    """
    # Apply degradation
    deg_mult = get_degradation_multiplier(tire_state.compound, tire_state.stint_age)
    lap_time = base_lap_time_ms * deg_mult
    
    # Traffic penalty
    if is_traffic:
        lap_time += 1500  # ~1.5s penalty
    
    # Temperature adjustment
    if track_temp_factor != 0:
        lap_time *= (1.0 + track_temp_factor * 0.02)
    
    return lap_time


def get_compound_order() -> dict:
    """Get hardness order for compounds."""
    return {
        "soft": 1,
        "medium": 2,
        "hard": 3,
        "intermediate": 4,
        "wet": 5,
    }