import pytest
from sim.scoring import ScenarioContext
from ml.baselines import predict_pit_decision, predict_finish_position_band, TIRE_CLIFF_THRESHOLDS


def test_predict_pit_safety_car_returns_stay_out():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39, safety_car_active=True,
    )
    action, conf, reasons = predict_pit_decision(context)
    assert action == "stay_out"
    assert conf == 0.9
    assert any("Safety car" in r for r in reasons)


def test_predict_pit_rain_returns_pit_now():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39, rainfall=True,
    )
    action, conf, reasons = predict_pit_decision(context)
    assert action == "pit_now"
    assert conf == 0.85
    assert any("Wet" in r for r in reasons)


def test_predict_pit_tire_cliff_returns_pit_now():
    for compound, threshold in TIRE_CLIFF_THRESHOLDS.items():
        context = ScenarioContext(
            driver="VER", lap=32, position=2, compound=compound, stint_age=threshold + 1,
            gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
        )
        action, conf, reasons = predict_pit_decision(context)
        assert action == "pit_now", f"Failed for {compound}"
        assert conf == 0.8
        assert any("cliff" in r for r in reasons)


def test_predict_pit_undercut_threat_returns_pit_now():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=2.5, laps_remaining=39, opponent_fresher_tires=True,
    )
    action, conf, reasons = predict_pit_decision(context)
    assert action == "pit_now"
    assert conf == 0.75
    assert any("Undercut" in r for r in reasons)


def test_predict_pit_too_late_returns_stay_out():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=5,
    )
    action, conf, reasons = predict_pit_decision(context)
    assert action == "stay_out"
    assert conf == 0.9
    assert any("few laps" in r for r in reasons)


def test_predict_pit_default_returns_stay_out():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=10,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    action, conf, reasons = predict_pit_decision(context)
    assert action == "stay_out"
    assert conf > 0.5
    assert any("No urgent" in r for r in reasons)


def test_predict_finish_podium_band():
    context = ScenarioContext(
        driver="VER", lap=32, position=2, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39,
    )
    band, conf, reasons = predict_finish_position_band(context, None)
    assert band == "P1-P3"
    assert any("podium" in r for r in reasons)


def test_predict_finish_safety_car_improves_band():
    context = ScenarioContext(
        driver="VER", lap=32, position=8, compound="medium", stint_age=14,
        gap_ahead=1.2, gap_behind=4.8, laps_remaining=39, safety_car_active=True,
    )
    band, conf, reasons = predict_finish_position_band(context, None)
    assert band == "P4-P6"
    assert any("Safety car" in r for r in reasons)
