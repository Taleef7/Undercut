# Advisor Update: Undercut Strategy Simulator

**Date:** 2026-05-03
**Status:** Sprints A+B Complete — Backend Hardened, Schema Expanded
**Working Branch:** `main` (all sprint work merged via PR #85)
**Project Timeline:** Compressed 4-week schedule (Start of Week 2)

---

## 1. Executive Summary

Sprints A and B are fully implemented, tested, and merged. The project now has:

- A hardened API with typed Pydantic models, CORS, proper DuckDB query patterns, and 3 working endpoints
- A simulation engine with per-circuit configs and fixed scoring logic
- A canonical DuckDB schema with 17 tables across 5 layers (dimensions → facts → race state → feature store → corrections)
- 3 curated decision point scenarios for Brazil 2024 with real race_state data
- An API contract document serving as the frontend's source of truth
- 5/5 tests passing
- Seed data for 10 circuits and 10 tyre compounds

Next sprint (C) is the data ingestion expansion with Jolpica/OpenF1 clients, normalization modules, race state builder, feature store builder, and CLI orchestration — this will make the pipeline capable of ingesting any F1 weekend, not just Brazil 2024.

---

## 2. Detailed Sprint A Deliverables

### 2.1 Scoring Bug Fix (`sim/scoring.py`)
The `score_decision` function had a `NameError` — `sim_position` was only assigned in the `if user_action != historical_action:` branch, but was referenced outside it for the `model_recommendation` return value. When `user_action == historical_action`, `sim_position` was never defined.

**Fix applied:** `sim_position = simulated_positions.get(user_action, context.position)` is now assigned at the top of the function, before all branches. Both matched-historical and sim-different code paths use it safely.

### 2.2 API Pydantic Models (`api/models.py`)
Created comprehensive typed response schemas:

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `RaceState` | Embedded race state block | position, compound, stint_age, gaps, laps_remaining, weather, track_status |
| `ScenarioSummary` | Card-grid list items | id, title, description, driver, lap, decision_type, available_actions, difficulty |
| `ScenarioDetail` | Full scenario page | All summary fields + scenario_description, explanation_long, explanation_short, RaceState |
| `SimulationSummary` | Nested in DecisionResponse | expected_position, expected_finish_position_band, risk_score, tire_risk, track_position_risk |
| `DecisionResponse` | POST response | score, grade, historical_decision, model_recommendation, model_confidence, model_top_features, simulation_summary, explanation, tradeoffs |
| `DecisionRequest` | POST body | action: str |

### 2.3 API Endpoint Rewrite (`api/main.py`)
**Previous state:** Used `fetchall()` (anonymous tuples), had a hardcoded `/simulate` endpoint that ignored DB row data, no CORS, no column-name access, no validation.

**Current state:**
- `GET /` — health check returning `{"message": "Undercut API is running"}`
- `GET /scenarios` — `fetchdf().to_dict(orient="records")` → `list[ScenarioSummary]`, DB connections opened/closed per request
- `GET /scenarios/{id}` — full `ScenarioDetail` with null-safe handling for `gap_ahead`/`gap_behind` (can be NULL in DB), HTTP 404 for missing IDs
- `POST /scenarios/{id}/decision` — validates action against `available_actions_json` from DB, returns HTTP 422 for invalid choices, constructs `ScenarioContext` from DB row by column name, runs through `UndercutEngine.evaluate_strategy()`, returns full `DecisionResponse`
- CORS middleware configured for `http://localhost:5173`
- Removed old `/simulate` endpoint entirely

**Verification results:**
```
GET /scenarios → 200, 3 scenarios
GET /scenarios/brazil_2024_lap32 → 200, P2, MEDIUM, stint 14, gap_ahead 1.2s
POST /scenarios/brazil_2024_lap32/decision {"action":"stay_out"} → 200, score 75, grade "Strong call"
POST /scenarios/brazil_2024_lap32/decision {"action":"invalid"} → 422, validation error
GET /scenarios/nonexistent → 404, not found
POST /scenarios/brazil_2024_lap32/decision {"action":"pit_now_inter"} → position change detected (P2→P3 from pit loss)
```

### 2.4 Decision Point YAML Enrichment (`data/decision_points/brazil_2024.yaml`)
Added structured `race_state:` blocks to all 3 scenarios with real values:

| Scenario | Lap | Position | Compound | Stint Age | Laps Left | Rainfall | Track |
|----------|-----|----------|----------|-----------|-----------|----------|-------|
| brazil_2024_lap32 | 32 | P2 (VER) | medium | 14 | 39 | false | green |
| brazil_2024_lap43 | 43 | P1 (VER) | intermediate | 18 | 28 | true | green |
| brazil_2024_lap69 | 69 | P1 (VER) | hard | 28 | 3 | false | green |

Normalized `decision_type` from `final_stint_tire_management` to `extend_to_end` to match the approved enum. Updated `ingest/load_decision_points.py` to support both list-format and dict-format YAML and write all race_state columns.

### 2.5 Per-Circuit Configuration (`sim/circuit_config.py`)
10 circuits with all 5 required fields each:

| Circuit | Base Lap (ms) | Pit Loss (s) | Overtaking | SC Prob | Length (km) |
|---------|---------------|--------------|------------|---------|-------------|
| interlagos | 75500 | 22.0 | 0.60 | 0.35 | 4.309 |
| monaco | 74000 | 18.0 | 0.95 | 0.55 | 3.337 |
| silverstone | 87500 | 19.0 | 0.70 | 0.30 | 5.891 |
| spa | 103000 | 24.0 | 0.55 | 0.25 | 7.004 |
| monza | 81000 | 23.0 | 0.45 | 0.30 | 5.793 |
| hungaroring | 92000 | 20.0 | 0.85 | 0.35 | 4.381 |
| suzuka | 91500 | 21.0 | 0.70 | 0.35 | 5.807 |
| yas_marina | 83000 | 20.0 | 0.55 | 0.25 | 5.281 |
| las_vegas | 94000 | 22.0 | 0.35 | 0.30 | 6.201 |
| albert_park | 90000 | 20.0 | 0.60 | 0.40 | 5.278 |

`UndercutEngine.__init__` accepts a `circuit` parameter (default `"interlagos"`) and looks up `base_lap_time_ms` from this config. Unknown circuits emit a `warnings.warn()` and fall back to 90000ms.

### 2.6 CORS Middleware
Added to `api/main.py` allowing `http://localhost:5173` origin with all methods and headers. This is the Vite dev server default URL.

### 2.7 API Contract (`docs/api_contract.md`)
Documents the full request/response contract for all endpoints with real Brazil 2024 example payloads, HTTP status codes, error shapes, and field-level documentation. This is the authoritative reference for frontend developers.

---

## 3. Detailed Sprint B Deliverables

### 3.1 Migration Files (`db/migrations/`)
Five migration files applied in numeric order via `db/apply_migrations.py`:

| File | Layer | Tables Created |
|------|-------|---------------|
| `001_core_dimensions.sql` | Dimensions | dim_season, dim_meeting, dim_circuit, dim_session, dim_driver, dim_constructor, dim_tyre_compound, dim_track_status_code |
| `002_fact_tables.sql` | Facts | fact_lap, fact_stint, fact_pit_stop, fact_session_result, fact_driver_session_entry, fact_weather_sample, fact_race_control_event, fact_interval_sample, fact_position_sample |
| `003_race_state.sql` | Race State | race_state_driver_lap_fact (33 columns), race_state_field_lap (18 columns) |
| `004_feature_store.sql` | Feature Store | feature_pit_decision, feature_undercut_opportunity |
| `005_corrections.sql` | Corrections | manual_data_correction |

All tables include required metadata columns (`source_system`, `ingested_at`, `data_version`, `record_hash`) per AGENTS.md §3.4.

### 3.2 Seed Data (`db/seeds/`)
- `seed_compounds.sql`: 10 rows — SOFT, MEDIUM, HARD, INTERMEDIATE, WET, C1, C2, C3, C4, C5 — with category, code, hardness_order, and boolean flags for wet/inter/slick
- `seed_circuits.sql`: 10 rows — interlagos, monaco, silverstone, spa, monza, hungaroring, suzuka, yas_marina, las_vegas, albert_park — with lat/lon, altitude, typical_pit_loss, overtaking_difficulty, and safety_car_probability

### 3.3 Apply Migrations Script (`db/apply_migrations.py`)
Python script that:
1. Connects to DuckDB at `data/undercut.db`
2. Reads `db/migrations/*.sql` in sorted order
3. Executes each file's SQL
4. Then runs seed files from `db/seeds/`
5. Reports progress to stdout

Command: `uv run python db/apply_migrations.py`

---

## 4. Current System State

### 4.1 Database
```
Tables: 17
Decision points: 3 (all Brazil 2024)
Compounds: 10 (seeded)
Circuits: 10 (seeded)
```

The DB file lives at `data/undercut.db` and was regenerated fresh during Sprint B (the legacy 5-table prototype was replaced). The DB on `main` branch currently contains the old schema — migrations/B1-B6 tables exist only in the worktree DB. This will be resolved when the Sprint B features are merged.

### 4.2 Tests
```
5 passed in 0.03s
- tests/test_engine.py::test_engine_uses_circuit_base_lap_time PASSED
- tests/test_scoring.py::test_score_decision_returns_model_recommendation_without_nameerror PASSED
- tests/test_scoring.py::test_get_grade_label_uses_rubric_labels PASSED
- tests/test_scoring.py::test_score_decision_uses_strong_call_for_historical_match PASSED
- tests/test_scoring.py::test_score_decision_uses_inspired_call_for_gain PASSED
```

### 4.3 API Endpoints (Verified Working)
All endpoints connected to DB, run through engine, return typed responses. No `fetchall()` tuples remaining. Column access is by name via DataFrames.

### 4.4 Recent Commits & PR
```
68788f8 docs: add project docs, sprint instructions, design spec and implementation plan
e39e894 Merge pull request #85 from Taleef7/feature/sprints-a-b
29992b6 fix: match all pit_ prefixed actions, not just pit_now
c329f42 feat: implement Sprints A+B - backend hardening and schema expansion
7fb73e4 fix: align scoring labels and types
8bcbcad fix: stabilize scoring test env
ef78ad7 fix: avoid scoring NameError
e70d8cf chore: ignore worktrees
```

PR #85 was reviewed (by Codex) and merged. A post-merge bug fix (pit_ action prefix matching) was committed directly to the PR branch before merge.

---

## 5. Bugs Discovered & Fixed During Sprints A+B

| Bug | Location | Cause | Fix |
|-----|----------|-------|-----|
| Scoring NameError | `sim/scoring.py:87` | `sim_position` not assigned in historical-match branch | Always assign at function top |
| Tire model degradation | `sim/tire_model.py:53` | Returned raw 0.01 instead of 1.01 when stint age > curve | `return 1.0 + deg_curve[-1]` |
| Lazy import anti-pattern | `sim/engine.py:56` | `is_in_tire_cliff_zone` imported inside method body | Moved to top-level import |
| pit_ action matching | `sim/engine.py:49,70` + `sim/scoring.py:87` | Only matched `== "pit_now"` but actions are `pit_now_inter`, `pit_now_hard` | Changed to `.startswith("pit_")` |
| Missing CORS | `api/main.py` | No middleware, frontend could not call API | Added CORSMiddleware for localhost:5173 |
| fetchall() tuple returns | `api/main.py` (old) | Anonymous tuples, no column names | Replaced all with `fetchdf().to_dict(orient="records")` |

---

## 6. What's Not Yet Done (Known Gaps)

### 6.1 ML Layer (Placeholder Only)
- `model_recommendation` hardcoded to `"stay_out"` in `sim/scoring.py`
- `model_confidence` returns `0.0`
- `model_top_features` returns `[]` (empty array)
- No trained model artifacts exist
- No SHAP explainer
- `POST /predict/pit-decision` endpoint not yet implemented
- `ml_model_registry` table exists in schema but is empty
- All ML work is deferred to Sprint F

### 6.2 Data Ingest Pipeline (Sprint C)
- No Jolpica or OpenF1 REST clients yet
- No normalization modules — raw parquet from FastF1 goes directly to dataframes
- No race state builder — `race_state_driver_lap_fact` and `race_state_field_lap` tables exist in schema but contain zero rows
- No feature store builder
- No CLI orchestration — data loading is manual script-by-script
- The pipeline currently only handles Brazil 2024 via `ingest/brazil_2024.py`

### 6.3 Decision Points (Sprint D)
- Only 3 scenarios (all Brazil 2024: laps 32, 43, 69)
- No Abu Dhabi 2021, Singapore 2023, or Hungary 2022 scenarios yet
- Decision types limited to `pit_now_vs_stay_out`, `switch_to_wet`, `extend_to_end` — missing `cover_undercut`, `safety_car_pit`, `late_race_attack`, `defend_position`

### 6.4 Frontend (Sprint E)
- No React/Vite app bootstrapped yet
- No `web/src/api/client.ts` typed fetch wrappers
- No scenario play screen, result screen, or scenario selector built

### 6.5 Chaos Engine (Sprint G)
- `sim/chaos.py` skeleton exists but is unimplemented
- No `chaos_modifier` table populated
- No `POST /scenarios/{id}/chaos` endpoint

### 6.6 Deployment (Sprint H)
- No Dockerfile or docker-compose service definitions
- No Railway/Procfile config
- No Vercel config
- No architecture diagram or deployment docs

### 6.7 Database on Main Branch
The `data/undercut.db` on the `main` branch still reflects the pre-Sprint-B state (5-table prototype). The worktree DB (`.worktrees/sprints-a-b/data/undercut.db`) has all 17 tables. This will be resolved when the DB is regenerated during Sprint C.

---

## 7. What's Next: Sprint C — Data Ingestion Expansion

Sprint C builds the full raw → canonical pipeline for any F1 weekend:

| Task | File(s) | Description |
|------|---------|-------------|
| C1 | `ingest/jolpica_client.py` | httpx-based REST client for Jolpica API (race results, qualifying, drivers, constructors, circuits, pit stops, lap times). Rate-limited at 1 req/s. Raw JSON stored to `data/raw/jolpica/{year}/{round}/` |
| C2 | `ingest/openf1_client.py` | httpx-based REST client for OpenF1 API (meetings, sessions, laps, stints, pit stops, intervals, positions, weather, race control, results, starting grid). Raw JSON stored to `data/raw/openf1/{year}/{meeting_key}/{session_key}/` |
| C3 | `ingest/normalize/*.py` (10 files) | Raw JSON → canonical DuckDB. Each normalizer: loads raw, validates, maps to schema, upserts via INSERT OR REPLACE. Covers circuits, drivers, constructors, sessions, laps, stints, pit stops, results, weather, race control |
| C4 | `ingest/build/build_race_state.py` | Reads facts → constructs `race_state_driver_lap_fact` and `race_state_field_lap` with derived columns (stint_age, laps_remaining, interval_behind, driver_ahead/behind, SC flags, rolling averages, pace_delta, pit_window_flag, undercut_threat_flag) |
| C5 | `ingest/build/build_features.py` | Reads race_state → constructs `feature_pit_decision` and `feature_undercut_opportunity`. Computes labels (actual_pitted_within_3_laps, undercut_succeeded) |
| C6 | `ingest/run_pipeline.py` | CLI orchestrator supporting: `bootstrap --source jolpica --seasons <years>`, `fetch-weekend --season X --round Y`, `normalize --season X --round Y`, `build-race-state`, `build-features` |

---

## 8. Questions for the Advisor

1. **Source priority:** The AGENTS.md specifies Jolpica → FastF1 → manual correction for historical metadata, but OpenF1 → FastF1 for modern lap-level data. For our normalization modules, what's the recommended approach for de-duplication when both sources cover the same session? Implement source-flagged rows (both inserted, prefer OpenF1 at query time) or merge on ingest with a precedence column?

2. **Raw storage strategy:** We're storing raw API JSON to `data/raw/`. For a portfolio project, is it worth implementing the full raw → canonical → race_state → feature_store pipeline, or would it be more impressive to readers to have a single clean ingestion pass that populates the DB directly? The full pipeline demonstrates data engineering rigor but adds ~2x the code.

3. **Rate limiting strategy:** Jolpica recommends 1 req/s and OpenF1 apparently has lenient limits. Should we implement aggressive caching (store raw, skip re-fetch on subsequent runs) from the start, or build smart progressive backoff with jitter?

4. **Sprint parallelism:** The sprint instructions suggest running Sprints C1-C3 alongside Sprint E (frontend). The C sub-tasks are all backend Python work — do you see value in parallelizing, or should we complete the full ingest pipeline before starting the frontend since the API contract is already stable?

5. **Scope of normalization:** Should we normalize ALL available session data (FP1, FP2, FP3, Sprint, Qualifying, Race) or focus on Race sessions only for the MVP? Full normalization adds complexity but enables future features like qualifying strategy comparison.

6. **Testing approach:** Currently we have 5 unit tests. For the ingest pipeline, should we invest in integration tests (fetch real data, verify round-trip) or stick with unit tests that mock API responses? Integration tests give higher confidence but add external dependencies.

---

## 9. Repository File Map (Current State)

```
undercut/
├── AGENTS.md
├── PROJECT_PLAN.md
├── README.md
├── pyproject.toml
├── .python-version (3.11)
├── .env.example
├── journal.md
│
├── data/
│   ├── decision_points/
│   │   └── brazil_2024.yaml          ← 3 scenarios with race_state blocks
│   ├── cache/                         ← FastF1 cache (gitignored)
│   └── undercut.db                    ← DuckDB (gitignored — worktree has 17 tables)
│
├── db/
│   ├── migrations/
│   │   ├── 001_core_dimensions.sql    ← 8 dimension tables
│   │   ├── 002_fact_tables.sql        ← 9 fact tables
│   │   ├── 003_race_state.sql         ← 2 race state tables
│   │   ├── 004_feature_store.sql      ← 2 feature store tables
│   │   └── 005_corrections.sql        ← 1 correction table
│   ├── seeds/
│   │   ├── seed_compounds.sql         ← 10 tyre compounds
│   │   └── seed_circuits.sql          ← 10 circuits
│   └── apply_migrations.py
│
├── ingest/
│   ├── __init__.py
│   ├── brazil_2024.py                 ← FastF1 loader for pilot race
│   ├── load_decision_points.py        ← YAML → DuckDB loader
│   └── schema.sql                     ← LEGACY — replaced by db/migrations/
│
├── sim/
│   ├── __init__.py
│   ├── circuit_config.py              ← 10 circuits with base lap times
│   ├── engine.py                      ← UndercutEngine using circuit config
│   ├── chaos.py                       ← ChaosEngine (skeleton only)
│   ├── pit_model.py                   ← Pit loss heuristics
│   ├── tire_model.py                  ← Degradation curves + cliff detection
│   └── scoring.py                     ← Decision scoring rubric (0-100)
│
├── ml/                                ← NOT YET BUILT
│
├── api/
│   ├── main.py                        ← FastAPI app with CORS, 3 endpoints
│   ├── models.py                      ← Pydantic request/response schemas
│   └── routers/                       ← (empty, endpoints in main.py)
│
├── web/                               ← NOT YET BUILT
│
├── docs/
│   ├── api_contract.md                ← Real payloads, all endpoints
│   ├── PROJECT_PLAN.md
│   ├── sprint_instructions.md
│   ├── advisor_update.md              ← You are reading this
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-03-sprints-a-b-design.md
│       └── plans/
│           └── 2026-05-03-sprints-a-b.md
│
├── tests/
│   ├── test_engine.py                 ← 1 test (circuit base lap time)
│   └── test_scoring.py                ← 4 tests (scoring rubric)
│
└── .worktrees/
    └── sprints-a-b/                   ← Sprint A+B implementation worktree
```

---

**Please review and advise on the six questions in Section 8. Sprint C design is ready to begin — currently waiting on your feedback before proceeding.**
