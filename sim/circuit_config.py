"""
Per-circuit constants for simulation engine.
"""
from typing import Dict, Any

CIRCUIT_CONFIG: Dict[str, Dict[str, Any]] = {
    "interlagos": {
        "base_lap_time_ms": 75500,
        "pit_loss_seconds": 22.0,
        "overtaking_difficulty": 0.60,
        "safety_car_probability_baseline": 0.35,
        "track_length_km": 4.309,
    },
    "monaco": {
        "base_lap_time_ms": 74000,
        "pit_loss_seconds": 18.0,
        "overtaking_difficulty": 0.95,
        "safety_car_probability_baseline": 0.55,
        "track_length_km": 3.337,
    },
    "silverstone": {
        "base_lap_time_ms": 87500,
        "pit_loss_seconds": 19.0,
        "overtaking_difficulty": 0.70,
        "safety_car_probability_baseline": 0.30,
        "track_length_km": 5.891,
    },
    "spa": {
        "base_lap_time_ms": 103000,
        "pit_loss_seconds": 24.0,
        "overtaking_difficulty": 0.55,
        "safety_car_probability_baseline": 0.25,
        "track_length_km": 7.004,
    },
    "monza": {
        "base_lap_time_ms": 81000,
        "pit_loss_seconds": 23.0,
        "overtaking_difficulty": 0.45,
        "safety_car_probability_baseline": 0.30,
        "track_length_km": 5.793,
    },
    "hungaroring": {
        "base_lap_time_ms": 92000,
        "pit_loss_seconds": 20.0,
        "overtaking_difficulty": 0.85,
        "safety_car_probability_baseline": 0.35,
        "track_length_km": 4.381,
    },
    "suzuka": {
        "base_lap_time_ms": 91500,
        "pit_loss_seconds": 21.0,
        "overtaking_difficulty": 0.70,
        "safety_car_probability_baseline": 0.35,
        "track_length_km": 5.807,
    },
    "yas_marina": {
        "base_lap_time_ms": 83000,
        "pit_loss_seconds": 20.0,
        "overtaking_difficulty": 0.55,
        "safety_car_probability_baseline": 0.25,
        "track_length_km": 5.281,
    },
    "las_vegas": {
        "base_lap_time_ms": 94000,
        "pit_loss_seconds": 22.0,
        "overtaking_difficulty": 0.35,
        "safety_car_probability_baseline": 0.30,
        "track_length_km": 6.201,
    },
    "albert_park": {
        "base_lap_time_ms": 90000,
        "pit_loss_seconds": 20.0,
        "overtaking_difficulty": 0.60,
        "safety_car_probability_baseline": 0.40,
        "track_length_km": 5.278,
    },
}
