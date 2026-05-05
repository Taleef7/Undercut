import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getScenarios, type ScenarioSummary } from "../api/client";
import { Loader2, Flag, Terminal, Calendar, ArrowLeft, ChevronDown } from "lucide-react";

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
  const [expandedRace, setExpandedRace] = useState<string | null>(null);

  useEffect(() => {
    getScenarios()
      .then((data) => {
        setScenarios(data);
        setLoading(false);
        // Auto-expand the first race if there's only one
        const groups = data.reduce<Record<string, ScenarioSummary[]>>((acc, s) => {
          const key = getRaceKey(s.decision_point_id);
          if (!acc[key]) acc[key] = [];
          acc[key].push(s);
          return acc;
        }, {});
        const raceKeys = Object.keys(groups).sort();
        if (raceKeys.length === 1) {
          setExpandedRace(raceKeys[0]);
        }
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

  const grouped = scenarios.reduce<Record<string, ScenarioSummary[]>>((acc, s) => {
    const key = getRaceKey(s.decision_point_id);
    if (!acc[key]) acc[key] = [];
    acc[key].push(s);
    return acc;
  }, {});

  const sortedRaces = Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 scanlines pointer-events-none" />

      <div className="relative px-6 py-12 max-w-5xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-papaya transition-colors font-mono px-3 py-1.5 border border-border hover:border-papaya/30 mb-8"
        >
          <ArrowLeft size={14} />
          <span>Back to Home</span>
        </button>

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
          <div className="space-y-6">
            {sortedRaces.map(([raceKey, raceScenarios]) => {
              const sorted = raceScenarios.sort((a, b) => a.lap_number - b.lap_number);
              const isExpanded = expandedRace === raceKey;

              return (
                <div key={raceKey} className="border border-border bg-card">
                  {/* Race Header — Click to expand */}
                  <button
                    data-testid="race-group-header"
                    onClick={() => setExpandedRace(isExpanded ? null : raceKey)}
                    className="w-full flex items-center justify-between px-5 py-4 hover:bg-secondary/30 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      <Calendar size={16} className="text-papaya shrink-0" />
                      <h2 className="text-base font-heading text-foreground">
                        {formatRaceName(raceKey)}
                      </h2>
                      <span className="text-xs font-mono text-muted-foreground">
                        {sorted.length} scenario{sorted.length !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <ChevronDown
                      size={16}
                      className={`text-muted-foreground transition-transform shrink-0 ${isExpanded ? "rotate-180" : ""}`}
                    />
                  </button>

                  {/* Expanded Scenario List */}
                  {isExpanded && (
                    <div className="border-t border-border px-5 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {sorted.map((scenario) => (
                          <div
                            key={scenario.decision_point_id}
                            data-testid="scenario-card"
                            className="bg-secondary/20 border border-border p-4 hover:border-papaya/30 transition-all cursor-pointer group"
                            onClick={() => navigate(`/scenario/${scenario.decision_point_id}`)}
                          >
                            <div className="flex items-start justify-between gap-3 mb-2">
                              <h3 className="text-sm font-heading group-hover:text-papaya transition-colors leading-tight">
                                {scenario.scenario_title}
                              </h3>
                              {scenario.difficulty_level && (
                                <span className={`text-[10px] font-mono uppercase shrink-0 ${DIFFICULTY_COLORS[scenario.difficulty_level] ?? "text-muted-foreground"}`}>
                                  {scenario.difficulty_level}
                                </span>
                              )}
                            </div>

                            <p className="text-xs text-muted-foreground leading-relaxed mb-3 font-sans line-clamp-2">
                              {scenario.scenario_description}
                            </p>

                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-foreground bg-secondary px-1.5 py-0.5 border border-border">
                                  Lap {scenario.lap_number}
                                </span>
                                <span className="text-xs font-mono text-muted-foreground capitalize">
                                  {scenario.decision_type.replace(/_/g, " ")}
                                </span>
                              </div>
                              <span className="text-xs font-mono text-muted-foreground">
                                {scenario.driver_id}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
