# Undercut API Contract

> Last updated: 2026-05-04

## Base URL

Development: `http://localhost:8000`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/scenarios` | List all decision points |
| `GET` | `/scenarios/{id}` | Detailed scenario with race state |
| `POST` | `/scenarios/{id}/decision` | Submit a decision, get scored result |
| `POST` | `/scenarios/{id}/chaos` | Submit a decision with chaos modifiers, get modified result |

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

## Submit Chaos Decision

**`POST /scenarios/{id}/chaos`**

Submit a user's strategy decision with one or more chaos modifiers applied, and receive a scored result based on the modified scenario context.

### Request Body

```json
{
  "action": "stay_out",
  "modifiers": [
    { "modifier_type": "safety_car", "modifier_value": 0.0 },
    { "modifier_type": "rain_starts", "modifier_value": 0.0 }
  ]
}
```

- `action` (string, required): One of the `available_actions` for this scenario
- `modifiers` (list[object], optional): Chaos modifiers to apply. Each modifier has:
  - `modifier_type` (string): One of `safety_car`, `vsc`, `rain_starts`, `tire_cliff_now`, `slow_pit_stop`, `rival_pits_this_lap`, `red_flag`
  - `modifier_value` (float): Numeric value for modifiers that require it (e.g. seconds for `slow_pit_stop`)

### Response

Same shape as `POST /scenarios/{id}/decision`:

```json
{
  "scenario_id": "brazil_2024_lap32",
  "user_action": "stay_out",
  "score": 75,
  "grade": "Strong call",
  "historical_decision": "stay_out",
  "model_recommendation": "stay_out",
  "model_confidence": 0.6,
  "model_top_features": ["No urgent signal to pit"],
  "simulation_summary": {
    "expected_position": 2,
    "expected_finish_position_band": "P1-P3",
    "risk_score": 0.5,
    "tire_risk": null,
    "track_position_risk": null
  },
  "explanation": "You made the same call as the real team!",
  "tradeoffs": []
}
```

### Error: Invalid Action

`POST /scenarios/brazil_2024_lap32/chaos` with `{"action": "invalid", "modifiers": []}`

Response (status 422):
```json
{
  "detail": "Invalid action 'invalid'. Available: ['pit_now_inter', 'pit_now_hard', 'stay_out', 'extend_stint']"
}
```

### Error: Missing Scenario

`POST /scenarios/nonexistent/chaos` with `{"action": "stay_out", "modifiers": []}`

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

## POST /predict/pit-decision

Direct ML model inference. Returns the trained XGBoost model's prediction for a specific session/driver/lap.

### Request Body

```json
{
    "session_id": "2024_21_R",
    "driver_id": "44",
    "lap_number": 32
}
```

| Field | Type | Description |
|-------|------|-------------|
| session_id | str | Session identifier (e.g. "2024_21_R") |
| driver_id | str | Driver number (e.g. "44") or 3-letter code (e.g. "VER") |
| lap_number | int | Lap number to evaluate (1-indexed) |

### Response (200)

```json
{
    "session_id": "2024_21_R",
    "driver_id": "44",
    "lap_number": 32,
    "recommendation": "stay_out",
    "confidence": 0.71,
    "probability_pit": 0.29,
    "probability_stay": 0.71,
    "top_features": [
        "Stint age was the key signal",
        "Track position was a significant factor",
        "Rain conditions changed the pit calculus"
    ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| session_id | str | Echoed from request |
| driver_id | str | Echoed from request |
| lap_number | int | Echoed from request |
| recommendation | str | "pit_now" or "stay_out" |
| confidence | float | Model confidence (0.5-1.0) |
| probability_pit | float | Raw probability of pit decision |
| probability_stay | float | Raw probability of stay-out decision |
| top_features | list[str] | Top 3 SHAP feature explanations |

### Error Responses

| Status | Condition |
|--------|-----------|
| 404 | No data found for the session/driver/lap combination |
| 422 | Feature mismatch between request and model expectations |
| 503 | No trained model is available (fallback to baselines active) |
