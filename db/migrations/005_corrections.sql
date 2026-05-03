CREATE TABLE IF NOT EXISTS manual_data_correction (
    correction_id VARCHAR PRIMARY KEY,
    target_table VARCHAR,
    target_record_key VARCHAR,
    field_name VARCHAR,
    old_value VARCHAR,
    new_value VARCHAR,
    correction_reason VARCHAR,
    source_reference VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
