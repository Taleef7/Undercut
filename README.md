# Undercut - F1 Strategy Simulator

> "Think you can out-strategize the pit wall?"

Undercut is an **unofficial Formula 1 strategy simulation** where users replay historical race scenarios, make pit-wall decisions, and compare their choices against:
- **Historical outcomes** — what the real team did
- **ML recommendations** — rule-based baseline models with explainable reasoning
- **Simulation projections** — tire degradation, pit loss, and position impact models

## Try It Out

- **Live Demo**: [https://undercut.vercel.app](https://undercut.vercel.app) *(update after deploy)*
- **API Docs**: [https://undercut-api.railway.app/docs](https://undercut-api.railway.app/docs) *(update after deploy)*

## Features

- **3 Curated Scenarios** — Brazil 2024 (VER lap 32, NOR lap 40, VER lap 68)
- **Real Race Data** — 1,137 laps, 54 stints, 35 pit stops from actual telemetry
- **Rule-Based ML** — 5 pit-decision rules + 3 finish-position rules with confidence scores
- **Chaos Engine** — "What if...?" modifiers: Safety Car, rain, tire cliff, slow stops, rival pits
- **Simulation Engine** — Tire degradation curves, pit loss by circuit, scoring rubric
- **Full Data Pipeline** — Jolpica + OpenF1 + FastF1 → DuckDB with 17 tables

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Jolpica   │     │   OpenF1    │     │   FastF1    │
│  (metadata) │     │ (telemetry) │     │  (legacy)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └─────────┬─────────┴─────────┬─────────┘
                 │                   │
           ┌─────▼─────┐       ┌─────▼─────┐
           │   Raw     │       │   Raw     │
           │  (JSON)   │       │  (JSON)   │
           └─────┬─────┘       └─────┬─────┘
                 │                   │
                 └─────────┬─────────┘
                           │
                    ┌──────▼──────┐
                    │  Normalize  │
                    │  (DuckDB)   │
                    │  17 tables  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
         │  Race   │  │ Feature │  │   API   │
         │  State  │  │  Store  │  │ FastAPI │
         └────┬────┘  └────┬────┘  └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │   React     │
                    │  Frontend   │
                    └─────────────┘
```

### Data Pipeline (Sprint C)

```bash
# Seed reference data
uv run python -m ingest.run_pipeline bootstrap --source jolpica --seasons 2024

# Fetch a race weekend
uv run python -m ingest.run_pipeline fetch-weekend --season 2024 --round 21

# Normalize to canonical schema
uv run python -m ingest.run_pipeline normalize --season 2024 --round 21

# Build race state tables
uv run python -m ingest.run_pipeline build-race-state --season 2024 --round 21

# Build feature store
uv run python -m ingest.run_pipeline build-features --season 2024 --round 21

# Validate
uv run python -m ingest.run_pipeline validate --season 2024 --round 21
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Data Sources** | Jolpica API, OpenF1 API, FastF1 |
| **Database** | DuckDB (file-based, 17 tables) |
| **Backend** | FastAPI + Pydantic + uvicorn |
| **Frontend** | React 18 + TypeScript + Vite |
| **Styling** | Tailwind CSS + shadcn/ui |
| **ML** | Rule-based baselines (scikit-learn in v2) |
| **Testing** | pytest (85 tests) |
| **Deploy** | Railway (backend), Vercel (frontend) |

## Project Structure

```
undercut/
├── api/                    # FastAPI backend
│   ├── main.py            # API routes + CORS
│   ├── models.py          # Pydantic schemas
│   └── routers/           # (reserved for future)
├── db/
│   ├── migrations/        # 7 SQL schema files
│   ├── seeds/             # Compounds + circuits
│   └── apply_migrations.py
├── data/
│   ├── raw/               # Immutable API responses
│   ├── decision_points/   # Curated YAML scenarios
│   └── undercut.db        # DuckDB database
├── ingest/
│   ├── base_client.py     # Cache-first HTTP client
│   ├── jolpica_client.py  # Jolpica API wrapper
│   ├── openf1_client.py   # OpenF1 API wrapper
│   ├── normalize/         # 10 normalizers
│   ├── validate/          # Data quality checks
│   ├── build/             # Race state + feature builders
│   └── run_pipeline.py    # CLI orchestrator
├── ml/
│   └── baselines.py       # Rule-based ML models
├── sim/
│   ├── engine.py          # UndercutEngine
│   ├── chaos.py           # ChaosEngine modifiers
│   ├── scoring.py         # Decision scoring rubric
│   ├── tire_model.py      # Degradation curves
│   ├── pit_model.py       # Pit loss heuristics
│   └── circuit_config.py  # Per-circuit constants
├── web/                   # React frontend
│   ├── src/
│   │   ├── api/client.ts  # Typed fetch wrappers
│   │   ├── components/    # Reusable UI
│   │   └── pages/         # Game screens
│   ├── package.json
│   └── vercel.json
└── tests/                 # 85 pytest tests
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/scenarios` | List all scenarios |
| `GET` | `/scenarios/{id}` | Get scenario detail |
| `POST` | `/scenarios/{id}/decision` | Submit decision, get score |
| `POST` | `/scenarios/{id}/chaos` | Submit with chaos modifiers |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- `uv` (Python package manager)

### Backend

```bash
# Install Python dependencies
uv sync

# Set up database
uv run python db/apply_migrations.py
uv run python -c "import duckdb; conn = duckdb.connect('data/undercut.db'); conn.execute(open('db/seeds/seed_compounds.sql').read()); conn.execute(open('db/seeds/seed_circuits.sql').read()); conn.close()"

# Load decision points
uv run python -m ingest.load_decision_points data/decision_points/brazil_2024.yaml

# Run API server
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` and expects the API at `http://localhost:8000`.

### Running Tests

```bash
# Backend tests
uv run pytest tests/ -v

# Frontend build check
cd web && npm run build
```

## Decision Scoring Rubric

| Condition | Score | Grade |
|-----------|-------|-------|
| Matches historical AND simulation confirms optimal | 90-100 | Masterful |
| Matches historical (simulation neutral/confirming) | 75-89 | Strong |
| Different from historical but simulation shows gain | 80-95 | Inspired call |
| Different, simulation shows similar outcome | 55-70 | Risky |
| Different, simulation shows position loss | 30-54 | Poor call |
| Extreme misread of conditions | 0-29 | Off the wall |

## Chaos Modifiers

| Modifier | Effect |
|----------|--------|
| Safety Car | Reduces pit loss by ~18s |
| Virtual Safety Car | Reduces pit loss by ~14s |
| Rain Starts | Forces intermediate tires |
| Tire Cliff Now | +8 laps of tire age |
| Slow Pit Stop | +N seconds to pit loss |
| Rival Pits This Lap | Compresses gap behind |
| Red Flag | Free pit opportunity |

## Data Sources

| Source | Coverage | Use Case |
|--------|----------|----------|
| **Jolpica** | 1950-present | Circuits, drivers, constructors, results |
| **OpenF1** | 2023-present | Laps, stints, pit stops, weather, positions |
| **FastF1** | 2018-present | Gap filling, cross-validation |

## Contributing

This is a personal portfolio project. Issues and PRs are welcome but may be handled on a best-effort basis.

## Disclaimer

This is an unofficial fan project created for educational and portfolio purposes. It is not affiliated with Formula 1, the FIA, any F1 team, driver, or data provider. All trademarks belong to their respective owners. Data is used under the terms of the respective source licenses and is intended for non-commercial personal use only.

## License

MIT
