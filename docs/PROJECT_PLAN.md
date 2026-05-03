# Undercut — Project Plan

**Working name:** Undercut
**Tagline:** *Race strategy, chaos included.*
**Status:** v2 — 4-week full-time build plan
**Target outcome:** Deployed, polished, portfolio-grade strategy simulator

---

## 1. Project Overview

Undercut is an unofficial, interactive Formula 1 race-strategy simulator. Users replay historical race scenarios as a pit-wall strategist, make decisions at curated inflection points, and see their choices scored against the real outcome, a simulated alternative, and an ML recommendation. A built-in Chaos Engine lets users inject alternate events — sudden rain, safety cars, slow pit stops, tire cliffs — to explore counterfactual race outcomes.

The project demonstrates depth across:

- **Data engineering** — multi-source ingestion, canonical schema design, ETL pipelines, validation, versioning
- **ML / data science** — feature engineering, tire-degradation regression, calibrated classifiers, model evaluation
- **Backend engineering** — typed FastAPI service, simulation engine, query-tuned warehouse access
- **Frontend / product** — opinionated React UI, narrative-driven interaction design, deployed live demo

### 1.1 Disclaimer

> Undercut is an unofficial fan project created for educational and portfolio purposes. It is not affiliated with Formula 1, FIA, any team, driver, or commercial rights holder. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX, and related marks are trademarks of Formula One Licensing B.V. Data sources are credited on the methodology page.

### 1.2 Success criteria (definition of done)

- Deployed at a public URL with a custom domain
- 3+ races playable end-to-end with curated decision points
- ML model registered, evaluated, served via API, with a methodology page
- Chaos Engine functional with at least 5 modifier types
- Repo clean enough that a hiring manager skimming `README.md` and the data pipeline thinks "this person knows what they're doing"
- 90-second demo video on the landing page

---

## 2. The 4-Week Plan at a Glance

| Week | Milestone | Ship |
|------|-----------|------|
| 1 | **MVP-0** — Vertical slice | Brazil 2024, 3 decisions, end-to-end playable on localhost |
| 2 | **MVP-1** — Foundation | Full canonical schema, full 2024 season ingested, 12+ decision points, Postgres |
| 3 | **MVP-2** — Intelligence | Tire deg model + pit classifier + full simulation engine + methodology page |
| 4 | **MVP-3** — Chaos & ship | Chaos Engine, deployed, polished, demo video, portfolio-ready |

Each week ends with a working demo. Don't ship perfectly; ship completely. Polish migrates from week to week.

---

## 3. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language (backend) | Python 3.11 | FastF1 ecosystem, ML libraries, FastAPI |
| Package manager | `uv` | Fast, modern, far better Windows/WSL2 experience than pip+venv |
| Local dev DB | DuckDB | Single-file, queries Parquet natively, zero setup, ideal for ETL |
| Production DB | Neon (serverless Postgres) | Free tier, scales to zero, branching, Postgres-standard |
| Data ingest | FastF1 (primary) + OpenF1 (gap-fill) | FastF1 already wraps Jolpica + live timing; OpenF1 fills interval-by-time gaps |
| Backend | FastAPI + Pydantic v2 + SQLAlchemy 2.0 | Typed, fast, modern, great OpenAPI docs |
| ML | scikit-learn, XGBoost, joblib | Lean, explainable, no GPU needed |
| Frontend | Vite + React 18 + TypeScript | Fast iteration, no SSR complexity |
| Styling | Tailwind + shadcn/ui | Rapid polished UIs, customizable, no design system to invent |
| State | TanStack Query + Zustand | Server state vs UI state, clean separation |
| Charts | Recharts | Good defaults, composable, easy to theme |
| Hosting (frontend) | Vercel | Free tier, GitHub integration, edge network |
| Hosting (backend) | Fly.io | Better cold-start than Render, generous free tier |
| Hosting (DB) | Neon | Free 0.5GB, branching, Postgres-standard |
| CI | GitHub Actions | Free, enough |

**Environment:** WSL2 on Windows. Native Windows works but you'll fight Docker, FastF1's cache paths, and FastAPI's hot reload. WSL2 removes all three problems.

---

## 4. Architecture

```
┌─────────────────┐
│ FastF1 + OpenF1 │  data sources
└────────┬────────┘
         │
┌────────▼────────────────────────────┐
│ ingest/ — Python ETL                │
│   raw → canonical → race_state      │
│   → feature_store                   │
└────────┬────────────────────────────┘
         │
    ┌────▼────────────┐  ┌──────────────┐
    │ DuckDB (dev)    │  │ Neon Postgres│
    │ warehouse.db    │  │ (production) │
    └────────┬────────┘  └──────┬───────┘
             │                  │
        ┌────▼──────────────────▼────┐
        │ FastAPI                    │
        │   simulation engine        │
        │   ML inference             │
        │   scoring                  │
        └────────────┬───────────────┘
                     │
              ┌──────▼──────┐
              │ React UI    │  Vercel
              └─────────────┘
```

**Key principle:** the canonical schema is identical between DuckDB and Postgres. DuckDB is for fast local iteration; Postgres is what the deployed API queries. ETL produces both.

---

## 5. Repo Structure

