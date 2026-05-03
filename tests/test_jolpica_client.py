import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ingest.jolpica_client import JolpicaClient


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def client(tmp_data_dir):
    return JolpicaClient(data_dir=tmp_data_dir)


def test_base_url_is_jolpica(client):
    assert client.BASE_URL == "https://api.jolpi.ca/ergast/f1"
    assert client.SOURCE_SYSTEM == "jolpica"


def test_fetch_raw_bootstrap_fetches_drivers_and_constructors(client):
    with patch.object(client, "_get", return_value={"MRData": {"test": True}}) as mock_get:
        result = client.fetch_raw_bootstrap(season=2024)
        assert mock_get.call_count == 2
        assert "drivers" in result
        assert "constructors" in result


def test_fetch_raw_fetches_round_endpoints(client):
    with patch.object(client, "_get", return_value={"MRData": {}}) as mock_get:
        with patch.object(client, "_get_all_paginated", return_value=[]):
            result = client.fetch_raw(season=2024, round=21)
            assert "results" in result
            assert "qualifying" in result
            assert "pit_stops" in result
            assert "lap_times" in result


def test_fetch_raw_all_time_fetches_circuits(client):
    with patch.object(client, "_get", return_value={"MRData": {}}) as mock_get:
        result = client.fetch_raw_all_time()
        assert "circuits" in result
        mock_get.assert_called_once()


def test_get_all_paginated_handles_multiple_pages(client):
    page1 = {"MRData": {"RaceTable": {"Races": [{"Laps": [{"number": 1}]}]}}}
    page2 = {"MRData": {"RaceTable": {"Races": [{"Laps": [{"number": 2}]}]}}}

    with patch.object(client, "_get") as mock_get:
        mock_get.side_effect = [page1, page2, {"MRData": {"RaceTable": {"Races": []}}}]
        with patch("time.sleep"):
            result = client._get_all_paginated("2024/21/laps", params={"limit": 1})
            assert len(mock_get.call_args_list) == 3
