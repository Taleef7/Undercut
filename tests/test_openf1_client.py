import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ingest.openf1_client import OpenF1Client


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def client(tmp_data_dir):
    return OpenF1Client(data_dir=tmp_data_dir)


def test_base_url_is_openf1(client):
    assert client.BASE_URL == "https://api.openf1.org/v1"
    assert client.SOURCE_SYSTEM == "openf1"


def test_get_meetings_returns_list(client):
    with patch.object(client, "_get") as mock_get:
        mock_get.return_value = [{"meeting_key": 47, "meeting_name": "Brazilian Grand Prix"}]
        result = client.get_meetings(year=2024)
        mock_get.assert_called_once()
        assert len(result) == 1
        assert result[0]["meeting_key"] == 47


def test_get_sessions_returns_list(client):
    with patch.object(client, "_get") as mock_get:
        mock_get.return_value = [
            {"session_key": 9540, "session_type": "Race"},
            {"session_key": 9539, "session_type": "Qualifying"},
        ]
        result = client.get_sessions(meeting_key=47)
        assert len(result) == 2
        assert result[0]["session_type"] == "Race"


def test_fetch_session_fetches_all_endpoints(client):
    with patch.object(client, "_get") as mock_get:
        mock_get.return_value = []
        result = client.fetch_session(session_key=9540, meeting_key=47)
        assert len(result) >= 9
        assert "laps" in result
        assert "weather" in result
        assert "race_control" in result


def test_cache_path_includes_session_key(client):
    path = client._cache_path("sessions/9540/laps")
    assert "9540" in str(path)