```
undercut/
├── README.md
├── PROJECT_PLAN.md                  ← this file
├── pyproject.toml                   ← uv-managed
├── .python-version
├── .env.example
├── .gitignore
├── docker-compose.yml               ← optional, week 4 for parity
│
├── data/
│   ├── decision_points/             ← YAML, hand-curated
│   │   ├── brazil_2024.yaml
│   │   ├── singapore_2023.yaml
│   │   └── ...
│   ├── cache/                       ← FastF1 cache (gitignored)
│   ├── parquet/                     ← raw snapshots (gitignored)
│   └── warehouse.duckdb             ← dev DB (gitignored)
│
├── ingest/
│   ├── __init__.py
│   ├── config.py
│   ├── sources/
│   │   ├── fastf1_loader.py
│   │   └── openf1_client.py
│   ├── normalize/
│   │   ├── drivers.py
│   │   ├── sessions.py
│   │   ├── laps.py
│   │   ├── stints.py
│   │   ├── pit_stops.py
│   │   ├── intervals.py
│   │   ├── weather.py
│   │   └── race_control.py
│   ├── build/
│   │   ├── race_state.py
│   │   └── features.py
│   ├── validate/
│   │   ├── checks.py
│   │   └── reports.py
│   └── schema/
│       ├── 001_dimensions.sql
│       ├── 002_facts.sql
│       ├── 003_race_state.sql
│       ├── 004_feature_store.sql
│       └── 005_chaos.sql
│
├── sim/
│   ├── __init__.py
│   ├── engine.py
│   ├── tire_model.py
│   ├── pit_model.py
│   ├── traffic_model.py
│   ├── weather_model.py
│   ├── chaos.py
│   └── scoring.py
│
├── ml/
│   ├── __init__.py
│   ├── datasets/
│   │   ├── pit_decision.py
│   │   └── tire_degradation.py
│   ├── models/
│   │   ├── pit_decision.py
│   │   └── tire_degradation.py
│   ├── train.py
│   ├── evaluate.py
│   └── registry.py
│
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── deps.py
│   ├── routes/
│   │   ├── seasons.py
│   │   ├── meetings.py
│   │   ├── sessions.py
│   │   ├── scenarios.py
│   │   ├── strategy.py
│   │   ├── chaos.py
│   │   └── meta.py
│   ├── services/
│   │   ├── scenario_service.py
│   │   ├── simulation_service.py
│   │   ├── scoring_service.py
│   │   └── prediction_service.py
│   └── db/
│       ├── connection.py
│       ├── models.py
│       └── queries.py
│
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── ScenarioList.tsx
│       │   ├── Scenario.tsx
│       │   ├── Result.tsx
│       │   ├── Methodology.tsx
│       │   └── About.tsx
│       ├── components/
│       │   ├── PitWallRadio.tsx
│       │   ├── RaceStateCard.tsx
│       │   ├── StrategyButtons.tsx
│       │   ├── ChaosToggle.tsx
│       │   ├── ScoreCard.tsx
│       │   └── ui/             ← shadcn primitives
│       ├── api/
│       │   └── client.ts
│       ├── lib/
│       └── styles/
│
├── tests/
│   ├── test_sim_engine.py
│   ├── test_scoring.py
│   ├── test_ingest.py
│   └── test_api.py
│
├── notebooks/
│   ├── 01_brazil_2024_exploration.ipynb
│   ├── 02_tire_degradation.ipynb
│   ├── 03_pit_decision_model.ipynb
│   └── 04_simulation_validation.ipynb
│
├── docs/
│   ├── data_sources.md
│   ├── schema.md
│   ├── methodology.md
│   ├── domain_rules.md
│   ├── model_cards.md
│   └── legal.md
│
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

---

## 6. Schema

The full canonical schema lands by end of Week 2. MVP-0 uses a 5-table subset.

### 6.1 MVP-0 minimal schema (Week 1)

Five tables in DuckDB, single-race scope:

```
dim_driver(driver_id, code, full_name, current_team, team_color_hex)
dim_compound(compound_id, label, category, hardness_order, is_wet)
fact_lap(lap_id, session_id, driver_id, lap_number, position, lap_time_ms,
         compound_id, stint_age, gap_to_leader_s, interval_ahead_s, track_status)
fact_stint(stint_id, session_id, driver_id, stint_number, compound_id,
           lap_start, lap_end, tyre_age_at_start)
fact_pit_stop(pit_id, session_id, driver_id, lap_number, pit_duration_ms,
              old_compound_id, new_compound_id)
