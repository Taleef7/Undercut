# Sprints A+B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the backend API + scoring and expand the DuckDB schema to the canonical model, with enriched decision points and a real API contract.

**Architecture:** Add canonical schema migrations and seeds, regenerate the DuckDB database, enrich decision points with race_state fields, refactor sim + API to use column-based reads, and document the contract. Simulation remains heuristic, but contract aligns with AGENTS.md.

**Tech Stack:** Python 3.11, DuckDB, FastAPI, Pydantic v2, FastF1, uv.

---

## File Map (create/modify)

**Create**
- `sim/circuit_config.py`
- `api/models.py`
- `db/migrations/001_core_dimensions.sql`
- `db/migrations/002_fact_tables.sql`
- `db/migrations/003_race_state.sql`
- `db/migrations/004_feature_store.sql`
- `db/migrations/005_corrections.sql`
- `db/seeds/seed_compounds.sql`
- `db/seeds/seed_circuits.sql`
- `db/apply_migrations.py`
- `docs/api_contract.md`

**Modify**
- `sim/scoring.py`
- `sim/engine.py`
- `api/main.py`
- `ingest/load_decision_points.py`
- `data/decision_points/brazil_2024.yaml`
- (optional legacy) `ingest/schema.sql` (do not use for schema creation; leave intact)

---

### Task 1: Fix scoring bug and align scoring output

**Files:**
- Modify: `sim/scoring.py`

- [ ] **Step 1: Write failing test for sim_position NameError**

Create `tests/test_scoring.py` with:

```python
from sim.scoring import StrategyDecision, ScenarioContext, score_decision


def test_score_decision_assigns_sim_position_for_historical_action():
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
    result = score_decision(
        decision=decision,
        context=context,
        historical_decision="stay_out",
        simulated_positions={"stay_out": 2},
    )
    assert result["model_recommendation"] in {"pit_now", "stay_out"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scoring.py -v`

Expected: FAIL with `NameError: name 'sim_position' is not defined`.

- [ ] **Step 3: Implement fix in sim/scoring.py**

Update `score_decision` to assign sim_position before branching and use it for `model_recommendation`:

```python
    user_action = decision.action
    historical_action = historical_decision

    sim_position = simulated_positions.get(user_action, context.position)

    # Basic scoring logic
    score = 0
    grade = "Poor"
    explanation = ""

    if user_action == historical_action:
        score = 75
        grade = "Solid call"
        explanation = "You made the same call as the real team!"
    else:
        if sim_position < context.position:
            score = 90
            grade = "Strong call"
            explanation = (
                f"Simulation suggests you could have gained {context.position - sim_position} position(s)"
            )
        elif sim_position == context.position:
            score = 60
            grade = "Risky"
            explanation = "Simulation suggests similar outcome, but risky given the conditions"
        else:
            score = 40
            grade = "Poor call"
            explanation = "Simulation suggests your choice would have cost positions"

    return {
        "score": score,
        "grade": grade,
        "explanation": explanation,
        "historical_decision": historical_action,
        "model_recommendation": "pit_now" if sim_position < context.position else "stay_out",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scoring.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_scoring.py sim/scoring.py
git commit -m "fix: avoid scoring NameError"
```

---

### Task 2: Add circuit config and use base lap time in engine

**Files:**
- Create: `sim/circuit_config.py`
- Modify: `sim/engine.py`

- [ ] **Step 1: Write failing test for base lap time lookup**

Create `tests/test_engine.py`:

```python
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
    assert result.estimated_lap_time < 90000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -v`

Expected: FAIL because base lap time is hardcoded to 90000.

- [ ] **Step 3: Implement circuit config + engine lookup**

Create `sim/circuit_config.py`:

```python
CIRCUIT_CONFIG = {
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
```

Update `sim/engine.py`:

