from dataclasses import dataclass, replace
from typing import Any
from sim.scoring import ScenarioContext
from sim.circuit_config import CIRCUIT_CONFIG


@dataclass
class ChaosModifier:
    modifier_type: str
    modifier_value: float = 0.0


class ChaosEngine:
    def apply_modifier(self, context: ScenarioContext, modifier: ChaosModifier) -> ScenarioContext:
        kwargs = {}

        if modifier.modifier_type == "safety_car":
            kwargs['safety_car_active'] = True
            kwargs['modifier_pit_loss_delta'] = getattr(context, 'modifier_pit_loss_delta', 0) - 18.0
        elif modifier.modifier_type == "vsc":
            kwargs['virtual_safety_car_active'] = True
            kwargs['modifier_pit_loss_delta'] = getattr(context, 'modifier_pit_loss_delta', 0) - 14.0
        elif modifier.modifier_type == "rain_starts":
            kwargs['rainfall'] = True
            kwargs['track_status'] = 'wet'
        elif modifier.modifier_type == "tire_cliff_now":
            kwargs['modifier_stint_age_delta'] = getattr(context, 'modifier_stint_age_delta', 0) + 8
        elif modifier.modifier_type == "slow_pit_stop":
            kwargs['modifier_pit_loss_delta'] = getattr(context, 'modifier_pit_loss_delta', 0) + modifier.modifier_value
        elif modifier.modifier_type == "rival_pits_this_lap":
            circuit_config = CIRCUIT_CONFIG.get(getattr(context, 'circuit', 'interlagos'), {})
            pit_loss = circuit_config.get('pit_loss_seconds', 22.0)
            kwargs['gap_behind'] = max(0, getattr(context, 'gap_behind', 0) - pit_loss)
        elif modifier.modifier_type == "red_flag":
            kwargs['track_status'] = 'red_flag'
        else:
            raise ValueError(f"Unknown modifier type: {modifier.modifier_type}")

        return replace(context, **kwargs)

    def apply_modifiers(self, context: ScenarioContext, modifiers: list[ChaosModifier]) -> ScenarioContext:
        for modifier in modifiers:
            context = self.apply_modifier(context, modifier)
        return context