```

Plus one materialized view: `race_state_driver_lap` (one row per driver per lap, joined and denormalized).

### 6.2 Full canonical schema (Week 2)

**Dimensions:**
- `dim_season` — championship year
- `dim_meeting` — race weekend
- `dim_circuit` — track identity + static metadata (incl. `typical_pit_loss_s`, `overtaking_difficulty`, `sc_probability_baseline`)
- `dim_constructor`
- `dim_driver`
- `dim_session` — FP1/FP2/FP3/Q/SQ/Sprint/Race
- `dim_tyre_compound`
- `dim_track_status_code`
- `dim_race_control_category`

**Facts:**
- `fact_driver_session_entry` — driver–team mapping per session
- `fact_starting_grid`
- `fact_session_result`
- `fact_lap`
- `fact_stint`
- `fact_pit_stop`
- `fact_interval_sample` — gap-to-leader / interval-ahead time series
- `fact_position_sample`
- `fact_weather_sample`
- `fact_race_control_event`
- `fact_penalty_event`
- `fact_driver_standing_snapshot`
- `fact_constructor_standing_snapshot`

**Race state (product layer):**
- `race_state_driver_lap` — primary table queried by UI
- `race_state_field_lap` — whole-field state per lap
- `race_state_decision_point` — curated and auto-generated scenarios

**Feature store (Week 3):**
- `feature_pit_decision`
- `feature_tire_degradation`
- `feature_undercut_opportunity`
- `feature_finish_position`
- `feature_safety_car_pit_gain`

**Chaos (Week 4):**
- `chaos_modifier_type` — registry of modifier kinds
- `chaos_scenario_run` — user-initiated chaos runs
- `chaos_event` — events injected within a run

**Operational:**
- `manual_data_correction` — explicit corrections
- `ml_model_registry` — model versions, training data versions, metrics
- `data_quality_flag` — coverage and quality metadata

**Metadata columns on every fact table:** `source_system`, `source_record_id`, `ingested_at`, `data_version`, `record_hash`.

---

## 7. Data Sources

| Source | Use | Auth | License notes |
|--------|-----|------|---------------|
| **FastF1** | Primary ingestion (uses Jolpica + live timing internally) | None | Open-source, unofficial |
| **OpenF1** | Gap-fill for interval-by-time samples and richer race control | None for historical | Non-commercial CC-style |
| **Jolpica** | Already inside FastF1; direct only if needed | None (200 req/hr) | Apache 2.0, alpha |
| **Kaggle bootstrap** | Optional, for pre-2018 historical context | None | Frozen, Ergast-derived |

**Coverage decision:** detailed race-state from 2023 onward. Older seasons stay result-centric only.
**Telemetry:** out of scope for v1; sidecar later if needed.
**Refresh cadence:** manual command in v1 (`uv run python -m ingest.fetch_weekend --season 2024 --round 21`). Scheduled refresh post-launch.

---

## 8. WEEK 1 — MVP-0: Vertical Slice

**Goal:** by Sunday night, anyone can clone the repo, run `make dev`, open localhost, and play Brazil 2024 with three decision points.

**Hard rules this week:** DuckDB only, no ML, no chaos, no auth, no deploy, single race.

### Issues

#### Setup
- [ ] **#1** Init repo, add MIT license, `.gitignore`, `pyproject.toml` (uv), `.python-version` = 3.11
- [ ] **#2** Set up `web/` with Vite + React + TypeScript + Tailwind + shadcn/ui base components
- [ ] **#3** Add `Makefile` with `dev`, `ingest`, `test`, `lint`, `format` targets
- [ ] **#4** Configure ruff + mypy (strict) for Python; eslint + prettier for TS
- [ ] **#5** Add `.env.example` with documented variables; `pydantic-settings` for typed config

#### Data ingest (Brazil 2024 only)
- [ ] **#6** `ingest/sources/fastf1_loader.py` — function `load_session(year, gp, session_type)` returning normalized dicts
- [ ] **#7** `ingest/schema/001_dimensions.sql` — DuckDB DDL for the 5 MVP-0 tables
- [ ] **#8** `ingest/normalize/` modules for drivers, laps, stints, pit_stops
- [ ] **#9** `ingest/brazil_2024.py` orchestrator — loads R session, normalizes, upserts
- [ ] **#10** `ingest/build/race_state.py` — build `race_state_driver_lap` view from base tables
- [ ] **#11** Smoke test: `pytest tests/test_ingest.py` — confirm 71 laps × 20 drivers loaded with no nulls in critical columns

#### Decision points
- [ ] **#12** Define YAML schema for decision points (see §10 below for shape)
- [ ] **#13** Write three Brazil 2024 decision points in `data/decision_points/brazil_2024.yaml` — see §10 for templates and field-level guidance
- [ ] **#14** Loader: `ingest/decision_points.py` — parse YAML, validate against Pydantic model, write to DuckDB

#### Simulation + scoring
- [ ] **#15** `sim/tire_model.py` — heuristic linear degradation by compound (see §13.2 for default constants)
- [ ] **#16** `sim/pit_model.py` — circuit pit-loss lookup (Interlagos = 22.0s)
- [ ] **#17** `sim/traffic_model.py` — heuristic traffic/clean-air bonus
- [ ] **#18** `sim/engine.py` — `simulate_forward(race_state, action) -> ProjectedOutcome`
- [ ] **#19** `sim/scoring.py` — composite score, see §14

#### API
- [ ] **#20** `api/main.py` — FastAPI app, CORS, health check at `/healthz`
- [ ] **#21** `api/db/connection.py` — DuckDB connection manager
- [ ] **#22** `GET /scenarios` — list available scenarios
- [ ] **#23** `GET /scenarios/{id}` — full scenario detail with race state
- [ ] **#24** `POST /scenarios/{id}/decision` — score a user decision, return projected outcome + comparison

#### Frontend
- [ ] **#25** `pages/Home.tsx` — landing with project tagline, "Play a scenario" CTA
- [ ] **#26** `pages/ScenarioList.tsx` — card grid of available scenarios
- [ ] **#27** `pages/Scenario.tsx` — race-state panel + strategy buttons + 90s decision timer
- [ ] **#28** `components/PitWallRadio.tsx` — terminal-style scrolling text feed (race engineer voice)
- [ ] **#29** `components/RaceStateCard.tsx` — driver + position + tire + stint age + gaps
- [ ] **#30** `components/StrategyButtons.tsx` — 4–6 action buttons with disabled-state logic
- [ ] **#31** `pages/Result.tsx` — score, grade, comparison: user vs historical vs simulated
- [ ] **#32** API client (`web/src/api/client.ts`) typed against backend OpenAPI

#### Polish + ship
- [ ] **#33** Loading states, error boundaries, skeleton screens
- [ ] **#34** Mobile-responsive layout (the demo video will be watched on phones)
- [ ] **#35** Record 90-second Loom walkthrough — this is your motivation artifact
- [ ] **#36** Update `README.md` with screenshots and run instructions

### Done when

You can hand a non-technical friend a URL (localhost via tunnel is fine), they pick a scenario, make a decision, see scored feedback, and want to play again.

---

## 9. WEEK 2 — MVP-1: Foundation

**Goal:** scale from one race to a full season with proper schema, validation, and persistent storage. Ship Postgres deployment-ready.

### Issues

#### Schema migration
- [ ] **#37** Write full canonical schema DDL for all dimensions and facts (`002_facts.sql`)
- [ ] **#38** Write `003_race_state.sql` for race_state tables
- [ ] **#39** Add `record_hash`, `data_version`, `ingested_at`, `source_system`, `source_record_id` to all fact tables
- [ ] **#40** Add `manual_data_correction` table + loader pattern
- [ ] **#41** Migration script: take MVP-0 DuckDB, transform to full schema, validate row counts match

#### Multi-source ingestion
- [ ] **#42** `ingest/sources/openf1_client.py` — async client for `intervals`, `position`, `race_control`, `weather` endpoints with retry + caching
- [ ] **#43** Source priority resolver: when same field exists in FastF1 and OpenF1, pick by priority rules (see plan §18)
- [ ] **#44** Ingest full 2024 season: `uv run python -m ingest.fetch_season --year 2024`
- [ ] **#45** Ingest 2023 season for additional decision-point material
- [ ] **#46** Add `intervals` and `position` time-series tables — needed for accurate gap reconstruction

#### Validation
- [ ] **#47** `ingest/validate/checks.py` — row-count expectations, no-duplicate-keys, lap-number monotonicity, stint-non-overlap, valid foreign keys
- [ ] **#48** Validation runs at end of every ingest job, fails loudly
- [ ] **#49** `data_quality_flag` table populated during validation
- [ ] **#50** `notebooks/01_brazil_2024_exploration.ipynb` — sanity check the warehouse, document quirks

#### Race state v2
- [ ] **#51** Rebuild `race_state_driver_lap` for full canonical, including all derived fields (rolling pace, pace delta, undercut/overcut threat flags, pit window flag)
- [ ] **#52** Build `race_state_field_lap` whole-field summary
- [ ] **#53** Decision-point auto-detection heuristics in `ingest/build/decision_points.py` — flag candidate moments (large stint age vs rivals, gap closing under threshold, pre-pit window) for human curation

#### Decision point library
- [ ] **#54** Add 9 more decision points (12 total): mix of races, decision types, difficulty levels
- [ ] **#55** Add `difficulty_level` (1–5) and `decision_type` taxonomy enforcement to YAML schema
- [ ] **#56** Front-matter linter: every decision point must have non-empty `expert_commentary` (≥150 words)

#### Postgres
- [ ] **#57** Provision Neon project, capture connection string in `.env`
- [ ] **#58** SQLAlchemy 2.0 models mirroring DuckDB schema
- [ ] **#59** Migration tooling — Alembic for Postgres, sync DuckDB via raw SQL files
- [ ] **#60** ETL writes to both DuckDB (analytics) and Postgres (API serving) — single command
- [ ] **#61** Switch API connection from DuckDB to Postgres behind a feature flag

#### API expansion
- [ ] **#62** `GET /seasons`, `GET /meetings?season=2024`, `GET /sessions?meeting_id=...`
- [ ] **#63** `GET /sessions/{id}/race-state?lap=N` — full field state at a given lap
- [ ] **#64** Pagination, filtering, sort params on list endpoints
- [ ] **#65** OpenAPI tags + examples for every endpoint

#### Frontend expansion
- [ ] **#66** `pages/RaceSelector.tsx` — pick a race from a list of available ones
- [ ] **#67** Filter scenarios by race, decision type, difficulty
- [ ] **#68** Persist last race / scenario in localStorage
- [ ] **#69** Skeleton state design pass — every loading state has a deliberate visual
- [ ] **#70** Empty states for "no scenarios match filter"

### Done when

Pick from any of 12+ scenarios across multiple races, race state UI feels rich, ingest is one command, schema and migrations are reviewed and clean.

---

## 10. Brazil 2024 — Decision Point Templates

These are the three decision points for Week 1. **Verify each against actual lap data after ingestion** — adjust laps and gaps to match what FastF1 reports. Treat the narrative scaffolding as the durable part; the numbers are the part you fill in from data.

### 10.1 YAML schema

```yaml
# data/decision_points/brazil_2024.yaml
- id: bra_2024_norris_sc_pit
  meeting: brazil_2024
  session: race
  driver_code: NOR
  lap_number: 32                      # VERIFY against ingested data
  decision_type: safety_car_pit       # enum: pit_now_vs_stay_out | safety_car_pit |
                                      #       cover_undercut | extend_stint |
                                      #       switch_to_wet | late_race_attack |
                                      #       defend_position | recover_after_bad_stop
  difficulty_level: 4                 # 1 (easy) to 5 (hard)
  scenario_title: "Safety car at Interlagos — pit or stay?"
  scenario_description: |
    Heavy rain has been falling for ten minutes. The safety car has just been
    deployed after Stroll's incident. You're leading on intermediates that are
    fifteen laps old. The field is bunched. Do you pit for fresh inters and
    sacrifice track position, or stay out and gamble that the conditions improve?
  race_state:
    position: 1                       # VERIFY
    compound: INTERMEDIATE
    stint_age_laps: 15
    gap_ahead_s: null                 # leader
    gap_behind_s: 0.8                 # bunched under SC
    rainfall_flag: true
    track_temperature_c: 19
    laps_remaining: 39
  available_actions:
    - id: pit_inters_fresh
      label: "Box for fresh inters"
      tagline: "Track position lost, tire risk gone"
    - id: pit_full_wet
      label: "Box for full wets"
      tagline: "Big gamble — only right if rain intensifies"
    - id: stay_out
      label: "Stay out"
      tagline: "Hold the lead, manage the tires"
  historical_decision: pit_inters_fresh    # what actually happened
  historical_outcome:
    finish_position: 6
    summary: |
      McLaren pitted Norris under the safety car. He rejoined behind several
      drivers who had stayed out. The intended undercut never materialized
      because the SC compressed the field. He finished sixth.
  expert_commentary: |
    [≥150 words explaining what makes this hard, what the textbook answer
    looks like, what the counter-considerations are. This is where your
    F1 fluency lives. Cover: what is the value of track position vs fresh
    rubber under a SC at this circuit? How does Interlagos's pit lane time
    affect the math? What was McLaren's likely reasoning? What's the
    statistical SC-pit-gain in wet conditions? Why did this one not pay off?]
  data_provenance:
    source: fastf1
    session_key: 2024_21_R
    notes: "Lap number and gaps verified against fastf1.get_session(2024, 'Brazil', 'R')"
