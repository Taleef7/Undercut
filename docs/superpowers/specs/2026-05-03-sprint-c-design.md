# Sprint C — Data Ingestion Expansion Design Spec

**Date:** 2026-05-03
**Status:** Approved
**Related:** Sprint instructions C1-C6, AGENTS.md §4-5

---

## 1. Goal

Build a full raw → canonical → race_state → feature_store ingestion pipeline capable of loading any F1 weekend from 2021 onward. Use Jolpica for historical metadata and pre-2023 race data, OpenF1 for rich 2023+ session data. The pipeline must demonstrate data engineering rigor: provenance, validation, immutable raw storage, source deduplication, and layered derived tables.

---

## 2. Architecture

```
CLI (run_pipeline.py)
    │
    ├── JolpicaClient / OpenF1Client
    │       │  httpx, cache-first, exponential backoff
    │       ▼
    │   data/raw/ (immutable JSON, partitioned by year/session)
    │
    ├── normalize/*.py (10 files)
    │       │  raw JSON → validate → DataFrame → DuckDB INSERT OR REPLACE
    │       ▼
    │   DuckDB canonical (dim_* + fact_*)
    │
    ├── build/build_race_state.py
    │       │  fact tables → derived columns → DataFrame bulk insert
    │       ▼
    │   DuckDB race_state (race_state_driver_lap_fact, race_state_field_lap)
    │
    └── build/build_features.py
            │  race_state → computed features + labels → DataFrame bulk insert
            ▼
        DuckDB feature_store (feature_pit_decision, feature_undercut_opportunity)
```

Each layer is independently testable with JSON fixtures. No step crashes the pipeline — failures produce logged warnings and skip bad rows.

---

## 3. File Structure (New Files)

```
ingest/
├── jolpica_client.py              ← ABC BaseClient → JolpicaClient
├── openf1_client.py               ← ABC BaseClient → OpenF1Client
├── normalize/
│   ├── __init__.py
│   ├── normalize_circuits.py       ← Jolpica circuits → dim_circuit
│   ├── normalize_drivers.py        ← Jolpica drivers → dim_driver
│   ├── normalize_constructors.py   ← Jolpica constructors → dim_constructor
│   ├── normalize_sessions.py       ← Jolpica schedule + OpenF1 → dim_season, dim_meeting, dim_session
│   ├── normalize_laps.py           ← OpenF1/FastF1 laps → fact_lap
│   ├── normalize_stints.py         ← OpenF1 stints → fact_stint
│   ├── normalize_pit_stops.py      ← OpenF1 pit → fact_pit_stop
│   ├── normalize_results.py        ← Jolpica results → fact_session_result
│   ├── normalize_weather.py        ← OpenF1 weather → fact_weather_sample
│   └── normalize_race_control.py   ← OpenF1 race_control → fact_race_control_event
├── validate/
│   ├── __init__.py
│   ├── checks.py                   ← validation rule functions
│   └── reports.py                  ← writes validation_report_{season}_{round}_{timestamp}.json
├── build/
│   ├── __init__.py
│   ├── build_race_state.py         ← fact tables → race_state
│   └── build_features.py           ← race_state → feature store
└── run_pipeline.py                 ← CLI orchestrator (argparse)
```

---

## 4. BaseClient (Abstract Base)

### 4.1 Class Definition

```python
from abc import ABC, abstractmethod
from pathlib import Path
import httpx

class BaseClient(ABC):
    BASE_URL: str          # set by subclass
    RAW_DIR: Path          # set by subclass
    SOURCE_SYSTEM: str     # 'jolpica' | 'openf1'

    def __init__(self, data_dir: Path | None = None):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={"User-Agent": "Undercut/0.1 (portfolio project; contact@example.com)"},
            timeout=30.0
        )
        self.raw_dir = data_dir / "raw" / self.SOURCE_SYSTEM if data_dir else self.RAW_DIR

    def _get(self, subpath: str, params: dict | None = None,
             filename: str | None = None) -> dict | None:
        """GET with cache-first, retry with exponential backoff + jitter."""
```

### 4.2 Cache-First Logic

