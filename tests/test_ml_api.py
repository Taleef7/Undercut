from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_predict_pit_decision_endpoint_exists():
    response = client.post("/predict/pit-decision", json={
        "session_id": "2024_21_R",
        "driver_id": "44",
        "lap_number": 32,
    })
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data
        assert "top_features" in data


def test_predict_pit_decision_missing_session():
    response = client.post("/predict/pit-decision", json={
        "session_id": "invalid",
        "driver_id": "44",
        "lap_number": 1,
    })
    assert response.status_code in (404, 503)