```

### 10.2 The three Brazil 2024 scenarios for MVP-0

I've left the exact lap numbers, gaps, and positions as `VERIFY` placeholders because race details should come from the data, not from memory. Fill these in during the ingest step (issue #11).

1. **`bra_2024_norris_sc_pit`** — Norris, mid-race safety car: pit for fresh inters or stay out? **Decision type:** `safety_car_pit`. **Difficulty:** 4. *Why it's interesting:* SC pit math is non-obvious; the field-compression effect is what trips up textbook reasoning.

2. **`bra_2024_verstappen_charge`** — Verstappen, mid-race during the rain charge from the back: push hard on warm inters or conserve? **Decision type:** `late_race_attack`. **Difficulty:** 3. *Why it's interesting:* the upside is huge; the downside is a spin in the wet that ends the race.

3. **`bra_2024_inter_to_wet_call`** — A midfield runner facing the call to switch from inters to full wets as conditions deteriorate. **Decision type:** `switch_to_wet`. **Difficulty:** 5. *Why it's interesting:* full wets are almost never the right answer; finding the rare race where they are is the puzzle.

These three together cover three different decision types, three different driver tiers (front-runner / underdog charging / midfielder gambling), and three different risk profiles. That gives MVP-0 enough variety to feel like a real game.

---

## 11. WEEK 3 — MVP-2: Intelligence

**Goal:** ML-assisted recommendations + a real simulation engine + a methodology page that demonstrates rigor.

### Issues

#### Feature engineering
- [ ] **#71** `ingest/build/features.py` — build `feature_pit_decision` from race state
- [ ] **#72** Build `feature_tire_degradation` — rows are (driver, session, lap, compound, stint_age, fuel_adjusted_lap_time)
- [ ] **#73** Build `feature_finish_position` from current state to final classification
- [ ] **#74** Build `feature_undercut_opportunity` from rival pairings per lap
- [ ] **#75** Build `feature_safety_car_pit_gain` from SC events
- [ ] **#76** Train/test split strategy: by season for time-series leakage prevention

#### Models
- [ ] **#77** `ml/models/tire_degradation.py` — gradient-boosted regressor predicting lap time delta given compound, stint age, track temp, circuit
- [ ] **#78** `ml/models/pit_decision.py` — calibrated logistic regression: should pit within next 3 laps? (binary)
- [ ] **#79** `ml/train.py` — CLI: `uv run python -m ml.train --target pit_decision`
- [ ] **#80** `ml/evaluate.py` — accuracy, F1, ROC-AUC, calibration plot, confusion matrix per circuit
- [ ] **#81** `ml/registry.py` + `ml_model_registry` table — track model_name, version, training_data_version, metrics, artifact_path
- [ ] **#82** Save artifacts via joblib to `models/` (gitignored), small models can also be checked in for reproducibility

#### Simulation engine v2
- [ ] **#83** Replace heuristic tire degradation with model output
- [ ] **#84** Add weather modifier (rainfall intensity affects pace and tire choice)
- [ ] **#85** Add safety car / VSC compression effect on gaps
- [ ] **#86** Add risk score: variance in projected outcome across N=1000 monte carlo runs
- [ ] **#87** `sim/engine.py` returns `ProjectedOutcome(position, position_band, finish_time_delta, risk_score, explanation)`

#### Scoring v2
- [ ] **#88** New scoring formula: 30% historical match, 30% simulated outcome rank, 20% model agreement, 20% risk-adjusted
- [ ] **#89** Generate human-readable explanations from numerical components
- [ ] **#90** Grade labels: Genius (95+), Strong call (80–94), Solid (65–79), Risky (50–64), Reconsider (<50)

#### Methodology page
- [ ] **#91** `pages/Methodology.tsx` — explains data sources, model targets, evaluation metrics
- [ ] **#92** Embed model evaluation plots (ROC, calibration, error-by-circuit) — generate as static PNGs from notebook
- [ ] **#93** Model card markdown for each registered model (`docs/model_cards.md`)
- [ ] **#94** "How scoring works" section with worked example
- [ ] **#95** Honest limitations section: what the model gets wrong, where the heuristics dominate, what's missing

#### API + frontend
- [ ] **#96** `POST /predict/pit-decision` — model inference endpoint
- [ ] **#97** `GET /models` — list registered models with metrics
- [ ] **#98** Result screen now shows 4 perspectives side-by-side: user / historical / model / simulation
- [ ] **#99** Recharts visualization of projected outcome distribution (histogram of monte carlo runs)
- [ ] **#100** "Why?" expandable explanations on each result

#### Notebooks
- [ ] **#101** `02_tire_degradation.ipynb` — full narrative of feature engineering, model selection, evaluation
- [ ] **#102** `03_pit_decision_model.ipynb` — same but for the classifier
- [ ] **#103** `04_simulation_validation.ipynb` — sim outputs against held-out historical races, error analysis

### Done when

Methodology page reads like the work of someone who's done this before. Model evaluation is honest. Result screens feel like real analysis, not flair.

---

## 12. WEEK 4 — MVP-3: Chaos & Ship

**Goal:** Chaos Engine works, app is deployed at a custom domain, demo video is on the landing page, repo passes a stranger's code review.

### Issues

#### Chaos Engine
- [ ] **#104** `ingest/schema/005_chaos.sql` — `chaos_modifier_type`, `chaos_scenario_run`, `chaos_event` tables
- [ ] **#105** `sim/chaos.py` — apply modifier to forward simulation:
  - [ ] `safety_car_now` (lap N)
  - [ ] `vsc_now` (lap N, duration M)
  - [ ] `rain_in_5_laps` (intensity 0–1)
  - [ ] `slow_pit_stop` (extra K seconds on next stop)
  - [ ] `tire_cliff_now` (compound X loses Z seconds/lap effective immediately)
  - [ ] `rival_pit_lap` (driver Y pits at lap N)
  - [ ] `red_flag_at_lap` (lap N)
- [ ] **#106** `POST /chaos/simulate` — body includes scenario id, user action, modifier list
- [ ] **#107** `components/ChaosToggle.tsx` — modifier picker UI
- [ ] **#108** Mode selector on scenario screen: Historical / Chaos / Mixed
- [ ] **#109** Result screen handles chaos mode: "In your alternate timeline..."

#### Polish
- [ ] **#110** Design pass on every screen — typography scale, color tokens, spacing audit
- [ ] **#111** Accessibility audit — keyboard navigation, ARIA labels, contrast
- [ ] **#112** Lighthouse pass — performance, accessibility, SEO, best practices all >90
- [ ] **#113** Custom 404 page
- [ ] **#114** Open Graph + Twitter card meta — generated share image per scenario
- [ ] **#115** Page-level analytics (Plausible or Vercel Analytics)
- [ ] **#116** `pages/About.tsx` — what this is, why it exists, who built it (link to your portfolio)

#### Deploy
- [ ] **#117** Buy domain (`undercut.app` if available, alternatives: `playundercut.com`, `undercut.gg`)
- [ ] **#118** Vercel deployment for `web/` — production branch from `main`
- [ ] **#119** Fly.io deployment for `api/` — Dockerfile + `fly.toml`
- [ ] **#120** Neon production branch + connection string in Fly secrets
- [ ] **#121** ETL pipeline runs from local: documented in `docs/operations.md`
- [ ] **#122** Custom domain pointed, SSL verified
- [ ] **#123** Smoke test the deployed site end-to-end

#### Marketing / portfolio
- [ ] **#124** Re-record demo video with deployed URL — 90 seconds, polished
- [ ] **#125** Embed demo video on landing page (above the fold, autoplay muted)
- [ ] **#126** Final `README.md` pass — TL;DR, screenshots, video link, architecture diagram, links to methodology + model cards
- [ ] **#127** Architecture diagram in `docs/` — produced cleanly (excalidraw or mermaid)
- [ ] **#128** Write a launch post (LinkedIn + personal blog if you have one) — link to demo, key technical decisions, what you'd build next
- [ ] **#129** Add to portfolio site

### Done when

You can paste the URL into a recruiter's chat and feel proud. A friend who doesn't know F1 plays a scenario and finds it interesting. Your repo's README answers every question a code reviewer would ask without you needing to explain.

---

## 13. Simulation Engine Spec

### 13.1 Architecture

```python
@dataclass
class RaceState:
    session_id: str
    driver_id: str
    lap_number: int
    laps_remaining: int
    position: int
    compound: str
    stint_age: int
    gap_ahead_s: float | None
    gap_behind_s: float | None
    track_status: str
    rainfall_flag: bool
    track_temperature_c: float
    air_temperature_c: float

