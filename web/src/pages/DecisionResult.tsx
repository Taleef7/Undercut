import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import type { ScenarioDetail, DecisionResponse, ChaosModifier } from "../api/client";
import { submitChaosDecision } from "../api/client";
import { RotateCcw, ArrowRight, Sparkles, Terminal, Activity, Zap, ArrowLeft } from "lucide-react";
import { getActionLabel } from "../lib/actionLabels";

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
          <Terminal size={32} className="text-muted-foreground mx-auto mb-4" />
          <h2 className="text-xl font-heading mb-2">
            No result to show
          </h2>
          <p className="text-muted-foreground mb-4 font-sans">
            Play a scenario first to see your result.
          </p>
          <Button onClick={() => navigate("/")} className="bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide">
            Browse Scenarios
          </Button>
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
    <div className="min-h-screen bg-background text-foreground relative">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 scanlines pointer-events-none" />

      <div className="relative px-6 py-8 max-w-3xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate(`/scenario/${scenario.decision_point_id}`)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-papaya transition-colors font-mono px-3 py-1.5 border border-border hover:border-papaya/30 mb-6"
        >
          <ArrowLeft size={14} />
          <span>Back to Scenario</span>
        </button>

        {/* Terminal chrome */}
        <div className="bg-card border border-border glow-border mb-6">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Terminal size={14} className="text-muted-foreground" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                strategy_analysis.exe
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Activity size={12} className="text-papaya" />
              <span className="text-xs font-mono text-papaya">ANALYSIS COMPLETE</span>
            </div>
          </div>

          <div className="p-5">
            {/* Score */}
            <div className="text-center mb-8 py-6 border-b border-border">
              <div className="text-xs font-mono text-muted-foreground mb-2 uppercase tracking-widest">Your Score</div>
              <div className="text-8xl font-heading text-foreground tracking-tight">
                {response.score}
              </div>
              <div
                className={`text-xl font-heading mt-2 uppercase tracking-wide ${getGradeColor(response.grade)}`}
              >
                {response.grade}
              </div>
            </div>

            {/* Comparison */}
            <div className="bg-secondary/30 border border-border p-4 mb-5">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">Your Call</div>
                  <span className="font-heading text-foreground uppercase tracking-wide">
                    {getActionLabel(response.user_action)}
                  </span>
                </div>
                <div>
                  <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">Real Team</div>
                  <span className="font-heading text-foreground uppercase tracking-wide">
                    {getActionLabel(response.historical_decision)}
                  </span>
                </div>
              </div>
            </div>

            {/* Model rec */}
            <div className="flex items-center gap-3 mb-5">
              <div className="px-2 py-1 bg-secondary border border-border">
                <span className="text-xs font-mono text-muted-foreground">
                  MODEL: {getActionLabel(response.model_recommendation).toUpperCase()}
                </span>
              </div>
              {response.model_confidence != null && (
                <span className="text-sm font-mono text-muted-foreground">
                  {(response.model_confidence * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>

            {/* Simulation Summary */}
            <div className="bg-secondary/30 border border-border p-4 mb-5">
              <div className="text-sm font-heading uppercase tracking-wider mb-4">
                Simulation Summary
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Expected Position</div>
                  <div className="text-2xl font-heading text-foreground">
                    P{sim.expected_position}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Finish Band</div>
                  <div className="text-2xl font-heading text-foreground">
                    {sim.expected_finish_position_band}
                  </div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground uppercase mb-2">
                  <span>Risk Score</span>
                  <span>{(sim.risk_score * 100).toFixed(0)}%</span>
                </div>
                <div className="w-full h-1.5 bg-secondary border border-border overflow-hidden">
                  <div
                    className={`h-full transition-all ${getRiskBarColor(
                      sim.risk_score
                    )}`}
                    style={{ width: `${sim.risk_score * 100}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground mt-2 uppercase">
                  <span>Tire: {sim.tire_risk}</span>
                  <span>Track: {sim.track_position_risk}</span>
                </div>
              </div>
            </div>

            {/* Tradeoffs */}
            <div className="mb-5">
              <div className="text-sm font-heading uppercase tracking-wider mb-3">Tradeoffs</div>
              <ul className="space-y-2">
                {response.tradeoffs.map((t, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 text-sm text-foreground font-sans"
                  >
                    <span className="mt-2 w-1 h-1 bg-papaya shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>

            {/* Explanation */}
            <div className="mb-8">
              <div className="text-sm font-heading uppercase tracking-wider mb-3">Analysis</div>
              <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                {response.explanation}
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 mb-10">
              <Button
                variant="outline"
                className="flex-1 border-border hover:border-papaya/50 font-heading uppercase tracking-wide"
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
                className="flex-1 bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide"
                onClick={() => navigate("/")}
              >
                <ArrowRight size={16} className="mr-2" />
                Play Another
              </Button>
            </div>
          </div>
        </div>

        {/* Chaos Engine */}
        <div className="bg-card border border-border glow-border">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-risky" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                chaos_engine.exe
              </span>
            </div>
            <span className="text-xs font-mono text-risky">EXPERIMENTAL</span>
          </div>

          <div className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-papaya" />
              <h2 className="text-lg font-heading">What if...?</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-4 font-sans">
              Toggle chaos modifiers to see how unexpected events would have changed the outcome of your decision.
            </p>

            <div className="bg-secondary/30 border border-border p-4 mb-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {MODIFIERS.map((m) => (
                  <div key={m.key} data-testid="chaos-toggle" className="flex items-center justify-between gap-3">
                    <span className="text-sm text-foreground font-mono">{m.label}</span>
                    <Switch
                      checked={!!activeModifiers[m.key]}
                      onCheckedChange={() => toggleModifier(m.key)}
                    />
                  </div>
                ))}
              </div>
            </div>

            {chaosError && (
              <div className="text-poor bg-poor/10 border border-poor/20 px-4 py-3 text-sm mb-4 font-mono">
                {chaosError}
              </div>
            )}

            <Button
              data-testid="chaos-simulate"
              onClick={handleSimulateChaos}
              disabled={chaosLoading}
              className="mb-6 bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide"
            >
              <Sparkles size={16} className="mr-2" />
              {chaosLoading ? "Simulating..." : "Simulate Chaos"}
            </Button>

            {chaosResult && (
              <div className="bg-secondary/30 border border-border p-4">
                <div className="text-sm font-heading uppercase tracking-wider mb-3">
                  Modified Result
                </div>
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Score</div>
                    <div className="text-2xl font-heading text-foreground">
                      {chaosResult.score}
                    </div>
                    <div className={`text-xs font-medium font-heading uppercase ${getGradeColor(chaosResult.grade)}`}>
                      {chaosResult.grade}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-mono text-muted-foreground uppercase mb-1">Expected Position</div>
                    <div className="text-2xl font-heading text-foreground">
                      P{chaosResult.simulation_summary.expected_position}
                    </div>
                  </div>
                </div>
                <div className="mb-3">
                  <div className="flex items-center justify-between text-xs font-mono text-muted-foreground uppercase mb-1">
                    <span>Risk Score</span>
                    <span>{(chaosResult.simulation_summary.risk_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-secondary border border-border overflow-hidden">
                    <div
                      className={`h-full transition-all ${getRiskBarColor(
                        chaosResult.simulation_summary.risk_score
                      )}`}
                      style={{ width: `${chaosResult.simulation_summary.risk_score * 100}%` }}
                    />
                  </div>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                  {chaosResult.explanation}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
