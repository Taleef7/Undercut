from sim.scoring import (
    ScenarioContext,
    StrategyDecision,
    get_grade_label,
    score_decision,
)


def test_score_decision_returns_model_recommendation_without_nameerror() -> None:
    context = ScenarioContext(
        driver="VER",
        lap=32,
        position=5,
        compound="medium",
        stint_age=12,
        gap_ahead=1.2,
        gap_behind=0.8,
        laps_remaining=20,
    )
    decision = StrategyDecision(action="stay_out")
    simulated_positions = {"stay_out": 3}

    result = score_decision(
        decision=decision,
        context=context,
        historical_decision="stay_out",
        simulated_positions=simulated_positions,
    )

    assert result["model_recommendation"] == "pit_now"


def test_get_grade_label_uses_rubric_labels() -> None:
    assert get_grade_label(95) == "Masterful"
    assert get_grade_label(80) == "Strong call"
    assert get_grade_label(70) == "Strong call"
    assert get_grade_label(55) == "Inspired call"
    assert get_grade_label(35) == "Risky"
    assert get_grade_label(15) == "Off the wall"


def test_score_decision_uses_strong_call_for_historical_match() -> None:
    context = ScenarioContext(
        driver="VER",
        lap=32,
        position=2,
        compound="medium",
        stint_age=12,
        gap_ahead=1.2,
        gap_behind=0.8,
        laps_remaining=20,
    )
    decision = StrategyDecision(action="stay_out")
    simulated_positions = {"stay_out": 2}

    result = score_decision(
        decision=decision,
        context=context,
        historical_decision="stay_out",
        simulated_positions=simulated_positions,
    )

    assert result["grade"] == "Strong call"


def test_score_decision_uses_inspired_call_for_gain() -> None:
    context = ScenarioContext(
        driver="VER",
        lap=32,
        position=5,
        compound="medium",
        stint_age=12,
        gap_ahead=1.2,
        gap_behind=0.8,
        laps_remaining=20,
    )
    decision = StrategyDecision(action="pit_now")
    simulated_positions = {"pit_now": 3}

    result = score_decision(
        decision=decision,
        context=context,
        historical_decision="stay_out",
        simulated_positions=simulated_positions,
    )

    assert result["grade"] == "Inspired call"