@dataclass
class StrategyAction:
    action_id: str  # pit_now | stay_out | switch_to_hard | ...
    target_compound: str | None

@dataclass
class ChaosModifier:
    modifier_type: str  # safety_car_now | rain_in_5_laps | ...
    parameters: dict

@dataclass
class ProjectedOutcome:
    finish_position: int
    finish_position_band: str  # "P3-P5"
    finish_time_delta_to_winner_s: float
    risk_score: float          # 0..1, std dev of monte carlo
    components: dict           # per-lap projections, for explainability
    explanation: str

def simulate_forward(
    state: RaceState,
    action: StrategyAction,
    modifiers: list[ChaosModifier] | None = None,
    n_runs: int = 1000,
) -> ProjectedOutcome: ...
```

### 13.2 Heuristic constants (MVP-0)

These are eyeball defaults; week 3 replaces them with learned values.

```python
# Tire degradation: lap time loss per lap of stint age
TIRE_DEGRADATION_S_PER_LAP = {
    "SOFT": 0.08,
    "MEDIUM": 0.05,
    "HARD": 0.03,
    "INTERMEDIATE": 0.10,
    "WET": 0.06,
}

# Circuit-specific pit loss (seconds)
PIT_LOSS_S = {
    "interlagos": 22.0,
    "monaco": 19.0,
    "spa": 19.5,
    # ...
}

