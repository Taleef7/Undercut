-- Migration 006: ML Model Registry
-- Tracks trained model versions, evaluation metrics, and artifact paths

CREATE TABLE IF NOT EXISTS ml_model_registry (
    model_id VARCHAR PRIMARY KEY,
    model_name VARCHAR NOT NULL,
    model_version VARCHAR NOT NULL,
    target_definition VARCHAR,
    training_data_version VARCHAR,
    feature_view_version VARCHAR,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy DOUBLE,
    f1_score DOUBLE,
    roc_auc DOUBLE,
    artifact_path VARCHAR,
    notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_registry_name_version
    ON ml_model_registry (model_name, model_version);
