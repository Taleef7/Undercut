# AGENTS.md — Undercut: F1 Strategy Simulator

> Last updated: 2026-05-02  
> This file is the authoritative guide for all AI agents working on this codebase.  
> Read it entirely before writing any code or making any structural decisions.

---

## 0. Project North Star

Undercut is an unofficial F1 strategy simulation and portfolio project. Users are dropped into historical race decision points, make pit-wall calls, and get their choice scored against historical outcomes, a simulation engine, and an ML model.

The full pipeline is:

```
Public Data (FastF1 / Jolpica / OpenF1)
    ↓
Raw Storage (Parquet + JSON in data/raw/)
    ↓
DuckDB Canonical Schema (dim_* + fact_* tables)
    ↓
Race State Tables (race_state_driver_lap_fact, race_state_field_lap)
    ↓
Feature Store (feature_pit_decision, feature_undercut_opportunity)
    ↓
ML Models + Simulation Engine (sim/)
    ↓
FastAPI Backend (api/)
    ↓
React Frontend (web/)
```

The baseline pilot race is the **2024 Brazilian GP**. All features must work for this race before expanding to others.

---

## 1. Repository Layout

```
undercut/
├── AGENTS.md                    ← you are here
├── PROJECT_PLAN.md              ← long-term vision document; read before building anything new
├── README.md
├── pyproject.toml               ← uv-managed dependencies
├── .python-version              ← 3.11
├── .env.example
├── docker-compose.yml
│
├── data/
│   ├── raw/                     ← immutable source payloads (never modify)
│   │   ├── jolpica/             ← raw Jolpica API JSON, partitioned by year/round
│   │   └── openf1/              ← raw OpenF1 API JSON, partitioned by year/meeting/session
│   ├── cache/                   ← FastF1 cache (gitignored)
│   ├── decision_points/         ← curated YAML scenario definitions
│   │   └── brazil_2024.yaml
│   └── undercut.db              ← DuckDB database (gitignored in production)
│
├── db/
│   ├── migrations/
│   │   ├── 001_core_dimensions.sql
│   │   ├── 002_fact_tables.sql
│   │   ├── 003_race_state.sql
│   │   ├── 004_feature_store.sql
│   │   └── 005_corrections.sql
│   ├── seeds/
│   │   ├── seed_compounds.sql
│   │   └── seed_circuits.sql
│   └── apply_migrations.py      ← runs all migrations in order
│
├── ingest/
│   ├── __init__.py
│   ├── run_pipeline.py          ← CLI orchestration entry point
│   ├── brazil_2024.py           ← FastF1 loader for pilot race
│   ├── load_decision_points.py  ← YAML → DuckDB loader
│   ├── jolpica_client.py        ← Jolpica REST client
│   ├── openf1_client.py         ← OpenF1 REST client
│   ├── normalize/
│   │   ├── normalize_circuits.py
│   │   ├── normalize_drivers.py
│   │   ├── normalize_constructors.py
│   │   ├── normalize_sessions.py
│   │   ├── normalize_laps.py
│   │   ├── normalize_stints.py
│   │   ├── normalize_pit_stops.py
│   │   ├── normalize_results.py
│   │   ├── normalize_weather.py
│   │   └── normalize_race_control.py
│   ├── validate/
│   │   ├── checks.py            ← validation rule functions
│   │   └── reports.py           ← validation summary output
│   └── build/
│       ├── build_race_state.py  ← constructs race_state_driver_lap_fact + race_state_field_lap
│       └── build_features.py    ← constructs feature store tables
│
├── sim/
│   ├── __init__.py
│   ├── engine.py                ← UndercutEngine orchestrator
│   ├── chaos.py                 ← ChaosEngine modifier layer
│   ├── pit_model.py             ← pit loss heuristics by circuit
│   ├── tire_model.py            ← degradation curves + cliff detection
│   ├── scoring.py               ← decision scoring rubric
│   └── circuit_config.py        ← per-circuit constants (base lap time, pit loss, etc.)
│
├── ml/
│   ├── datasets/
│   │   ├── pit_decision_dataset.py
│   │   └── finish_position_dataset.py
│   ├── models/
│   │   ├── pit_decision_model.py
│   │   └── finish_position_model.py
│   ├── train.py
│   ├── evaluate.py
│   └── registry.py              ← writes to ml_model_registry table
│
├── api/
│   ├── main.py                  ← FastAPI app + CORS
│   ├── models.py                ← Pydantic request/response schemas
│   └── routers/
│       ├── scenarios.py
│       ├── simulation.py
│       └── prediction.py
│
├── web/                         ← Vite + React + TypeScript + Tailwind + shadcn/ui
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts        ← typed fetch wrappers for all API endpoints
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── ScenarioSelect.tsx
│   │   │   ├── ScenarioPlay.tsx
│   │   │   ├── DecisionResult.tsx
│   │   │   ├── ChaosEngine.tsx
│   │   │   └── Methodology.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vercel.json
│
└── docs/
    ├── api_contract.md          ← ALWAYS update this when API shapes change
    ├── data_sources.md
    ├── schema.md
    ├── domain_rules.md
    ├── model_cards.md
    └── legal_disclaimer.md
```

