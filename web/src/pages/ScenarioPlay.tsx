import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import {
  getScenario,
  getScenarios,
  submitDecision,
  type ScenarioSummary,
  type ScenarioDetail,
  type DecisionResponse,
} from "../api/client";
import StintTimeline from "../components/StintTimeline";
import {
  ChevronUp,
  ChevronDown,
  CloudRain,
  Sun,
  Thermometer,
  Radio,
  Loader2,
  Terminal,
  ArrowLeft,
  Activity,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { getActionLabel } from "../lib/actionLabels";

const COMPOUND_COLORS: Record<string, string> = {
  soft: "bg-red-500",
  medium: "bg-yellow-500",
  hard: "bg-gray-400",
  intermediate: "bg-green-500",
  wet: "bg-blue-500",
};

const COMPOUND_GLOWS: Record<string, string> = {
  soft: "shadow-[0_0_8px_rgba(239,68,68,0.4)]",
  medium: "shadow-[0_0_8px_rgba(234,179,8,0.4)]",
  hard: "shadow-[0_0_8px_rgba(156,163,175,0.4)]",
  intermediate: "shadow-[0_0_8px_rgba(34,197,94,0.4)]",
  wet: "shadow-[0_0_8px_rgba(59,130,246,0.4)]",
};

const DEFAULT_TRACK_STATUS = "green";

const TRACK_STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  green: { bg: "bg-strong/10", text: "text-strong", border: "border-strong/30" },
  yellow: { bg: "bg-risky/10", text: "text-risky", border: "border-risky/30" },
  safety_car: { bg: "bg-poor/10", text: "text-poor", border: "border-poor/30" },
  vsc: { bg: "bg-poor/10", text: "text-poor", border: "border-poor/30" },
  red_flag: { bg: "bg-poor/20", text: "text-poor", border: "border-poor/50" },
};

