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

-- Race State Driver Lap View
-- Flattened view for simulation engine to get current state per driver per lap
CREATE VIEW IF NOT EXISTS race_state_driver_lap AS
SELECT 
    l.session_id,
    l.lap_number,
    l.driver_id,
    d.full_name as driver_name,
    l.position_at_lap as current_pos,
    l.lap_time_ms,
    -- Rolling average pace (last 3 laps) to smooth out anomalies
    AVG(l.lap_time_ms) OVER (
        PARTITION BY l.session_id, l.driver_id 
        ORDER BY l.lap_number 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as rolling_pace_ms,
    l.compound_id,
    c.label as compound_label,
    l.stint_age,
    l.gap_to_leader_s,
    l.interval_ahead_s,
    l.track_status
FROM 
    fact_lap l
JOIN 
    dim_driver d ON l.driver_id = d.driver_id
JOIN 
    dim_compound c ON l.compound_id = c.compound_id;
