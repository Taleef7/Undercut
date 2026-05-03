Full Agent Sprint Instructions
SPRINT A — Backend Hardening + API Contract (Do This First)
A1. Fix the scoring bug
In sim/scoring.py, refactor score_decision so sim_position is always assigned before it's referenced. The safe pattern:
pythonsim_position = simulated_positions.get(user_action, context.position)
model_rec = "pit_now" if sim_position < context.position else "stay_out"
Then restructure the scoring logic so matched-historical and sim-based paths both use sim_position safely.
A2. Add Pydantic response models to the API
Create api/models.py with typed response schemas:
pythonclass ScenarioSummary(BaseModel):
    decision_point_id: str
    scenario_title: str
    scenario_description: str
    driver_id: str
    lap_number: int
    decision_type: str
    available_actions: list[str]
    difficulty_level: Optional[str]

class SimulationResult(BaseModel):
    score: int
    grade: str
    explanation: str
    historical_decision: str
    model_recommendation: str
    expected_position: int
    risk_score: float
    simulation_summary: dict  # position_band, tire_risk, track_position_risk

class DecisionResponse(BaseModel):
    scenario_id: str
    user_action: str
    score: int
    grade: str
    historical_decision: str
    model_recommendation: str
    simulation_summary: SimulationSummary
    explanation: str
    tradeoffs: list[str]  # bullet points for the result screen
A3. Rewrite the API endpoints properly
GET /scenarios — return list[ScenarioSummary], use fetchdf() from DuckDB (returns a DataFrame with named columns), serialize properly.
GET /scenarios/{id} — return the full ScenarioSummary plus the scenario_description and explanation_long.
POST /scenarios/{id}/decision — read ALL fields from the DB record by column name, not by index. Pull gap_ahead, gap_behind, stint_age etc. from the race state view when available, or from enriched YAML fields (see A4 below).
A4. Enrich the YAML decision points with actual race state
The YAML currently has scenario descriptions in prose but doesn't have structured fields like gap_ahead, gap_behind, current_position, stint_age, laps_remaining, weather, track_status. Add these as explicit fields to each YAML scenario and to the race_state_decision_point schema:
yaml- id: "brazil_2024_lap32"
  ...
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
Add these columns to race_state_decision_point in the schema. The simulate endpoint should read from these columns, eliminating all hardcoded values.
A5. Add per-circuit base lap times to the engine config
Create sim/circuit_config.py:
pythonCIRCUIT_CONFIG = {
    "interlagos": {
        "base_lap_time_ms": 75500,
        "pit_loss_seconds": 22.0,
        "overtaking_difficulty": 0.6,
        "safety_car_probability": 0.35,
        "track_length_km": 4.309,
    },
    "monaco": {
        "base_lap_time_ms": 74000,
        "pit_loss_seconds": 18.0,
        "overtaking_difficulty": 0.95,
        "safety_car_probability": 0.55,
        "track_length_km": 3.337,
    },
    # add silverstone, spa, monza, hungary, suzuka, etc.
}
The UndercutEngine should pull base_lap_time_ms from this config keyed by circuit, not hardcode 90000.
A6. Add CORS middleware to FastAPI
The frontend can't talk to the backend without it:
pythonfrom fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
A7. Write docs/api_contract.md
After the above is done, document the exact request/response shapes for all three endpoints with real example payloads from Brazil 2024 data. This file is the contract the frontend agent works from.

SPRINT B — Schema Expansion Toward Full PROJECT_PLAN
The current 5-table schema is a prototype. Expand it toward the full canonical schema from the PROJECT_PLAN. Do this as an additive migration, not a rewrite.
B1. Add the full dimension tables
sql-- Add to schema.sql or create db/migrations/002_dimensions.sql

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
    session_type VARCHAR,  -- FP1, FP2, FP3, Qualifying, Sprint, Race
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
B2. Add the full fact tables
sql-- db/migrations/003_facts.sql

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
    classified_position VARCHAR,  -- can be 'R', 'DNF', 'DSQ', etc.
    points DOUBLE,
    status VARCHAR,
    status_normalized VARCHAR,  -- Finished, DNF, DNS, DSQ, NC
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
B3. Add the full race_state tables
sql-- db/migrations/004_race_state.sql

