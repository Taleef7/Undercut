CREATE TABLE IF NOT EXISTS fact_driver_session_entry (
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
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_session_result (
    session_result_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    driver_id VARCHAR,
    constructor_id VARCHAR,
    position_order INT,
    classified_position VARCHAR,
    points DOUBLE,
    status VARCHAR,
    status_normalized VARCHAR,
    laps_completed INT,
    time_milliseconds BIGINT,
    fastest_lap_rank INT,
    fastest_lap_time VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_weather_sample (
    weather_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    sample_time TIMESTAMP,
    lap_number INT,
    air_temperature DOUBLE,
    track_temperature DOUBLE,
    humidity DOUBLE,
    pressure DOUBLE,
    rainfall BOOLEAN,
    wind_speed DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_race_control_event (
    race_control_event_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    meeting_id VARCHAR,
    season_id VARCHAR,
    event_time TIMESTAMP,
    lap_number INT,
    category VARCHAR,
    message VARCHAR,
    flag VARCHAR,
    scope VARCHAR,
    driver_id VARCHAR,
    normalized_event_type VARCHAR,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_interval_sample (
    interval_sample_id VARCHAR PRIMARY KEY,
    session_id VARCHAR,
    driver_id VARCHAR,
    lap_number INT,
    gap_to_leader_seconds DOUBLE,
    interval_to_ahead_seconds DOUBLE,
    source_system VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