```python
# Construct cache filename from subpath + params
cache_path = self._cache_path(subpath, params)

# If file exists and --force not set, return cached
if cache_path.exists():
    return json.loads(cache_path.read_text())

# HTTP GET with retry: 1s, 2s, 4s, 8s, 16s (max 3 retries)
# Add jitter: actual_wait = base_wait * (0.5 + random.random())
# On 4xx: log warning, return None
# On 5xx: retry, then log + return None

# Save raw JSON
cache_path.parent.mkdir(parents=True, exist_ok=True)
cache_path.write_text(json.dumps(data, indent=2))

return data
```

### 4.3 Cache Path Derivation

The cache filename MUST include query params to avoid collisions. Use a structured subdirectory approach:

```python
def _cache_path(self, subpath: str, params: dict | None) -> Path:
    """Derive cache file path from subpath + params."""
    base = self.raw_dir / subpath.strip("/")
    if params:
        # Convert params to safe filename: laps_session_key_9540.json
        param_suffix = "_".join(f"{k}_{v}" for k, v in sorted(params.items()))
        return base.parent / f"{base.name}_{param_suffix}.json"
    return base.with_suffix(".json")
```

This ensures `GET /laps?session_key=9540` and `GET /laps?session_key=9541` produce distinct cache files.

---

## 5. JolpicaClient

### 5.1 Configuration

```python
class JolpicaClient(BaseClient):
    BASE_URL = "https://api.jolpi.ca/ergast/f1"
    SOURCE_SYSTEM = "jolpica"
```

### 5.2 Methods — Round-Specific (fetch_raw)

Call once per weekend:

```python
def fetch_raw(self, season: int, round: int) -> dict[str, Path]:
    """Fetch all round-specific Jolpica endpoints, save raw, return path map."""
    return {
        "results":     self._get(f"{season}/{round}/results.json"),
        "qualifying":  self._get(f"{season}/{round}/qualifying.json"),
        "pit_stops":   self._get(f"{season}/{round}/pitstops.json"),
        "lap_times":   self._get_all_paginated(f"{season}/{round}/laps.json"),
    }
```

Raw storage: `data/raw/jolpica/{season}/{round}/{endpoint}.json`

### 5.3 Methods — Season-Scoped (fetch_raw_bootstrap)

Call once per season during bootstrap:

```python
def fetch_raw_bootstrap(self, season: int) -> dict[str, Path]:
    """Fetch season-scoped reference data."""
    return {
        "drivers":       self._get(f"{season}/drivers.json"),
        "constructors":  self._get(f"{season}/constructors.json"),
    }
```

Raw storage: `data/raw/jolpica/{season}/season/{endpoint}.json`

### 5.4 Methods — All-Time (fetch_raw_all_time)

Call once, ever:

```python
def fetch_raw_all_time(self) -> dict[str, Path]:
    """Fetch global reference data (circuits)."""
    return {"circuits": self._get("circuits.json", params={"limit": 100})}
```

Raw storage: `data/raw/jolpica/all_time/{endpoint}.json`

### 5.5 Pagination

Jolpica returns pages of 30 items. For `lap_times` (71 laps × 20 drivers = 1,420 results), implement:

```python
def _get_all_paginated(self, subpath: str, params: dict | None = None) -> list[dict]:
    """Fetch all pages, respect rate limit, return concatenated data."""
```

Rate limit: `time.sleep(1.0)` between requests.

---

## 6. OpenF1Client

### 6.1 Configuration

```python
class OpenF1Client(BaseClient):
    BASE_URL = "https://api.openf1.org/v1"
    SOURCE_SYSTEM = "openf1"
```

### 6.2 Methods

```python
def fetch_session(self, session_key: int) -> dict[str, Path]:
    """Fetch all endpoints for a session, save raw, return path map."""
    endpoints = {
        "laps":          f"sessions/{session_key}/laps",
        "stints":        f"sessions/{session_key}/stints",
        "pit":           f"sessions/{session_key}/pit",
        "intervals":     f"sessions/{session_key}/intervals",
        "positions":     f"sessions/{session_key}/position",
        "weather":       f"sessions/{session_key}/weather",
        "race_control":  f"sessions/{session_key}/race_control",
        "session_result": f"sessions/{session_key}/session_result",
        "starting_grid": f"sessions/{session_key}/starting_grid",
    }
    # Each returns data/raw/openf1/{meeting_key}/{session_key}/{endpoint}.json
```

Meeting lookup first:

