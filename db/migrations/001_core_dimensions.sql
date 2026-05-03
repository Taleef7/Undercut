CREATE TABLE IF NOT EXISTS dim_season (
    season_id VARCHAR PRIMARY KEY,
    year INT,
    regulations_era_label VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_meeting (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_circuit (
    circuit_id VARCHAR PRIMARY KEY,
    circuit_ref VARCHAR,
    circuit_name VARCHAR,
    location VARCHAR,
    country VARCHAR,
    latitude DOUBLE,
    longitude DOUBLE,
    altitude INT,
    track_length_km DOUBLE,
    typical_pit_loss_seconds DOUBLE,
    overtaking_difficulty_score DOUBLE,
    safety_car_probability_baseline DOUBLE,
    source_system VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_session (
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
    source_system VARCHAR,
    source_session_key VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_constructor (
    constructor_id VARCHAR PRIMARY KEY,
    constructor_ref VARCHAR,
    constructor_name VARCHAR,
    nationality VARCHAR,
    source_system VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_tyre_compound (
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
