import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import type { ScenarioDetail, DecisionResponse, ChaosModifier } from "../api/client";
import { submitChaosDecision } from "../api/client";
import {
  RotateCcw, ArrowRight, Sparkles, Terminal, Activity, Zap, ArrowLeft,
  Info, ChevronDown, ChevronUp, Brain, Flag,
} from "lucide-react";
import { getActionLabel } from "../lib/actionLabels";

const GRADE_COLORS: Record<string, string> = {
  Masterful: "text-gold", "Strong call": "text-strong",
  "Inspired call": "text-inspired", Risky: "text-risky",
  "Poor call": "text-poor", "Off the wall": "text-offwall",
};

const RISK_LABELS: Record<string, { label: string; desc: string }> = {
  low: { label: "Low Risk", desc: "Safe, high-probability outcome" },
  medium: { label: "Medium Risk", desc: "Reasonable, some uncertainty" },
  high: { label: "High Risk", desc: "Gamble — could go either way" },
};

const SCORE_BANDS = [
  { min: 90, grade: "Masterful", desc: "Matched the optimal call. Textbook." },
  { min: 75, grade: "Strong call", desc: "Solid reasoning, simulation confirms it." },
  { min: 60, grade: "Inspired call", desc: "Different from real life but simulation shows a gain." },
  { min: 40, grade: "Risky", desc: "Could work in some conditions, but uncertain." },
  { min: 0, grade: "Poor call", desc: "Cost track position or ignored key signals." },
];

function getGradeInfo(score: number): { grade: string; desc: string } {
  for (const b of SCORE_BANDS) {
    if (score >= b.min) return { grade: b.grade, desc: b.desc };
  }
  return SCORE_BANDS[SCORE_BANDS.length - 1];
}

function getRiskBarColor(score: number): string {
  if (score < 0.3) return "bg-strong";
  if (score < 0.6) return "bg-risky";
  return "bg-poor";
}

function getGradeColor(grade: string): string {
  return GRADE_COLORS[grade] ?? "text-muted-foreground";
}

interface ModifierConfig {
  key: string; label: string; defaultValue?: number;
}

const MODIFIERS: ModifierConfig[] = [
  { key: "safety_car", label: "Safety Car" },
  { key: "vsc", label: "Virtual Safety Car" },
  { key: "rain_starts", label: "Rain Starts" },
  { key: "tire_cliff_now", label: "Tire Cliff (+8 laps)" },
  { key: "slow_pit_stop", label: "Slow Pit Stop (+3s)", defaultValue: 3 },
  { key: "rival_pits_this_lap", label: "Rival Pits This Lap" },
  { key: "red_flag", label: "Red Flag" },
];