```python
def get_meetings(self, year: int) -> list[dict]:
    """Return all meetings for a year. Used to find meeting_key for a given round."""
```

```python
def get_sessions(self, meeting_key: int) -> list[dict]:
    """Return all sessions for a meeting. Used to find session_key for Race/Qualifying."""
```

### 6.3 Raw Storage

```
data/raw/openf1/{year}/{meeting_key}/{session_key}/{endpoint}.json
```

Where `meeting_key` is OpenF1's internal meeting ID (e.g., 47 for Brazil 2024) and `session_key` is the session ID (e.g., 9540 for Brazil 2024 Race).

---

## 7. Normalization Layer

### 7.1 Normalizer Pattern (Every File)

Every normalizer follows the same interface:

```python
def normalize(session_id: str, db_path: Path, data_dir: Path) -> int:
    """
    Load raw JSON from data_dir, validate, insert into DuckDB.
    Returns: row count inserted.
    
    Steps:
    1. Load raw JSON from data/raw/
    2. Flatten nested structures into flat rows
    3. Build DataFrame with canonical column names
    4. Add metadata: source_system, ingested_at, data_version, record_hash
    5. Run validate.checks.validate_rows(df, table_name)
    6. Filter out bad rows (log to validation report)
    7. conn.execute("INSERT OR REPLACE INTO {table} SELECT * FROM df")
    """
```

### 7.2 Record Hash

Every row gets `record_hash = SHA256(source_system + source_record_id + colon-separated key field values)`. Implement as a shared utility:

```python
# ingest/normalize/__init__.py
import hashlib

def compute_record_hash(source_system: str, record_id: str, key_fields: str) -> str:
    payload = f"{source_system}:{record_id}:{key_fields}"
    return hashlib.sha256(payload.encode()).hexdigest()
```

### 7.3 Compound FK Validation

When normalizing laps and stints, verify each compound label exists in `dim_tyre_compound`. If a compound is unknown:

1. Log a validation warning with the raw label
2. Map to the "UNKNOWN" compound ID in dim_tyre_compound
3. Continue — do not fail the row

The "UNKNOWN" compound must be present in `db/seeds/seed_compounds.sql`. If it does not already exist, add it: `('UNKNOWN', 'UNKNOWN', 'slick', 'UNC', NULL, FALSE, FALSE, TRUE)`.

### 7.4 Normalize Order (Enforced)

The normalizer registration must respect FK dependencies:

```
1. normalize_circuits       (Jolpica all-time)    → dim_circuit
2. normalize_drivers        (Jolpica season)       → dim_driver
3. normalize_constructors   (Jolpica season)       → dim_constructor
4. normalize_sessions       (Jolpica schedule)     → dim_season, dim_meeting, dim_session
5. normalize_laps           (OpenF1)               → fact_lap
6. normalize_stints         (OpenF1)               → fact_stint
7. normalize_pit_stops      (OpenF1/Jolpica)       → fact_pit_stop
8. normalize_results        (Jolpica)              → fact_session_result
9. normalize_weather        (OpenF1)               → fact_weather_sample
10. normalize_race_control   (OpenF1)               → fact_race_control_event
```

### 7.5 Session Filtering

By default, normalize only Race (`R`) sessions. When `--session Q` is passed, only qualifying-relevant normalizers run (laps, results, weather) — skip stints and pit_stops which don't apply to qualifying.

---

## 8. Validation Layer

### 8.1 checks.py Functions

```python
def validate_rows(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, list[str]]:
    """Run all validation rules for table. Returns (valid_rows, warnings)."""

def check_not_null(df: pd.DataFrame, columns: list[str]) -> list[str]: ...

def check_unique(df: pd.DataFrame, columns: list[str]) -> list[str]: ...

def check_fk_exists(df: pd.DataFrame, col: str, fk_table: str, fk_col: str,
                    db_path: Path) -> list[str]: ...

def check_lap_range(df: pd.DataFrame, total_laps: int = 71) -> list[str]:
    """Flag laps outside [1, total_laps]. total_laps read from dim_session."""

def check_no_duplicate_compound_stint(df: pd.DataFrame) -> list[str]:
    """Flag rows where same driver/session has overlapping stint lap ranges."""

def check_record_hash_not_null(df: pd.DataFrame) -> list[str]: ...
```

### 8.2 reports.py