CREATE TABLE IF NOT EXISTS race_state_driver_lap_fact (
    -- This is the materialized table version; the view becomes derived from this
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
B4. Add the feature store tables
sql-- db/migrations/005_feature_store.sql

CREATE TABLE IF NOT EXISTS feature_pit_decision (
    feature_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    -- Features
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
    -- Labels
    actual_pitted_within_3_laps BOOLEAN,
    final_position_after_pit INT,
    -- Metadata
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
    -- Label
    undercut_succeeded BOOLEAN,
    feature_version VARCHAR DEFAULT 'v0.1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
B5. Add a manual corrections table
sqlCREATE TABLE IF NOT EXISTS manual_data_correction (
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
B6. Restructure the SQL files into a migrations folder
Move all SQL into:
db/
  migrations/
    001_core_dimensions.sql
    002_fact_tables.sql
    003_race_state.sql
    004_feature_store.sql
    005_corrections.sql
  seeds/
    seed_compounds.sql   ← insert the standard compound rows
    seed_circuits.sql    ← insert Brazil, Monaco, Silverstone, Spa etc. from circuit_config.py
  apply_migrations.py   ← script that runs migrations in order on DuckDB

SPRINT C — Data Ingestion Expansion
C1. Add a Jolpica client
Create ingest/jolpica_client.py. The Jolpica base URL is https://api.jolpi.ca/ergast/f1/. Key endpoints to implement:
pythonclass JolpicaClient:
    BASE_URL = "https://api.jolpi.ca/ergast/f1"
    
    def get_season_schedule(self, year: int) -> list[dict]: ...
    def get_race_results(self, year: int, round: int) -> dict: ...
    def get_qualifying_results(self, year: int, round: int) -> dict: ...
    def get_sprint_results(self, year: int, round: int) -> dict: ...
    def get_driver_standings(self, year: int, round: int) -> dict: ...
    def get_constructor_standings(self, year: int, round: int) -> dict: ...
    def get_drivers(self, year: int) -> list[dict]: ...
    def get_constructors(self, year: int) -> list[dict]: ...
    def get_circuits(self) -> list[dict]: ...
    def get_pit_stops(self, year: int, round: int) -> list[dict]: ...
    def get_lap_times(self, year: int, round: int, lap: int) -> list[dict]: ...
Implement with httpx, add retry logic, rate-limit awareness (1 req/s to be safe), and store raw JSON responses to data/raw/jolpica/ before normalizing.
C2. Add an OpenF1 client
Create ingest/openf1_client.py. Base URL: https://api.openf1.org/v1/. Implement:
pythonclass OpenF1Client:
    BASE_URL = "https://api.openf1.org/v1"
    
    def get_meetings(self, year: int) -> list[dict]: ...
    def get_sessions(self, meeting_key: int) -> list[dict]: ...
    def get_laps(self, session_key: int, driver_number: int = None) -> list[dict]: ...
    def get_stints(self, session_key: int) -> list[dict]: ...
    def get_pit_stops(self, session_key: int) -> list[dict]: ...
    def get_intervals(self, session_key: int) -> list[dict]: ...
    def get_positions(self, session_key: int) -> list[dict]: ...
    def get_weather(self, session_key: int) -> list[dict]: ...
    def get_race_control(self, session_key: int) -> list[dict]: ...
    def get_session_result(self, session_key: int) -> list[dict]: ...
    def get_starting_grid(self, session_key: int) -> list[dict]: ...
OpenF1 is available from 2023 onward. Store raw to data/raw/openf1/ partitioned by year/meeting_key/session_key/.
C3. Add normalization modules
Create ingest/normalize/:
normalize/
  normalize_circuits.py      ← Jolpica circuits → dim_circuit
  normalize_drivers.py       ← Jolpica drivers → dim_driver
  normalize_constructors.py  ← Jolpica constructors → dim_constructor
  normalize_sessions.py      ← OpenF1/Jolpica → dim_session + dim_meeting + dim_season
  normalize_laps.py          ← FastF1/OpenF1 laps → fact_lap
  normalize_stints.py        ← FastF1/OpenF1 stints → fact_stint
  normalize_pit_stops.py     ← FastF1/OpenF1 pit → fact_pit_stop
  normalize_results.py       ← Jolpica results → fact_session_result
  normalize_weather.py       ← OpenF1 weather → fact_weather_sample
  normalize_race_control.py  ← OpenF1 race_control → fact_race_control_event
Each normalizer should: load from raw JSON/parquet → validate → map to canonical schema → upsert into DuckDB using INSERT OR REPLACE.
C4. Build the race_state builder
Create ingest/build/build_race_state.py. This script reads from fact_lap, fact_stint, fact_pit_stop, fact_interval_sample, fact_weather_sample, fact_race_control_event and constructs race_state_driver_lap_fact and race_state_field_lap. Key derived columns:

stint_age_laps: lap_number - stint.lap_start
laps_remaining: total_laps - lap_number (needs total laps from session)
interval_behind_seconds: computed from position-sorted interval samples
driver_ahead_id, driver_behind_id: from position samples at that lap
safety_car_active_flag: from race_control events spanning that lap
rolling_3_lap_avg_ms, rolling_5_lap_avg_ms: windowed avg over fact_lap
pace_delta_to_field_ms: driver rolling avg minus field median rolling avg
undercut_threat_flag: interval_behind < 2.0 AND rival stint_age > own stint_age + 5
pit_window_open_flag: stint_age > compound optimal window start (from tire model)

C5. Build the feature store builder
Create ingest/build/build_features.py. Reads from race_state_driver_lap_fact and constructs feature_pit_decision and feature_undercut_opportunity. For feature_pit_decision, the label actual_pitted_within_3_laps is computed by checking if there's a fact_pit_stop within 3 laps of the current row for that driver/session.
C6. Add a CLI orchestration command
Create ingest/run_pipeline.py:
bash# Usage examples:
uv run python -m ingest.run_pipeline bootstrap --source jolpica --seasons 2018 2019 2020 2021 2022 2023 2024
uv run python -m ingest.run_pipeline fetch-weekend --season 2024 --round 21  # Brazil
uv run python -m ingest.run_pipeline normalize --season 2024 --round 21
uv run python -m ingest.run_pipeline build-race-state --season 2024 --round 21
uv run python -m ingest.run_pipeline build-features --season 2024 --round 21

SPRINT D — Expand Decision Points
D1. Add 3 more races as YAML decision points
Good candidates that have well-documented dramatic strategy moments:

Abu Dhabi 2021, Lap 53 — The safety car restart. VER vs HAM tire choice. Decision: pit for softs vs stay on worn hards.
Singapore 2023, Lap 40 — ALO defending against PER. Decision: extend stint on hards or pit for coverage.
Hungary 2022, Lap 38 — SAI strategy blunder reference point. Decision: pit for softs when leading vs stay out.

Each YAML should have the full race_state block with real numbers, not approximations. Pull actual figures from FastF1 before writing the YAML.
D2. Add more decision types
Current scenarios are all pit_now_vs_stay_out or switch_to_wet. Add:

cover_undercut — rival behind just pitted, do you cover?
safety_car_pit — SC just deployed, pit now or stay out?
extend_to_end — can you make the tires last to the flag?


SPRINT E — Frontend
E1. Bootstrap
bashcd web
npm create vite@latest . -- --template react-ts
npm install tailwindcss @tailwindcss/vite shadcn-ui
npx shadcn@latest init
Configure VITE_API_BASE_URL from .env. Create web/src/api/client.ts with typed fetch wrappers for all three endpoints.
E2. Scenario Play Screen (build this first)
Dark theme, cockpit feel. Layout:
┌─────────────────────────────────────────────────────┐
│  🏁 2024 Brazilian GP  •  LAP 32/71  •  INTERLAGOS  │
├──────────────────┬──────────────────────────────────┤
│  Max Verstappen  │  📻 "Box, box? The mediums are  │
│  P2              │   starting to go. Rain coming."  │
│  ▲ 1.2s to NOR   │                                  │
│  ▼ 4.8s to HAM   │                                  │
├──────────────────┴──────────────────────────────────┤
│  MEDIUM • 14 laps old  •  ⚠️ approaching cliff      │
│  Track: 48°C  •  🌧 Rain probability rising          │
├─────────────────────────────────────────────────────┤
│  WHAT'S YOUR CALL?                                  │
│                                                     │
│  [ PIT NOW — INTERS ]  [ PIT NOW — HARDS ]         │
│  [ STAY OUT ]           [ EXTEND STINT ]            │
└─────────────────────────────────────────────────────┘
On action click: POST to /scenarios/{id}/decision, show loading state, then navigate to result screen.
E3. Result Screen
Large score number (animated count-up). Grade label styled by tier (Masterful = gold, Strong = green, Risky = amber, Poor = red). Then:

"You chose: [action]" vs "Real team chose: [historical]"
ML recommendation badge
Simulation outcome: expected position, risk score visualized as a gauge
Tradeoffs list (from tradeoffs array in response)
Two buttons: "Play Another" and "Try Different Call" (re-submit different action on same scenario)

E4. Scenario Selector
Card grid. Each card: race name, flag emoji, lap number, driver name, decision type as a badge, difficulty badge. Sort by difficulty ascending for new users.
E5. Add a Race State Timeline component
This is a key differentiator from other F1 apps. On the scenario screen, show a horizontal lap timeline for the relevant driver from lap 1 to current lap, with:

Colored bands per stint (compound color: red=soft, yellow=medium, white=hard, green=inter, blue=wet)
Pit stop markers as vertical lines
Safety car periods as grey bands
Current lap highlighted
Position line as a small sparkline above

Use Recharts for this. This component alone will make screenshots impressive.
E6. Landing Page (do this last)
Hero section with the tagline. Animated race state card preview. "Pick a scenario" CTA. Disclaimer footer. Keep it one page.

SPRINT F — ML Baseline
F1. Build the pit decision dataset
Create ml/datasets/pit_decision_dataset.py. Reads from feature_pit_decision, handles class imbalance (most laps drivers don't pit), returns train/val split. Target: actual_pitted_within_3_laps.
F2. Train baseline models
Create ml/models/pit_decision_model.py. Train in this order:

Rule-based baseline (pit if stint_age > compound threshold — this is the floor to beat)
Logistic regression
Random forest
XGBoost

Evaluate each with accuracy, F1, ROC-AUC. Log results to ml/registry/.
F3. Add explainability
Use SHAP for the XGBoost model. Store feature importances. The API should return the top 3 SHAP features as human-readable strings in the decision response — e.g., "Stint age was the strongest signal", "Gap ahead reduced pit urgency".
F4. Wire model into the API
Add POST /predict/pit-decision endpoint. Also update the simulate endpoint to call the model and include model_recommendation and model_confidence in the response. The model and scaler artifacts should be serialized with joblib and loaded at API startup.
F5. Add a model registry table
sqlCREATE TABLE IF NOT EXISTS ml_model_registry (
    model_id VARCHAR PRIMARY KEY,
    model_name VARCHAR,
    model_version VARCHAR,
    target_definition VARCHAR,
    training_data_version VARCHAR,
    feature_view_version VARCHAR,
    training_date TIMESTAMP,
    accuracy DOUBLE,
    f1_score DOUBLE,
    roc_auc DOUBLE,
    artifact_path VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

SPRINT G — Chaos Engine
G1. Add chaos variables to the schema
Add a chaos_state table:
sqlCREATE TABLE IF NOT EXISTS chaos_modifier (
    chaos_id VARCHAR PRIMARY KEY,
    base_decision_point_id VARCHAR,
    modifier_type VARCHAR,  -- safety_car, rain, tire_cliff, slow_pit, rival_pit, red_flag
    trigger_lap INT,
    modifier_value DOUBLE,  -- intensity, delay seconds, etc.
    modifier_description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
G2. Add chaos simulation to the engine
Extend sim/engine.py with a ChaosEngine class:
pythonclass ChaosEngine:
    def apply_modifier(self, modifier_type: str, modifier_value: float, context: ScenarioContext) -> ScenarioContext:
        """Return a modified context with chaos applied."""
        ...
    
    def safety_car_now(self, context: ScenarioContext) -> ScenarioContext: ...
    def rain_starts(self, context: ScenarioContext, intensity: float) -> ScenarioContext: ...
    def tire_cliff_now(self, context: ScenarioContext) -> ScenarioContext: ...
    def slow_pit_stop(self, context: ScenarioContext, extra_seconds: float) -> ScenarioContext: ...
    def rival_pits_this_lap(self, context: ScenarioContext) -> ScenarioContext: ...
G3. Add chaos endpoint to API
POST /scenarios/{id}/chaos
Body: { "modifiers": [{ "type": "safety_car", "trigger_lap": 32 }], "action": "pit_now_inter" }
Returns same DecisionResponse shape but with chaos-adjusted simulation.
G4. Chaos Engine UI
After the result screen, add a "What if...?" section with toggle buttons:

🚗 Safety Car deployed
🌧 Rain starts now
⚠️ Tire cliff triggered
🐌 Slow pit stop (+5s)
🔄 Rival pits this lap

Each toggle re-submits to the chaos endpoint and shows the delta vs original outcome.

SPRINT H — Deployment + Polish
H1. Dockerize
dockerfile# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync
COPY . .
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
yaml# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    env_file: .env
  web:
    build: ./web
    ports: ["5173:5173"]
    environment:
      - VITE_API_BASE_URL=http://api:8000
H2. Railway config

Set DUCKDB_PATH to a Railway volume mount path
Add a Procfile: web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
Pre-run the ingest pipeline and commit the populated data/undercut.db (or use a Railway volume)

H3. Vercel config
Add web/vercel.json:
json{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
H4. Add docs pages

docs/data_sources.md — provenance, sources, licenses
docs/schema.md — ERD description, table purposes, source priority rules
docs/domain_rules.md — sprint weekends, DNF classification, driver-team mapping, tire normalization
docs/model_cards.md — for each trained model: training data, features, evaluation metrics, known limitations
docs/legal_disclaimer.md — unofficial fan project, non-commercial, OpenF1 license note

Also add a /methodology page in the frontend that pulls from these docs. Recruiters will look at this.
H5. Add an architecture diagram
Generate a visual architecture diagram showing the pipeline:
FastF1 / Jolpica / OpenF1
       ↓
  Raw Storage (Parquet + JSON)
       ↓
  DuckDB Canonical Schema
       ↓
  Race State Tables
       ↓
  Feature Store
       ↓
  ML Models + Simulation Engine
       ↓
  FastAPI
       ↓
  React Frontend
Add this to docs/architecture.md and render it on the methodology page.

Execution Order
Given 4 weeks and powerful agents, run in this order:
Week 2: Sprints A + B + C1–C3 (backend hardening, schema expansion, Jolpica + OpenF1 clients) simultaneously with Sprint E1–E4 (frontend through result screen). These can be parallelized across two agents.
Week 3: Sprints C4–C6 + D (race state builder, feature store builder, expand decision points) simultaneously with Sprint F (ML baseline). Pipeline agent and ML agent in parallel.
Week 4: Sprint G (Chaos Engine) + Sprint H (deployment, docs, polish). One agent on chaos, one on deployment and docs.