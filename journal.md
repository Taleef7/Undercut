# Project Journal: Undercut

## 2026-05-03 — Sprint A Completed: Backend Hardening + API Contract

### A1 — Scoring Bug Fix (`sim/scoring.py`)
- Fixed `NameError` where `sim_position` was referenced before assignment when `user_action == historical_action`
- Now always assigns `sim_position = simulated_positions.get(user_action, context.position)` at top before branching
- Realigned scoring logic so matched-historical and sim-based paths both use `sim_position` safely
- 4 scoring tests passing

### A2 — Pydantic Response Models (`api/models.py`)
- `ScenarioSummary`: formatted for card grid (id, title, description, driver, lap, decision_type, actions, difficulty)
- `ScenarioDetail`: extends Summary with `scenario_description`, `explanation_long`, full `RaceState` block
- `SimulationSummary`: expected_position, expected_finish_position_band, risk_score, tire_risk, track_position_risk
- `DecisionResponse`: scenario_id, user_action, score, grade, historical_decision, model_recommendation, simulation_summary, explanation, tradeoffs
- `DecisionRequest`: `action: str` validated via `Field(min_length=1)`

### A3 — API Endpoint Rewrite (`api/main.py`)
- `GET /`: health check
- `GET /scenarios`: returns `list[ScenarioSummary]`, uses `fetchdf().to_dict(orient="records")` (no more `fetchall()` anonymous tuples)
- `GET /scenarios/{id}`: full detail with race_state fields, HTTP 404 for missing
- `POST /scenarios/{id}/decision`: reads `gap_ahead`, `gap_behind`, `stint_age`, `compound`, `position` etc. from DB by column name, validates action against `available_actions_json`, returns `DecisionResponse`, HTTP 422 for invalid actions

### A4 — Decision Point YAML Enrichment (`data/decision_points/brazil_2024.yaml`)
- Added `race_state:` block with current_position, gap_ahead_seconds, gap_behind_seconds, compound, stint_age_laps, laps_remaining, track_temperature_c, air_temperature_c, rainfall, track_status, safety_car_active, virtual_safety_car_active to all 3 scenarios
- Normalized `decision_type`: `final_stint_tire_management` → `extend_to_end`
- Updated `ingest/load_decision_points.py` to insert all race_state columns into DuckDB

### A5 — Per-Circuit Base Lap Times (`sim/circuit_config.py`)
- 10 circuits: interlagos (75500ms), monaco (74000), silverstone (87500), spa (103000), monza (81000), hungaroring (92000), suzuka (91500), yas_marina (83000), las_vegas (94000), albert_park (90000)
- Each with: base_lap_time_ms, pit_loss_seconds, overtaking_difficulty, safety_car_probability_baseline, track_length_km
- `UndercutEngine` now pulls `base_lap_time_ms` from config keyed by circuit, warns on unknown circuit

### A6 — CORS Middleware
- `api/main.py`: `CORSMiddleware` allowing `http://localhost:5173` with all methods/headers

### A7 — API Contract (`docs/api_contract.md`)
- Documented all 3 endpoints with real Brazil 2024 example payloads, error examples (404/422), field descriptions

### Bug Fixes During Sprint A
- **tire_model.py**: `get_degradation_multiplier` returned raw degradation (0.01) instead of `1.0 + degradation` when stint age exceeded curve length. Fixed: `return 1.0 + deg_curve[-1]`
- **engine.py**: Moved lazy import of `is_in_tire_cliff_zone` to module level
- **engine.py**: `decision.action == "pit_now"` changed to `decision.action.startswith("pit_")` to match all variant actions (`pit_now_inter`, `pit_now_hard`, `pit_now_wet`, etc.)
- **scoring.py**: Same `pit_` prefix fix applied

---

## 2026-05-03 — Sprint B Completed: Schema Expansion

### B1 — Full Dimension Tables
Migration `001_core_dimensions.sql`:
- `dim_season` (year, regulations_era_label)
- `dim_meeting` (season_id, round_number, meeting_name, circuit_id, dates)
- `dim_circuit` (circuit_ref, name, location, lat/lon, altitude, track_length_km, typical_pit_loss, overtaking_difficulty, safety_car_probability)
- `dim_session` (meeting_id, session_name, session_type, date, source keys)
- `dim_constructor` (constructor_ref, name, nationality)
- `dim_tyre_compound` (compound_label, category, code, hardness_order, wet/inter/slick flags)
- `dim_driver` (driver_ref, number, code, name, nationality, dob)
- `dim_track_status_code` (status_code, description, race_suspension_flag)
All tables include `source_system`, `ingested_at`, `data_version`, `record_hash` metadata columns

