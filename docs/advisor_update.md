# Advisor Update: Undercut Strategy Simulator

**Date:** 2026-05-03  
**Status:** Sprints A+B+C Complete — Full Data Pipeline Built, PR #86 Merged  
**Working Branch:** `main` (PR #85 and #86 both merged)  
**Project Timeline:** Compressed 4-week schedule (End of Week 2)

> **Note for advisor:** This document captures the full state after Sprints A+B+C. We are at a decision point for Sprint ordering (D vs E vs parallel). Questions for you are in Section 9.

---

## 1. Executive Summary

Sprints A, B, and C are fully implemented and tested. The project now has:

- A hardened API with typed Pydantic models, CORS, proper DuckDB query patterns, and 3 working endpoints
- A simulation engine with per-circuit configs and fixed scoring logic
- A canonical DuckDB schema with 17 tables across 5 layers (dimensions → facts → race state → feature store → corrections)
- 3 curated decision point scenarios for Brazil 2024 with real race_state data
- **A complete data ingestion pipeline** — Jolpica + OpenF1 REST clients, 10 normalizers, validation layer, race state builder, feature store builder, CLI orchestrator with 6 commands
- An API contract document serving as the frontend's source of truth
- **68 tests passing**, 0 failures
- Seed data for 10 circuits and 10 tyre compounds

Next sprint (D or E) can proceed in parallel — the API contract is stable, and the pipeline can now ingest any F1 weekend, not just Brazil 2024.

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
- `seed_compounds.sql`: 10 rows — SOFT, MEDIUM, HARD, INTERMEDIATE, WET, C1, C2, C3, C4, C5
- `seed_circuits.sql`: 10 rows — interlagos, monaco, silverstone, spa, monza, hungaroring, suzuka, yas_marina, las_vegas, albert_park

### 3.3 Apply Migrations Script (`db/apply_migrations.py`)
Runs migrations in numeric order, then seeds. Command: `uv run python db/apply_migrations.py`

---

## 4. Detailed Sprint C Deliverables — Data Ingestion Pipeline

Sprint C built the full raw → canonical pipeline: API clients → raw storage → normalization → validation → race state builder → feature store builder → CLI orchestration. All 68 tests pass.

### 4.1 BaseClient ABC (`ingest/base_client.py`)

Abstract base class with shared HTTP logic:
- **Cache-first:** `_get(endpoint, params)` checks `data/raw/` before making any API call. If the raw file exists, it's loaded from disk — idempotent reruns are free.
- **Exponential backoff with jitter:** 3 retries, starting at 1s, with `actual_sleep = delay * (0.5 + random())` jitter. Max wait ~30s per request.
- **Subdirectory-structured cache:** Cache paths include query parameters for uniqueness — e.g., `laps_session_key_9540.json`.
- **Required abstract methods:** `BASE_URL`, `RAW_DIR`, `_get_headers()`.
- 6 tests covering cache hit, cache miss, retry exhaustion, and URL construction.

### 4.2 JolpicaClient (`ingest/jolpica_client.py`)

REST client for `https://api.jolpi.ca/ergast/f1/`. Implements 7 endpoints:

| Method | Endpoint | Storage Path |
|--------|----------|-------------|
| `fetch_raw_all_time()` | `circuits.json` | `data/raw/jolpica/all_time/circuits.json` |
| `fetch_raw_bootstrap(season)` | `drivers.json`, `constructors.json` | `data/raw/jolpica/{season}/season/drivers.json` |
| `fetch_raw(season, round)` | `results.json`, `qualifying.json`, `pit_stops.json`, `laps.json` | `data/raw/jolpica/{season}/{round}/` |

- **Paginated laps:** `_get_all_paginated()` handles Jolpica's 30-lap page limit with offset-based pagination.
- **1 req/s rate limiting:** `time.sleep(1.0)` between paginated requests.
- 5 tests covering URL construction, bootstrap fetch, round endpoints, all-time circuits, and multi-page pagination.

### 4.3 OpenF1Client (`ingest/openf1_client.py`)

REST client for `https://api.openf1.org/v1/`. Implements 9 endpoints:

| Method | Endpoint |
|--------|----------|
| `get_meetings(year)` | `/meetings?year={year}` |
| `get_sessions(meeting_key)` | `/sessions?meeting_key={key}` |
| `get_laps(session_key)` | `/laps?session_key={key}` |
| `get_stints(session_key)` | `/stints?session_key={key}` |
| `get_pit(session_key)` | `/pit?session_key={key}` |
| `get_intervals(session_key)` | `/intervals?session_key={key}` |
| `get_position(session_key)` | `/position?session_key={key}` |
| `get_weather(session_key)` | `/weather?session_key={key}` |
| `get_race_control(session_key)` | `/race_control?session_key={key}` |

- **Bulk fetch:** `fetch_session(session_key, meeting_key)` fetches all 7 session endpoints in one call.
- Raw storage: `data/raw/openf1/{year}/{meeting_key}/{session_key}/{endpoint}.json`.
- Includes `User-Agent` header identifying the project.
- 5 tests covering meeting/session lookup and bulk fetch with fixtures.

### 4.4 Normalization Layer (`ingest/normalize/`)

Shared utilities in `ingest/normalize/__init__.py`:
- `compute_record_hash(source_system, source_record_id, key_field_values)` → SHA256 hex digest for idempotent upserts
- `load_raw_json(raw_dir, year, round, endpoint)` → loads cached JSON, returns dict

**Dimension normalizers (4 files, 5 tests):**

| Normalizer | Source | Fixture | Output Table |
|------------|--------|---------|-------------|
| `normalize_circuits.py` | Jolpica | `all_time/circuits.json` | dim_circuit |
| `normalize_drivers.py` | Jolpica | `{year}/season/drivers.json` | dim_driver |
| `normalize_constructors.py` | Jolpica | `{year}/season/constructors.json` | dim_constructor |
| `normalize_sessions.py` | OpenF1 | `{year}/{meeting}/{session}/sessions.json` | dim_session |

**Fact normalizers (6 files, 18 tests in 6 test files):**

| Normalizer | Source | Fixture | Output Table |
|------------|--------|---------|-------------|
| `normalize_results.py` | Jolpica | `results.json` | fact_session_result |
| `normalize_laps.py` | OpenF1 | `laps.json` | fact_lap |
| `normalize_stints.py` | OpenF1 | `stints.json` | fact_stint |
| `normalize_pit_stops.py` | OpenF1 | `pit.json` | fact_pit_stop |
| `normalize_weather.py` | OpenF1 | `weather.json` | fact_weather_sample |
| `normalize_race_control.py` | OpenF1 | `race_control.json` | fact_race_control_event |

All normalizers:
- Load raw JSON from `data/raw/` fixtures
- Compute `record_hash` for every row
- Insert via `INSERT OR REPLACE` for idempotent reruns
- Return `int` row count
- **Compound FK fallback:** Map source labels (SOFT, Soft, S, C3) to `dim_tyre_compound`, fallback to compound_id=99 (UNKNOWN) with warning
- Used explicit column lists (not `SELECT * FROM df`) to avoid DuckDB column count mismatches

### 4.5 Validation Layer (`ingest/validate/`)

**checks.py** — 6 validation functions:
- `check_not_null(df, columns)` — flags null values in required columns
- `check_unique(df, columns)` — flags duplicate key combinations
- `check_lap_range(df, total_laps)` — flags lap numbers outside [1, total_laps]
- `check_record_hash_not_null(df)` — ensures all rows have a hash
- `check_fk_exists(df, col, fk_table, fk_col, db_path)` — verifies foreign key references
- `validate_rows(df, table_name)` — orchestration: runs table-specific checks, returns `(clean_df, warnings_list)`. Bad rows are dropped from output.

**reports.py** — `write_report(warnings, errors, season, round_num, session_type, output_dir)`:
- Writes `validation_report_{season}_{round}_{timestamp}.json` to output directory
- Includes season, round, session_type, timestamp, warning_count, error_count

7 tests covering all check functions and report naming convention.

### 4.6 Builders (`ingest/build/`)

**build_race_state.py** — constructs race state tables from canonical facts:
- `check_prerequisites(session_id, db_path)`:
  - **Hard tier** (fact_lap, fact_stint, fact_pit_stop): raises `ValueError` if zero rows — pipeline must not proceed
  - **Soft tier** (fact_interval_sample, fact_position_sample, fact_weather_sample, fact_race_control_event): emits warnings — derived columns depending on these tables will be NULL
- `build_race_state_driver_lap(session_id, db_path)` — populates `race_state_driver_lap_fact`:
  - Joins `fact_lap` + `fact_stint` + `fact_pit_stop`
  - Derives: `stint_age_laps`, `laps_remaining`, `is_pit_lap`
  - Leaves 15 derived columns NULL for later enrichment (rolling averages, gaps, positions, driver ahead/behind, track status, SC/rain flags, undercut_threat)
- `build_race_state_field_lap(session_id, db_path)` — populates `race_state_field_lap`:
  - Groups driver-lap data per lap number
  - Derives: `running_drivers_count`

**build_features.py** — constructs feature store tables:
- `check_prerequisites(session_id, db_path)`: raises `ValueError` if `race_state_driver_lap_fact` is empty
- `build_feature_pit_decision(session_id, db_path)` — populates `feature_pit_decision`:
  - Copies selected race_state columns
  - Computes `actual_pitted_within_3_laps` label via subquery on `fact_pit_stop`
- `build_feature_undercut_opportunity(session_id, db_path)` — populates `feature_undercut_opportunity`:
  - Maps `driver_behind_id` → `target_driver_ref`, `gap_behind_seconds` → `gap_to_target_seconds`

6 tests (4 race_state + 2 features) covering prerequisites, builder output, and column presence.

### 4.7 CLI Orchestrator (`ingest/run_pipeline.py`)

argparse-based CLI with 6 commands and enforced dependency order:

| Command | Flags | Description |
|---------|-------|-------------|
| `bootstrap` | `--source jolpica`, `--seasons Y1 Y2` | Fetch circuits/drivers/constructors from Jolpica, normalize all |
| `fetch-weekend` | `--season Y --round R [--force]` | Fetch Jolpica + OpenF1 data for a race weekend. `--force` deletes existing raw files first |
| `normalize` | `--season Y --round R [--session R\|Q]` | Transform raw JSON to canonical DuckDB. Defaults to `R` (Race). `Q` skips stints/stops/weather/race_control |
| `build-race-state` | `--season Y --round R` | Construct race_state_driver_lap_fact + race_state_field_lap |
| `build-features` | `--season Y --round R` | Construct feature_pit_decision + feature_undercut_opportunity |
| `validate` | `--season Y --round R [--session R\|Q]` | Run validation checks, write report |

Usage: `uv run python -m ingest.run_pipeline <command> [--flags]`

7 tests covering all 6 commands, defaults (`--session` defaults to `R`), `--force` flag, and missing-command error handling.

### 4.8 Source Deduplication Config (`ingest/__init__.py`)

```python
SOURCE_PRIORITY = {"openf1": 1, "fastf1": 2, "jolpica": 3}
```

For query-time deduplication — insert both sources' rows, then use `QUALIFY ROW_NUMBER() OVER (PARTITION BY ... ORDER BY source_priority ASC) = 1` at query time. This preserves raw data immutability and allows fixing merge rules without re-ingestion.

### 4.9 Integration Test (`tests/test_integration.py`)

End-to-end smoke test: creates DB schema → seeds dim_driver + dim_session + dim_tyre_compound → runs `normalize_results()` against fixture data → verifies 2 rows in `fact_session_result` with correct `position_order` and non-null `record_hash`.

---

## 5. Current System State

### 5.1 Database
```
Tables: 17 (across 5 schema layers)
Decision points: 3 (all Brazil 2024)
Compounds: 10 (seeded)
Circuits: 10 (seeded)
```

### 5.2 Tests
```
68 passed in ~0.15s

Breakdown:
  test_engine.py:              1 test
  test_scoring.py:              4 tests
  test_source_priority.py:      2 tests
  test_base_client.py:          6 tests
  test_jolpica_client.py:       5 tests
  test_openf1_client.py:        5 tests
  test_normalize_dimensions.py: 5 tests
  test_normalize_results.py:    3 tests
  test_normalize_laps.py:       3 tests
  test_normalize_stints.py:     3 tests
  test_normalize_pit_stops.py:  3 tests
  test_normalize_weather.py:    3 tests
  test_normalize_race_control.py:3 tests
  test_validation.py:           7 tests
  test_build_race_state.py:     4 tests
  test_build_features.py:       2 tests
  test_cli.py:                  7 tests
  test_integration.py:          2 tests
```

### 5.3 API Endpoints (Verified Working)
All endpoints connected to DB, run through engine, return typed responses. No `fetchall()` tuples remaining. Column access is by name via DataFrames.

### 5.4 Recent Commits
```
026ec6b test: add integration smoke test, full suite passes
8d0f5b6 feat: add CLI orchestrator with 6 commands, --force, --session
f266e9a feat: add builders (race_state with hard/soft prereqs, features)
f681037 feat: add validation layer (checks + reports with season/round naming)
0d21d1c feat: add fact normalizers for results, laps, stints, pit stops, weather, race_control
96bef92 feat: add normalize utilities and dimension normalizers
66f22fd feat: add OpenF1Client with meeting/session lookup and bulk fetch
cd608cf feat: add JolpicaClient with paginated laps, bootstrap, all-time fetches
9479922 feat: add BaseClient ABC with cache-first, jittered retry
0f7b1f1 feat: add SOURCE_PRIORITY config for query-time dedup
```

Pull requests:
- [PR #85](https://github.com/Taleef7/Undercut/pull/85) — Sprints A+B (merged)
- [PR #86](https://github.com/Taleef7/Undercut/pull/86) — Sprint C (merged, with review fixes)

---

## 6. Bugs Discovered & Fixed (All Sprints)

| Bug | Location | Sprint | Cause | Fix |
|-----|----------|--------|-------|-----|
| Scoring NameError | `sim/scoring.py:87` | A | `sim_position` not assigned in historical-match branch | Always assign at function top |
| Tire model degradation | `sim/tire_model.py:53` | A | Returned raw 0.01 instead of 1.01 when stint age > curve | `return 1.0 + deg_curve[-1]` |
| Lazy import anti-pattern | `sim/engine.py:56` | A | `is_in_tire_cliff_zone` imported inside method body | Moved to top-level import |
| pit_ action matching | `sim/engine.py:49,70` + `scoring.py:87` | A+B | Only matched `== "pit_now"` but actions are `pit_now_inter`, `pit_now_hard` | Changed to `.startswith("pit_")` |
| Missing CORS | `api/main.py` | A | No middleware, frontend could not call API | Added CORSMiddleware for localhost:5173 |
| fetchall() tuple returns | `api/main.py` (old) | A | Anonymous tuples, no column names | Replaced all with `fetchdf().to_dict(orient="records")` |

### Sprint C PR Review Fixes (Post-Merge)

After merging Sprint C, Codex PR review identified 6 additional issues. All were fixed and pushed:

| Fix | Location | Severity | Issue | Resolution |
|-----|----------|----------|-------|------------|
| OpenF1 meeting selection | `ingest/run_pipeline.py` | High | Hardcoded `or args.round == 21` only supported Brazil 2024 | Added `ROUND_TO_CIRCUIT` mapping for all 4 curated races: Brazil 2024 (21), Singapore 2023 (15), Abu Dhabi 2021 (22), Hungary 2022 (13) |
| Hardcoded OpenF1 keys | `ingest/run_pipeline.py` | High | `meeting_key=47, session_key=9540` hardcoded | Added `_resolve_openf1_keys()` helper that queries OpenF1 dynamically by circuit name |
| Validation placeholder | `ingest/run_pipeline.py` | High | `cmd_validate` was a stub — no actual checks run | Now iterates fact tables, runs `validate_rows()` on each, writes real per-weekend reports |
| Decision point idempotency | `ingest/load_decision_points.py` | Medium | `INSERT INTO` would fail on re-run | Changed to `INSERT OR REPLACE INTO` for idempotent loads |
| Dynamic SQL injection risk | `ingest/validate/checks.py` | Medium | `check_fk_exists()` accepted arbitrary table/column names | Added `ALLOWED_TABLES` and `ALLOWED_COLS` allowlists with `ValueError` for unknown identifiers |
| API null handling | `api/main.py` | Medium | `int(row["field"])` crashed on NULL gap values | Changed to `int(row.get("field") or default)` pattern throughout endpoints |

---

## 7. What's Not Yet Done (Known Gaps)

### 7.1 ML Layer (Placeholder Only)
- `model_recommendation` hardcoded to `"stay_out"` in `sim/scoring.py`
- `model_confidence` returns `0.0`
- `model_top_features` returns `[]` (empty array)
- No trained model artifacts exist
- No SHAP explainer
- `POST /predict/pit-decision` endpoint not yet implemented
- `ml_model_registry` table exists in schema but is empty
- All ML work is deferred to Sprint F

### 7.2 Pipeline: Empty Tables
- `race_state_driver_lap_fact` and `race_state_field_lap` tables exist (schema + builders) but contain zero rows on the main DB — the pipeline builds them on-demand per weekend but hasn't been run with real data yet
- `feature_pit_decision` and `feature_undercut_opportunity` tables exist but are empty — same reason
- `fact_penalty_event` table not yet in schema (targeted for Sprint D)
- No real API data fetched yet — all canonical tables on main branch are empty aside from decision points

### 7.3 Decision Points (Sprint D)
- Only 3 scenarios (all Brazil 2024: laps 32, 43, 69)
- No Abu Dhabi 2021, Singapore 2023, or Hungary 2022 scenarios yet
- Decision types limited to `pit_now_vs_stay_out`, `switch_to_wet`, `extend_to_end` — missing `cover_undercut`, `safety_car_pit`, `late_race_attack`, `defend_position`
- Note: the pipeline can now ingest any F1 weekend data via `fetch-weekend`, but the YAML scenarios and decision points are still manual curation

### 7.4 Frontend (Sprint E)
- No React/Vite app bootstrapped yet
- No `web/src/api/client.ts` typed fetch wrappers
- No scenario play screen, result screen, or scenario selector built

### 7.5 Chaos Engine (Sprint G)
- `sim/chaos.py` skeleton exists but is unimplemented
- No `chaos_modifier` table populated
- No `POST /scenarios/{id}/chaos` endpoint

### 7.6 Deployment (Sprint H)
- No Dockerfile or docker-compose service definitions
- No Railway/Procfile config
- No Vercel config
- No architecture diagram or deployment docs

---

## 8. Repository File Map (Current State)

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
│   ├── raw/                             ← immutable source payloads
│   │   ├── jolpica/                     ← raw Jolpica API JSON
│   │   └── openf1/                      ← raw OpenF1 API JSON
│   ├── decision_points/
│   │   └── brazil_2024.yaml             ← 3 scenarios with race_state blocks
│   ├── cache/                            ← FastF1 cache (gitignored)
│   ├── validation_report_*.json          ← validation reports (gitignored)
│   └── undercut.db                       ← DuckDB (gitignored)
│
├── db/
│   ├── migrations/
│   │   ├── 001_core_dimensions.sql       ← 8 dimension tables
│   │   ├── 002_fact_tables.sql           ← 9 fact tables
│   │   ├── 003_race_state.sql            ← 2 race state tables
│   │   ├── 004_feature_store.sql         ← 2 feature store tables
│   │   └── 005_corrections.sql           ← 1 correction table
│   ├── seeds/
│   │   ├── seed_compounds.sql            ← 10 tyre compounds
│   │   └── seed_circuits.sql             ← 10 circuits
│   └── apply_migrations.py
│
├── ingest/
│   ├── __init__.py                       ← SOURCE_PRIORITY config
│   ├── run_pipeline.py                   ← CLI orchestrator (6 commands)
│   ├── base_client.py                    ← ABC with cache-first, jittered retry
│   ├── jolpica_client.py                 ← Jolpica REST client (7 endpoints)
│   ├── openf1_client.py                  ← OpenF1 REST client (9 endpoints)
│   ├── brazil_2024.py                    ← FastF1 loader for pilot race (legacy)
│   ├── load_decision_points.py           ← YAML → DuckDB loader
│   ├── normalize/
│   │   ├── __init__.py                   ← compute_record_hash, load_raw_json
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
│   │   ├── __init__.py
│   │   ├── checks.py                     ← 6 validation checks
│   │   └── reports.py                    ← per-weekend report writer
│   ├── build/
│   │   ├── __init__.py
│   │   ├── build_race_state.py           ← driver_lap + field_lap builders
│   │   └── build_features.py             ← pit_decision + undercut_opportunity
│   └── schema.sql                        ← LEGACY — replaced by db/migrations/
│
├── sim/
│   ├── __init__.py
│   ├── circuit_config.py                 ← 10 circuits with base lap times
│   ├── engine.py                         ← UndercutEngine using circuit config
│   ├── chaos.py                          ← ChaosEngine (skeleton only)
│   ├── pit_model.py                      ← Pit loss heuristics
│   ├── tire_model.py                     ← Degradation curves + cliff detection
│   └── scoring.py                        ← Decision scoring rubric (0-100)
│
├── ml/                                   ← NOT YET BUILT
│
├── api/
│   ├── main.py                           ← FastAPI app with CORS, 3 endpoints
│   ├── models.py                         ← Pydantic request/response schemas
│   └── routers/                          ← (empty, endpoints in main.py)
│
├── web/                                  ← NOT YET BUILT
│
├── docs/
│   ├── api_contract.md                   ← Real payloads, all endpoints
│   ├── PROJECT_PLAN.md
│   ├── sprint_instructions.md
│   ├── advisor_update.md                 ← You are reading this
│   └── superpowers/
│       ├── specs/
│       │   ├── 2026-05-03-sprints-a-b-design.md
│       │   └── 2026-05-03-sprint-c-design.md
│       └── plans/
│           ├── 2026-05-03-sprints-a-b.md
│           └── 2026-05-03-sprint-c.md
│
├── tests/
│   ├── fixtures/
│   │   ├── duckdb/
│   │   │   └── test_schema.sql           ← Complete test schema
│   │   └── raw/
│   │       ├── jolpica/                  ← Jolpica API response fixtures
│   │       └── openf1/                   ← OpenF1 API response fixtures
│   ├── test_engine.py
│   ├── test_scoring.py
│   ├── test_source_priority.py
│   ├── test_base_client.py
│   ├── test_jolpica_client.py
│   ├── test_openf1_client.py
│   ├── test_normalize_dimensions.py
│   ├── test_normalize_results.py
│   ├── test_normalize_laps.py
│   ├── test_normalize_stints.py
│   ├── test_normalize_pit_stops.py
│   ├── test_normalize_weather.py
│   ├── test_normalize_race_control.py
│   ├── test_validation.py
│   ├── test_build_race_state.py
│   ├── test_build_features.py
│   ├── test_cli.py
│   └── test_integration.py
│
└── .worktrees/
    ├── sprints-a-b/                      ← Sprint A+B worktree (done)
    └── sprint-c/                         ← Sprint C worktree (done)
```

---

## 9. Questions for Advisor Feedback

We are at a natural decision point before starting the next sprint. The following questions need your input:

### Q1 — Sprint ordering: D (ML) vs E (Frontend) vs parallel?

The advisor previously recommended parallelizing C and E because the API contract was stable. Now that Sprint C is complete:

- **Sprint D** = Train ML models (pit decision classifier, finish position band). Requires real data in `race_state_driver_lap_fact` to generate training labels.
- **Sprint E** = Build React frontend (scenario play, result display, scenario selector). Works from `docs/api_contract.md` with mocked API responses.
- **Sprint G** = Chaos engine modifiers (rain, SC, tire cliff, slow stop, rival pit).

**Options:**
1. **Parallel D+E** — one agent trains a simple rule-based ML baseline while another builds the frontend. The ML model improves later; the frontend gets a real integration target.
2. **E first, then D** — build the full frontend first (it can work with mocked responses), then train the model against real data once the UI proves the interaction model.
3. **D first, then E** — train the model first so the frontend can show real `model_recommendation` and `model_confidence` from day one.
4. **E + G in parallel, defer D** — build frontend and chaos engine now, leave ML for last (it is the most deferred-able component).

**Our current thinking:** Option 1 (parallel D+E) with a rule-based baseline model (not XGBoost yet) so the frontend shows *something* in the model recommendation badge. The rule-based model uses the same features as the eventual XGBoost model, so upgrading later is a drop-in replacement.

### Q2 — Should we run the pipeline against real data now?

The pipeline is code-complete but has never been run against live APIs. Running it now would:
- Populate `fact_lap`, `fact_stint`, `fact_pit_stop` with real Brazil 2024 data
- Populate `race_state_driver_lap_fact` with ~1,400 rows (70 laps × 20 drivers)
- Validate the end-to-end pipeline works in production
- Provide real training data for Sprint D

But it also risks hitting rate limits, discovering schema mismatches, or finding bugs in the live path that our fixtures didn't catch.

**Question:** Should we run `uv run python -m ingest.run_pipeline fetch-weekend --season 2024 --round 21` now, or wait until after the frontend is built and we can do a full integration test?

### Q3 — Frontend: should we bootstrap the web app now or wait?

The AGENTS.md specifies: Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts.

- The `web/` directory does not exist yet.
- `package.json`, `vite.config.ts`, `tailwind.config.js`, and shadcn/ui initialization are all unstarted.
- The API contract in `docs/api_contract.md` is stable and sufficient for frontend development.

**Question:** Is now the right time to bootstrap the frontend, or should we wait for any reason? Also: should the frontend agent work from a separate git worktree (like `feature/sprint-e`) or directly on `main`?

### Q4 — ML model scope for Sprint D

The spec says: "Preferred model order: rule-based baseline → logistic regression → random forest → XGBoost."

For Sprint D, we have two tasks:
1. **Pit decision** — binary: should this driver pit in the next 1–3 laps?
2. **Finish position band** — multiclass: given current race state, which position band will they finish in?

**Options:**
1. Build both rule-based baselines now (simple if-then rules using stint age, compound, gap, laps remaining)
2. Build one rule-based baseline (pit decision only) and one logistic regression (finish position)
3. Build both as logistic regression models with scikit-learn
4. Skip ML entirely for now and keep `model_recommendation` as a hardcoded heuristic

**Our current thinking:** Option 1 — rule-based baselines for both. They are deterministic, explainable, require no training data volume, and provide a foundation to upgrade later. The `model_confidence` can be derived from how many rules fired.

### Q5 — Should we close out remaining GitHub issues?

We have 30 open issues organized by milestone:
- **Week 3 — Frontend (#55-#68):** 14 issues, all unstarted
- **Week 4 — Chaos + Deploy + Polish (#69-#84):** 16 issues, all unstarted

All 16 closed issues are from Week 1-2 work that is now complete.

**Question:** Should we close the open issues that represent completed backend work (e.g., API endpoints, scoring, schema), or leave them open until the frontend consumes them? Currently none of the open issues describe completed work — they all describe future frontend/chaos/deploy tasks.

---

**PR #86 merged at https://github.com/Taleef7/Undercut/pull/86. All sprints A+B+C complete.**
