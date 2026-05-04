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


def test_finish_position_dataset_returns_features():
    from ml.datasets.finish_position_dataset import FinishPositionDataset
    ds = FinishPositionDataset()
    X_train, y_train, X_test, y_test, feature_names = ds.build()
    assert len(feature_names) >= 3
    assert len(X_train) > 0
    assert len(y_train) == len(X_train)


def test_finish_position_band_mapping():
    from ml.datasets.finish_position_dataset import FinishPositionDataset
    assert FinishPositionDataset._position_to_band(1) == "P1-P3"
    assert FinishPositionDataset._position_to_band(4) == "P4-P6"
    assert FinishPositionDataset._position_to_band(8) == "P7-P10"
    assert FinishPositionDataset._position_to_band(12) == "P11-P15"
    assert FinishPositionDataset._position_to_band(20) == "P16+"
