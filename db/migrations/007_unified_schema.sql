-- Unified schema migration
-- Creates all tables with columns exactly matching normalizer INSERT statements
-- Drops and recreates tables to ensure consistency

DROP TABLE IF EXISTS fact_lap;
DROP TABLE IF EXISTS fact_stint;
DROP TABLE IF EXISTS fact_pit_stop;
DROP TABLE IF EXISTS fact_position_sample;
DROP TABLE IF EXISTS fact_session_result;
DROP TABLE IF EXISTS fact_weather_sample;
DROP TABLE IF EXISTS fact_race_control_event;
DROP TABLE IF EXISTS fact_interval_sample;
DROP TABLE IF EXISTS fact_driver_session_entry;
DROP TABLE IF EXISTS dim_driver;
DROP TABLE IF EXISTS dim_season;
DROP TABLE IF EXISTS dim_meeting;
DROP TABLE IF EXISTS dim_circuit;
DROP TABLE IF EXISTS dim_session;
DROP TABLE IF EXISTS dim_constructor;
DROP TABLE IF EXISTS dim_tyre_compound;

-- Dimension tables

CREATE TABLE dim_season (
    season_id VARCHAR PRIMARY KEY,
    year INT,
    url VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_meeting (
    meeting_id VARCHAR PRIMARY KEY,
    season_id VARCHAR,
    round_number INT,
    meeting_name VARCHAR,
    official_event_name VARCHAR,
    country VARCHAR,
    location VARCHAR,
    circuit_id VARCHAR,
    start_date DATE,
    end_date DATE,
    source_system VARCHAR,
    source_meeting_key VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_circuit (
    circuit_id VARCHAR PRIMARY KEY,
    circuit_ref VARCHAR,
    circuit_name VARCHAR,
    location VARCHAR,
    country VARCHAR,
    lat DOUBLE,
    lng DOUBLE,
    altitude INT,
    track_length_km DOUBLE,
    typical_pit_loss_seconds DOUBLE,
    overtaking_difficulty_score DOUBLE,
    safety_car_probability_baseline DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_session (
    session_id VARCHAR PRIMARY KEY,
    meeting_id VARCHAR,
    season_id VARCHAR,
    session_name VARCHAR,
    session_type VARCHAR,
    session_date DATE,
    session_start_time_utc TIMESTAMP,
    is_race BOOLEAN,
    is_qualifying BOOLEAN,
    is_sprint BOOLEAN,
    total_laps INT,
    source_system VARCHAR,
    source_session_key VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_constructor (
    constructor_id VARCHAR PRIMARY KEY,
    constructor_ref VARCHAR,
    constructor_name VARCHAR,
    nationality VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_driver (
    driver_id VARCHAR PRIMARY KEY,
    driver_ref VARCHAR,
    driver_number INT,
    first_name VARCHAR,
    last_name VARCHAR,
    full_name VARCHAR,
    nationality VARCHAR,
    date_of_birth DATE,
    permanent_number INT,
    code VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE dim_tyre_compound (
    tyre_compound_id VARCHAR PRIMARY KEY,
    compound_label VARCHAR,
    compound_category VARCHAR,
    compound_code VARCHAR,
    compound_hardness_order INT,
    is_wet BOOLEAN,
    is_intermediate BOOLEAN,
    is_slick BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact tables

CREATE TABLE fact_driver_session_entry (
    driver_session_entry_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    driver_number INT,
    team_name_source VARCHAR,
    is_replacement_driver BOOLEAN DEFAULT FALSE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_session_result (
    session_result_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    classified_position VARCHAR,
    position_order INT,
    grid_position INT,
    points DOUBLE,
    laps_completed INT,
    status VARCHAR,
    time_milliseconds BIGINT,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_lap (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INT,
    PRIMARY KEY (session_id, driver_ref, lap_number),
    lap_time_ms DOUBLE,
    lap_time_seconds DOUBLE,
    tyre_compound_id VARCHAR,
    compound_label_source VARCHAR,
    stint_number INT,
    is_pit_out_lap BOOLEAN,
    lap_start_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_stint (
    session_id VARCHAR,
    driver_ref VARCHAR,
    stint_number INT,
    PRIMARY KEY (session_id, driver_ref, stint_number),
    tyre_compound_id VARCHAR,
    compound_label_source VARCHAR,
    lap_start INT,
    lap_end INT,
    tyre_age_at_start INT,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_pit_stop (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INT,
    PRIMARY KEY (session_id, driver_ref, lap_number),
    pit_duration_seconds DOUBLE,
    pit_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_weather_sample (
    session_id VARCHAR,
    sample_time VARCHAR,
    air_temperature_c DOUBLE,
    track_temperature_c DOUBLE,
    humidity_pct INT,
    rainfall_flag BOOLEAN,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_race_control_event (
    session_id VARCHAR,
    event_time VARCHAR,
    category VARCHAR,
    flag VARCHAR,
    scope VARCHAR,
    message VARCHAR,
    lap_number INT,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE fact_interval_sample (
    interval_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    gap_to_leader_seconds DOUBLE,
    interval_to_ahead_seconds DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);
