const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface ScenarioSummary {
  id: string;
  session_id: string;
  driver_id: string;
  lap_number: number;
  decision_type: string;
  scenario_title: string;
  scenario_description: string;
}

export interface ScenarioDetail extends ScenarioSummary {
  available_actions: string[];
  actual_decision: string;
  actual_outcome_summary: string;
  explanation_short: string;
  explanation_long: string;
  race_state: {
    current_position: number;
    gap_ahead_seconds: number | null;
    gap_behind_seconds: number | null;
    compound: string;
    stint_age_laps: number;
    laps_remaining: number;
    track_temperature_c: number;
    air_temperature_c: number;
    rainfall: boolean;
    track_status: string;
    safety_car_active: boolean;
    virtual_safety_car_active: boolean;
  };
}

export interface SimulationSummary {
  expected_position: number;
  expected_finish_position_band: string;
  risk_score: number;
  tire_risk: string;
  track_position_risk: string;
}

export interface DecisionResponse {
  scenario_id: string;
  user_action: string;
  score: number;
  grade: string;
  historical_decision: string;
  model_recommendation: string;
  model_confidence: number;
  model_top_features: string[];
  simulation_summary: SimulationSummary;
  explanation: string;
  tradeoffs: string[];
}

export async function getScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.status}`);
  return res.json();
}

export async function getScenario(id: string): Promise<ScenarioDetail> {
  const res = await fetch(`${API_BASE}/scenarios/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch scenario: ${res.status}`);
  return res.json();
}

export async function submitDecision(id: string, action: string): Promise<DecisionResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`Failed to submit decision: ${res.status}`);
  return res.json();
}