```python
def write_report(warnings: list[str], errors: list[str], season: int,
                 round: int, session_type: str) -> Path:
    """
    Write validation_report_{season}_{round}_{timestamp}.json to data/.
    Returns report path.
    """
    report = {
        "season": season,
        "round": round,
        "session_type": session_type,
        "timestamp": datetime.now().isoformat(),
        "warnings": warnings,
        "errors": errors,
        "warning_count": len(warnings),
        "error_count": len(errors),
    }
    filename = f"validation_report_{season}_{round}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = DATA_DIR / filename
    path.write_text(json.dumps(report, indent=2))
    return path
```

### 8.3 Validation Rules (Minimum Set)

| Check | Tables | Rule |
|-------|--------|------|
| FK drivers | All fact tables | driver_id exists in dim_driver |
| FK circuits | dim_meeting | circuit_id exists in dim_circuit |
| FK compounds | fact_lap, fact_stint | tyre_compound_id exists in dim_tyre_compound |
| Unique laps | fact_lap | No duplicate (session_id, driver_id, lap_number) |
| Lap range | fact_lap | lap_number between 1 and total_laps (from dim_session) |
| Stint overlap | fact_stint | No overlapping lap ranges for same driver/session |
| Pit stop laps | fact_pit_stop | lap_number exists in fact_lap |
| Non-null hash | All canonical | record_hash is not null |
| Position unique | fact_session_result | classified_position unique (allow ties for DNF) |

---

## 9. Build Layer

### 9.1 build_race_state.py

**Prerequisites:** fact_lap, fact_stint, fact_pit_stop, fact_interval_sample, fact_weather_sample, fact_race_control_event, fact_position_sample, dim_session, dim_driver.

```python
def check_prerequisites(session_id: str, db_path: Path) -> list[str]:
    """
    Verify prerequisite tables have data. Returns list of warning messages.
    Raises ValueError only for hard prerequisites.

    Hard prerequisites (build cannot proceed without these):
        fact_lap, fact_stint, fact_pit_stop
    Soft prerequisites (log warning if missing, use NULL/defaults):
        fact_interval_sample, fact_position_sample, fact_weather_sample,
        fact_race_control_event
    """
    warnings = []
    hard = ["fact_lap", "fact_stint", "fact_pit_stop"]
    soft = ["fact_interval_sample", "fact_position_sample",
            "fact_weather_sample", "fact_race_control_event"]

    for table in hard:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
            [session_id]
        ).fetchone()[0]
        if count == 0:
            raise ValueError(
                f"No {table} rows for session {session_id}. Run 'normalize' first."
            )

    for table in soft:
        count = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
            [session_id]
        ).fetchone()[0]
        if count == 0:
            msg = f"WARNING: No {table} rows for session {session_id}. Derived columns depending on this table will be NULL."
            warnings.append(msg)

    return warnings

def build_race_state_driver_lap(session_id: str, db_path: Path) -> int:
    """
    Build race_state_driver_lap_fact rows for a session.
    
    Derived columns:
    - stint_age_laps: lap_number - fact_stint.lap_start
    - laps_remaining: total_laps - lap_number
    - is_pit_lap: TRUE if lap_number is within 1 lap of a fact_pit_stop (pit in/out laps have abnormally slow times)
    - interval_behind_seconds: from fact_interval_sample (nearest lap)
    - driver_ahead_id, driver_behind_id: from fact_position_sample
    - safety_car_active_flag: from fact_race_control_event spanning that lap
    - rolling_3_lap_avg_ms: avg of lap_time_ms for laps N-2, N-1, N (excluding pit laps)
    - rolling_5_lap_avg_ms: avg of lap_time_ms for laps N-4..N (excluding pit laps)
    - pace_delta_to_field_ms: driver's rolling_3_lap_avg_ms - field median rolling_3_lap_avg_ms
        where "field median" = median of all non-pit-lap drivers' rolling_3_lap_avg_ms
        at the same lap number (is_pit_lap = FALSE rows only)
    - undercut_threat_flag: interval_behind < 2.0 AND rival stint_age > own stint_age + 5
    - pit_window_open_flag: stint_age > compound_optimal_window
    - track_status_normalized: derived from race_control events
    - rainfall_flag: from fact_weather_sample (nearest lap)
    
    Uses DataFrame construction + conn.execute("INSERT INTO ... SELECT * FROM df").
    Single SQL transaction per session.
    """
```

