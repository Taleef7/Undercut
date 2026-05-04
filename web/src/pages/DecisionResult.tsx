import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import type { ScenarioDetail, DecisionResponse, ChaosModifier } from "../api/client";
import { submitChaosDecision } from "../api/client";
import { RotateCcw, ArrowRight, Sparkles } from "lucide-react";

const GRADE_COLORS: Record<string, string> = {
  Masterful: "text-gold",
  Strong: "text-strong",
  "Strong call": "text-strong",
  Inspired: "text-inspired",
  "Inspired call": "text-inspired",
  Risky: "text-risky",
  Poor: "text-poor",
  "Poor call": "text-poor",
  "Off the wall": "text-offwall",
};

function getGradeColor(grade: string): string {
  return GRADE_COLORS[grade] ?? "text-muted-foreground";
}

function getRiskBarColor(score: number): string {
  if (score < 0.3) return "bg-strong";
  if (score < 0.6) return "bg-risky";
  return "bg-poor";
}

interface ModifierConfig {
  key: string;
  label: string;
  defaultValue?: number;
}

const MODIFIERS: ModifierConfig[] = [
  { key: "safety_car", label: "Safety Car" },
  { key: "vsc", label: "Virtual Safety Car" },
  { key: "rain_starts", label: "Rain Starts" },
  { key: "tire_cliff_now", label: "Tire Cliff Now (+8 laps)" },
  { key: "slow_pit_stop", label: "Slow Pit Stop (+3s)", defaultValue: 3 },
  { key: "rival_pits_this_lap", label: "Rival Pits This Lap" },
  { key: "red_flag", label: "Red Flag" },
];