---

## 2. Tooling & Environment

| Concern | Tool | Notes |
|---|---|---|
| Python version | 3.11 | Managed via `.python-version` |
| Package manager | `uv` | Never use `pip` directly |
| Database | DuckDB | File at `data/undercut.db` |
| API framework | FastAPI + uvicorn | |
| Frontend | Vite + React + TypeScript | |
| Styling | Tailwind CSS + shadcn/ui | Dark theme throughout |
| Charts | Recharts | Use for race timeline, pace charts |
| HTTP client | `httpx` | For Jolpica and OpenF1 clients |
| ML | scikit-learn + XGBoost + SHAP | No PyTorch/TensorFlow in v1 |
| Serialization | `joblib` | For model artifacts |
| Linting | `ruff` | |
| Type checking | `mypy` | |

**Install dependencies:**
```bash
uv sync
uv sync --extra dev   # includes pytest, ruff, mypy
```

**Run the API:**
```bash
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**Run the frontend:**
```bash
cd web && npm install && npm run dev
```

---

## 3. Database

### 3.1 Connection pattern

Always open and close connections within the scope of a function. Never hold a connection as a global. Use `fetchdf()` for queries that return rows the API will serialize — it returns a named-column DataFrame, not anonymous tuples.

```python
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "undercut.db"

def get_scenarios() -> list[dict]:
    conn = duckdb.connect(str(DB_PATH))
    df = conn.execute("SELECT * FROM race_state_decision_point").fetchdf()
    conn.close()
    return df.to_dict(orient="records")
```

Never use `fetchone()` or `fetchall()` in API handlers — they return tuples with no column names, which produces silent bugs when column order changes.

### 3.2 Migration order

Migrations must be applied in numeric order using `db/apply_migrations.py`. Never modify a migration file after it has been applied to a live database — add a new migration instead.

```bash
uv run python db/apply_migrations.py
```

### 3.3 Schema layers (in order of dependency)

1. **Dimension tables** (`dim_season`, `dim_meeting`, `dim_circuit`, `dim_session`, `dim_driver`, `dim_constructor`, `dim_tyre_compound`, `dim_track_status_code`)
2. **Fact tables** (`fact_lap`, `fact_stint`, `fact_pit_stop`, `fact_session_result`, `fact_driver_session_entry`, `fact_weather_sample`, `fact_race_control_event`, `fact_interval_sample`, `fact_position_sample`)
3. **Race state tables** (`race_state_driver_lap_fact`, `race_state_field_lap`, `race_state_decision_point`)
4. **Feature store** (`feature_pit_decision`, `feature_undercut_opportunity`)
5. **ML registry** (`ml_model_registry`)
6. **Corrections** (`manual_data_correction`)

### 3.4 Required metadata columns

Every canonical and fact table must include these columns:

```sql
source_system VARCHAR,          -- 'fastf1' | 'openf1' | 'jolpica' | 'kaggle' | 'manual'
ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
data_version VARCHAR,           -- e.g. 'v0.1.0'
record_hash VARCHAR             -- SHA256 of key fields for dedup/change detection
```

### 3.5 Seed data

After running migrations, run seeds:

```bash
uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); conn.execute(open('db/seeds/seed_compounds.sql').read()); conn.execute(open('db/seeds/seed_circuits.sql').read()); conn.close()"
```

`seed_compounds.sql` must insert rows for: SOFT, MEDIUM, HARD, INTERMEDIATE, WET, C1–C5.  
`seed_circuits.sql` must insert rows for at minimum: interlagos, monaco, silverstone, spa, monza, hungaroring, suzuka, las_vegas, yas_marina, albert_park.

---

## 4. Data Sources & Priority

### 4.1 Source priority rules

When the same data exists in multiple sources, apply this hierarchy:

| Data type | Priority order |
|---|---|
| Historical metadata (schedules, circuits, drivers, constructors) | Jolpica → Kaggle → manual correction |
| Results and classification | Jolpica → FastF1 → manual correction |
| Stints, pit stops, weather, race control | OpenF1 → FastF1 → derived |
| Modern session/lap-level detail (2023+) | OpenF1 → FastF1 |
| Pre-2023 lap times | FastF1 → Jolpica lap endpoint |

### 4.2 FastF1

- **Always enable cache before any session load.** Failing to do so causes repeated API calls and will get rate-limited.
- Cache directory: set via `FASTF1_CACHE_DIR` env var, default `data/cache`.
- Load sessions with `session.load()` before accessing `session.laps`, `session.results`, etc.
- Stints are per-driver: iterate `session.laps.pick_driver(number).pick_stints()`.
- Available data varies by session type — handle missing attributes gracefully with try/except.

```python
import fastf1
fastf1.Cache.enable_cache("data/cache")
session = fastf1.get_session(2024, "Brazil", "R")
session.load()
```

### 4.3 Jolpica

- Base URL: `https://api.jolpi.ca/ergast/f1/`
- Rate limit: stay at or under 1 request/second.
- Supports: schedule, results, qualifying, sprint, standings, drivers, constructors, circuits, pit stops, lap times.
- Store raw JSON responses to `data/raw/jolpica/{year}/{round}/{endpoint}.json` before normalizing.
- Historical coverage: 1950 to present.

