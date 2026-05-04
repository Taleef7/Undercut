-- Missing dimension table
CREATE TABLE IF NOT EXISTS dim_driver (
    driver_id VARCHAR PRIMARY KEY,
    driver_ref VARCHAR,
    driver_code VARCHAR,
    driver_number VARCHAR,
    driver_forename VARCHAR,
    driver_surname VARCHAR,
    nationality VARCHAR,
    date_of_birth DATE,
    source_system VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Missing fact tables
CREATE TABLE IF NOT EXISTS fact_lap (
    lap_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    lap_time_ms DOUBLE,
    lap_time_seconds DOUBLE,
    sector1_time_ms DOUBLE,
    sector2_time_ms DOUBLE,
    sector3_time_ms DOUBLE,
    tyre_compound_id VARCHAR,
    compound_label_source VARCHAR,
    stint_number INT,
    is_pit_out_lap BOOLEAN DEFAULT FALSE,
    is_pit_in_lap BOOLEAN DEFAULT FALSE,
    lap_start_time TIMESTAMP,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_stint (
    stint_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    stint_number INT,
    tyre_compound_id VARCHAR,
    compound_label_source VARCHAR,
    lap_start INT,
    lap_end INT,
    stint_length INT,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_pit_stop (
    pit_stop_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    pit_stop_number INT,
    pit_duration_seconds DOUBLE,
    tyre_compound_id VARCHAR,
    compound_label_source VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_position_sample (
    position_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    position INT,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
