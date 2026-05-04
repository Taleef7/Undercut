from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)


def evaluate_binary_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    model_name: str = "model",
) -> Dict[str, Any]:
    metrics = {
        "model_name": model_name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1_score": round(f1_score(y_true, y_pred, zero_division=0), 4),
    }
    try:
        metrics["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)
    except Exception:
        metrics["roc_auc"] = 0.0
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics["true_negatives"] = int(tn)
    metrics["false_positives"] = int(fp)
    metrics["false_negatives"] = int(fn)
    metrics["true_positives"] = int(tp)
    metrics["total_samples"] = len(y_true)
    
    return metrics


def evaluate_multiclass_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    model_name: str = "model",
) -> Dict[str, Any]:
    metrics = {
        "model_name": model_name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "f1_weighted": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "total_samples": len(y_true),
    }
    report = classification_report(y_true, y_pred, target_names=class_names, zero_division=0, output_dict=True)
    metrics["classification_report"] = report
    return metrics