**Target:** 1,400 rows per race session (20 drivers × 70 laps).
**Insert pattern:** Build full DataFrame, then bulk insert via DuckDB's DataFrame registration — never row-by-row.

```python
def build_race_state_field_lap(session_id: str, db_path: Path) -> int:
    """
    Build race_state_field_lap rows.
    
    Derived columns:
    - leader_driver_id: driver with position 1 at lap N
    - total_running_drivers: COUNT(*) WHERE laps_completed >= lap_number
    - number_on_soft/medium/hard/intermediate/wet: COUNT per compound at lap N
    - field_spread_seconds: MAX(gap_to_leader) - MIN(gap_to_leader)
    - average_lap_time_ms, median_lap_time_ms, fastest_lap_time_ms
    """
```

### 9.2 build_features.py

**Prerequisites:** race_state_driver_lap_fact, fact_pit_stop, dim_circuit.

```python
def check_prerequisites(session_id: str, db_path: Path) -> None:
    """Raise ValueError if race_state_driver_lap_fact is empty."""

def build_feature_pit_decision(session_id: str, db_path: Path) -> int:
    """
    Build feature_pit_decision rows from race_state_driver_lap_fact.
    
    Label computation: actual_pitted_within_3_laps
    - For each row (session, driver, lap):
      - Check if there's a fact_pit_stop with lap_number in [lap, lap+3]
      - If yes: TRUE, else FALSE
    
    Features copied from race_state: laps_remaining, current_position, gaps,
    stint_age, compound_hardness, rolling pace, pace_delta, SC/VSC/rain flags,
    track_temp, pit_loss_estimate (from dim_circuit).
    """

def build_feature_undercut_opportunity(session_id: str, db_path: Path) -> int:
    """
    Build feature_undercut_opportunity rows.
    
    For each driver at each lap, identify the driver immediately behind.
    Compute: gap_to_target, both stint ages, both compounds, pit_loss_estimate,
    circuit overtaking_difficulty.
    
    Label: undercut_succeeded — did this driver pit and come out ahead of target?
    """
```

---

## 10. DuckDB DataFrame Insert Pattern

To avoid row-by-row inserts, all normalizers and builders use DuckDB's Python DataFrame integration:

```python
conn.execute("INSERT OR REPLACE INTO table_name SELECT * FROM df")
```

DuckDB natively recognizes pandas DataFrames in SQL queries. For INSERT OR REPLACE to work correctly, the primary key must be defined in the schema and the DataFrame must include it. The normalizer guarantees the primary key column is populated before insert.

For large tables (fact_lap: 1,400+ rows), this is the only acceptable insert pattern. The builder scripts construct the full DataFrame programmatically and insert in one statement. No `executemany()`, no row-by-row loops.

---

## 11. Source Deduplication

When multiple sources cover the same data (e.g., OpenF1 and Jolpica both have lap times), insert both rows with their `source_system` preserved. At query time, use:

```sql
SELECT * FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY session_id, driver_id, lap_number
            ORDER BY
                CASE source_system
                    WHEN 'openf1' THEN 1
                    WHEN 'fastf1'  THEN 2
                    WHEN 'jolpica' THEN 3
                END ASC
        ) AS rn
    FROM fact_lap
) WHERE rn = 1
```

The `source_priority` mapping lives in a small config dict in `ingest/__init__.py`:

```python
SOURCE_PRIORITY = {"openf1": 1, "fastf1": 2, "jolpica": 3}
```

This applies to all fact tables that may have overlapping coverage.

---

## 12. CLI (run_pipeline.py)

### 11.1 Commands

