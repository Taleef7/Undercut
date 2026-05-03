# Undercut - F1 Strategy Simulator

> "Think you can out-strategize the pit wall?"

Undercut is an unofficial Formula 1 strategy simulation where users can repl historical race scenarios, make pit-wall decisions, and compare their choices against real outcomes, ML recommendations, and simulation-based alternatives.

## Status

This project is in active development. See the [project board](https://github.com/users/Taleef7/projects/5) for progress.

## Project Structure

```
undercut/
├── data/               # Data files (raw, cached, processed)
│   ├── cache/         # FastF1 cache
│   └── decision_points/  # Curated scenarios
├── docs/              # Documentation
├── ingest/            # Data ingestion scripts
├── sim/               # Simulation engine
├── api/               # FastAPI backend
└── web/               # React frontend
```

## Getting Started

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run locally
uv run python -m api.main
```

## Tech Stack

- **Ingestion**: FastF1, DuckDB
- **Backend**: FastAPI, Python 3.11
- **Frontend**: React + TypeScript + Tailwind + shadcn/ui
- **ML**: scikit-learn, XGBoost
- **Deploy**: Vercel (frontend), Railway (backend)

## Disclaimer

This is an unofficial fan project created for educational and portfolio purposes. It is not affiliated with, endorsed by, or in any way officially connected with Formula 1, the FIA, any F1 team, driver, or data provider.

All trademarks belong to their respective owners.

## License

MIT