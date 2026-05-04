import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getScenarios, type ScenarioSummary } from "../api/client";
import { Button } from "../components/ui/button";
import { Loader2, ChevronRight, Flag, Terminal, Calendar } from "lucide-react";
import { getActionLabel } from "../lib/actionLabels";

const DIFFICULTY_COLORS: Record<string, string> = {
  Easy: "text-strong",
  Medium: "text-risky",
  Hard: "text-poor",
};

// Parse race key from scenario ID, e.g. "brazil_2024_lap32" -> "brazil_2024"
function getRaceKey(id: string): string {
  const match = id.match(/^(.+)_lap\d+$/);
  return match ? match[1] : id;
}

// Format race key for display, e.g. "brazil_2024" -> "Brazil 2024"
function formatRaceName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ScenarioSelect() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getScenarios()
      .then((data) => {
        setScenarios(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load scenarios");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="animate-spin text-papaya" size={24} />
          <span className="text-sm font-mono text-muted-foreground">Loading scenarios...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-6">
        <div className="text-poor bg-poor/10 border border-poor/20 px-4 py-3 max-w-md text-center font-mono text-sm">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 scanlines pointer-events-none" />

      <div className="relative px-6 py-12 max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-3">
            <Flag size={16} className="text-papaya" />
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
              Scenario Select
            </span>
          </div>
          <h1 className="text-foreground mb-3">Choose Your Moment</h1>
          <p className="text-muted-foreground max-w-lg font-sans">
            Select a historical race decision point and take the reins from the pit wall.
          </p>
        </div>

        {/* Race Groups */}
        {scenarios.length === 0 ? (
          <div className="text-center py-20">
            <Terminal size={32} className="text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground font-mono text-sm">No scenarios loaded.</p>
            <p className="text-muted-foreground text-xs mt-2">Run the ingestion pipeline to populate decision points.</p>
          </div>
        ) : (
          <div className="space-y-10">
            {Object.entries(
              scenarios.reduce<Record<string, ScenarioSummary[]>>((acc, s) => {
                const key = getRaceKey(s.decision_point_id);
                if (!acc[key]) acc[key] = [];
                acc[key].push(s);
                return acc;
              }, {})
            )
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([raceKey, raceScenarios]) => {
                const sorted = raceScenarios.sort((a, b) => a.lap_number - b.lap_number);
                return (
                  <div key={raceKey}>
                    {/* Race Header */}
                    <div className="flex items-center gap-3 mb-4 pb-3 border-b border-border">
                      <Calendar size={16} className="text-papaya" />
                      <h2 className="text-lg font-heading text-foreground">
                        {formatRaceName(raceKey)}
                      </h2>
                      <span className="text-xs font-mono text-muted-foreground">
                        {sorted.length} scenario{sorted.length !== 1 ? "s" : ""}
                      </span>
                    </div>

                    {/* Scenario Grid for this race */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {sorted.map((scenario) => (
                        <div
                          key={scenario.decision_point_id}
                          className="bg-card border border-border p-5 hover:border-papaya/30 transition-all cursor-pointer group glow-border"
                          onClick={() => navigate(`/scenario/${scenario.decision_point_id}`)}
                        >
                          {/* Terminal chrome */}
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <Terminal size={12} className="text-muted-foreground" />
                              <span className="text-xs font-mono text-muted-foreground uppercase">
                                {scenario.decision_point_id}
                              </span>
                            </div>
                            {scenario.difficulty_level && (
                              <span className={`text-xs font-mono uppercase ${DIFFICULTY_COLORS[scenario.difficulty_level] ?? "text-muted-foreground"}`}>
                                {scenario.difficulty_level}
                              </span>
                            )}
                          </div>

                          <h3 className="text-lg font-heading mb-2 group-hover:text-papaya transition-colors">
                            {scenario.scenario_title}
                          </h3>

                          <p className="text-sm text-muted-foreground leading-relaxed mb-4 font-sans line-clamp-2">
                            {scenario.scenario_description}
                          </p>

                          <div className="flex items-center gap-2 mb-4 flex-wrap">
                            <div className="px-2 py-0.5 bg-secondary border border-border">
                              <span className="text-xs font-mono text-foreground">
                                Lap {scenario.lap_number}
                              </span>
                            </div>
                            <div className="px-2 py-0.5 bg-secondary border border-border">
                              <span className="text-xs font-mono text-foreground capitalize">
                                {scenario.decision_type.replace(/_/g, " ")}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap">
                            {scenario.available_actions.map((action) => (
                              <span
                                key={action}
                                className="text-xs font-mono px-2 py-1 bg-secondary/50 border border-border text-muted-foreground"
                              >
                                {getActionLabel(action)}
                              </span>
                            ))}
                          </div>

                          <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                            <span className="text-xs font-mono text-muted-foreground">
                              Driver: {scenario.driver_id}
                            </span>
                            <ChevronRight size={14} className="text-muted-foreground group-hover:text-papaya transition-colors" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
}