export default function DecisionResult() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as {
    scenario?: ScenarioDetail;
    response?: DecisionResponse;
  } | null;

  const [activeModifiers, setActiveModifiers] = useState<Record<string, boolean>>({});
  const [chaosResult, setChaosResult] = useState<DecisionResponse | null>(null);
  const [chaosLoading, setChaosLoading] = useState(false);
  const [chaosError, setChaosError] = useState<string | null>(null);

  if (!state?.scenario || !state?.response) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <h2 className="text-xl font-semibold text-foreground mb-2">
            No result to show
          </h2>
          <p className="text-muted-foreground mb-4">
            Play a scenario first to see your result.
          </p>
          <Button onClick={() => navigate("/")}>Browse Scenarios</Button>
        </div>
      </div>
    );
  }

  const { scenario, response } = state;
  const sim = response.simulation_summary;

  const toggleModifier = (key: string) => {
    setActiveModifiers((prev) => ({ ...prev, [key]: !prev[key] }));
    setChaosResult(null);
    setChaosError(null);
  };

  const handleSimulateChaos = async () => {
    const selected: ChaosModifier[] = MODIFIERS.filter((m) => activeModifiers[m.key]).map((m) => ({
      modifier_type: m.key,
      modifier_value: m.defaultValue,
    }));

    if (selected.length === 0) {
      setChaosError("Select at least one modifier.");
      return;
    }

    setChaosLoading(true);
    setChaosError(null);
    try {
      const result = await submitChaosDecision(scenario.decision_point_id, response.user_action, selected);
      setChaosResult(result);
    } catch (err) {
      setChaosError(err instanceof Error ? err.message : "Failed to simulate chaos scenario");
    } finally {
      setChaosLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground px-6 py-8">
      <div className="max-w-2xl mx-auto text-left">
        {/* Score */}
        <div className="text-center mb-6">
          <div className="text-sm text-muted-foreground mb-1">Your Score</div>
          <div className="text-7xl font-bold text-foreground tracking-tight">
            {response.score}
          </div>
          <div
            className={`text-lg font-semibold mt-1 ${getGradeColor(response.grade)}`}
          >
            {response.grade}
          </div>
        </div>

        {/* Comparison */}
        <div className="bg-card border border-border rounded-xl p-4 mb-5">
          <div className="flex items-center justify-between text-sm">
            <div>
              <span className="text-muted-foreground">You chose</span>{" "}
              <span className="font-semibold text-foreground capitalize">
                {response.user_action.replace(/_/g, " ")}
              </span>
            </div>
            <div className="text-muted-foreground">/</div>
            <div>
              <span className="text-muted-foreground">Real team chose</span>{" "}
              <span className="font-semibold text-foreground capitalize">
                {response.historical_decision.replace(/_/g, " ")}
              </span>
            </div>
          </div>
        </div>

        {/* Model rec */}
        <div className="flex items-center gap-3 mb-5">
          <Badge variant="secondary" className="text-xs">
            Model says: {response.model_recommendation.replace(/_/g, " ")}
          </Badge>
          {response.model_confidence != null && (
            <span className="text-sm text-muted-foreground">
              {(response.model_confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>

        {/* Simulation Summary */}
        <div className="bg-card border border-border rounded-xl p-4 mb-5">
          <div className="text-sm font-medium text-foreground mb-3">
            Simulation Summary
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs text-muted-foreground">Expected Position</div>
              <div className="text-lg font-semibold text-foreground">
                P{sim.expected_position}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Finish Band</div>
              <div className="text-lg font-semibold text-foreground">
                {sim.expected_finish_position_band}
              </div>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>Risk Score</span>
              <span>{(sim.risk_score * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${getRiskBarColor(
                  sim.risk_score
                )}`}
                style={{ width: `${sim.risk_score * 100}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
              <span>Tire: {sim.tire_risk}</span>
              <span>Track: {sim.track_position_risk}</span>
            </div>
          </div>
        </div>

        {/* Tradeoffs */}
        <div className="mb-5">
          <div className="text-sm font-medium text-foreground mb-2">Tradeoffs</div>
          <ul className="space-y-2">
            {response.tradeoffs.map((t, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-foreground"
              >
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                {t}
              </li>
            ))}
          </ul>
        </div>

        {/* Explanation */}
        <div className="mb-8">
          <div className="text-sm font-medium text-foreground mb-2">Analysis</div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {response.explanation}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 mb-10">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() =>
              navigate(`/scenario/${scenario.decision_point_id}`, {
                state: { disabledAction: response.user_action },
              })
            }
          >
            <RotateCcw size={16} className="mr-2" />
            Try a Different Call
          </Button>
          <Button
            className="flex-1"
            onClick={() => navigate("/")}
          >
            <ArrowRight size={16} className="mr-2" />
            Play Another
          </Button>
        </div>

        {/* Chaos Engine */}
        <div className="border-t border-border pt-8">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={18} className="text-primary" />
            <h2 className="text-lg font-semibold text-foreground">What if...?</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            Toggle chaos modifiers to see how unexpected events would have changed the outcome of your decision.
          </p>

          <div className="bg-card border border-border rounded-xl p-4 mb-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {MODIFIERS.map((m) => (
                <div key={m.key} className="flex items-center justify-between gap-3">
                  <span className="text-sm text-foreground">{m.label}</span>
                  <Switch
                    checked={!!activeModifiers[m.key]}
                    onCheckedChange={() => toggleModifier(m.key)}
                  />
                </div>
              ))}
            </div>
          </div>

          {chaosError && (
            <div className="text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 text-sm mb-4">
              {chaosError}
            </div>
          )}

          <Button
            onClick={handleSimulateChaos}
            disabled={chaosLoading}
            className="mb-6"
          >
            <Sparkles size={16} className="mr-2" />
            {chaosLoading ? "Simulating..." : "Simulate Chaos"}
          </Button>

          {chaosResult && (
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="text-sm font-medium text-foreground mb-3">
                Modified Result
              </div>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <div className="text-xs text-muted-foreground">Score</div>
                  <div className="text-lg font-semibold text-foreground">
                    {chaosResult.score}
                  </div>
                  <div className={`text-xs font-medium ${getGradeColor(chaosResult.grade)}`}>
                    {chaosResult.grade}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Expected Position</div>
                  <div className="text-lg font-semibold text-foreground">
                    P{chaosResult.simulation_summary.expected_position}
                  </div>
                </div>
              </div>
              <div className="mb-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                  <span>Risk Score</span>
                  <span>{(chaosResult.simulation_summary.risk_score * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${getRiskBarColor(
                      chaosResult.simulation_summary.risk_score
                    )}`}
                    style={{ width: `${chaosResult.simulation_summary.risk_score * 100}%` }}
                  />
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {chaosResult.explanation}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
