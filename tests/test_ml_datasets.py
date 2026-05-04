from ml.datasets.pit_decision_dataset import PitDecisionDataset


def test_pit_decision_dataset_returns_features_and_labels():
    ds = PitDecisionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()
    assert len(feature_names) >= 5
    assert len(X_train) > 0
    assert len(y_train) == len(X_train)
    assert set(y_train.unique()).issubset({0, 1})


def test_pit_decision_dataset_feature_names_are_strings():
    ds = PitDecisionDataset()
    _, _, _, _, feature_names = ds.build()
    assert all(isinstance(f, str) for f in feature_names)
    assert "stint_age_laps" in feature_names
    assert "compound_hardness" in feature_names


def test_pit_decision_dataset_no_nan_in_label():
    ds = PitDecisionDataset()
    _, y_train, _, y_test, _ = ds.build()
    assert y_train.isna().sum() == 0
    assert y_test.isna().sum() == 0


def test_pit_decision_dataset_label_distribution():
    ds = PitDecisionDataset()
    _, y_train, _, _, _ = ds.build()
    ratio = y_train.mean()
    assert 0 < ratio < 1
