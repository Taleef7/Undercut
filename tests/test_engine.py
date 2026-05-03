from sim.engine import UndercutEngine
from sim.scoring import ScenarioContext, StrategyDecision


def test_engine_uses_circuit_base_lap_time():
    engine = UndercutEngine(circuit="interlagos")
    context = ScenarioContext(
        driver="VER",
        lap=32,
        position=2,
        compound="medium",
        stint_age=14,
        gap_ahead=1.2,
        gap_behind=4.8,
        laps_remaining=39,
    )
    decision = StrategyDecision(action="stay_out")
    result = engine.simulate_decision(decision, context, historical_decision="stay_out")
    assert 75500 <= result.estimated_lap_time <= 77000
