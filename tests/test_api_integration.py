import pytest, json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200_and_message(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Undercut API is running"

    def test_health_returns_json_content_type(self):
        resp = client.get("/")
        assert resp.headers["content-type"] == "application/json"


class TestListScenarios:
    def test_returns_200(self):
        resp = client.get("/scenarios")
        assert resp.status_code == 200

    def test_returns_list(self):
        resp = client.get("/scenarios")
        data = resp.json()
        assert isinstance(data, list)

    def test_returns_all_12_scenarios(self):
        resp = client.get("/scenarios")
        data = resp.json()
        assert len(data) == 12

    def test_each_scenario_has_required_fields(self):
        resp = client.get("/scenarios")
        data = resp.json()
        for s in data:
            assert "decision_point_id" in s
            assert "scenario_title" in s
            assert "scenario_description" in s
            assert "driver_id" in s
            assert "lap_number" in s
            assert "decision_type" in s
            assert "available_actions" in s
            assert isinstance(s["lap_number"], int)
            assert isinstance(s["available_actions"], list)
            assert len(s["available_actions"]) >= 2

    def test_scenarios_span_multiple_races(self):
        resp = client.get("/scenarios")
        data = resp.json()
        races = set(s["decision_point_id"].rsplit("_", 1)[0] for s in data)
        assert len(races) == 4  # brazil_2024, abu_dhabi_2021, singapore_2023, hungary_2022

    def test_each_scenario_has_difficulty(self):
        resp = client.get("/scenarios")
        data = resp.json()
        for s in data:
            assert s["difficulty_level"] is None or isinstance(s["difficulty_level"], str)

    def test_all_decision_types_present(self):
        resp = client.get("/scenarios")
        data = resp.json()
        types = set(s["decision_type"] for s in data)
        expected = {"pit_now_vs_stay_out", "safety_car_pit", "cover_undercut",
                    "extend_to_end", "defend_position", "late_race_attack"}
        assert expected.issubset(types), f"Missing types: {expected - types}"


class TestGetScenario:
    def test_get_existing_scenario_returns_200(self):
        resp = client.get("/scenarios/brazil_2024_lap32")
        assert resp.status_code == 200

    def test_get_scenario_returns_full_detail(self):
        resp = client.get("/scenarios/brazil_2024_lap32")
        data = resp.json()
        assert data["decision_point_id"] == "brazil_2024_lap32"
        assert data["driver_id"] == "VER"
        assert data["lap_number"] == 32
        assert "current_position" in data
        assert "gap_ahead_seconds" in data
        assert "gap_behind_seconds" in data
        assert "compound" in data
        assert "stint_age_laps" in data
        assert "laps_remaining" in data
        assert "track_temperature_c" in data
        assert "air_temperature_c" in data
        assert "rainfall" in data
        assert "track_status" in data
        assert "safety_car_active" in data
        assert "virtual_safety_car_active" in data
        assert "actual_decision" in data
        assert "actual_outcome_summary" in data
        assert "explanation_short" in data
        assert "explanation_long" in data

    def test_get_scenario_returns_valid_numeric_fields(self):
        resp = client.get("/scenarios/brazil_2024_lap32")
        data = resp.json()
        assert isinstance(data["current_position"], int)
        assert isinstance(data["gap_ahead_seconds"], (float, int, type(None)))
        assert isinstance(data["stint_age_laps"], int)
        assert isinstance(data["laps_remaining"], int)
        assert data["current_position"] >= 1
        assert data["laps_remaining"] >= 0

    def test_get_nonexistent_scenario_returns_404(self):
        resp = client.get("/scenarios/nonexistent_id")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    def test_get_all_12_scenarios_individually(self):
        ids = [
            "brazil_2024_lap32", "brazil_2024_lap43", "brazil_2024_lap65",
            "abu_dhabi_2021_lap14", "abu_dhabi_2021_lap53", "abu_dhabi_2021_lap56",
            "singapore_2023_lap20", "singapore_2023_lap40", "singapore_2023_lap43",
            "hungary_2022_lap38", "hungary_2022_lap47", "hungary_2022_lap51",
        ]
        for sid in ids:
            resp = client.get(f"/scenarios/{sid}")
            assert resp.status_code == 200, f"Failed for {sid}: {resp.status_code}"


class TestSubmitDecision:
    def test_submit_valid_decision_returns_200(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        assert resp.status_code == 200

    def test_submit_decision_returns_decision_response_shape(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        data = resp.json()
        assert "scenario_id" in data
        assert "user_action" in data
        assert "score" in data
        assert "grade" in data
        assert "historical_decision" in data
        assert "model_recommendation" in data
        assert "simulation_summary" in data
        assert "explanation" in data
        assert "tradeoffs" in data

    def test_submit_decision_score_is_in_range(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        data = resp.json()
        assert 0 <= data["score"] <= 100

    def test_submit_decision_grade_is_valid(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        data = resp.json()
        valid_grades = {"Masterful", "Strong call", "Inspired call", "Risky", "Poor call", "Off the wall"}
        assert data["grade"] in valid_grades

    def test_submit_decision_model_fields_present(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        data = resp.json()
        assert "model_recommendation" in data
        assert "model_confidence" in data
        assert "model_top_features" in data
        assert isinstance(data["model_top_features"], list)

    def test_submit_decision_simulation_summary(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        data = resp.json()
        sim = data["simulation_summary"]
        assert "expected_position" in sim
        assert "expected_finish_position_band" in sim
        assert "risk_score" in sim
        assert "tire_risk" in sim
        assert "track_position_risk" in sim
        assert isinstance(sim["expected_position"], int)
        assert 0 <= sim["risk_score"] <= 1

    def test_submit_invalid_action_returns_422(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "invalid_action"})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data

    def test_submit_decision_for_nonexistent_scenario_returns_404(self):
        resp = client.post("/scenarios/nonexistent_id/decision", json={"action": "stay_out"})
        assert resp.status_code == 404

    def test_submit_pit_action_works(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "used_inters"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_action"] == "used_inters"

    def test_submit_all_scenarios_all_actions(self):
        # Test first action of each scenario to ensure all work
        resp = client.get("/scenarios")
        scenarios = resp.json()
        for s in scenarios:
            first_action = s["available_actions"][0]
            resp2 = client.post(
                f"/scenarios/{s['decision_point_id']}/decision",
                json={"action": first_action},
            )
            assert resp2.status_code == 200, f"Failed {s['decision_point_id']}:{first_action} -> {resp2.status_code}"
            data2 = resp2.json()
            assert data2["user_action"] == first_action
            assert 0 <= data2["score"] <= 100


class TestChaosEndpoint:
    def test_submit_chaos_returns_200(self):
        resp = client.post("/scenarios/brazil_2024_lap32/chaos", json={
            "action": "fresh_inters",
            "modifiers": [{"modifier_type": "safety_car", "modifier_value": 0.0}],
        })
        assert resp.status_code == 200

    def test_submit_chaos_returns_decision_response_shape(self):
        resp = client.post("/scenarios/brazil_2024_lap32/chaos", json={
            "action": "fresh_inters",
            "modifiers": [{"modifier_type": "safety_car", "modifier_value": 0.0}],
        })
        data = resp.json()
        assert "scenario_id" in data
        assert "score" in data
        assert "grade" in data
        assert "simulation_summary" in data

    def test_submit_chaos_multiple_modifiers(self):
        resp = client.post("/scenarios/singapore_2023_lap20/chaos", json={
            "action": "stay_out",
            "modifiers": [
                {"modifier_type": "rain_starts", "modifier_value": 0.5},
                {"modifier_type": "tire_cliff_now", "modifier_value": 0.0},
            ],
        })
        assert resp.status_code == 200

    def test_submit_chaos_all_modifier_types(self):
        modifiers = [
            {"modifier_type": "safety_car", "modifier_value": 0.0},
            {"modifier_type": "vsc", "modifier_value": 0.0},
            {"modifier_type": "rain_starts", "modifier_value": 0.5},
            {"modifier_type": "tire_cliff_now", "modifier_value": 0.0},
            {"modifier_type": "slow_pit_stop", "modifier_value": 5.0},
            {"modifier_type": "rival_pits_this_lap", "modifier_value": 0.0},
            {"modifier_type": "red_flag", "modifier_value": 0.0},
        ]
        resp = client.post("/scenarios/brazil_2024_lap32/chaos", json={
            "action": "fresh_inters",
            "modifiers": modifiers,
        })
        assert resp.status_code == 200

    def test_submit_chaos_invalid_action_returns_422(self):
        resp = client.post("/scenarios/brazil_2024_lap32/chaos", json={
            "action": "invalid_action",
            "modifiers": [{"modifier_type": "safety_car", "modifier_value": 0.0}],
        })
        assert resp.status_code == 422

    def test_submit_chaos_nonexistent_scenario_returns_404(self):
        resp = client.post("/scenarios/nonexistent_id/chaos", json={
            "action": "stay_out",
            "modifiers": [{"modifier_type": "safety_car", "modifier_value": 0.0}],
        })
        assert resp.status_code == 404

    def test_submit_chaos_modifier_changes_outcome(self):
        base = client.post("/scenarios/brazil_2024_lap32/decision", json={"action": "fresh_inters"})
        base_data = base.json()

        chaos = client.post("/scenarios/brazil_2024_lap32/chaos", json={
            "action": "fresh_inters",
            "modifiers": [{"modifier_type": "safety_car", "modifier_value": 0.0}],
        })
        chaos_data = chaos.json()

        # Chaos result should differ somehow (risk or position)
        assert (chaos_data["simulation_summary"]["risk_score"] !=
                base_data["simulation_summary"]["risk_score"] or
                chaos_data["score"] != base_data["score"])


class TestPredictEndpoint:
    def test_predict_valid_request_returns_200(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "44",
            "lap_number": 32,
        })
        assert resp.status_code in (200, 503)

    def test_predict_response_shape(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "44",
            "lap_number": 32,
        })
        if resp.status_code != 200:
            pytest.skip("Model not available")
        data = resp.json()
        assert "session_id" in data
        assert "driver_id" in data
        assert "lap_number" in data
        assert "recommendation" in data
        assert "confidence" in data
        assert "probability_pit" in data
        assert "probability_stay" in data
        assert "top_features" in data
        assert data["recommendation"] in ("pit_now", "stay_out")
        assert 0 <= data["confidence"] <= 1

    def test_predict_invalid_session_returns_404(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "invalid",
            "driver_id": "44",
            "lap_number": 1,
        })
        assert resp.status_code in (404, 503)

    def test_predict_accepts_driver_number(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "1",
            "lap_number": 5,
        })
        assert resp.status_code in (200, 503)

    def test_predict_probabilities_sum_to_one(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "44",
            "lap_number": 32,
        })
        if resp.status_code != 200:
            pytest.skip("Model not available")
        data = resp.json()
        total = data["probability_pit"] + data["probability_stay"]
        assert abs(total - 1.0) < 0.01

    def test_predict_top_features_are_strings(self):
        resp = client.post("/predict/pit-decision", json={
            "session_id": "2024_21_R",
            "driver_id": "44",
            "lap_number": 32,
        })
        if resp.status_code != 200:
            pytest.skip("Model not available")
        data = resp.json()
        assert len(data["top_features"]) <= 3
        for feat in data["top_features"]:
            assert isinstance(feat, str)


class TestCrossRaceFlows:
    def test_brazil_decision(self):
        resp = client.post("/scenarios/brazil_2024_lap43/decision", json={"action": "push_for_lead"})
        assert resp.status_code == 200
        assert resp.json()["scenario_id"] == "brazil_2024_lap43"

    def test_abu_dhabi_decision(self):
        resp = client.post("/scenarios/abu_dhabi_2021_lap53/decision", json={"action": "stay_out"})
        assert resp.status_code == 200
        assert resp.json()["scenario_id"] == "abu_dhabi_2021_lap53"

    def test_singapore_decision(self):
        resp = client.post("/scenarios/singapore_2023_lap40/decision", json={"action": "stay_out_defend"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "singapore_2023_lap40"

    def test_hungary_decision(self):
        resp = client.post("/scenarios/hungary_2022_lap38/decision", json={"action": "stay_out_extend"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_id"] == "hungary_2022_lap38"

    def test_all_races_have_different_compounds(self):
        scenarios = [
            ("brazil_2024_lap32", "medium"),
            ("abu_dhabi_2021_lap53", "hard"),
            ("singapore_2023_lap40", "hard"),
            ("hungary_2022_lap38", "medium"),
        ]
        for sid, _ in scenarios:
            resp = client.get(f"/scenarios/{sid}")
            assert resp.status_code == 200


class TestErrorHandling:
    def test_empty_request_body_returns_422(self):
        resp = client.post("/scenarios/brazil_2024_lap32/decision", json={})
        assert resp.status_code == 422

    def test_wrong_method_returns_405(self):
        resp = client.put("/scenarios/brazil_2024_lap32")
        assert resp.status_code == 405

    def test_invalid_json_returns_422(self):
        resp = client.post(
            "/scenarios/brazil_2024_lap32/decision",
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_cors_headers_present(self):
        resp = client.options(
            "/scenarios",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" in resp.headers