### 4.4 OpenF1

- Base URL: `https://api.openf1.org/v1/`
- Coverage: 2023 onward only.
- Key endpoints: `meetings`, `sessions`, `laps`, `stints`, `pit`, `intervals`, `position`, `weather`, `race_control`, `session_result`, `starting_grid`.
- Store raw to `data/raw/openf1/{year}/{meeting_key}/{session_key}/{endpoint}.json`.
- This is a non-commercial license source. Keep the project clearly unofficial and non-commercial.
- All requests must include a `User-Agent` header identifying the project.

### 4.5 Raw data rule

Raw data is **never modified**. It is stored as received. Transformations happen only in the normalize layer. If a source has bad data, add a row to `manual_data_correction` — do not edit the raw file.

---

## 5. Data Pipeline CLI

All pipeline stages are orchestrated via `ingest/run_pipeline.py`. Use these commands:

```bash
# Seed canonical reference data from Jolpica
uv run python -m ingest.run_pipeline bootstrap --source jolpica --seasons 2022 2023 2024

# Fetch and normalize a specific race weekend
uv run python -m ingest.run_pipeline fetch-weekend --season 2024 --round 21

# Normalize a fetched weekend into canonical tables
uv run python -m ingest.run_pipeline normalize --season 2024 --round 21

# Build race state tables for a session
uv run python -m ingest.run_pipeline build-race-state --season 2024 --round 21

# Build feature store for a session
uv run python -m ingest.run_pipeline build-features --season 2024 --round 21

# Validate data for a session
uv run python -m ingest.run_pipeline validate --season 2024 --round 21

# Load curated decision points from YAML
uv run python -m ingest.load_decision_points data/decision_points/brazil_2024.yaml
```

---

## 6. Decision Point YAML Format

Each scenario YAML file lives in `data/decision_points/`. The required schema for each entry:

