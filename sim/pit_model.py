"""
Pit stop model - estimates pit loss time by circuit.
"""
from dataclasses import dataclass


# Pit loss estimates by circuit (in seconds)
PIT_LOSS_BY_CIRCUIT = {
    "interlagos": 22.0,  # Brazil
    "monaco": 18.0,      # Monaco
    "spa": 24.0,        # Belgium
    "silverstone": 19.0, # Great Britain
    "hungaroring": 20.0,# Hungary
    "las_vegas": 22.0,  # Las Vegas
    # Add more as needed
}


@dataclass
class PitLossConfig:
    """Pit loss configuration for a circuit."""
    circuit_name: str
    base_loss_seconds: float
    sc_reduction_seconds: float = 18.0  # Normal pit loss under SC/VSC
    vsc_reduction_seconds: float = 14.0  # Normal pit loss under VSC


def get_pit_loss(circuit: str, is_sc: bool = False, is_vsc: bool = False) -> float:
    """
    Get pit loss estimate for a circuit.
    
    Args:
        circuit: Circuit name (lowercase)
        is_sc: Is safety car deployed?
        is_vsc: Is virtual safety car deployed?
    
    Returns:
        Pit loss in seconds
    """
    base_loss = PIT_LOSS_BY_CIRCUIT.get(circuit.lower(), 20.0)
    
    if is_sc:
        base_loss -= 18.0
    elif is_vsc:
        base_loss -= 14.0
    
    return max(base_loss, 8.0)  # Minimum 8 seconds


def estimate_pit_delta(
    current_position: int,
    gap_ahead: float,
    gap_behind: float,
    pit_loss_seconds: float,
    clean_air_bonus: float = 0.5,
    traffic_penalty: float = 1.0
) -> float:
    """
    Estimate position delta from pitting.
    
    Positive = lose positions, Negative = gain positions.
    
    Args:
        current_position: Starting position
        gap_ahead: Gap to car ahead (seconds)
        gap_behind: Gap to car behind (seconds)
        pit_loss_seconds: Expected pit stop time loss
        clean_air_bonus: Bonus for clean air after pit
        traffic_penalty: Penalty for rejoining in traffic
    
    Returns:
        Expected position change
    """
    # Base position loss from pit
    delta = pit_loss_seconds / 90  # Rough: ~90 seconds per position
    
    # Adjust for gaps
    if gap_ahead < pit_loss_seconds:
        delta += 0.5  # At risk of being passed
    if gap_behind > pit_loss_seconds:
        delta += 0.3  # Other driver may pass while in pit
    
    # Clean air bonus
    if gap_ahead > 3.0 and gap_behind > 3.0:
        delta -= clean_air_bonus
    
    # Traffic penalty
    # Simplified: assume 1s penalty for now
    delta += traffic_penalty
    
    return delta