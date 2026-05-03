from ingest import SOURCE_PRIORITY


def test_source_priority_has_correct_order():
    assert SOURCE_PRIORITY == {"openf1": 1, "fastf1": 2, "jolpica": 3}


def test_source_priority_returns_int():
    for k, v in SOURCE_PRIORITY.items():
        assert isinstance(v, int)
