const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://undercut-api-production.up.railway.app";

export interface ScenarioSummary {
  decision_point_id: string;
  scenario_title: string;
  scenario_description: string;
  driver_id: string;
  lap_number: number;
  decision_type: string;
  available_actions: string[];
  difficulty_level: string | null;
}

export interface ScenarioDetail extends ScenarioSummary {
  actual_decision: string;
  actual_outcome_summary: string;
  explanation_short: string;
  explanation_long: string;
  current_position: number;
  gap_ahead_seconds: number | null;
  gap_behind_seconds: number | null;
  compound: string;
  stint_age_laps: number;
  laps_remaining: number;
  track_temperature_c: number | null;
  air_temperature_c: number | null;
  rainfall: boolean | null;
  track_status: string | null;
  safety_car_active: boolean | null;
  virtual_safety_car_active: boolean | null;
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
  model_confidence: number | null;
  model_top_features: string[];
  simulation_summary: SimulationSummary;
  explanation: string;
  tradeoffs: string[];
}

export async function getScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getScenario(id: string): Promise<ScenarioDetail> {
  const res = await fetch(`${API_BASE}/scenarios/${id}`);
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface ChaosModifier {
  modifier_type: string;
  modifier_value?: number;
}

export async function submitDecision(id: string, action: string): Promise<DecisionResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function submitChaosDecision(
  id: string,
  action: string,
  modifiers: ChaosModifier[]
): Promise<DecisionResponse> {
  const res = await fetch(`${API_BASE}/scenarios/${id}/chaos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, modifiers }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
