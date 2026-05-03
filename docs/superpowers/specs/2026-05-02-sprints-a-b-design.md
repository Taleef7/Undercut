# Undercut — Sprints A+B Design (Backend Hardening + Schema Expansion)

## Overview
This design defines the Sprint A and Sprint B work for Undercut. The goal is to harden the backend API and simulation contracts, enrich decision-point data, and expand the DuckDB schema to the canonical structure described in AGENTS.md. The dev database will be regenerated after migrations and reloaded with updated decision points. The `/scenarios/{id}/simulate` endpoint will be removed and replaced by `/scenarios/{id}/decision`.

## Scope

### Sprint A — Backend Hardening + API Contract
- Fix scoring bug by always assigning `sim_position` before branching.
- Add `sim/circuit_config.py` and use per-circuit `base_lap_time_ms` in the simulation engine.
- Add Pydantic response models in `api/models.py` aligned to AGENTS.md contract.
- Rewrite API endpoints to use `fetchdf()` and column-name access; remove hardcoded values.
- Enrich decision-point YAML with structured `race_state` values (exact values via FastF1 Brazil 2024 ingest).
- Add CORS middleware for frontend access.
- Write `docs/api_contract.md` with real example payloads based on updated Brazil 2024 scenarios.
- Remove `/scenarios/{id}/simulate` endpoint and replace with `/scenarios/{id}/decision`.

### Sprint B — Schema Expansion
- Introduce `db/migrations/` with five additive migration files per AGENTS.md.
- Add `db/seeds/seed_compounds.sql` and `db/seeds/seed_circuits.sql`.
- Add `db/apply_migrations.py` to apply migrations in numeric order.
- Regenerate `data/undercut.db`, then reload decision points.
- Treat `ingest/schema.sql` as legacy and stop using it for schema creation.

## Architecture & Data Flow

1. Run migrations to create canonical schema in DuckDB.
2. Run seeds for compounds and circuits.
3. FastF1 ingest for Brazil 2024 to compute exact decision-point race_state values.
4. Update decision-point YAML with race_state values and normalized decision types.
5. Load YAML into `race_state_decision_point` table using updated loader.
6. API reads scenarios via `fetchdf()` and column-name access, builds `ScenarioContext`, runs simulation and scoring, returns Pydantic responses.
7. API contract doc reflects real updated payloads and sample outputs.

## Data Model Changes

### race_state_decision_point (expanded)
- Add explicit race_state fields:
  - `current_position`, `gap_ahead_seconds`, `gap_behind_seconds`
  - `compound`, `stint_age_laps`, `laps_remaining`
  - `track_temperature_c`, `air_temperature_c`, `rainfall`
  - `track_status`, `safety_car_active`, `virtual_safety_car_active`

### Canonical schema
- Add dimensions (`dim_season`, `dim_meeting`, `dim_circuit`, `dim_session`, `dim_constructor`, `dim_tyre_compound`).
- Add facts (`fact_driver_session_entry`, `fact_session_result`, `fact_weather_sample`, `fact_race_control_event`, `fact_interval_sample`).
- Add race_state tables (`race_state_driver_lap_fact`, `race_state_field_lap`).
- Add feature store tables (`feature_pit_decision`, `feature_undercut_opportunity`).
- Add corrections table (`manual_data_correction`).

## API Contract

### Pydantic models (api/models.py)
- `ScenarioSummary`, `ScenarioDetail`, `SimulationSummary`, `DecisionResponse`.
- Response shape matches AGENTS.md contract including `model_confidence`, `model_top_features`, `expected_finish_position_band`, `tire_risk`, `track_position_risk`. These may be `null` placeholders until Sprint F.

### Endpoints
- `GET /scenarios` → list of `ScenarioSummary`.
- `GET /scenarios/{id}` → `ScenarioDetail` (includes `explanation_long` and race_state fields).
- `POST /scenarios/{id}/decision` → `DecisionResponse`.
- `GET /` remains health check; add CORS middleware.
- Remove `/scenarios/{id}/simulate`.

## Error Handling
- `404` for missing scenarios.
- `422` for invalid action values (validate against `available_actions_json`).

## Testing & Verification
- Run `uv run python db/apply_migrations.py` after creating migrations.
- Reload decision points with `uv run python -m ingest.load_decision_points data/decision_points/brazil_2024.yaml`.
- Manually verify `/scenarios` and `/scenarios/{id}` outputs match contract.

## Open Decisions
- None. All clarifications resolved: regenerate dev DB, replace simulate endpoint, FastF1 ingest for race_state values, normalize decision_type, and match API contract now with placeholders.