# Traffic penalty per lap when within 1.5s of car ahead
TRAFFIC_PENALTY_S_PER_LAP = 0.5

# Clean air bonus when >2.5s clear
CLEAN_AIR_BONUS_S_PER_LAP = -0.2

# Wet condition multiplier on tire deg
WET_DEG_MULTIPLIER = 1.4
```

### 13.3 Forward sim (week 3)

For each remaining lap, sample a lap time from the model + noise, accumulate, project finishing time, compare to other cars' projected times, derive position. Run N=1000 monte carlo paths, take the median position and the std dev as risk score.

---

## 14. Scoring System Spec

### 14.1 Composite formula

```
score = (
    0.30 * historical_match_score
  + 0.30 * simulated_outcome_score
  + 0.20 * model_agreement_score
  + 0.20 * risk_adjusted_score
) * 100
```

| Component | How it's computed |
|-----------|-------------------|
| `historical_match_score` | 1.0 if user picked the historical action, 0.5 if picked something the historical-outcome-data shows worked for someone else, 0.0 otherwise |
| `simulated_outcome_score` | (best_sim_pos − user_sim_pos) / (best_sim_pos − worst_sim_pos), inverted so higher is better, clipped 0–1 |
| `model_agreement_score` | model's predicted optimal action match — 1.0 exact, 0.5 same direction (both pit / both stay), 0.0 opposite |
| `risk_adjusted_score` | rewards picking actions with good expected value AND low variance, penalizes high-variance gambles unless they paid off |

In MVP-0 (no ML, no monte carlo): `historical_match` and `simulated_outcome` carry full weight 50/50; the other two activate in week 3.

### 14.2 Grade labels

| Score | Grade | Voice |
|-------|-------|-------|
| 95–100 | **Genius** | "The pit wall is taking notes." |
| 80–94 | **Strong call** | "Textbook. Toto would approve." |
| 65–79 | **Solid** | "Reasonable. Defendable on the radio." |
| 50–64 | **Risky** | "Bold. Ask yourself why." |
| 0–49 | **Reconsider** | "Even the simulator winced." |

(Tone: race-engineer dry humor, not condescending.)

---

## 15. Frontend Spec

### 15.1 Voice

- Race-engineer dry, not bombastic
- Monospace for race data (positions, gaps, lap times)
- Sans-serif for narrative (descriptions, commentary)
- Low chrome, high information density
- Animations earn their place — subtle, fast, never blocking

### 15.2 Color tokens

```
--bg: #0a0a0b              (near-black, slight warm tint)
--surface: #16161a
--surface-elev: #1f1f24
--border: #2a2a30
--text: #e8e8ea
--text-dim: #9a9aa2
--accent: #ff1801          (generic motorsport red, not protected)
--accent-cool: #00d2be     (cyan, secondary)
--success: #00b14c
--warning: #ffb300
--danger: #ff4444
```

### 15.3 Key components

- **PitWallRadio** — auto-scrolling terminal feed. Shows race events as they unfold during the scenario "tick" (purely cosmetic in MVP-0; functional in MVP-2 when sim runs lap-by-lap).
- **RaceStateCard** — driver row with team color stripe, compact status line: `P5 · MED · 14L · +2.1 / +4.7`
- **StrategyButtons** — 4–6 large tappable cards. Disabled actions show *why* disabled.
- **ScoreCard** — animated score reveal, grade label, expandable "why" sections.
- **ChaosToggle** — pill-style modifier picker, only visible in chaos mode.

---

## 16. API Spec

```
GET    /healthz
GET    /seasons
GET    /meetings?season=2024
GET    /meetings/{meeting_id}/sessions
GET    /sessions/{session_id}/drivers
GET    /sessions/{session_id}/race-state?lap=N