```yaml
- id: "brazil_2024_lap32"           # globally unique, slug format
  session_id: "R"                   # R, Q, S, SQ, FP1, FP2, FP3
  driver_id: "VER"                  # 3-letter driver code
  lap_number: 32
  decision_type: "pit_now_vs_stay_out"  # see decision types below
  scenario_title: "Short string for card display"
  scenario_description: |
    Multiline prose shown on the scenario screen. Written in pit-wall radio style.
    Include tension, context, rival threats. Aim for 3-5 sentences.
  available_actions:
    - "pit_now_inter"
    - "pit_now_hard"
    - "stay_out"
    - "extend_stint"
  actual_decision: "stay_out"
  actual_outcome_summary: "One sentence of what happened."
  explanation_short: "One sentence explanation for result card."
  explanation_long: |
    Detailed explanation for result screen. 3-5 sentences covering the tradeoffs,
    what the simulation suggests, and why the historical decision was or wasn't optimal.
  race_state:                        # REQUIRED — must have real numbers, not approximations
    current_position: 2
    gap_ahead_seconds: 1.2
    gap_behind_seconds: 4.8
    compound: "medium"               # soft | medium | hard | intermediate | wet
    stint_age_laps: 14
    laps_remaining: 39
    track_temperature_c: 48
    air_temperature_c: 29
    rainfall: false
    track_status: "green"            # green | yellow | safety_car | vsc | red_flag
    safety_car_active: false
    virtual_safety_car_active: false
```

**Valid decision types:**
- `pit_now_vs_stay_out`
- `cover_undercut`
- `extend_to_end`
- `switch_to_wet`
- `safety_car_pit`
- `late_race_attack`
- `defend_position`

**Curated races (expand in this order):**
1. Brazil 2024 — already started (3 scenarios)
2. Abu Dhabi 2021 lap 53 — SC restart, VER vs HAM tire decision
3. Singapore 2023 lap 40 — ALO defending on old hards vs PER
4. Hungary 2022 lap 38 — SAI strategy reference point

All `race_state` values must come from actual FastF1 data for that lap, not estimated.

---

## 7. Simulation Engine

### 7.1 Key files

| File | Purpose |
|---|---|
| `sim/circuit_config.py` | Per-circuit constants: base_lap_time_ms, pit_loss_seconds, overtaking_difficulty, safety_car_probability |
| `sim/tire_model.py` | Degradation curves per compound, cliff threshold detection, lap time estimation |
| `sim/pit_model.py` | Pit loss by circuit + SC/VSC reduction, position delta estimation |
| `sim/scoring.py` | Rubric: score 0–100, grade label, tradeoffs list |
| `sim/engine.py` | `UndercutEngine` — orchestrates the above into a full evaluate_strategy response |
| `sim/chaos.py` | `ChaosEngine` — applies modifiers (SC, rain, tire cliff, slow stop, rival pit) to a context |

### 7.2 Circuit config (required entries)

`sim/circuit_config.py` must contain at minimum:

```python
CIRCUIT_CONFIG = {
    "interlagos": {
        "base_lap_time_ms": 75500,
        "pit_loss_seconds": 22.0,
        "overtaking_difficulty": 0.60,
        "safety_car_probability_baseline": 0.35,
        "track_length_km": 4.309,
    },
    "monaco": { "base_lap_time_ms": 74000, "pit_loss_seconds": 18.0, ... },
    "silverstone": { "base_lap_time_ms": 87500, "pit_loss_seconds": 19.0, ... },
    "spa": { "base_lap_time_ms": 103000, "pit_loss_seconds": 24.0, ... },
    "monza": { "base_lap_time_ms": 81000, "pit_loss_seconds": 23.0, ... },
    "suzuka": { "base_lap_time_ms": 91500, "pit_loss_seconds": 21.0, ... },
    "yas_marina": { "base_lap_time_ms": 83000, "pit_loss_seconds": 20.0, ... },
}
```

The engine must look up `base_lap_time_ms` from this config, not hardcode it.

### 7.3 Scoring rubric

| Condition | Score | Grade |
|---|---|---|
| Matches historical AND simulation confirms it was optimal | 90–100 | Masterful |
| Matches historical (simulation neutral or confirming) | 75–89 | Strong |
| Different from historical but simulation shows gain | 80–95 | Inspired call |
| Different from historical, simulation shows similar outcome | 55–70 | Risky |
| Different from historical, simulation shows position loss | 30–54 | Poor call |
| Extreme misread of conditions | 0–29 | Off the wall |

The `explanation` field must always explain *why* in terms of the tradeoffs visible in the scenario context, not just "you matched the historical decision."

### 7.4 Chaos Engine modifiers

`ChaosEngine.apply_modifier()` accepts a modifier type and returns a modified `ScenarioContext`. Supported types:

