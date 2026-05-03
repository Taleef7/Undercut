# Undercut Architecture

Undercut is a race strategy simulator for F1, focusing on historical data analysis and heuristic-based simulation for decision making.

## Core Components

### 1. Data Pipeline (`ingest/`)
- Extracts data from **FastF1 API**.
- Loads raw data into **DuckDB** using `schema.sql`.
- Ingests curated decision points from YAML files.

### 2. Simulation Engine (`sim/`)
- **Pit Model**: Heuristics for time loss per circuit.
- **Tire Model**: Degradation curves and cliff detection.
- **Scoring**: Rubric-based evaluation of user decisions vs historical outcomes.
- **Engine**: Orchestrates models to generate expected position/time deltas.

### 3. API (`api/`)
- **FastAPI** backend exposing endpoints for:
  - Fetching scenarios.
  - Simulating decisions.
  - Retrieving historical context.

### 4. Storage (`data/`)
- **DuckDB**: Operational database for race state, laps, and telemetry.
- **YAML**: Curated decision point definitions (scenarios).