```
bootstrap     Fetch + normalize reference data from Jolpica
  --source jolpica
  --seasons 2022 2023 2024
  → fetch_raw_all_time() once (circuits)
  → fetch_raw_bootstrap(season) per season (drivers, constructors)
  → normalize circuits, drivers, constructors
  → normalize seasons, meetings, sessions from Jolpica schedule

fetch-weekend Fetch round-specific data from both sources
  --season 2024
  --round 21
  [--force]           Delete existing raw files before fetch
  → JolpicaClient.fetch_raw(season, round)
  → OpenF1Client: get_meetings → get_sessions → fetch_session(session_key)
  → Saves all raw JSON to data/raw/

normalize     Transform raw JSON into canonical DuckDB tables
  --season 2024
  --round 21
  [--session R|Q]     Default: R. Q skips stints + pit_stops
  → Runs normalizers in dependency order
  → Runs validation after each normalizer

build-race-state  Construct derived race state tables
  --season 2024
  --round 21
  → check_prerequisites() → build both race_state tables

build-features    Construct feature store tables
  --season 2024
  --round 21
  → check_prerequisites() → build both feature tables

validate    Run validation checks only, write report
  --season 2024
  --round 21
  [--session R|Q]     Default: R
  → Runs all checks, writes report, prints summary
```

### 11.2 Dependency Enforcement

`normalize` checks that raw files exist for the given season/round.
`build-race-state` checks that fact_lap has rows for the session.
`build-features` checks that race_state_driver_lap_fact has rows for the session.

Each provides a clear error message: `"No fact_lap rows for season=2024, round=21. Run 'normalize' first."`

---

## 13. Error Handling Matrix

| Layer | Error | Behavior |
|-------|-------|----------|
| BaseClient._get() | Network timeout | Retry 3× with jitter (1s, 2s, 4s, 8s, 16s) |
| BaseClient._get() | HTTP 4xx | Log warning, return None |
| BaseClient._get() | HTTP 5xx | Retry 3×, then log + return None |
| Normalizer.load() | Missing raw file | Log "no data for session X", skip, return 0 |
| Normalizer.load() | Malformed JSON | Log "corrupt raw file: {path}", skip |
| Normalizer.insert() | FK violation | Log + skip bad row, insert rest |
| Validator checks | Hard failure | Log to report, skip bad rows |
| Validator checks | Soft warning | Log to report, continue |
| Builder.prereqs() | Empty table | Raise ValueError with "Run normalize first" |
| CLI missing args | argparse error | Print usage, exit 1 |

---

## 14. API Contract Stability

The `/scenarios`, `/scenarios/{id}`, and `/scenarios/{id}/decision` endpoints defined in Sprint A are stable and documented in `docs/api_contract.md`. Sprint C does not modify these endpoints. The frontend can be developed in parallel (Sprint E) using mock responses that match the API contract.

---

## 15. Testing

### 14.1 JSON Fixtures

```
tests/fixtures/
├── jolpica/
│   ├── 2024_21_results.json
│   ├── all_time_circuits.json
│   └── 2024_season_drivers.json
├── openf1/
│   ├── 9540_laps.json
│   ├── 9540_stints.json
│   ├── 9540_pit.json
│   ├── 9540_weather.json
│   └── 9540_race_control.json
└── duckdb/
    └── test_schema.sql
```

### 14.2 Test Files

- `tests/test_jolpica_client.py` — mock httpx, verify URL construction, cache behavior, --force
- `tests/test_openf1_client.py` — mock httpx, verify session_key routing, cache paths
- `tests/test_normalize_results.py` — fixture → validate → DB → assert rows + hashes
- `tests/test_normalize_laps.py` — same pattern, verify compound FK fallback
- `tests/test_build_race_state.py` — seed minimal fact data, verify derived columns
- `tests/test_build_features.py` — seed race_state data, verify label computation

### 14.3 No Live API Tests

Tests never call real Jolpica or OpenF1 endpoints. They load pre-saved JSON fixtures saved from actual API responses. This avoids rate limits, network fragility, and API schema changes breaking CI.

---

## 16. Rate Limiting

- Jolpica: `time.sleep(1.0)` between requests
- OpenF1: no explicit sleep (lenient limits) but cache-first means we almost never make repeat calls
- Aggressive caching: always check raw file existence before GET
- `--force` flag: delete raw files for the target before fetching (destructive, documented)

---

## 17. Out of Scope (This Sprint)

- FastF1 integration: only use existing `ingest/brazil_2024.py` for the pilot race. Full FastF1 normalizer deferred.
- FP1/FP2/FP3 sessions: Race + Qualifying only. Free practice deferred.
- Sprint sessions: Not normalized in this sprint.
- fact_driver_session_entry population: Schema exists (B2), data population deferred.
- fact_interval_sample and fact_position_sample from Jolpica: These come from OpenF1 only.
- ML training or model registry: Sprint F.
- Frontend: Sprint E (parallel).