### B2 — Full Fact Tables
Migration `002_fact_tables.sql`:
- `fact_lap` (session_id, driver_id, lap_number, lap_time_ms, compound, sector times, speed traps)
- `fact_stint` (driver_id, session_id, stint_number, lap_start, lap_end, compound, fresh_compound_flag, stint_length_km)
- `fact_pit_stop` (driver_id, session_id, lap_number, pit_stop_number, pit_duration_seconds, estimated_pit_loss_flag)
- `fact_session_result` (position_order, classified_position, points, status, laps_completed, fastest_lap_rank)
- `fact_driver_session_entry` (constructor mapping per session, replacement_driver flag)
- `fact_weather_sample` (air_temp, track_temp, humidity, pressure, rainfall, wind_speed, lap_number)
- `fact_race_control_event` (category, message, flag, scope, normalized_event_type)
- `fact_interval_sample` (gap_to_leader, interval_to_ahead)
- `fact_position_sample` (position per lap, used for driver_ahead/behind derivation)

### B3 — Race State Tables
Migration `003_race_state.sql`:
- `race_state_driver_lap_fact`: 33 columns including current_position, starting_position, gaps, compound_labels, stint_number, stint_age, pit stops count, rolling lap averages, pace_delta, track status flags, pit_window_open_flag, undercut_threat_flag, overcut_opportunity_flag
- `race_state_field_lap`: 18 columns covering leader, running/retired counts, safety car/vsc/red flag flags, average/median/fastest lap times, compound counts, field_spread

### B4 — Feature Store Tables
Migration `004_feature_store.sql`:
- `feature_pit_decision`: features (laps_remaining, position, gaps, stint_age, compound hardness, rolling pace, pace delta, safety_car/vsc/rain flags, track temp, pit loss estimate) + label `actual_pitted_within_3_laps`
- `feature_undercut_opportunity`: driver-to-target driver features (gap, stint ages, compounds, pit loss, overtaking difficulty) + label `undercut_succeeded`

### B5 — Data Corrections Table
Migration `005_corrections.sql`:
- `manual_data_correction`: target_table, target_record_key, field_name, old_value, new_value, correction_reason, source_reference

### B6 — Migrations Structure + Apply Script
- `db/migrations/001_core_dimensions.sql` through `005_corrections.sql`
- `db/seeds/seed_compounds.sql`: 10 compounds (SOFT, MEDIUM, HARD, INTERMEDIATE, WET, C1-C5)
- `db/seeds/seed_circuits.sql`: 10 circuits (interlagos, monaco, silverstone, spa, monza, hungaroring, suzuka, yas_marina, las_vegas, albert_park)
- `db/apply_migrations.py`: reads and executes all migration files in numeric order against DuckDB

---

## Current DB State
- **17 tables** across all schema layers
- **3 decision points** loaded for Brazil 2024 (lap 32, lap 43, lap 69)
- **10 tyre compounds** seeded
- **10 circuits** seeded
- All tables include proper metadata columns (source_system, ingested_at, data_version, record_hash)

## Current Test State
- **5/5 tests passing**: 1 engine test (circuit base lap time), 4 scoring tests
- Test files: `tests/test_engine.py`, `tests/test_scoring.py`

## API Verification
- `GET /scenarios` → returns 3 scenarios
- `GET /scenarios/brazil_2024_lap32` → returns full detail with race_state (P2, medium, stint 14, gap ahead 1.2s)
- `POST /scenarios/brazil_2024_lap32/decision` with `{"action": "stay_out"}` → score 75, grade "Strong call"
- `POST /scenarios/brazil_2024_lap32/decision` with `{"action": "pit_now_inter"}` → position change detected
- 404 for unknown scenario IDs
- 422 for invalid actions

## Commits Pushed
- `fix: match all pit_ prefixed actions, not just pit_now`
- `feat: implement Sprints A+B - backend hardening and schema expansion`
- `fix: align scoring labels and types`
- `fix: stabilize scoring test env`
- `fix: avoid scoring NameError`
- `chore: ignore worktrees`
- PR #85 created, reviewed, and merged

## Documentation Created/Updated
- `AGENTS.md` — comprehensive agent guide
- `docs/PROJECT_PLAN.md` — long-term vision
- `docs/advisor_update.md` — advisor-facing status
- `docs/sprint_instructions.md` — all sprints A-H detailed
- `docs/api_contract.md` — typed contract with real examples
- `docs/superpowers/specs/2026-05-03-sprints-a-b-design.md` — design spec
- `docs/superpowers/plans/2026-05-03-sprints-a-b.md` — implementation plan
- `journal.md` — this file

## Known Issues & Limitations
- ML layer is placeholder only (model_recommendation returns "stay_out", model_confidence returns 0.0)
- `model_top_features` returns empty array in API responses
- No real feature store data populated yet
- Simulation engine is heuristic-based, not data-driven
- Only 3 curated scenarios (all Brazil 2024)
- Frontend not yet started
- No deployment config (Railway/Vercel)
- `data/undercut.db` on main branch does not contain B1-B6 migrations (still in worktree DB)

---

## Next Sprint: C — Data Ingestion Expansion
- C1: Jolpica REST client (`ingest/jolpica_client.py`)
- C2: OpenF1 REST client (`ingest/openf1_client.py`)
- C3: Normalization modules (10 files in `ingest/normalize/`)
- C4: Race state builder (`ingest/build/build_race_state.py`)
- C5: Feature store builder (`ingest/build/build_features.py`)
- C6: CLI orchestration (`ingest/run_pipeline.py`)
