CREATE TABLE IF NOT EXISTS dim_circuit (
    circuit_ref VARCHAR PRIMARY KEY,
    circuit_name VARCHAR,
    location VARCHAR,
    country VARCHAR,
    lat REAL,
    lng REAL,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_driver (
    driver_ref VARCHAR PRIMARY KEY,
    driver_code VARCHAR,
    driver_number VARCHAR,
    driver_forename VARCHAR,
    driver_surname VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_constructor (
    constructor_ref VARCHAR PRIMARY KEY,
    constructor_name VARCHAR,
    constructor_nationality VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_season (
    year INTEGER PRIMARY KEY,
    wiki_url VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_meeting (
    meeting_key VARCHAR PRIMARY KEY,
    season INTEGER,
    round INTEGER,
    meeting_name VARCHAR,
    meeting_official_name VARCHAR,
    circuit_ref VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_session (
    session_id VARCHAR PRIMARY KEY,
    meeting_key VARCHAR,
    session_type VARCHAR,
    session_name VARCHAR,
    total_laps INTEGER,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_tyre_compound (
    tyre_compound_id INTEGER PRIMARY KEY,
    compound_name VARCHAR,
    compound_type VARCHAR,
    compound_code VARCHAR,
    hardness INTEGER,
    is_wet BOOLEAN,
    is_intermediate BOOLEAN,
    is_unknown BOOLEAN
);

CREATE TABLE IF NOT EXISTS dim_track_status_code (
    track_status_code VARCHAR PRIMARY KEY,
    status_description VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_session_result (
    session_id VARCHAR,
    driver_ref VARCHAR,
    constructor_ref VARCHAR,
    classified_position VARCHAR,
    position_order INTEGER,
    grid_position INTEGER,
    points FLOAT,
    laps_completed INTEGER,
    status VARCHAR,
    time_millis INTEGER,
    time_gap VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR,
    PRIMARY KEY (session_id, driver_ref)
);

CREATE TABLE IF NOT EXISTS fact_lap (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INTEGER,
    lap_time_ms DOUBLE,
    lap_time_seconds DOUBLE,
    tyre_compound_id INTEGER,
    compound_label_source VARCHAR,
    stint_number INTEGER,
    is_pit_out_lap BOOLEAN,
    lap_start_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR,
    PRIMARY KEY (session_id, driver_ref, lap_number)
);

CREATE TABLE IF NOT EXISTS fact_stint (
    session_id VARCHAR,
    driver_ref VARCHAR,
    stint_number INTEGER,
    tyre_compound_id INTEGER,
    compound_label_source VARCHAR,
    lap_start INTEGER,
    lap_end INTEGER,
    tyre_age_at_start INTEGER,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR,
    PRIMARY KEY (session_id, driver_ref, stint_number)
);

CREATE TABLE IF NOT EXISTS fact_pit_stop (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INTEGER,
    pit_duration_seconds DOUBLE,
    pit_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR,
    PRIMARY KEY (session_id, driver_ref, lap_number)
);

CREATE TABLE IF NOT EXISTS fact_weather_sample (
    session_id VARCHAR,
    sample_time VARCHAR,
    air_temperature_c DOUBLE,
    track_temperature_c DOUBLE,
    humidity_pct INTEGER,
    rainfall_flag BOOLEAN,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_race_control_event (
    session_id VARCHAR,
    event_time VARCHAR,
    category VARCHAR,
    flag VARCHAR,
    scope VARCHAR,
    message VARCHAR,
    lap_number INTEGER,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_version VARCHAR,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS race_state_driver_lap_fact (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INTEGER,
    lap_time_ms INTEGER,
    lap_time_seconds FLOAT,
    tyre_compound_id INTEGER,
    compound_label_source VARCHAR,
    stint_number INTEGER,
    stint_age_laps INTEGER,
    laps_remaining INTEGER,
    is_pit_lap BOOLEAN,
    rolling_3_lap_avg_ms FLOAT,
    rolling_5_lap_avg_ms FLOAT,
    pace_delta_to_field_ms FLOAT,
    interval_behind_seconds FLOAT,
    safety_car_active_flag BOOLEAN,
    rainfall_flag BOOLEAN,
    track_status_normalized VARCHAR,
    current_position INTEGER,
    gap_ahead_seconds FLOAT,
    gap_behind_seconds FLOAT,
    driver_ahead_id VARCHAR,
    driver_behind_id VARCHAR,
    undercut_threat_flag BOOLEAN,
    pit_window_open_flag BOOLEAN,
    computed_at TIMESTAMP,
    data_version VARCHAR
);

CREATE TABLE IF NOT EXISTS race_state_field_lap (
    session_id VARCHAR,
    lap_number INTEGER,
    leader_driver_id VARCHAR,
    running_drivers_count INTEGER,
    field_spread_seconds FLOAT,
    avg_lap_time_ms FLOAT,
    median_lap_time_ms FLOAT,
    fastest_lap_time_ms FLOAT,
    field_median_rolling_3_lap_ms FLOAT,
    computed_at TIMESTAMP,
    data_version VARCHAR
);

CREATE TABLE IF NOT EXISTS feature_pit_decision (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INTEGER,
    stint_age_laps INTEGER,
    laps_remaining INTEGER,
    current_position INTEGER,
    tyre_compound_id INTEGER,
    gap_ahead_seconds FLOAT,
    gap_behind_seconds FLOAT,
    safety_car_active_flag BOOLEAN,
    rainfall_flag BOOLEAN,
    track_temperature_c FLOAT,
    pit_loss_estimate FLOAT,
    actual_pitted_within_3_laps BOOLEAN,
    computed_at TIMESTAMP,
    data_version VARCHAR
);

CREATE TABLE IF NOT EXISTS feature_undercut_opportunity (
    session_id VARCHAR,
    driver_ref VARCHAR,
    lap_number INTEGER,
    target_driver_ref VARCHAR,
    gap_to_target_seconds FLOAT,
    own_stint_age_laps INTEGER,
    target_stint_age_laps INTEGER,
    own_compound_id INTEGER,
    target_compound_id INTEGER,
    pit_loss_estimate FLOAT,
    overtaking_difficulty FLOAT,
    undercut_succeeded BOOLEAN,
    computed_at TIMESTAMP,
    data_version VARCHAR
);
