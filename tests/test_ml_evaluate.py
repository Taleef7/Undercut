import numpy as np
from ml.evaluate import evaluate_binary_classification, evaluate_multiclass_classification


def test_binary_evaluation_returns_expected_keys():
    y_true = np.array([0, 1, 0, 1, 0])
    y_pred = np.array([0, 1, 0, 0, 0])
    y_proba = np.array([0.2, 0.8, 0.3, 0.4, 0.1])
    metrics = evaluate_binary_classification(y_true, y_pred, y_proba)
    for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc", "true_positives", "false_negatives"):
        assert key in metrics
    assert metrics["accuracy"] == 0.8


def test_binary_evaluation_perfect_prediction():
    y_true = np.array([0, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 1])
    y_proba = np.array([0.1, 0.9, 0.2, 0.8])
    metrics = evaluate_binary_classification(y_true, y_pred, y_proba)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1_score"] == 1.0
