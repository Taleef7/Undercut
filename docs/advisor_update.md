# Advisor Update: Undercut Strategy Simulator

**Date**: 2026-05-02
**Status**: Backend Foundation Complete (Vertical Slice)
**Project Timeline**: Compressed 4-week schedule (Week 1 of 4)

---

## Executive Summary
Undercut is a race strategy simulation project. We are following a vertical-slice approach, using the 2024 Brazilian Grand Prix as the pilot race. We have successfully established the backend foundation, data pipeline, and simulation core within the first week of the compressed 4-week timeline.

---

## Technical Status
- **Stack**: Python 3.11 (`uv`), DuckDB, FastF1, FastAPI, React/TypeScript (pending).
- **Core Engine**: Functional heuristic-based simulation (pit loss, tire degradation, position impact).
- **Database**: Operational DuckDB schema with core facts, dimensions, and simulation views.
- **API**: Functional FastAPI skeleton connecting data to the simulation engine.

---

## Accomplishments & Completed Issues

### Completed Backend Infrastructure
- **Issue #1**: Project foundation (repo structure, tooling with `uv`, configuration).
- **Issue #2**: Brazil 2024 data preparation (curated decision points in YAML).
- **Issue #3**: Database schema (5-table DuckDB structure).
- **Issue #4**: `race_state_driver_lap` SQL view for streamlined state access.
- **Issue #5**: Decision points data loading.
- **Issue #6**: `UndercutEngine` core implementation (integrating Pit, Tire, and Scoring models).
- **Issue #7**: Scoring rubric implementation.
- **Issue #8**: Data ingestion scripts (YAML -> DuckDB).
- **Issue #9**: FastAPI skeleton implementation.

---

## Roadmap & Planned Work

### Immediate Next Steps (Backend & Frontend)
- **Issue #10**: Develop API endpoint tests and robust error handling.
- **Issue #11**: Frontend bootstrap (Vite/React/Tailwind/shadcn).
- **Issues #12-16**: Build scenario selection, scenario play screen, and results screen.

### Upcoming Challenges (Advisor Focus Areas)
1. **Frontend Complexity**: We need to efficiently map API scenario data to React/shadcn UI components.
2. **Simulation Fidelity**: We need to validate our current heuristic simulation against other races to ensure scalability.
3. **Deployment**: We plan to deploy to Railway (Backend) and Vercel (Frontend). We need guidance on the CI/CD pipeline best practices for this hybrid deployment.
4. **Data Ingestion**: Refining the FastF1 ingestion for full-season capability while managing rate limits.

---

## Current Journal Summary
Our development log (`journal.md`) tracks all granular progress. Key technical milestone this week was the successful integration of the `UndercutEngine` and the flattening of race states using DuckDB views, allowing for immediate simulation of driver decisions based on real-world telemetry data.

---

**Please review the architecture and proposed simulation heuristics. We are prepared to pivot to frontend development next week.**