| modifier_type | Effect on context |
|---|---|
| `safety_car` | Reduces effective pit loss by ~18s, compresses field intervals |
| `vsc` | Reduces pit loss by ~14s |
| `rain_starts` | Adds rainfall flag, reduces optimal compound to intermediate/wet |
| `tire_cliff_now` | Artificially ages tire by +8 laps for degradation calculations |
| `slow_pit_stop` | Adds `modifier_value` seconds to pit_loss_seconds |
| `rival_pits_this_lap` | Reduces gap_behind by pit_loss, simulates rival coming out ahead |
| `red_flag` | Sets track_status to red_flag, triggers free pit opportunity |

---

## 8. API

### 8.1 Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/scenarios` | List all decision points (summary shape) |
| `GET` | `/scenarios/{id}` | Full scenario detail |
| `POST` | `/scenarios/{id}/decision` | Submit a user action, get scored result |
| `POST` | `/scenarios/{id}/chaos` | Submit action + chaos modifiers, get modified result |
| `POST` | `/predict/pit-decision` | Direct ML model inference endpoint |

### 8.2 Request/response contract

The full contract is defined in `docs/api_contract.md`. All agents must update that file whenever an endpoint shape changes. Frontend agents must read it before writing any fetch code.

**`POST /scenarios/{id}/decision` response shape:**

```json
{
  "scenario_id": "brazil_2024_lap32",
  "user_action": "stay_out",
  "score": 82,
  "grade": "Strong call",
  "historical_decision": "stay_out",
  "model_recommendation": "stay_out",
  "model_confidence": 0.71,
  "model_top_features": [
    "Stint age was the key signal",
    "Gap ahead reduced pit urgency",
    "Rain flag increased track position value"
  ],
  "simulation_summary": {
    "expected_position": 2,
    "expected_finish_position_band": "P1-P3",
    "risk_score": 0.28,
    "tire_risk": "medium",
    "track_position_risk": "low"
  },
  "explanation": "Full explanation string.",
  "tradeoffs": [
    "Staying out preserves track position ahead of Norris",
    "Medium tires were 14 laps old — approaching cliff territory",
    "Rain probability increased the value of not pitting"
  ]
}
```

### 8.3 Rules for API agents

- All responses must be typed Pydantic `BaseModel` classes defined in `api/models.py`.
- Always use `fetchdf()` for DB queries, never `fetchall()` or `fetchone()`.
- DB column access by index is forbidden. Always access by column name from a DataFrame or named dict.
- The API must include CORS middleware allowing `http://localhost:5173` in development.
- DB connections must be opened and closed within each request handler, not held at module level.
- HTTP 404 for missing scenarios, HTTP 422 for invalid action values (validate against `available_actions_json`).

---

## 9. ML Layer

### 9.1 Scope (v1)

Two tasks only:
1. **Pit decision** — binary classifier: should this driver pit in the next 1–3 laps?
2. **Finish position band** — multiclass: given current race state, which position band will the driver finish in?

Do not build deep learning models in v1. Preferred model order: rule-based baseline → logistic regression → random forest → XGBoost.

### 9.2 Model training

```bash
uv run python ml/train.py --target pit_decision --data-version v0.1
uv run python ml/train.py --target finish_position --data-version v0.1
```

### 9.3 Artifacts

Train artifacts are serialized with `joblib` and stored in `ml/artifacts/{model_name}/{version}/`. The artifact bundle includes:
- `model.joblib` — trained estimator
- `scaler.joblib` — feature scaler
- `feature_names.json` — ordered list of feature columns
- `shap_explainer.joblib` — SHAP explainer for the XGBoost model

### 9.4 Model registry

Every training run writes a row to `ml_model_registry` via `ml/registry.py`. This includes training data version, feature view version, evaluation metrics, and artifact path. Never deploy a model that isn't registered.

### 9.5 Explainability requirement

The pit decision model must produce SHAP values at inference time. The API response for `/scenarios/{id}/decision` must include `model_top_features` — the top 3 SHAP contributors as human-readable strings.

---

## 10. Frontend

### 10.1 Stack

- Vite + React + TypeScript
- Tailwind CSS (dark theme by default — `darkMode: 'class'` in config, `dark` class on `<html>`)
- shadcn/ui component library
- Recharts for data visualizations
- `VITE_API_BASE_URL` env var for API base (default: `http://localhost:8000`)

### 10.2 Page build order (strict)

