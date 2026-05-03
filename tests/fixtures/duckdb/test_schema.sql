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