export default function ScenarioPlay() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [allScenarios, setAllScenarios] = useState<ScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const disabledAction = (location.state as { disabledAction?: string } | null)
    ?.disabledAction;

  // Parse race key from scenario ID (e.g., "brazil_2024_lap32" -> "brazil_2024")
  function getRaceKey(sid: string): string {
    const match = sid.match(/^(.+)_lap\d+$/);
    return match ? match[1] : sid;
  }

  useEffect(() => {
    if (!id) return;
    // Load current scenario and all scenarios for prev/next navigation
    Promise.all([getScenario(id), getScenarios()])
      .then(([scenarioData, scenariosData]) => {
        setScenario(scenarioData);
        setAllScenarios(scenariosData);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load scenario");
        setLoading(false);
      });
  }, [id]);

  const raceKey = scenario ? getRaceKey(scenario.decision_point_id) : "";
  const raceScenarios = allScenarios
    .filter((s) => getRaceKey(s.decision_point_id) === raceKey)
    .sort((a, b) => a.lap_number - b.lap_number);
  const currentRaceIndex = raceScenarios.findIndex(
    (s) => s.decision_point_id === scenario?.decision_point_id
  );
  const hasPrev = currentRaceIndex > 0;
  const hasNext = currentRaceIndex >= 0 && currentRaceIndex < raceScenarios.length - 1;

  const handleAction = async (action: string) => {
    if (!id) return;
    setError(null);
    setSubmitting(true);
    try {
      const response: DecisionResponse = await submitDecision(id, action);
      navigate("/result", { state: { scenario, response } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit decision");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="animate-spin text-papaya" size={24} />
          <span className="text-sm font-mono text-muted-foreground">Loading telemetry...</span>
        </div>
      </div>
    );
  }

  if (!scenario) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
        <div className="text-poor bg-poor/10 border border-poor/20 px-4 py-3 max-w-md text-center font-mono text-sm">
          {error || "Scenario not found"}
        </div>
      </div>
    );
  }

  const rs = {
    current_position: scenario.current_position,
    gap_ahead_seconds: scenario.gap_ahead_seconds,
    gap_behind_seconds: scenario.gap_behind_seconds,
    compound: scenario.compound,
    laps_remaining: scenario.laps_remaining,
    stint_age_laps: scenario.stint_age_laps,
    track_status: scenario.track_status ?? DEFAULT_TRACK_STATUS,
    track_temperature_c: scenario.track_temperature_c,
    rainfall: scenario.rainfall,
  };
  const totalLaps = scenario.lap_number + rs.laps_remaining;
  const compoundColor = COMPOUND_COLORS[rs.compound.toLowerCase()] ?? "bg-gray-500";
  const compoundGlow = COMPOUND_GLOWS[rs.compound.toLowerCase()] ?? "";
  const trackStatusStyle = TRACK_STATUS_STYLES[rs.track_status] ?? TRACK_STATUS_STYLES.green;
  const cliffWarning =
    rs.stint_age_laps > 25 ? "text-poor" : rs.stint_age_laps > 20 ? "text-risky" : "";

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 scanlines pointer-events-none" />

      <div className="relative px-6 py-8 max-w-4xl mx-auto">
        {/* Header nav */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate("/scenarios")}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-papaya transition-colors font-mono px-3 py-1.5 border border-border hover:border-papaya/30"
          >
            <ArrowLeft size={14} />
            <span>Back to Scenarios</span>
          </button>
          <div className="flex items-center gap-2">
            {hasPrev && (
              <button
                onClick={() =>
                  navigate(`/scenario/${raceScenarios[currentRaceIndex - 1].decision_point_id}`)
                }
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-papaya transition-colors font-mono px-3 py-1.5 border border-border hover:border-papaya/30"
              >
                <ChevronLeft size={12} />
                Prev
              </button>
            )}
            {raceScenarios.length > 0 && (
              <span className="text-xs font-mono text-muted-foreground px-2">
                {currentRaceIndex + 1} / {raceScenarios.length}
              </span>
            )}
            {hasNext && (
              <button
                onClick={() =>
                  navigate(`/scenario/${raceScenarios[currentRaceIndex + 1].decision_point_id}`)
                }
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-papaya transition-colors font-mono px-3 py-1.5 border border-border hover:border-papaya/30"
              >
                Next
                <ChevronRight size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Terminal chrome header */}
        <div className="bg-card border border-border glow-border mb-6">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Terminal size={14} className="text-muted-foreground" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                race_live_telemetry.exe
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-strong animate-pulse" />
              <span className="text-xs font-mono text-strong">LIVE</span>
            </div>
          </div>

          <div className="p-5">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase tracking-wider">
                  Brazil 2024 · Race
                </div>
                <h1 className="text-2xl font-heading">
                  Lap {scenario.lap_number} of {totalLaps}
                </h1>
              </div>
              <div className={`px-3 py-1 ${trackStatusStyle.bg} border ${trackStatusStyle.border}`}>
                <span className={`text-xs font-mono uppercase tracking-wider ${trackStatusStyle.text}`}>
                  {rs.track_status.replace(/_/g, " ")}
                </span>
              </div>
            </div>

            {/* Driver + Position */}
            <div className="grid grid-cols-2 gap-4 mb-5">
              <div className="bg-secondary/50 border border-border p-4">
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">Driver</div>
                <div className="text-4xl font-heading text-foreground">
                  {scenario.driver_id}
                </div>
              </div>
              <div className="bg-secondary/50 border border-border p-4 text-right">
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">Position</div>
                <div className="text-6xl font-heading text-papaya leading-none">
                  P{rs.current_position}
                </div>
              </div>
            </div>

            {/* Gaps */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              <div className="bg-secondary/30 border border-border p-4">
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-1 uppercase">
                  <ChevronUp size={14} className="text-strong" />
                  Gap Ahead
                </div>
                <div className="text-xl font-mono text-foreground">
                  {rs.gap_ahead_seconds !== null
                    ? `+${rs.gap_ahead_seconds.toFixed(1)}s`
                    : "—"}
                </div>
              </div>
              <div className="bg-secondary/30 border border-border p-4">
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-1 uppercase">
                  <ChevronDown size={14} className="text-poor" />
                  Gap Behind
                </div>
                <div className="text-xl font-mono text-foreground">
                  {rs.gap_behind_seconds !== null
                    ? `+${rs.gap_behind_seconds.toFixed(1)}s`
                    : "—"}
                </div>
              </div>
            </div>

            {/* Tire + Weather */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
              <div className="bg-secondary/30 border border-border p-4">
                <div className="text-xs font-mono text-muted-foreground mb-2 uppercase">Tire Strategy</div>
                <div className="flex items-center gap-3">
                  <div
                    className={`w-4 h-4 ${compoundColor} ${compoundGlow}`}
                  />
                  <div className="text-base font-heading capitalize text-foreground">
                    {rs.compound}
                  </div>
                  <div className={`text-sm font-mono ${cliffWarning}`}>
                    {rs.stint_age_laps} laps old
                    {rs.stint_age_laps > 25 && " · CLIFF"}
                    {rs.stint_age_laps > 20 && rs.stint_age_laps <= 25 && " · WARNING"}
                  </div>
                </div>
              </div>
              <div className="bg-secondary/30 border border-border p-4">
                <div className="text-xs font-mono text-muted-foreground mb-2 uppercase">Conditions</div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1.5 text-sm text-foreground font-mono">
                    <Thermometer size={14} className="text-muted-foreground" />
                    Track {rs.track_temperature_c}°C
                  </div>
                  <div className="flex items-center gap-1.5 text-sm text-foreground font-mono">
                    {rs.rainfall ? (
                      <CloudRain size={14} className="text-blue-400" />
                    ) : (
                      <Sun size={14} className="text-yellow-400" />
                    )}
                    {rs.rainfall ? "Rain" : "Dry"}
                  </div>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="mb-5">
              <div className="text-xs font-mono text-muted-foreground mb-2 uppercase">Stint Timeline</div>
              <StintTimeline
                totalLaps={totalLaps}
                currentLap={scenario.lap_number}
                compound={rs.compound}
                stintAge={rs.stint_age_laps}
              />
            </div>

            {/* Radio Quote */}
            <div className="bg-secondary/30 border border-border p-4 mb-6">
              <div className="flex items-start gap-3">
                <Radio size={16} className="text-papaya mt-0.5 shrink-0" />
                <p className="text-sm text-foreground leading-relaxed italic font-sans">
                  {scenario.scenario_description}
                </p>
              </div>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="mb-4 text-poor bg-poor/10 border border-poor/20 px-4 py-3 text-sm font-mono">
                {error}
              </div>
            )}

            {/* Actions */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={14} className="text-papaya" />
                <span className="text-sm font-heading uppercase tracking-wider">Your Call</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {scenario.available_actions.map((action) => {
                  const isDisabled = action === disabledAction;
                  return (
                    <Button
                      key={action}
                      variant={isDisabled ? "outline" : "default"}
                      size="lg"
                      disabled={isDisabled || submitting}
                      className={`w-full justify-center text-sm font-heading uppercase tracking-wide ${
                        isDisabled
                          ? "opacity-40 cursor-not-allowed border-border"
                          : "bg-papaya text-background hover:bg-papaya/90"
                      }`}
                      onClick={() => handleAction(action)}
                    >
                      {submitting && !isDisabled ? (
                        <Loader2 className="animate-spin mr-2" size={16} />
                      ) : null}
                      {getActionLabel(action)}
                    </Button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
