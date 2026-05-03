# Undercut API Contract

> Last updated: 2026-05-03

## Base URL

Development: `http://localhost:8000`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/scenarios` | List all decision points |
| `GET` | `/scenarios/{id}` | Detailed scenario with race state |
| `POST` | `/scenarios/{id}/decision` | Submit a decision, get scored result |

## Health Check

**`GET /`**

Response:
```json
{
  "message": "Undercut API is running"
}
```

## List Scenarios

**`GET /scenarios`**

Returns all available decision points as a summary list.

Response:
```json
[
  {
    "decision_point_id": "brazil_2024_lap32",
    "scenario_title": "VER vs NOR battle - pit decision under pressure",
    "scenario_description": "Lap 32 of the 2024 Brazilian GP. Verstappen is pressuring Norris for P2.\nYour driver is VER. Medium tires are 14 laps old. Gap to Norris is 1.2 seconds.\nRain is starting to fall. Team asks: pit now or stay out?",
    "driver_id": "VER",
    "lap_number": 32,
    "decision_type": "pit_now_vs_stay_out",
    "available_actions": ["pit_now_inter", "pit_now_hard", "stay_out", "extend_stint"],
    "difficulty_level": null
  },
  {
    "decision_point_id": "brazil_2024_lap48",
    "scenario_title": "Rain starting - wet weather call",
    "scenario_description": "Lap 48. Light rain has started. Track is drying but conditions are tricky.\nYour driver is VER on intermediate tires, 18 laps old. Gap to P2 is 4.5 seconds.\nTeam asks: stay on inters or switch to wets?",
    "driver_id": "VER",
    "lap_number": 48,
    "decision_type": "switch_to_wet",
    "available_actions": ["stay_inter", "pit_wet", "wait_and_see"],
    "difficulty_level": null
  },
  {
    "decision_point_id": "brazil_2024_lap68",
    "scenario_title": "Final stint - tire management",
    "scenario_description": "Lap 68 (final lap). VER is leading on hard tires, 28 laps old.\nGap to P2 is 12 seconds. Race is essentially over.\nTeam asks: push for fastest lap or manage to the finish?",
    "driver_id": "VER",
    "lap_number": 68,
    "decision_type": "extend_to_end",
    "available_actions": ["push", "manage", "ease_off"],
    "difficulty_level": null
  }
]
```

## Get Scenario Detail

**`GET /scenarios/{id}`**

Returns full scenario detail including race state and explanation text.

### Example: `GET /scenarios/brazil_2024_lap32`

Response:
```json
{
  "decision_point_id": "brazil_2024_lap32",
  "scenario_title": "VER vs NOR battle - pit decision under pressure",
  "scenario_description": "Lap 32 of the 2024 Brazilian GP. Verstappen is pressuring Norris for P2.\nYour driver is VER. Medium tires are 14 laps old. Gap to Norris is 1.2 seconds.\nRain is starting to fall. Team asks: pit now or stay out?",
  "driver_id": "VER",
  "lap_number": 32,
  "decision_type": "pit_now_vs_stay_out",
  "available_actions": ["pit_now_inter", "pit_now_hard", "stay_out", "extend_stint"],
  "difficulty_level": null,
  "actual_decision": "stay_out",
  "actual_outcome_summary": "VER stayed out, passed Norris on track, won the race",
  "explanation_short": "Staying out was the right call - wet track favored experienced drivers",
  "explanation_long": "By pitting earlier, VER would have lost track position to Norris who had\nfresher tires. By staying out, VER inherited the lead when Norris pitted\nand controlled the race from the front in wet conditions.",
  "current_position": 2,
  "gap_ahead_seconds": 1.2,
  "gap_behind_seconds": 4.8,
  "compound": "medium",
  "stint_age_laps": 14,
  "laps_remaining": 39,
  "track_temperature_c": 48.0,
  "air_temperature_c": 29.0,
  "rainfall": false,
  "track_status": "green",
  "safety_car_active": false,
  "virtual_safety_car_active": false
}
```

### Error: `GET /scenarios/nonexistent`

```json
{
  "detail": "Scenario not found"
}
```

Status: 404

## Submit Decision

**`POST /scenarios/{id}/decision`**

Submit a user's strategy decision and receive a scored result with simulation summary.

### Request Body

```json
{
  "action": "stay_out",
  "compound": null
}
```

- `action` (string, required): One of the `available_actions` for this scenario
- `compound` (string, optional): Target compound if pitting (e.g. `"soft"`, `"medium"`, `"hard"`, `"inter"`, `"wet"`)

### Response

```json
{
  "scenario_id": "brazil_2024_lap32",
  "user_action": "stay_out",
  "score": 75,
  "grade": "Strong call",
  "historical_decision": "stay_out",
  "model_recommendation": "stay_out",
  "model_confidence": null,
  "model_top_features": [],
  "simulation_summary": {
    "expected_position": 2,
    "expected_finish_position_band": null,
    "risk_score": 0.5,
    "tire_risk": null,
    "track_position_risk": null
  },
  "explanation": "You made the same call as the real team!",
  "tradeoffs": []
}
```

### Error: Invalid Action

`POST /scenarios/brazil_2024_lap32/decision` with `{"action": "invalid"}`

Response (status 422):
```json
{
  "detail": "Invalid action 'invalid'. Available: ['pit_now_inter', 'pit_now_hard', 'stay_out', 'extend_stint']"
}
```

### Error: Missing Scenario

`POST /scenarios/nonexistent/decision` with `{"action": "stay_out"}`

Response (status 404):
```json
{
  "detail": "Scenario not found"
}
```

## Pydantic Models

### ScenarioSummary
| Field | Type | Description |
|-------|------|-------------|
| decision_point_id | str | Unique scenario identifier |
| scenario_title | str | Short display title |
| scenario_description | str | Scenario narrative context |
| driver_id | str | 3-letter driver code (e.g. "VER") |
| lap_number | int | Current lap in the race |
| decision_type | str | Category: pit_now_vs_stay_out, switch_to_wet, extend_to_end, etc. |
| available_actions | list[str] | Allowed strategy choices |
| difficulty_level | str or None | Optional difficulty rating |

### ScenarioDetail
Extends ScenarioSummary with:

| Field | Type | Description |
|-------|------|-------------|
| actual_decision | str | What the team chose historically |
| actual_outcome_summary | str | Historical result summary |
| explanation_short | str | One-sentence explanation |
| explanation_long | str | Detailed analysis (3-5 sentences) |
| current_position | int | Driver's position at scenario lap |
| gap_ahead_seconds | float or None | Time gap to car ahead (null if leader) |
| gap_behind_seconds | float or None | Time gap to car behind |
| compound | str | Current tire compound |
| stint_age_laps | int | Laps on current tires |
| laps_remaining | int | Laps left in race |
| track_temperature_c | float or None | Track temperature |
| air_temperature_c | float or None | Ambient temperature |
| rainfall | bool or None | Is it raining? |
| track_status | str or None | green, yellow, safety_car, vsc, red_flag |
| safety_car_active | bool or None | Is SC deployed? |
| virtual_safety_car_active | bool or None | Is VSC active? |

### DecisionResponse
| Field | Type | Description |
|-------|------|-------------|
| scenario_id | str | Scenario identifier |
| user_action | str | User's chosen action |
| score | int | Score 0-100 |
| grade | str | Grade label (Masterful, Strong call, Inspired call, Risky, Poor call, Off the wall) |
| historical_decision | str | What the real team chose |
| model_recommendation | str | ML model suggestion |
| model_confidence | float or None | ML confidence score (Sprint F+) |
| model_top_features | list[str] | Top SHAP features (Sprint F+) |
| simulation_summary | object | Simulation outcome summary |
| explanation | str | Overall explanation text |
| tradeoffs | list[str] | Decision tradeoffs as bullet points (Sprint E+) |

### SimulationSummary
| Field | Type | Description |
|-------|------|-------------|
| expected_position | int | Projected finishing position |
| expected_finish_position_band | str or None | Position range (e.g. "P1-P3") |
| risk_score | float | Risk 0-1 (higher = riskier) |
| tire_risk | str or None | Tire risk assessment |
| track_position_risk | str or None | Track position risk |
