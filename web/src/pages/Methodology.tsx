import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function Methodology() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-background text-foreground px-6 py-8 flex flex-col">
      <div className="max-w-2xl mx-auto text-left flex-1">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-4">
            Methodology
          </h1>
          <p className="text-muted-foreground text-base mb-6">
            How Undercut works under the hood.
          </p>
        </div>

        <div className="space-y-6 mb-8">
          <section className="bg-card border border-border rounded-xl p-5">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Data Sources
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              We combine three primary data sources: <strong className="text-foreground">Jolpica</strong> for historical schedules, results, and standings; <strong className="text-foreground">OpenF1</strong> for modern session-level detail including stints, pit stops, weather, and race control events (2023+); and <strong className="text-foreground">FastF1</strong> for pre-2023 lap times and telemetry. When sources overlap, we apply a priority hierarchy: Jolpica for metadata, OpenF1 for modern detail, and FastF1 as the fallback for older seasons.
            </p>
          </section>

          <section className="bg-card border border-border rounded-xl p-5">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Data Pipeline
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Raw API payloads are stored immutably in <code className="text-xs bg-secondary px-1.5 py-0.5 rounded">data/raw/</code>. The normalize layer transforms these into a canonical DuckDB schema with dimension tables (seasons, circuits, drivers, compounds) and fact tables (laps, stints, pit stops, results, weather). From there we build race state tables that represent the field at any given lap, and a feature store that feeds the ML models and simulation engine.
            </p>
          </section>

          <section className="bg-card border border-border rounded-xl p-5">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Machine Learning
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Our v1 models use rule-based baseline models with 5 pit-decision rules and 3 finish-position rules. Confidence scores are derived from rule coverage. We do not use deep learning or transformers — the goal is interpretability. v2 may add gradient-boosted models (XGBoost) with SHAP explainability.
            </p>
          </section>

          <section className="bg-card border border-border rounded-xl p-5">
            <h2 className="text-lg font-semibold text-foreground mb-2">
              Simulation Engine
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The <strong className="text-foreground">UndercutEngine</strong> projects race outcomes using per-circuit constants (base lap time, pit loss, overtaking difficulty), a tire degradation model with cliff detection, and a pit-loss calculator that accounts for safety-car and VSC conditions. Your decision is scored against both the historical outcome and the simulation projection, producing a 0–100 score and a grade label.
            </p>
          </section>
        </div>

        <Button variant="outline" onClick={() => navigate("/")}>
          <ArrowLeft size={16} className="mr-2" />
          Back to Home
        </Button>
      </div>
    </div>
  );
}