export default function DecisionResult() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { scenario?: ScenarioDetail; response?: DecisionResponse } | null;

  const [activeModifiers, setActiveModifiers] = useState<Record<string, boolean>>({});
  const [chaosResult, setChaosResult] = useState<DecisionResponse | null>(null);
  const [chaosLoading, setChaosLoading] = useState(false);
  const [chaosError, setChaosError] = useState<string | null>(null);
  const [showScoreInfo, setShowScoreInfo] = useState(false);
  const [modelTooltip, setModelTooltip] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  if (!state?.scenario || !state?.response) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <Terminal size={32} className="text-muted-foreground mx-auto mb-4" />
          <h2 className="text-xl font-heading mb-2">No result to show</h2>
          <p className="text-muted-foreground mb-4 font-sans">Play a scenario first to see your result.</p>
          <Button onClick={() => navigate("/")} className="bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide">
            Browse Scenarios
          </Button>
        </div>
      </div>
    );
  }

  const { scenario, response } = state;
  const sim = response.simulation_summary;
  const gradeInfo = getGradeInfo(response.score);
  const riskInfo = RISK_LABELS[sim.risk_score < 0.3 ? "low" : sim.risk_score < 0.6 ? "medium" : "high"];

  // Chaos: auto-submit when toggles change (debounced)
  useEffect(() => {
    const selected = MODIFIERS.filter((m) => activeModifiers[m.key]);
    if (selected.length === 0) {
      setChaosResult(null);
      setChaosError(null);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setChaosLoading(true);
      setChaosError(null);
      try {
        const modifiers: ChaosModifier[] = selected.map((m) => ({
          modifier_type: m.key,
          modifier_value: m.defaultValue,
        }));
        const result = await submitChaosDecision(scenario.decision_point_id, response.user_action, modifiers);
        setChaosResult(result);
      } catch (err) {
        setChaosError(err instanceof Error ? err.message : "Chaos simulation failed");
      } finally {
        setChaosLoading(false);
      }
    }, 600);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [activeModifiers]);

  const toggleModifier = (key: string) => {
    setActiveModifiers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 scanlines pointer-events-none" />

      <div className="relative px-6 py-8 max-w-3xl mx-auto">
        {/* Back */}
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
            {/* SCORE — prominent with info toggle */}
            <div className="text-center mb-6 py-6 border-b border-border">
              <div className="flex items-center justify-center gap-2 mb-2">
                <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Your Score</span>
                <button
                  onClick={() => setShowScoreInfo(!showScoreInfo)}
                  className="text-muted-foreground hover:text-papaya transition-colors"
                  aria-label="How scoring works"
                >
                  <Info size={13} />
                </button>
              </div>
              <div className="text-8xl font-heading text-foreground tracking-tight">
                {response.score}
              </div>
              <div className={`text-xl font-heading mt-2 uppercase tracking-wide ${getGradeColor(response.grade)}`}>
                {response.grade}
              </div>
              {showScoreInfo && (
                <div className="mt-4 mx-auto max-w-md text-xs text-muted-foreground font-mono bg-secondary/50 border border-border p-3 text-left space-y-1">
                  {SCORE_BANDS.map((b) => (
                    <div key={b.grade} className={`flex items-start gap-2 ${response.grade === b.grade ? "text-papaya" : ""}`}>
                      <span className="mt-1 w-1.5 h-1.5 shrink-0 rounded-full bg-current" />
                      <span><strong>{b.grade}</strong> ({b.min}–{b.min === 90 ? "100" : b.min + 24}) — {b.desc}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t border-border mt-2">
                    Scores combine how your call compares to the historical decision, the simulation outcome, and the model recommendation.
                  </div>
                </div>
              )}
            </div>

            {/* THREE-WAY COMPARISON ROW */}
            <div className="bg-secondary/30 border border-border p-4 mb-5">
              <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mb-3 text-center">
                Decision Comparison
              </div>
              <div className="grid grid-cols-3 gap-3">
                {/* Your Call */}
                <div className="text-center p-3 bg-secondary/50 border border-border">
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">You</div>
                  <div className="text-sm font-heading text-foreground uppercase tracking-wide">
                    {getActionLabel(response.user_action)}
                  </div>
                  {response.user_action === response.historical_decision && (
                    <div className="text-[10px] font-mono text-strong mt-1">✓ Matched real team</div>
                  )}
                </div>

                {/* Real Team */}
                <div className="text-center p-3 bg-secondary/50 border border-border">
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Real Team</div>
                  <div className="text-sm font-heading text-foreground uppercase tracking-wide">
                    {getActionLabel(response.historical_decision)}
                  </div>
                  {scenario.actual_outcome_summary && (
                    <div className="text-[10px] font-mono text-muted-foreground mt-1 leading-tight">
                      {scenario.actual_outcome_summary}
                    </div>
                  )}
                </div>

                {/* Model */}
                <div
                  className="text-center p-3 bg-secondary/50 border border-border relative cursor-default"
                  onMouseEnter={() => setModelTooltip(true)}
                  onMouseLeave={() => setModelTooltip(false)}
                >
                  <div className="flex items-center justify-center gap-1">
                    <Brain size={11} className="text-papaya" />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">AI Model</span>
                  </div>
                  <div className="text-sm font-heading text-papaya uppercase tracking-wide">
                    {getActionLabel(response.model_recommendation)}
                  </div>
                  {response.model_confidence != null && (
                    <div className="text-[10px] font-mono text-muted-foreground mt-1">
                      {(response.model_confidence * 100).toFixed(0)}% confident
                    </div>
                  )}
                  {modelTooltip && response.model_top_features?.length > 0 && (
                    <div className="absolute z-20 left-1/2 -translate-x-1/2 top-full mt-2 w-56 bg-card border border-border shadow-lg p-3 text-left">
                      <div className="text-[10px] font-mono text-muted-foreground uppercase mb-2">Key Factors</div>
                      {response.model_top_features.map((f, i) => (
                        <div key={i} className="flex items-start gap-2 text-[11px] text-foreground font-sans mb-1.5 last:mb-0">
                          <span className="text-papaya shrink-0 mt-0.5">{i + 1}.</span>
                          {f}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* SIMULATION SUMMARY — clarified */}
            <div className="bg-secondary/30 border border-border p-4 mb-5">
              <div className="flex items-center gap-2 mb-4">
                <Flag size={14} className="text-papaya" />
                <span className="text-sm font-heading uppercase tracking-wider">Projected Outcome</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Your Projected Finish</div>
                  <div className="text-2xl font-heading text-foreground">
                    P{sim.expected_position}
                  </div>
                  <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
                    Predicted final position with your call
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Actual Race Finish</div>
                  <div className="text-2xl font-heading text-muted-foreground">
                    {scenario.actual_outcome_summary ? (
                      scenario.actual_outcome_summary.split(",")[0] || "DNF"
                    ) : "—"}
                  </div>
                  <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
                    What happened historically (real team call)
                  </div>
                </div>
              </div>

              <div className="border-t border-border pt-4">
                <div className="flex items-center justify-between text-xs font-mono text-muted-foreground uppercase mb-2">
                  <span className="flex items-center gap-1.5">
                    <Activity size={11} />
                    Risk Assessment
                  </span>
                  <span className={getGradeColor(response.grade)}>
                    {riskInfo.label}
                  </span>
                </div>
                <div className="w-full h-1.5 bg-secondary border border-border overflow-hidden">
                  <div
                    className={`h-full transition-all ${getRiskBarColor(sim.risk_score)}`}
                    style={{ width: `${sim.risk_score * 100}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground mt-1.5">
                  <span>Conservative</span>
                  <span>{riskInfo.desc}</span>
                  <span>Risky</span>
                </div>

                {/* Tire + Track risk in a single line with icons */}
                <div className="flex gap-4 mt-3 pt-3 border-t border-border">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground">Tire Risk:</span>
                    <span className={`text-[11px] font-mono ${sim.tire_risk === "high" ? "text-poor" : sim.tire_risk === "medium" ? "text-risky" : "text-strong"}`}>
                      {sim.tire_risk}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono uppercase text-muted-foreground">Track Position Risk:</span>
                    <span className={`text-[11px] font-mono ${sim.track_position_risk === "high" ? "text-poor" : sim.track_position_risk === "medium" ? "text-risky" : "text-strong"}`}>
                      {sim.track_position_risk}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* ANALYSIS */}
            <div className="mb-6">
              <div className="text-sm font-heading uppercase tracking-wider mb-3">Analysis</div>
              <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                {response.explanation}
              </p>
            </div>

            {/* Tradeoffs — shown with clearer context */}
            {response.tradeoffs.length > 0 && (
              <div className="mb-6">
                <div className="text-sm font-heading uppercase tracking-wider mb-3">Key Tradeoffs</div>
                <ul className="space-y-2">
                  {response.tradeoffs.map((t, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-foreground font-sans">
                      <span className="mt-2 w-1 h-1 bg-papaya shrink-0" />
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 mb-6">
              <Button
                variant="outline"
                className="flex-1 border-border hover:border-papaya/50 font-heading uppercase tracking-wide"
                onClick={() => navigate(`/scenario/${scenario.decision_point_id}`, {
                  state: { disabledAction: response.user_action },
                })}
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

        {/* CHAOS ENGINE — auto-submits on toggle */}
        <div className="bg-card border border-border glow-border">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-risky" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">chaos_engine.exe</span>
            </div>
            <span className="text-xs font-mono text-risky">LIVE</span>
          </div>

          <div className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={16} className="text-papaya" />
              <h2 className="text-lg font-heading">What if...?</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-4 font-sans">
              Toggle modifiers below. The analysis updates automatically.
            </p>

            <div className="bg-secondary/30 border border-border p-4 mb-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {MODIFIERS.map((m) => (
                  <div key={m.key} className="flex items-center justify-between gap-3">
                    <span className="text-sm text-foreground font-mono">{m.label}</span>
                    <Switch data-testid="chaos-toggle" checked={!!activeModifiers[m.key]} onCheckedChange={() => toggleModifier(m.key)} />
                  </div>
                ))}
              </div>
            </div>

            {chaosLoading && (
              <div className="text-xs font-mono text-muted-foreground mb-4 animate-pulse">
                Recalculating...
              </div>
            )}

            {chaosError && (
              <div className="text-poor bg-poor/10 border border-poor/20 px-4 py-3 text-sm mb-4 font-mono">
                {chaosError}
              </div>
            )}

            {chaosResult && !chaosLoading && (
              <div className="bg-secondary/30 border border-border p-4">
                <div className="text-sm font-heading uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Zap size={14} className="text-risky" />
                  Modified Outcome
                </div>
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="text-center">
                    <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Score</div>
                    <div className="text-xl font-heading text-foreground">{chaosResult.score}</div>
                    <div className={`text-[10px] font-mono uppercase ${getGradeColor(chaosResult.grade)}`}>
                      {chaosResult.grade}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Position</div>
                    <div className="text-xl font-heading text-foreground">
                      P{chaosResult.simulation_summary.expected_position}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] font-mono text-muted-foreground uppercase mb-1">Risk</div>
                    <div className="text-xl font-heading text-foreground">
                      {(chaosResult.simulation_summary.risk_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed font-sans">
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
