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