```python
from .circuit_config import CIRCUIT_CONFIG

...
        circuit_config = CIRCUIT_CONFIG.get(self.circuit, {})
        base_lap_time_ms = circuit_config.get("base_lap_time_ms", 90000)
        est_lap_time = estimate_lap_time(
            base_lap_time_ms=base_lap_time_ms,
            tire_state=tire_state,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sim/circuit_config.py sim/engine.py tests/test_engine.py
git commit -m "feat: add circuit config base lap times"
```

---

### Task 3: Add canonical schema migrations + seeds

**Files:**
- Create: `db/migrations/001_core_dimensions.sql`
- Create: `db/migrations/002_fact_tables.sql`
- Create: `db/migrations/003_race_state.sql`
- Create: `db/migrations/004_feature_store.sql`
- Create: `db/migrations/005_corrections.sql`
- Create: `db/seeds/seed_compounds.sql`
- Create: `db/seeds/seed_circuits.sql`
- Create: `db/apply_migrations.py`

- [ ] **Step 1: Write migration files**

Create `db/migrations/001_core_dimensions.sql` with:

```sql
CREATE TABLE IF NOT EXISTS dim_season (
    season_id VARCHAR PRIMARY KEY,
    year INT,
    regulations_era_label VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_meeting (
    meeting_id VARCHAR PRIMARY KEY,
    season_id VARCHAR,
    round_number INT,
    meeting_name VARCHAR,
    official_event_name VARCHAR,
    country VARCHAR,
    location VARCHAR,
    circuit_id VARCHAR,
    start_date DATE,
    end_date DATE,
    source_system VARCHAR,
    source_meeting_key VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_circuit (
    circuit_id VARCHAR PRIMARY KEY,
    circuit_ref VARCHAR,
    circuit_name VARCHAR,
    location VARCHAR,
    country VARCHAR,
    latitude DOUBLE,
    longitude DOUBLE,
    altitude INT,
    track_length_km DOUBLE,
    typical_pit_loss_seconds DOUBLE,
    overtaking_difficulty_score DOUBLE,
    safety_car_probability_baseline DOUBLE,
    source_system VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_session (
    session_id VARCHAR PRIMARY KEY,
    meeting_id VARCHAR,
    season_id VARCHAR,
    session_name VARCHAR,
    session_type VARCHAR,
    session_date DATE,
    session_start_time_utc TIMESTAMP,
    is_race BOOLEAN,
    is_qualifying BOOLEAN,
    is_sprint BOOLEAN,
    source_system VARCHAR,
    source_session_key VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_constructor (
    constructor_id VARCHAR PRIMARY KEY,
    constructor_ref VARCHAR,
    constructor_name VARCHAR,
    nationality VARCHAR,
    source_system VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_tyre_compound (
    tyre_compound_id VARCHAR PRIMARY KEY,
    compound_label VARCHAR,
    compound_category VARCHAR,
    compound_code VARCHAR,
    compound_hardness_order INT,
    is_wet BOOLEAN,
    is_intermediate BOOLEAN,
    is_slick BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create `db/migrations/002_fact_tables.sql` with:

```sql
CREATE TABLE IF NOT EXISTS fact_driver_session_entry (
    driver_session_entry_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    driver_number INT,
    team_name_source VARCHAR,
    is_replacement_driver BOOLEAN DEFAULT FALSE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_session_result (
    session_result_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    position_order INT,
    classified_position VARCHAR,
    points DOUBLE,
    status VARCHAR,
    status_normalized VARCHAR,
    laps_completed INT,
    time_milliseconds BIGINT,
    fastest_lap_rank INT,
    fastest_lap_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_weather_sample (
    weather_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    sample_time TIMESTAMP,
    lap_number INT,
    air_temperature DOUBLE,
    track_temperature DOUBLE,
    humidity DOUBLE,
    pressure DOUBLE,
    rainfall BOOLEAN,
    wind_speed DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_race_control_event (
    race_control_event_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    event_time TIMESTAMP,
    lap_number INT,
    category VARCHAR,
    message VARCHAR,
    flag VARCHAR,
    scope VARCHAR,
    driver_id VARCHAR,
    normalized_event_type VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_interval_sample (
    interval_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    gap_to_leader_seconds DOUBLE,
    interval_to_ahead_seconds DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create `db/migrations/003_race_state.sql` with:

```sql
CREATE TABLE IF NOT EXISTS race_state_driver_lap_fact (
    race_state_driver_lap_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    lap_number INT,
    race_lap_pct DOUBLE,
    laps_remaining INT,
    current_position INT,
    starting_position INT,
    positions_gained_lost INT,
    gap_to_leader_seconds DOUBLE,
    interval_ahead_seconds DOUBLE,
    interval_behind_seconds DOUBLE,
    driver_ahead_id VARCHAR,
    driver_behind_id VARCHAR,
    current_compound_id VARCHAR,
    current_compound_label VARCHAR,
    stint_number INT,
    stint_age_laps INT,
    total_pit_stops INT,
    last_pit_lap INT,
    lap_time_ms DOUBLE,
    rolling_3_lap_avg_ms DOUBLE,
    rolling_5_lap_avg_ms DOUBLE,
    pace_delta_to_field_ms DOUBLE,
    track_status_normalized VARCHAR,
    safety_car_active_flag BOOLEAN,
    virtual_safety_car_active_flag BOOLEAN,
    red_flag_active_flag BOOLEAN,
    rainfall_flag BOOLEAN,
    air_temperature DOUBLE,
    track_temperature DOUBLE,
    pit_window_open_flag BOOLEAN,
    undercut_threat_flag BOOLEAN,
    overcut_opportunity_flag BOOLEAN,
    source_coverage_quality VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS race_state_field_lap (
    race_state_field_lap_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    lap_number INT,
    leader_driver_id VARCHAR,
    total_running_drivers INT,
    total_retired_drivers INT,
    safety_car_active_flag BOOLEAN,
    virtual_safety_car_active_flag BOOLEAN,
    red_flag_active_flag BOOLEAN,
    rainfall_flag BOOLEAN,
    average_lap_time_ms DOUBLE,
    median_lap_time_ms DOUBLE,
    fastest_lap_time_ms DOUBLE,
    number_on_soft INT,
    number_on_medium INT,
    number_on_hard INT,
    number_on_intermediate INT,
    number_on_wet INT,
    field_spread_seconds DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS race_state_decision_point (
    decision_point_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    decision_type VARCHAR,
    scenario_title VARCHAR,
    scenario_description VARCHAR,
    available_actions_json VARCHAR,
    actual_decision VARCHAR,
    actual_outcome_summary VARCHAR,
    explanation_short VARCHAR,
    explanation_long VARCHAR,
    current_position INT,
    gap_ahead_seconds DOUBLE,
    gap_behind_seconds DOUBLE,
    compound VARCHAR,
    stint_age_laps INT,
    laps_remaining INT,
    track_temperature_c DOUBLE,
    air_temperature_c DOUBLE,
    rainfall BOOLEAN,
    track_status VARCHAR,
    safety_car_active BOOLEAN,
    virtual_safety_car_active BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create `db/migrations/004_feature_store.sql` with:

```sql
CREATE TABLE IF NOT EXISTS feature_pit_decision (
    feature_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    laps_remaining INT,
    current_position INT,
    gap_ahead_seconds DOUBLE,
    gap_behind_seconds DOUBLE,
    stint_age_laps INT,
    compound_hardness_order INT,
    rolling_3_lap_avg_ms DOUBLE,
    pace_delta_to_field_ms DOUBLE,
    safety_car_active_flag BOOLEAN,
    vsc_active_flag BOOLEAN,
    rainfall_flag BOOLEAN,
    track_temperature DOUBLE,
    pit_loss_estimate_seconds DOUBLE,
    actual_pitted_within_3_laps BOOLEAN,
    final_position_after_pit INT,
    feature_version VARCHAR DEFAULT 'v0.1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_undercut_opportunity (
    feature_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    target_driver_id VARCHAR,
    lap_number INT,
    gap_to_target_seconds DOUBLE,
    target_stint_age_laps INT,
    own_stint_age_laps INT,
    own_compound VARCHAR,
    target_compound VARCHAR,
    pit_loss_estimate_seconds DOUBLE,
    circuit_overtaking_difficulty DOUBLE,
    undercut_succeeded BOOLEAN,
    feature_version VARCHAR DEFAULT 'v0.1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create `db/migrations/005_corrections.sql` with:

```sql
CREATE TABLE IF NOT EXISTS manual_data_correction (
    correction_id VARCHAR PRIMARY KEY,
    target_table VARCHAR,
    target_record_key VARCHAR,
    field_name VARCHAR,
    old_value VARCHAR,
    new_value VARCHAR,
    correction_reason VARCHAR,
    source_reference VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Create `db/seeds/seed_compounds.sql`:

```sql
INSERT INTO dim_tyre_compound (
    tyre_compound_id,
    compound_label,
    compound_category,
    compound_code,
    compound_hardness_order,
    is_wet,
    is_intermediate,
    is_slick
) VALUES
('SOFT', 'Soft', 'slick', 'S', 1, FALSE, FALSE, TRUE),
('MEDIUM', 'Medium', 'slick', 'M', 2, FALSE, FALSE, TRUE),
('HARD', 'Hard', 'slick', 'H', 3, FALSE, FALSE, TRUE),
('INTERMEDIATE', 'Intermediate', 'wet', 'I', 4, FALSE, TRUE, FALSE),
('WET', 'Wet', 'wet', 'W', 5, TRUE, FALSE, FALSE),
('C1', 'C1', 'slick', 'C1', 1, FALSE, FALSE, TRUE),
('C2', 'C2', 'slick', 'C2', 2, FALSE, FALSE, TRUE),
('C3', 'C3', 'slick', 'C3', 3, FALSE, FALSE, TRUE),
('C4', 'C4', 'slick', 'C4', 4, FALSE, FALSE, TRUE),
('C5', 'C5', 'slick', 'C5', 5, FALSE, FALSE, TRUE);
```

Create `db/seeds/seed_circuits.sql`:

```sql
INSERT INTO dim_circuit (
    circuit_id,
    circuit_ref,
    circuit_name,
    location,
    country,
    track_length_km,
    typical_pit_loss_seconds,
    overtaking_difficulty_score,
    safety_car_probability_baseline,
    source_system
) VALUES
('interlagos', 'interlagos', 'Interlagos', 'Sao Paulo', 'Brazil', 4.309, 22.0, 0.60, 0.35, 'manual'),
('monaco', 'monaco', 'Monaco', 'Monte Carlo', 'Monaco', 3.337, 18.0, 0.95, 0.55, 'manual'),
('silverstone', 'silverstone', 'Silverstone', 'Silverstone', 'UK', 5.891, 19.0, 0.70, 0.30, 'manual'),
('spa', 'spa', 'Spa-Francorchamps', 'Stavelot', 'Belgium', 7.004, 24.0, 0.55, 0.25, 'manual'),
('monza', 'monza', 'Monza', 'Monza', 'Italy', 5.793, 23.0, 0.45, 0.30, 'manual'),
('hungaroring', 'hungaroring', 'Hungaroring', 'Mogyorod', 'Hungary', 4.381, 20.0, 0.85, 0.35, 'manual'),
('suzuka', 'suzuka', 'Suzuka', 'Suzuka', 'Japan', 5.807, 21.0, 0.70, 0.35, 'manual'),
('las_vegas', 'las_vegas', 'Las Vegas', 'Las Vegas', 'USA', 6.201, 22.0, 0.35, 0.30, 'manual'),
('yas_marina', 'yas_marina', 'Yas Marina', 'Abu Dhabi', 'UAE', 5.281, 20.0, 0.55, 0.25, 'manual'),
('albert_park', 'albert_park', 'Albert Park', 'Melbourne', 'Australia', 5.278, 20.0, 0.60, 0.40, 'manual');
```

Create `db/apply_migrations.py`:

```python
from pathlib import Path
import duckdb


ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "undercut.db"
MIGRATIONS_DIR = ROOT / "db" / "migrations"


def apply_migrations() -> None:
    conn = duckdb.connect(str(DB_PATH))
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))
    conn.close()


if __name__ == "__main__":
    apply_migrations()
```

- [ ] **Step 2: Run migrations to validate**

Run: `uv run python db/apply_migrations.py`

Expected: no errors.

- [ ] **Step 3: Run seeds**

Run:

```bash
uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); conn.execute(open('db/seeds/seed_compounds.sql').read()); conn.execute(open('db/seeds/seed_circuits.sql').read()); conn.close()"
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add db/migrations db/seeds db/apply_migrations.py
git commit -m "feat: add canonical schema migrations"
```

---

### Task 4: Update decision-point YAML + loader for race_state fields

**Files:**
- Modify: `data/decision_points/brazil_2024.yaml`
- Modify: `ingest/load_decision_points.py`

- [ ] **Step 1: Update YAML schema (normalize decision_type + add race_state)**

Update `data/decision_points/brazil_2024.yaml` to:

```yaml
- id: "brazil_2024_lap32"
  session_id: "R"
  driver_id: "VER"
  lap_number: 32
  decision_type: "pit_now_vs_stay_out"
  scenario_title: "VER vs NOR battle - pit decision under pressure"
  scenario_description: |
    Lap 32 of the 2024 Brazilian GP. Verstappen is pressuring Norris for P2.
    Your driver is VER. Medium tires are 14 laps old. Gap to Norris is 1.2 seconds.
    Rain is starting to fall. Team asks: pit now or stay out?
  available_actions:
    - "pit_now_inter"
    - "pit_now_hard"
    - "stay_out"
    - "extend_stint"
  actual_decision: "stay_out"
  actual_outcome_summary: "VER stayed out, passed Norris on track, won the race"
  explanation_short: "Staying out was the right call - wet track favored experienced drivers"
  explanation_long: |
    By pitting earlier, VER would have lost track position to Norris who had
    fresher tires. By staying out, VER inherited the lead when Norris pitted
    and controlled the race from the front in wet conditions.
  race_state:
    current_position: 2
    gap_ahead_seconds: 1.2
    gap_behind_seconds: 4.8
    compound: "medium"
    stint_age_laps: 14
    laps_remaining: 39
    track_temperature_c: 48
    air_temperature_c: 29
    rainfall: false
    track_status: "green"
    safety_car_active: false
    virtual_safety_car_active: false

- id: "brazil_2024_lap48"
  session_id: "R"
  driver_id: "VER"
  lap_number: 48
  decision_type: "switch_to_wet"
  scenario_title: "Rain starting - wet weather call"
  scenario_description: |
    Lap 48. Light rain has started. Track is drying but conditions are tricky.
    Your driver is VER on intermediate tires, 18 laps old. Gap to P2 is 4.5 seconds.
    Team asks: stay on inters or switch to wets?
  available_actions:
    - "stay_inter"
    - "pit_wet"
    - "wait_and_see"
  actual_decision: "stay_inter"
  actual_outcome_summary: "VER stayed on inters, built lead, won the race"
  explanation_short: "Inters were the right call - track was mostly dry"
  explanation_long: ""
  race_state:
    current_position: 1
    gap_ahead_seconds: null
    gap_behind_seconds: 4.5
    compound: "intermediate"
    stint_age_laps: 18
    laps_remaining: 23
    track_temperature_c: 24
    air_temperature_c: 20
    rainfall: true
    track_status: "green"
    safety_car_active: false
    virtual_safety_car_active: false

- id: "brazil_2024_lap68"
  session_id: "R"
  driver_id: "VER"
  lap_number: 68
  decision_type: "extend_to_end"
  scenario_title: "Final stint - tire management"
  scenario_description: |
    Lap 68 (final lap). VER is leading on hard tires, 28 laps old.
    Gap to P2 is 12 seconds. Race is essentially over.
    Team asks: push for fastest lap or manage to the finish?
  available_actions:
    - "push"
    - "manage"
    - "ease_off"
  actual_decision: "manage"
  actual_outcome_summary: "VER took the flag, finished P1"
  explanation_short: "No point risking it - race was won"
  explanation_long: ""
  race_state:
    current_position: 1
    gap_ahead_seconds: null
    gap_behind_seconds: 12.0
    compound: "hard"
    stint_age_laps: 28
    laps_remaining: 3
    track_temperature_c: 26
    air_temperature_c: 20
    rainfall: false
    track_status: "green"
    safety_car_active: false
    virtual_safety_car_active: false
```

Note: Replace race_state numeric values above with exact FastF1-derived values before final save.

- [ ] **Step 2: Update loader to insert race_state fields**

Modify `ingest/load_decision_points.py`:

```python
        race_state = dp.get("race_state", {})
        conn.execute(
            """
            INSERT INTO race_state_decision_point 
            (decision_point_id, session_id, driver_id, lap_number, decision_type,
             scenario_title, scenario_description, available_actions_json,
             actual_decision, actual_outcome_summary, explanation_short, explanation_long,
             current_position, gap_ahead_seconds, gap_behind_seconds, compound,
             stint_age_laps, laps_remaining, track_temperature_c, air_temperature_c,
             rainfall, track_status, safety_car_active, virtual_safety_car_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dp.get("id"),
                dp.get("session_id"),
                dp.get("driver_id"),
                dp.get("lap_number"),
                dp.get("decision_type"),
                dp.get("scenario_title"),
                dp.get("scenario_description"),
                actions_json,
                dp.get("actual_decision"),
                dp.get("actual_outcome_summary"),
                dp.get("explanation_short"),
                dp.get("explanation_long"),
                race_state.get("current_position"),
                race_state.get("gap_ahead_seconds"),
                race_state.get("gap_behind_seconds"),
                race_state.get("compound"),
                race_state.get("stint_age_laps"),
                race_state.get("laps_remaining"),
                race_state.get("track_temperature_c"),
                race_state.get("air_temperature_c"),
                race_state.get("rainfall"),
                race_state.get("track_status"),
                race_state.get("safety_car_active"),
                race_state.get("virtual_safety_car_active"),
            )
        )
```

- [ ] **Step 3: Run loader after regenerating DB**

Run: `uv run python -m ingest.load_decision_points data/decision_points/brazil_2024.yaml`

- [ ] **Step 4: Commit**

```bash
git add data/decision_points/brazil_2024.yaml ingest/load_decision_points.py
git commit -m "feat: enrich decision points race state"
```

---

### Task 5: Refactor API models + endpoints + CORS

**Files:**
- Create: `api/models.py`
- Modify: `api/main.py`

- [ ] **Step 1: Add Pydantic models**

Create `api/models.py`:

```python
from typing import List, Optional
from pydantic import BaseModel


class ScenarioSummary(BaseModel):
    decision_point_id: str
    scenario_title: str
    scenario_description: str
    driver_id: str
    lap_number: int
    decision_type: str
    available_actions: List[str]
    difficulty_level: Optional[str] = None


class ScenarioDetail(ScenarioSummary):
    actual_decision: str
    actual_outcome_summary: str
    explanation_short: str
    explanation_long: str
    current_position: int
    gap_ahead_seconds: Optional[float]
    gap_behind_seconds: Optional[float]
    compound: str
    stint_age_laps: int
    laps_remaining: int
    track_temperature_c: Optional[float]
    air_temperature_c: Optional[float]
    rainfall: Optional[bool]
    track_status: Optional[str]
    safety_car_active: Optional[bool]
    virtual_safety_car_active: Optional[bool]


class SimulationSummary(BaseModel):
    expected_position: int
    expected_finish_position_band: Optional[str]
    risk_score: float
    tire_risk: Optional[str]
    track_position_risk: Optional[str]


class DecisionResponse(BaseModel):
    scenario_id: str
    user_action: str
    score: int
    grade: str
    historical_decision: str
    model_recommendation: str
    model_confidence: Optional[float]
    model_top_features: List[str]
    simulation_summary: SimulationSummary
    explanation: str
    tradeoffs: List[str]
```

- [ ] **Step 2: Refactor API endpoints and add CORS**

Modify `api/main.py` to:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import duckdb
from pathlib import Path
from sim.engine import UndercutEngine
from sim.scoring import StrategyDecision, ScenarioContext
from api.models import ScenarioSummary, ScenarioDetail, DecisionResponse, SimulationSummary

app = FastAPI(title="Undercut API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "undercut.db"


@app.get("/")
def read_root():
    return {"message": "Undercut API is running"}


@app.get("/scenarios", response_model=List[ScenarioSummary])
def get_scenarios():
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute("SELECT * FROM race_state_decision_point").fetchdf()
    conn.close()
    records = []
    for row in df.to_dict(orient="records"):
        records.append(
            ScenarioSummary(
                decision_point_id=row["decision_point_id"],
                scenario_title=row["scenario_title"],
                scenario_description=row["scenario_description"],
                driver_id=row["driver_id"],
                lap_number=row["lap_number"],
                decision_type=row["decision_type"],
                available_actions=json.loads(row["available_actions_json"]),
                difficulty_level=row.get("difficulty_level"),
            )
        )
    return records


@app.get("/scenarios/{decision_id}", response_model=ScenarioDetail)
def get_scenario(decision_id: str):
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?",
        (decision_id,),
    ).fetchdf()
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Scenario not found")

    row = df.to_dict(orient="records")[0]
    return ScenarioDetail(
        decision_point_id=row["decision_point_id"],
        scenario_title=row["scenario_title"],
        scenario_description=row["scenario_description"],
        driver_id=row["driver_id"],
        lap_number=row["lap_number"],
        decision_type=row["decision_type"],
        available_actions=json.loads(row["available_actions_json"]),
        difficulty_level=row.get("difficulty_level"),
        actual_decision=row["actual_decision"],
        actual_outcome_summary=row["actual_outcome_summary"],
        explanation_short=row["explanation_short"],
        explanation_long=row["explanation_long"],
        current_position=row["current_position"],
        gap_ahead_seconds=row["gap_ahead_seconds"],
        gap_behind_seconds=row["gap_behind_seconds"],
        compound=row["compound"],
        stint_age_laps=row["stint_age_laps"],
        laps_remaining=row["laps_remaining"],
        track_temperature_c=row["track_temperature_c"],
        air_temperature_c=row["air_temperature_c"],
        rainfall=row["rainfall"],
        track_status=row["track_status"],
        safety_car_active=row["safety_car_active"],
        virtual_safety_car_active=row["virtual_safety_car_active"],
    )


class DecisionRequest(BaseModel):
    action: str
    compound: Optional[str] = None


@app.post("/scenarios/{decision_id}/decision", response_model=DecisionResponse)
def submit_decision(decision_id: str, request: DecisionRequest):
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?",
        (decision_id,),
    ).fetchdf()
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="Scenario not found")

    row = df.to_dict(orient="records")[0]
    available_actions = json.loads(row["available_actions_json"])
    if request.action not in available_actions:
        raise HTTPException(status_code=422, detail="Invalid action")

    context = ScenarioContext(
        driver=row["driver_id"],
        lap=row["lap_number"],
        position=row["current_position"],
        compound=row["compound"],
        stint_age=row["stint_age_laps"],
        gap_ahead=row["gap_ahead_seconds"] or 0.0,
        gap_behind=row["gap_behind_seconds"] or 0.0,
        laps_remaining=row["laps_remaining"],
    )

    engine = UndercutEngine(circuit="interlagos")
    sim_result = engine.simulate_decision(
        StrategyDecision(action=request.action, compound=request.compound),
        context,
        row["actual_decision"],
    )

    score_data = engine.evaluate_strategy(
        StrategyDecision(action=request.action, compound=request.compound),
        context,
        row["actual_decision"],
    )

    simulation_summary = SimulationSummary(
        expected_position=sim_result.expected_position,
        expected_finish_position_band=None,
        risk_score=sim_result.risk_score,
        tire_risk=None,
        track_position_risk=None,
    )

    return DecisionResponse(
        scenario_id=row["decision_point_id"],
        user_action=request.action,
        score=score_data["score"],
        grade=score_data["grade"],
        historical_decision=row["actual_decision"],
        model_recommendation=score_data["model_recommendation"],
        model_confidence=None,
        model_top_features=[],
        simulation_summary=simulation_summary,
        explanation=score_data["explanation"],
        tradeoffs=[],
    )
```

- [ ] **Step 3: Run API smoke test**

Run: `uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000`

Check:
- `GET http://127.0.0.1:8000/scenarios`
- `GET http://127.0.0.1:8000/scenarios/brazil_2024_lap32`

- [ ] **Step 4: Commit**

```bash
git add api/main.py api/models.py
git commit -m "feat: add typed scenario API"
```

---

### Task 6: Regenerate DuckDB + reload decision points

**Files:**
- Modify database at `data/undercut.db`

- [ ] **Step 1: Delete dev DB**

Run: `Remove-Item -Force data/undercut.db`

- [ ] **Step 2: Apply migrations + seeds**

Run:

```bash
uv run python db/apply_migrations.py
uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); conn.execute(open('db/seeds/seed_compounds.sql').read()); conn.execute(open('db/seeds/seed_circuits.sql').read()); conn.close()"
```

- [ ] **Step 3: Load decision points**

Run: `uv run python -m ingest.load_decision_points data/decision_points/brazil_2024.yaml`

- [ ] **Step 4: Commit**

No commit (DB file is ignored).

---

### Task 7: Write API contract doc with real examples

**Files:**
- Create: `docs/api_contract.md`

- [ ] **Step 1: Fetch real example output**

Run API and call:

```bash
curl http://127.0.0.1:8000/scenarios/brazil_2024_lap32
curl -X POST http://127.0.0.1:8000/scenarios/brazil_2024_lap32/decision -H "Content-Type: application/json" -d '{"action": "stay_out"}'
```

Use actual responses as examples.

- [ ] **Step 2: Write `docs/api_contract.md`**

Include:
- Endpoint list and descriptions
- Request/response schemas
- Example payloads for all endpoints

- [ ] **Step 3: Commit**

```bash
git add docs/api_contract.md
git commit -m "docs: add api contract"
```

---

## Plan Self-Review

**Spec coverage:**
- Scoring bug fix: Task 1
- Circuit config + base lap time: Task 2
- Pydantic models + API refactor + CORS: Task 5
- YAML enrichment + loader: Task 4
- Canonical schema + migrations + seeds: Task 3
- Regenerate DB: Task 6
- API contract: Task 7

**Placeholder scan:**
- YAML race_state values are placeholders pending FastF1 ingest; must be replaced with exact values before final save.
- `tradeoffs` and ML fields are placeholders; allowed per spec.

**Type consistency:**
- All models and API fields match AGENTS.md names.
