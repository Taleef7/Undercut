# Project Journal: Undercut

## [YYYY-MM-DD] - Project Foundation
- Initialized repository structure.
- Configured `uv` for Python 3.11 environment.
- Implemented core schema for DuckDB in `ingest/schema.sql`.
- Added initial simulation heuristics in `sim/`.
- Curated Brazil 2024 decision points for vertical slice.
- Created `AGENTS.md` for agent ramp-up.
- Closed Issues #1, #2, #3, #5.

## [2024-05-23] - Data State & Views
- Implemented `race_state_driver_lap` view in `ingest/schema.sql`.
- Added rolling 3-lap average pace to provide a smoothed state for the simulation engine.
- Closed Issue #4.

## [2024-05-23] - Simulation Engine Core
- Implemented `UndercutEngine` in `sim/engine.py`.
- Integrated `pit_model`, `tire_model`, and `scoring` into a single simulation pipeline.
- Added basic risk scoring and position estimation logic.
- Closed Issue #6.

## [2024-05-23] - API & Architecture
- Created `docs/architecture.md` outlining system components.
- Implemented API skeleton in `api/main.py` using FastAPI.
- Connected API to DuckDB for scenarios and `UndercutEngine` for simulations.
- Closed Issues #7 and #9.
