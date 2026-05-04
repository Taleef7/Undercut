import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

from ml.datasets.pit_decision_dataset import PitDecisionDataset
from ml.models.pit_decision_model import PitDecisionModel


@pytest.fixture
def training_data():
    ds = PitDecisionDataset()
    X_train, y_train, _, _, feature_names = ds.build()
    return X_train, y_train, feature_names


def test_pit_model_train_and_predict(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="xgboost")
    model.train(X_train, y_train, feature_names)
    rec, conf = model.predict(X_train.iloc[[0]])
    assert rec in ("pit_now", "stay_out")
    assert 0 <= conf <= 1


def test_pit_model_save_and_load(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="logistic_regression")
    model.train(X_train, y_train, feature_names)
    tmpdir = Path(tempfile.mkdtemp())
    model.save(tmpdir)
    loaded = PitDecisionModel.load(tmpdir)
    rec, conf = loaded.predict(X_train.iloc[[0]])
    assert rec in ("pit_now", "stay_out")
    assert 0 <= conf <= 1
    shutil.rmtree(tmpdir)


def test_pit_model_explain_returns_strings(training_data):
    X_train, y_train, feature_names = training_data
    model = PitDecisionModel(model_type="xgboost")
    model.train(X_train, y_train, feature_names)
    explanations = model.explain(X_train.iloc[[0]])
    assert len(explanations) == 3
    assert all(isinstance(e, str) for e in explanations)