Build pages in this order. Do not skip ahead.

1. `ScenarioPlay.tsx` — the core game screen
2. `DecisionResult.tsx` — the scored result + explanation
3. `ScenarioSelect.tsx` — scenario card grid
4. `ChaosEngine.tsx` — chaos modifier toggles on the result screen
5. `Methodology.tsx` — data pipeline + model methodology
6. `Home.tsx` — landing page (last)

### 10.3 ScenarioPlay layout requirements

The scenario screen must show:
- Race name, lap number, circuit name in a header bar
- Driver name and current position (prominent)
- Gap ahead and gap behind (with directional indicators)
- Tire compound + stint age + visual cliff warning if applicable
- Track status badge (green / yellow / SC / VSC / rain)
- Temperature and weather conditions
- A "pit wall radio" flavour text quote
- A **Race State Timeline** component (horizontal, lap 1 to current, showing stints as colored bands, pit stop markers, SC periods, current lap highlight)
- 3–4 strategy action buttons (never more than 4 choices at once)

### 10.4 DecisionResult layout requirements

- Large animated score number (count-up animation, 0 to final score)
- Grade label styled by tier: Masterful=gold, Strong=green, Inspired=teal, Risky=amber, Poor=red
- "You chose X / Real team chose Y" comparison row
- Model recommendation badge with confidence percentage
- Simulation summary: expected position, risk gauge (0–1 rendered as a visual meter)
- Tradeoffs list (bullet points from the `tradeoffs` array)
- Explanation paragraph
- "Play Another" button → back to ScenarioSelect
- "Try a Different Call" button → re-render ScenarioPlay with same scenario, previous choice locked out
- After result is shown: chaos modifier toggles appear as a "What if...?" section

### 10.5 Race State Timeline component

This is a required component, not optional. It is a key visual differentiator.

Implementation: Recharts `ComposedChart` or custom SVG. Shows:
- Horizontal axis: lap number 1 to total laps
- Colored band for each stint (red=soft, yellow=medium, white/grey=hard, green=inter, blue=wet)
- Vertical dashed line at each pit stop lap
- Grey shaded region for SC/VSC periods
- Current lap marked with a vertical highlight
- Position sparkline as a thin line above the compound bands

### 10.6 API client

All fetch calls must go through `web/src/api/client.ts`. This file exports typed async functions matching every API endpoint. No raw `fetch()` calls in page components.

```typescript
// Example shape
export async function getScenario(id: string): Promise<ScenarioDetail> { ... }
export async function submitDecision(id: string, action: string): Promise<DecisionResponse> { ... }
export async function submitChaosDecision(id: string, action: string, modifiers: ChaosModifier[]): Promise<DecisionResponse> { ... }
```

Types must match `docs/api_contract.md` exactly.

---

## 11. Domain Rules

These are explicit and must be followed. Do not infer alternatives.

**Sprint weekends:** Sprint and Race are separate sessions. Never merge them. Keep Sprint Shootout, Sprint, Qualifying, and Race as distinct `session_type` values.

**Classified position:** `classified_position` is the official result and may be a string like `'R'`, `'DNF'`, `'DSQ'`, `'NC'`. `position_order` is the sort order from the source. Keep them separate.

**Penalties:** Store penalties as rows in `fact_penalty_event`, not only as text in results.

**Driver-team mapping:** The relationship between a driver and constructor is session-level, not season-level. A driver can switch teams, race as a substitute, or enter a practice session for a different team. Always use `fact_driver_session_entry` for this.

**Tire compound labels:** Source labels vary (e.g., `SOFT`, `Soft`, `S`, `C3`). All must be normalized to internal `tyre_compound_id` via `dim_tyre_compound`. Preserve the raw source label in `compound_label_source`.

**Track status flags:** Safety car, VSC, and red flag status should be derived from `fact_race_control_event` as boolean flags on each lap row. Store events, derive flags — do not only store flags.

**Weather:** Store as timestamped samples in `fact_weather_sample`. Derive lap-level weather by nearest-sample join when building race state.

**Pit loss:** When not directly available, estimate using the circuit config `typical_pit_loss_seconds`. Mark estimated values with `estimated_pit_loss_flag = TRUE`.

**Time granularity:** Canonical and raw tables support timestamps where available. Race state tables are lap-first. Never discard timestamps from raw data even if the product tables are lap-indexed.

