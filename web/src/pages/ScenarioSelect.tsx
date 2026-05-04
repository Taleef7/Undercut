import { useNavigate } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useEffect, useState } from "react";
import { getScenarios, type ScenarioSummary } from "@/api/client";

const SESSION_LABELS: Record<string, string> = {
  R: "Race",
  Q: "Qualifying",
  S: "Sprint",
  SQ: "Sprint Shootout",
  FP1: "Free Practice 1",
  FP2: "Free Practice 2",
  FP3: "Free Practice 3",
};

function parseCircuitName(id: string): string {
  const parts = id.split("_");
  if (parts.length >= 2) {
    const city = parts[0];
    const year = parts[1];
    return `${city.charAt(0).toUpperCase() + city.slice(1)} ${year}`;
  }
  return id;
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

  return (
    <div className="min-h-screen bg-background text-foreground px-6 py-8">
      <div className="max-w-6xl mx-auto text-left">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-2">
            Strategy Scenarios
          </h1>
          <p className="text-muted-foreground text-base">
            Choose a race moment and make the call from the pit wall.
          </p>
        </div>

        {loading && (
          <div className="text-muted-foreground">Loading scenarios...</div>
        )}

        {error && (
          <div className="text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {scenarios.map((s) => (
              <Card
                key={s.id}
                className="bg-card border-border hover:border-primary/50 hover:shadow-md transition-all cursor-pointer text-left"
                onClick={() => navigate(`/scenario/${s.id}`)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base font-semibold leading-snug text-foreground">
                      {s.scenario_title}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      className="shrink-0 text-xs border-border text-muted-foreground"
                    >
                      {SESSION_LABELS[s.session_id] ?? s.session_id}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs text-muted-foreground mt-1">
                    {parseCircuitName(s.id)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center gap-3 text-sm">
                    <div className="flex items-center gap-1.5">
                      <span className="text-muted-foreground">Driver</span>
                      <span className="font-semibold text-foreground">
                        {s.driver_id}
                      </span>
                    </div>
                    <div className="w-px h-3 bg-border" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-muted-foreground">Lap</span>
                      <span className="font-semibold text-foreground">
                        {s.lap_number}
                      </span>
                    </div>
                    <div className="w-px h-3 bg-border" />
                    <div className="flex items-center gap-1.5">
                      <span className="text-muted-foreground">Type</span>
                      <span className="font-semibold text-foreground capitalize">
                        {s.decision_type.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
