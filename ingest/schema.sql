-- Undercut DuckDB Schema (MVP-0)

-- Enable pandas
SET pandas_analyze_sample_size = 1000;

-- Dimension: Driver
CREATE TABLE IF NOT EXISTS dim_driver (
    driver_id VARCHAR PRIMARY KEY,
    code VARCHAR,
    full_name VARCHAR,
    current_team VARCHAR,
    source_system VARCHAR DEFAULT 'fastf1',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Tyre Compound
CREATE TABLE IF NOT EXISTS dim_compound (
    compound_id VARCHAR PRIMARY KEY,
    label VARCHAR,
    category VARCHAR,
    hardness_order INT,
    source VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Lap
CREATE TABLE IF NOT EXISTS fact_lap (
    lap_id BIGINT PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    position_at_lap INT,
    lap_time_ms DOUBLE,
    compound_id VARCHAR,
    stint_age INT,
    gap_to_leader_s DOUBLE,
    interval_ahead_s DOUBLE,
    track_status VARCHAR,
    source_system VARCHAR DEFAULT 'fastf1',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Stint
CREATE TABLE IF NOT EXISTS fact_stint (
    stint_id BIGINT PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    stint_number INT,
    compound_id VARCHAR,
    lap_start INT,
    lap_end INT,
    tyre_age_at_start INT,
    source_system VARCHAR DEFAULT 'fastf1',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Pit Stop
CREATE TABLE IF NOT EXISTS fact_pit_stop (
    pit_id BIGINT PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    pit_duration_ms DOUBLE,
    old_compound_id VARCHAR,
    new_compound_id VARCHAR,
    source_system VARCHAR DEFAULT 'fastf1',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Race State Decision Point
CREATE TABLE IF NOT EXISTS race_state_decision_point (
    decision_point_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    decision_type VARCHAR,
    scenario_title VARCHAR,
    scenario_description VARCHAR,
    available_actions_json VARCHAR,
    actual_decision VARCHAR,
    actual_outcome_summary VARCHAR,
    explanation_short VARCHAR,
    explanation_long VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);