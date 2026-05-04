import pytest
from sim.scoring import ScenarioContext
from sim.chaos import ChaosEngine, ChaosModifier


def test_safety_car_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="safety_car")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.safety_car_active is True
    assert new_ctx.modifier_pit_loss_delta == -18.0


def test_vsc_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="vsc")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.virtual_safety_car_active is True
    assert new_ctx.modifier_pit_loss_delta == -14.0


def test_rain_starts_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="rain_starts")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.rainfall is True
    assert new_ctx.track_status == "wet"


def test_tire_cliff_now_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="tire_cliff_now")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.modifier_stint_age_delta == 8


def test_slow_pit_stop_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="slow_pit_stop", modifier_value=3.5)
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.modifier_pit_loss_delta == 3.5


def test_rival_pits_this_lap_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39, circuit="interlagos",
    )
    mod = ChaosModifier(modifier_type="rival_pits_this_lap")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.gap_behind == max(0, 4.8 - 22.0)


def test_red_flag_modifier():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="red_flag")
    new_ctx = engine.apply_modifier(context, mod)
    assert new_ctx.track_status == "red_flag"


def test_unknown_modifier_raises_error():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mod = ChaosModifier(modifier_type="alien_invasion")
    with pytest.raises(ValueError, match="Unknown modifier type"):
        engine.apply_modifier(context, mod)


def test_apply_modifiers_chain():
    engine = ChaosEngine()
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    mods = [
        ChaosModifier(modifier_type="safety_car"),
        ChaosModifier(modifier_type="slow_pit_stop", modifier_value=2.0),
    ]
    new_ctx = engine.apply_modifiers(context, mods)
    assert new_ctx.safety_car_active is True
    assert new_ctx.modifier_pit_loss_delta == -16.0
