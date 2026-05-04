"""
Chaos Engine — applies scenario modifiers to create "what-if" variants.
"""
from dataclasses import dataclass, replace
from typing import Any

from sim.scoring import ScenarioContext
from sim.circuit_config import CIRCUIT_CONFIG


@dataclass
class ChaosModifier:
    modifier_type: str
    modifier_value: float = 0.0


class ChaosEngine:
    """
    Applies chaos modifiers to a ScenarioContext, returning a NEW context.
    """

    def __init__(self, circuit: str = "interlagos"):
        self.circuit = circuit

    def _get_pit_loss(self) -> float:
        """Retrieve base pit loss for the configured circuit."""
        config = CIRCUIT_CONFIG.get(self.circuit, {})
        return float(config.get("pit_loss_seconds", 20.0))

    def apply_modifier(
        self, context: ScenarioContext, modifier: ChaosModifier
    ) -> ScenarioContext:
        """
        Apply a single chaos modifier to a scenario context.

        Returns a NEW ScenarioContext; the original is not mutated.
        """
        mtype = modifier.modifier_type
        mval = modifier.modifier_value

        # Gather current modifier deltas (default to existing values on context)
        pit_loss_delta = getattr(context, "modifier_pit_loss_delta", 0.0)
        stint_age_delta = getattr(context, "modifier_stint_age_delta", 0)
        safety_car = getattr(context, "safety_car_active", False)
        vsc = getattr(context, "virtual_safety_car_active", False)
        rainfall = getattr(context, "rainfall", False)
        track_status = getattr(context, "track_status", "green")
        gap_behind = context.gap_behind

        if mtype == "safety_car":
            safety_car = True
            pit_loss_delta -= 18.0
        elif mtype == "vsc":
            vsc = True
            pit_loss_delta -= 14.0
        elif mtype == "rain_starts":
            rainfall = True
            track_status = "wet"
        elif mtype == "tire_cliff_now":
            stint_age_delta += 8
        elif mtype == "slow_pit_stop":
            pit_loss_delta += mval
        elif mtype == "rival_pits_this_lap":
            pit_loss = self._get_pit_loss()
            gap_behind = max(0.0, gap_behind - pit_loss)
        elif mtype == "red_flag":
            track_status = "red_flag"
        else:
            raise ValueError(f"Unknown chaos modifier type: {mtype}")

        return replace(
            context,
            safety_car_active=safety_car,
            virtual_safety_car_active=vsc,
            rainfall=rainfall,
            track_status=track_status,
            modifier_pit_loss_delta=pit_loss_delta,
            modifier_stint_age_delta=stint_age_delta,
            gap_behind=gap_behind,
        )

    def apply_modifiers(
        self, context: ScenarioContext, modifiers: list[ChaosModifier]
    ) -> ScenarioContext:
        """
        Apply a list of modifiers sequentially.

        Returns a NEW ScenarioContext.
        """
        current = context
        for modifier in modifiers:
            current = self.apply_modifier(current, modifier)
        return current
