import pytest
from sim.scoring import ScenarioContext
from ml.baselines import predict_pit_decision, predict_finish_position_band, BANDS


def _make_context(
    safety_car_active: bool = False,
    rainfall: bool = False,
    track_status: str = "green",
    compound: str = "medium",
    stint_age: int = 10,
    gap_behind: float = 4.0,
    gap_ahead: float = 2.0,
    laps_remaining: int = 20,
    position: int = 5,
    opponent_fresher_tires: bool = False,
) -> ScenarioContext:
    return ScenarioContext(
        driver="VER",
        lap=32,
        position=position,
        compound=compound,
        stint_age=stint_age,
        gap_ahead=gap_ahead,
        gap_behind=gap_behind,
        laps_remaining=laps_remaining,
        safety_car_active=safety_car_active,
        rainfall=rainfall,
        track_status=track_status,
        opponent_fresher_tires=opponent_fresher_tires,
    )


class TestPredictPitDecision:
    """Tests for the rule-based pit decision baseline."""

    def test_rule_1_safety_car_recommends_stay_out(self) -> None:
        context = _make_context(safety_car_active=True)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "stay_out"
        assert conf == 0.9
        assert "Safety car" in reasons[0]

    def test_rule_2_rainfall_recommends_pit_now(self) -> None:
        context = _make_context(rainfall=True)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.85
        assert "Wet" in reasons[0]

    def test_rule_2_wet_track_status_recommends_pit_now(self) -> None:
        context = _make_context(track_status="wet")
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.85

    def test_rule_3_tire_cliff_soft_recommends_pit_now(self) -> None:
        context = _make_context(compound="soft", stint_age=20)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.8
        assert "cliff" in reasons[0]

    def test_rule_3_tire_cliff_medium_recommends_pit_now(self) -> None:
        context = _make_context(compound="medium", stint_age=30)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.8

    def test_rule_3_tire_cliff_hard_recommends_pit_now(self) -> None:
        context = _make_context(compound="hard", stint_age=40)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.8

    def test_rule_4_undercut_threat_recommends_pit_now(self) -> None:
        context = _make_context(gap_behind=2.0, opponent_fresher_tires=True)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "pit_now"
        assert conf == 0.75
        assert "Undercut" in reasons[0]

    def test_rule_4_no_opponent_fresher_tires_does_not_fire(self) -> None:
        context = _make_context(gap_behind=2.0, opponent_fresher_tires=False)
        rec, conf, _ = predict_pit_decision(context)
        # Should fall through to default because gap_behind condition alone is not enough
        assert rec == "stay_out"

    def test_rule_5_too_late_to_pit_recommends_stay_out(self) -> None:
        context = _make_context(laps_remaining=5)
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "stay_out"
        assert conf == 0.9
        assert "Too few laps" in reasons[0]

    def test_default_no_rules_match(self) -> None:
        context = _make_context()
        rec, conf, reasons = predict_pit_decision(context)
        assert rec == "stay_out"
        assert conf == 0.6
        assert "No urgent signal" in reasons[0]

    def test_composite_confidence_with_multiple_rules(self) -> None:
        # rainfall + tire cliff + too late + undercut all match
        context = _make_context(
            rainfall=True,
            compound="soft",
            stint_age=20,
            gap_behind=2.0,
            opponent_fresher_tires=True,
            laps_remaining=5,
        )
        rec, conf, _ = predict_pit_decision(context)
        # rainfall has highest priority among matching rules -> "pit_now"
        assert rec == "pit_now"
        # Composite formula: 0.5 + 0.45 * (4/5) = 0.86, but capped at 0.95
        assert conf == pytest.approx(0.5 + 0.45 * (4 / 5), 0.01)

    def test_confidence_capped_at_0_95(self) -> None:
        context = _make_context(
            safety_car_active=True,
            rainfall=True,
            compound="soft",
            stint_age=20,
            gap_behind=2.0,
            opponent_fresher_tires=True,
            laps_remaining=5,
        )
        _, conf, _ = predict_pit_decision(context)
        assert conf == 0.95


class TestPredictFinishPositionBand:
    """Tests for the rule-based finish position band baseline."""

    def test_default_position_mapping(self) -> None:
        class FakeSim:
            expected_position = 1

        for pos, expected_band in [
            (1, "P1-P3"),
            (3, "P1-P3"),
            (4, "P4-P6"),
            (7, "P7-P10"),
            (11, "P11-P15"),
            (16, "P16+"),
        ]:
            context = _make_context(position=pos, gap_ahead=10.0)
            band, _, _ = predict_finish_position_band(context, FakeSim())
            assert band == expected_band, f"Position {pos} should map to {expected_band}"

    def test_rule_1_front_runner_with_small_gap(self) -> None:
        class FakeSim:
            expected_position = 1

        context = _make_context(position=2, gap_ahead=3.0)
        band, _, reasons = predict_finish_position_band(context, FakeSim())
        assert band == "P1-P3"
        assert any("Strong pace" in r for r in reasons)

    def test_rule_3_large_gap_pushes_to_midfield(self) -> None:
        class FakeSim:
            expected_position = 8

        context = _make_context(position=5, gap_ahead=35.0)
        band, _, reasons = predict_finish_position_band(context, FakeSim())
        assert band == "P7-P10"
        assert any("Substantial gap" in r for r in reasons)

    def test_rule_3_very_large_gap_pushes_to_back(self) -> None:
        class FakeSim:
            expected_position = 18

        context = _make_context(position=15, gap_ahead=95.0)
        band, _, reasons = predict_finish_position_band(context, FakeSim())
        assert band == "P16+"
        assert any("Large gap" in r for r in reasons)

    def test_rule_2_safety_car_improves_band(self) -> None:
        class FakeSim:
            expected_position = 8

        context = _make_context(position=8, gap_ahead=10.0, safety_car_active=True)
        band, _, reasons = predict_finish_position_band(context, FakeSim())
        # Default for position 8 is P7-P10, improves by one tier -> P4-P6
        assert band == "P4-P6"
        assert any("Safety car" in r for r in reasons)

    def test_safety_car_cannot_improve_past_p1_p3(self) -> None:
        class FakeSim:
            expected_position = 1

        context = _make_context(position=1, gap_ahead=1.0, safety_car_active=True)
        band, _, _ = predict_finish_position_band(context, FakeSim())
        assert band == "P1-P3"
