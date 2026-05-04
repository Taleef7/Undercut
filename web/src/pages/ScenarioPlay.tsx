import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  getScenario,
  submitDecision,
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
} from "lucide-react";

const ACTION_LABELS: Record<string, string> = {
  pit_now_inter: "Pit for Inters",
  pit_now_hard: "Pit for Hards",
  stay_out: "Stay Out",
  extend_stint: "Extend Stint",
};

const COMPOUND_COLORS: Record<string, string> = {
  soft: "bg-red-500",
  medium: "bg-yellow-500",
  hard: "bg-gray-400",
  intermediate: "bg-green-500",
  wet: "bg-blue-500",
};

const DEFAULT_TRACK_STATUS = "green";

const TRACK_STATUS_VARIANTS: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  green: "default",
  yellow: "secondary",
  safety_car: "destructive",
  vsc: "destructive",
  red_flag: "destructive",
};

export default function ScenarioPlay() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const disabledAction = (location.state as { disabledAction?: string } | null)
    ?.disabledAction;

  useEffect(() => {
    if (!id) return;
    getScenario(id)
      .then((data) => {
        setScenario(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load scenario");
        setLoading(false);
      });
  }, [id]);

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
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  if (!scenario) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
        <div className="text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 max-w-md text-center">
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
  const cliffWarning =
    rs.stint_age_laps > 25 ? "text-destructive" : rs.stint_age_laps > 20 ? "text-risky" : "";

  return (
    <div className="min-h-screen bg-background text-foreground px-6 py-8">
      <div className="max-w-3xl mx-auto text-left">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-sm text-muted-foreground mb-1">
              Brazil 2024 · Race
            </div>
            <h1 className="text-2xl font-bold text-foreground">
              Lap {scenario.lap_number} of {totalLaps}
            </h1>
          </div>
          <Badge
            variant={TRACK_STATUS_VARIANTS[rs.track_status] ?? "outline"}
            className="text-xs uppercase tracking-wider"
          >
            {rs.track_status.replace(/_/g, " ")}
          </Badge>
        </div>

        {/* Driver + Position */}
        <div className="bg-card border border-border rounded-xl p-5 mb-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-muted-foreground mb-1">Driver</div>
              <div className="text-3xl font-bold text-foreground tracking-tight">
                {scenario.driver_id}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground mb-1">Position</div>
              <div className="text-5xl font-bold text-primary leading-none">
                P{rs.current_position}
              </div>
            </div>
          </div>
        </div>

        {/* Gaps */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <ChevronUp size={16} className="text-strong" />
              Gap Ahead
            </div>
            <div className="text-xl font-semibold text-foreground">
              {rs.gap_ahead_seconds !== null
                ? `+${rs.gap_ahead_seconds.toFixed(1)}s`
                : "—"}
            </div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <ChevronDown size={16} className="text-destructive" />
              Gap Behind
            </div>
            <div className="text-xl font-semibold text-foreground">
              {rs.gap_behind_seconds !== null
                ? `+${rs.gap_behind_seconds.toFixed(1)}s`
                : "—"}
            </div>
          </div>
        </div>

        {/* Tire + Weather */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-2">Tire Strategy</div>
            <div className="flex items-center gap-3">
              <div
                className={`w-4 h-4 rounded-full ${compoundColor} ring-2 ring-white/10`}
              />
              <div className="text-base font-semibold capitalize text-foreground">
                {rs.compound}
              </div>
              <div className={`text-sm font-medium ${cliffWarning}`}>
                {rs.stint_age_laps} laps old
                {rs.stint_age_laps > 25 && " · CLIFF"}
                {rs.stint_age_laps > 20 && rs.stint_age_laps <= 25 && " · Warning"}
              </div>
            </div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-2">Conditions</div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm text-foreground">
                <Thermometer size={16} className="text-muted-foreground" />
                Track {rs.track_temperature_c}°C
              </div>
              <div className="flex items-center gap-1.5 text-sm text-foreground">
                {rs.rainfall ? (
                  <CloudRain size={16} className="text-blue-400" />
                ) : (
                  <Sun size={16} className="text-yellow-400" />
                )}
                {rs.rainfall ? "Rain" : "Dry"}
              </div>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="mb-5">
          <div className="text-sm text-muted-foreground mb-2">Stint Timeline</div>
          <StintTimeline
            totalLaps={totalLaps}
            currentLap={scenario.lap_number}
            compound={rs.compound}
            stintAge={rs.stint_age_laps}
          />
        </div>

        {/* Radio Quote */}
        <div className="bg-secondary/30 border border-border rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <Radio size={18} className="text-primary mt-0.5 shrink-0" />
            <p className="text-sm text-foreground leading-relaxed italic">
              {scenario.scenario_description}
            </p>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-4 text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">Your Call</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {scenario.available_actions.map((action) => {
              const isDisabled = action === disabledAction;
              return (
                <Button
                  key={action}
                  variant={isDisabled ? "outline" : "default"}
                  size="lg"
                  disabled={isDisabled || submitting}
                  className={`w-full justify-center text-sm font-semibold ${
                    isDisabled ? "opacity-40 cursor-not-allowed" : ""
                  }`}
                  onClick={() => handleAction(action)}
                >
                  {submitting && !isDisabled ? (
                    <Loader2 className="animate-spin mr-2" size={16} />
                  ) : null}
                  {ACTION_LABELS[action] ?? action}
                </Button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
