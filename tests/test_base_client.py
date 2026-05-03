import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ingest.base_client import BaseClient


class TestClient(BaseClient):
    BASE_URL = "https://fake.api/v1"
    SOURCE_SYSTEM = "test"

    def __init__(self, data_dir: Path):
        super().__init__(data_dir)


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def client(tmp_data_dir):
    return TestClient(data_dir=tmp_data_dir)


def test_cache_path_without_params(client):
    path = client._cache_path("2024/21/results")
    expected = client.raw_dir / "2024" / "21" / "results.json"
    assert path == expected


def test_cache_path_with_params(client):
    path = client._cache_path("sessions", {"session_key": 9540})
    expected = client.raw_dir / "sessions_session_key_9540.json"
    assert path == expected


def test_get_returns_cached_data(client, tmp_data_dir):
    raw_dir = tmp_data_dir / "raw" / "test"
    raw_dir.mkdir(parents=True)
    cache_file = raw_dir / "endpoint.json"
    cache_file.write_text(json.dumps({"cached": True}))

    with patch.object(client.client, "get") as mock_get:
        result = client._get("endpoint")
        mock_get.assert_not_called()
        assert result == {"cached": True}


def test_get_fetches_and_caches_on_miss(client, tmp_data_dir):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "fresh"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "get", return_value=mock_response) as mock_get:
        result = client._get("endpoint")
        mock_get.assert_called_once()
        assert result == {"data": "fresh"}

    cache_path = client.raw_dir / "endpoint.json"
    assert cache_path.exists()
    assert json.loads(cache_path.read_text()) == {"data": "fresh"}


def test_get_retries_on_5xx_then_returns_none(client, tmp_data_dir):
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "get", return_value=mock_response):
        with patch("time.sleep"):
            result = client._get("endpoint")
            assert result is None


def test_get_returns_none_on_4xx(client):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "get", return_value=mock_response):
        result = client._get("endpoint")
        assert result is None
