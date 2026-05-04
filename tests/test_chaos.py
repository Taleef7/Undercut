import pytest
from sim.scoring import ScenarioContext
from sim.chaos import ChaosEngine, ChaosModifier


def _make_context(**overrides) -> ScenarioContext:
    defaults = {
        "driver": "VER",
        "lap": 32,
        "position": 2,
        "compound": "medium",
        "stint_age": 14,
        "gap_ahead": 1.2,
        "gap_behind": 4.8,
        "laps_remaining": 39,
        "safety_car_active": False,
        "virtual_safety_car_active": False,
        "rainfall": False,
        "track_status": "green",
        "modifier_pit_loss_delta": 0.0,
        "modifier_stint_age_delta": 0,
    }
    defaults.update(overrides)
    return ScenarioContext(**defaults)


class TestChaosModifierSafetyCar:
    def test_sets_safety_car_active(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("safety_car"))
        assert modified.safety_car_active is True

    def test_reduces_pit_loss_delta_by_18(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("safety_car"))
        assert modified.modifier_pit_loss_delta == pytest.approx(-18.0)


class TestChaosModifierVSC:
    def test_sets_vsc_active(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("vsc"))
        assert modified.virtual_safety_car_active is True

    def test_reduces_pit_loss_delta_by_14(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("vsc"))
        assert modified.modifier_pit_loss_delta == pytest.approx(-14.0)


class TestChaosModifierRainStarts:
    def test_sets_rainfall_and_track_status(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("rain_starts"))
        assert modified.rainfall is True
        assert modified.track_status == "wet"


class TestChaosModifierTireCliffNow:
    def test_adds_8_to_stint_age_delta(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context(modifier_stint_age_delta=3)
        modified = engine.apply_modifier(context, ChaosModifier("tire_cliff_now"))
        assert modified.modifier_stint_age_delta == 11


class TestChaosModifierSlowPitStop:
    def test_adds_modifier_value_to_pit_loss_delta(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("slow_pit_stop", 5.0))
        assert modified.modifier_pit_loss_delta == pytest.approx(5.0)


class TestChaosModifierRivalPitsThisLap:
    def test_reduces_gap_behind_by_pit_loss(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context(gap_behind=25.0)
        modified = engine.apply_modifier(context, ChaosModifier("rival_pits_this_lap"))
        # interlagos pit loss is 22.0 seconds
        assert modified.gap_behind == pytest.approx(3.0)

    def test_clamps_gap_behind_at_zero(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context(gap_behind=15.0)
        modified = engine.apply_modifier(context, ChaosModifier("rival_pits_this_lap"))
        assert modified.gap_behind == pytest.approx(0.0)


class TestChaosModifierRedFlag:
    def test_sets_track_status_to_red_flag(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modified = engine.apply_modifier(context, ChaosModifier("red_flag"))
        assert modified.track_status == "red_flag"


class TestChaosEngineImmutability:
    def test_original_context_not_mutated(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        original = _make_context()
        modified = engine.apply_modifier(original, ChaosModifier("safety_car"))
        assert original.safety_car_active is False
        assert original.modifier_pit_loss_delta == 0.0
        assert modified.safety_car_active is True
        assert modified.modifier_pit_loss_delta == pytest.approx(-18.0)


class TestChaosEngineStacking:
    def test_multiple_modifiers_stack_pit_loss_delta(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modifiers = [
            ChaosModifier("safety_car"),
            ChaosModifier("slow_pit_stop", 3.0),
        ]
        modified = engine.apply_modifiers(context, modifiers)
        # -18.0 from SC + 3.0 from slow stop = -15.0
        assert modified.modifier_pit_loss_delta == pytest.approx(-15.0)

    def test_multiple_modifiers_stack_stint_age(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modifiers = [
            ChaosModifier("tire_cliff_now"),
            ChaosModifier("tire_cliff_now"),
        ]
        modified = engine.apply_modifiers(context, modifiers)
        assert modified.modifier_stint_age_delta == 16

    def test_sc_and_vsc_stack_both_flags(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        modifiers = [
            ChaosModifier("safety_car"),
            ChaosModifier("vsc"),
        ]
        modified = engine.apply_modifiers(context, modifiers)
        assert modified.safety_car_active is True
        assert modified.virtual_safety_car_active is True
        # -18 + -14 = -32
        assert modified.modifier_pit_loss_delta == pytest.approx(-32.0)


class TestChaosEngineUnknownModifier:
    def test_raises_value_error(self) -> None:
        engine = ChaosEngine(circuit="interlagos")
        context = _make_context()
        with pytest.raises(ValueError, match="Unknown chaos modifier type"):
            engine.apply_modifier(context, ChaosModifier("alien_invasion"))