GET    /scenarios?race=brazil_2024&difficulty=4&decision_type=safety_car_pit
GET    /scenarios/{scenario_id}
POST   /scenarios/{scenario_id}/decision
        body: {action_id, mode: "historical"|"chaos", chaos_modifiers?: [...]}

POST   /simulate
        body: {race_state, action, modifiers?}
POST   /predict/pit-decision
        body: {race_state}

GET    /models
GET    /models/{model_id}
```

All POST endpoints return JSON with `score`, `grade`, `historical_decision`, `model_recommendation`, `simulation_summary`, `explanation`. Standard error envelope: `{error: {code, message, detail?}}`.

---

## 17. Deployment Plan

| Component | Where | Notes |
|-----------|-------|-------|
| Frontend | Vercel | Auto-deploy from `main`. Preview deploys on PRs. |
| Backend | Fly.io | Single small VM, 256MB plenty. Health check on `/healthz`. |
| Database | Neon | Free tier, auto-suspend OK; first-request latency tolerated. |
| Domain | Namecheap or Cloudflare | $12/year. Cloudflare DNS for CDN. |
| Secrets | Fly secrets + Vercel env vars | Never check in `.env` |
| Logs | Fly.io built-in + Vercel built-in | Sufficient for v1 |
| Monitoring | Plausible Analytics | Privacy-friendly, simple |

ETL runs from local for v1. Document how to run it. Schedule it via cron or GitHub Actions in a post-launch task.

---

## 18. Source Priority Rules

When the same logical field appears in multiple sources, resolve by priority:

| Field group | Priority order |
|-------------|----------------|
| Historical metadata (drivers, constructors, circuits) | Jolpica via FastF1 → Kaggle bootstrap → manual correction |
| Modern session detail (laps, stints, pit, weather, race control) | FastF1 → OpenF1 → derived → manual correction |
| Results / classification | Jolpica via FastF1 → FastF1 timing-derived → Kaggle → manual |
| Intervals / position time-series | OpenF1 → derived from FastF1 → manual |

Manual corrections live in `manual_data_correction` table, applied as a final transform. Every correction has `correction_reason` and `source_reference`.

---

## 19. IP & Disclaimer

### Must do
- "Unofficial fan project" disclaimer in footer of every page
- Attribution to FastF1, OpenF1, Jolpica on methodology page
- License repo as MIT

### Must avoid
- F1, FORMULA 1, FORMULA ONE in the product name (Undercut sidesteps this)
- F1 logo, team logos, driver photos sourced from official media
- Driver-likeness in marketing materials
- Any UI element that mimics official F1 broadcast graphics in a way that implies endorsement

### Acceptable
- "an unofficial Formula 1 strategy simulator" in body copy (factual description)
- Generic team colors as data attributes (Mercedes silver-cyan, Ferrari red)
- Driver names and three-letter codes (factual data, not protected)
- Circuit names

---

## 20. Out of Scope (Explicit)

To stay in 4 weeks, these are *not* in v1:

- Real-time / live race companion (OpenF1 paywalls live data anyway)
- Multiplayer / social features
- User accounts / saved progress (localStorage is enough)
- Full season simulator
- Telemetry-grade analysis
- Team-radio audio processing
- Fantasy mode
- Mobile native apps
- Internationalization (English only)
- Pre-2023 detailed decision points
- Any practice-session scenarios (race + sprint + qualifying only)

Capture good post-v1 ideas in `docs/roadmap_v2.md` as you have them.

---

## 21. Daily Operating Rhythm

A 4-week full-time sprint succeeds on rhythm, not heroics. Suggested cadence:

- **Morning (4h):** the hardest engineering work of the day — schema, sim, ML, anything requiring deep focus
- **Lunch + walk:** non-negotiable
- **Afternoon (3h):** integration work — wiring API to frontend, debugging, polish
- **Evening (1–2h):** decision-point copywriting, methodology writing, video script work, demo prep — the parts that need calm and attention to language, not code

End each day by ticking issues off this plan and adding new ones discovered. End each week by recording an updated demo video (even a rough one) — it forces you to confront whether the work is actually shippable, and it keeps the artifact trail visible.

---

## 22. Closing Out Issues

This plan contains **129 numbered issues**. Treat them as your GitHub project board. Recommended workflow:

1. Create a GitHub Project (table view) with columns: `Backlog`, `Week 1` / `Week 2` / `Week 3` / `Week 4`, `In progress`, `Review`, `Done`
2. Generate issues from this plan in one batch — each `**#N**` line becomes one issue, body = the bullet text
3. Label by week and by area (`area:ingest`, `area:sim`, `area:ml`, `area:api`, `area:web`, `area:infra`, `area:docs`)
4. For opencode workflows: point the agent at this plan as the source-of-truth, use issue numbers in commit messages (`feat: implement #18 simulation engine forward pass`)
5. Close the issue when the corresponding deliverable is in `main` and tested

When something blocks an issue, don't reorder the plan — append a new issue and link it. The plan is durable; the order is flexible inside a week.

---

*End of plan. Build well.*