**Record hashes:** Every canonical fact row must have a `record_hash` column computed as `SHA256(source_system + source_record_id + key_field_values)`. This enables idempotent upserts.

---

## 12. Validation

After any ingestion run, validate the loaded data. Rules are implemented in `ingest/validate/checks.py`:

- Expected number of sessions per meeting (7 for a sprint weekend, 5 for a standard weekend)
- Expected 20 drivers per race session (allow 18–22 for edge cases)
- No duplicate `(session_id, driver_id, lap_number)` rows in `fact_lap`
- Lap numbers within expected range for the session
- Stint lap ranges do not overlap for the same driver in the same session
- Pit stop laps reference valid lap numbers in `fact_lap`
- Classified positions are unique where expected (allow ties for same-lap DNFs)
- All `driver_id` values in fact tables exist in `dim_driver`
- `record_hash` is non-null on all canonical rows

Validation failures write to `data/validation_report_{timestamp}.json`. Warnings are logged; hard failures should stop the pipeline and require manual review.

---

## 13. Deployment

### 13.1 Backend — Railway

- Entry point: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- `DUCKDB_PATH` env var must point to a Railway volume mount
- Pre-populate the database with the ingestion pipeline before first deploy
- `Procfile`: `web: uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### 13.2 Frontend — Vercel

`web/vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

Set `VITE_API_BASE_URL` as a Vercel environment variable pointing to the Railway backend URL.

### 13.3 Docker (local full-stack)

```bash
docker-compose up --build
```

Backend available at `http://localhost:8000`, frontend at `http://localhost:5173`.

---

## 14. Known Bugs to Fix Before New Features

These must be resolved before building on top of them:

1. **`sim/scoring.py` NameError** — `sim_position` is referenced in `model_recommendation` even when `user_action == historical_action`, where it is never assigned. Fix: always assign `sim_position = simulated_positions.get(user_action, context.position)` at the top of the function before branching.

2. **`api/main.py` tuple returns** — `/scenarios` uses `fetchall()` and returns anonymous tuples. Fix: use `fetchdf().to_dict(orient="records")` and validate with a Pydantic response model.

3. **`api/main.py` hardcoded simulation inputs** — The `/simulate` endpoint hardcodes `position=1`, `compound="medium"`, `stint_age=15`, `gap_ahead=1.2`, `gap_behind=0.8`, `laps_remaining=10`. Fix: read these from the `race_state` columns in the database row.

4. **`sim/engine.py` hardcoded base lap time** — `base_lap_time_ms=90000` (~1:30) is wrong for all real circuits. Brazil 2024 is ~1:15. Fix: read from `circuit_config.py` keyed by circuit name.

5. **No CORS middleware** — The frontend cannot call the API without it. Fix: add `CORSMiddleware` to `api/main.py` before any other feature work.

---

## 15. What Not to Build in v1

Do not implement any of the following unless explicitly instructed. They are deferred to later phases:

- Live race companion or real-time telemetry
- Full multiplayer or leaderboards
- High-frequency car telemetry (car data endpoint from OpenF1)
- Full season simulator
- Team radio processing
- Deep learning / transformer models
- Official F1 branding, logos, or any marks implying affiliation
- Any commercial feature or monetization

---

## 16. Conventions

- **Branch names:** `feature/`, `fix/`, `data/`, `ml/` prefixes
- **Commit messages:** imperative present tense — "Add Jolpica client", "Fix scoring NameError", "Build race state for Brazil 2024"
- **Pydantic models:** all in `api/models.py`, no inline model definitions in route handlers
- **SQL:** all schema-changing SQL goes in `db/migrations/`. One-off queries go in `notebooks/` or scripts
- **No magic strings:** compound names, session types, action names, and source system identifiers must be defined as constants or enums, not scattered as inline strings
- **Type annotations required everywhere** — no untyped function signatures; mypy must pass
- **Never commit** `data/undercut.db`, `data/cache/`, `.env`, raw parquet/JSON files

---

## 17. Disclaimer (required on all user-facing surfaces)

> This is an unofficial fan project created for educational and portfolio purposes. It is not affiliated with Formula 1, the FIA, any F1 team, driver, or data provider. All trademarks belong to their respective owners. Data is used under the terms of the respective source licenses and is intended for non-commercial personal use only.