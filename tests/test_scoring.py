from sim.scoring import ScenarioContext, StrategyDecision, score_decision


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
