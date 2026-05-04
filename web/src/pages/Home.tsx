import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  ChevronRight,
  Trophy,
  Brain,
  Gauge,
  Shuffle,
  Radio,
  Timer,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

const FEATURES = [
  {
    icon: Brain,
    title: "ML-Powered Recommendations",
    description:
      "Rule-based baseline models analyze stint age, gap deltas, weather flags, and track position to suggest optimal pit strategy.",
  },
  {
    icon: Gauge,
    title: "Simulation Engine",
    description:
      "Per-circuit tire degradation curves, pit-loss calculators, and overtaking difficulty models project race outcomes lap by lap.",
  },
  {
    icon: Shuffle,
    title: "Chaos Engine",
    description:
      "Replay decisions with 'What if...?' modifiers: Safety Car, rain, tire cliff, slow stops, rival pits, red flags.",
  },
  {
    icon: Trophy,
    title: "Decision Scoring",
    description:
      "Get scored 0–100 against historical outcomes. Grades from 'Masterful' to 'Off the wall' with detailed tradeoff analysis.",
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Pick a Scenario",
    description:
      "Choose from curated historical race moments. Brazil 2024 lap 32 — VER vs NOR under pressure.",
  },
  {
    step: "02",
    title: "Make the Call",
    description:
      "Pit now for fresh rubber? Stay out and defend track position? Switch to wets as rain falls?",
  },
  {
    step: "03",
    title: "Get Scored",
    description:
      "Compare your call against the real team's decision, ML recommendation, and simulation projection.",
  },
];

const TECH_STACK = [
  "FastF1",
  "Jolpica API",
  "OpenF1 API",
  "DuckDB",
  "FastAPI",
  "React 19",
  "TypeScript",
  "Tailwind CSS",
  "shadcn/ui",
  "XGBoost",
  "SHAP",
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 py-20 sm:py-28">
        <div className="max-w-4xl mx-auto text-center">
          <Badge
            variant="outline"
            className="mb-6 text-xs border-border text-muted-foreground"
          >
            Unofficial F1 Fan Project
          </Badge>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground mb-6">
            Think you can out-strategize{" "}
            <span className="text-primary">the pit wall?</span>
          </h1>

          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            Replay historical race scenarios, make the call from the pit wall,
            and see how your strategy stacks up against real teams, ML models,
            and simulation projections.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              className="text-base px-8 py-6"
              onClick={() => navigate("/scenarios")}
            >
              Pick a Scenario
              <ChevronRight size={18} className="ml-2" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="text-base px-8 py-6"
              onClick={() => navigate("/methodology")}
            >
              How It Works
            </Button>
          </div>
        </div>

        {/* Decorative gradient blob */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl -z-10 pointer-events-none" />
      </section>

      {/* Animated Race State Card Preview */}
      <section className="px-6 py-12">
        <div className="max-w-3xl mx-auto">
          <div className="bg-card border border-border rounded-2xl p-6 sm:p-8 shadow-lg">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-sm text-muted-foreground mb-1">
                  2024 Brazilian GP · Race
                </div>
                <h2 className="text-xl font-bold text-foreground">
                  Lap 32 of 71
                </h2>
              </div>
              <Badge
                variant="default"
                className="text-xs uppercase tracking-wider"
              >
                Green
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-secondary/30 rounded-xl p-4">
                <div className="text-sm text-muted-foreground mb-1">
                  Driver
                </div>
                <div className="text-2xl font-bold text-foreground">VER</div>
              </div>
              <div className="bg-secondary/30 rounded-xl p-4 text-right">
                <div className="text-sm text-muted-foreground mb-1">
                  Position
                </div>
                <div className="text-4xl font-bold text-primary leading-none">
                  P2
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-secondary/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <TrendingUp size={16} className="text-strong" />
                  Gap Ahead
                </div>
                <div className="text-lg font-semibold text-foreground">
                  +1.2s
                </div>
              </div>
              <div className="bg-secondary/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <TrendingUp
                    size={16}
                    className="text-destructive rotate-180"
                  />
                  Gap Behind
                </div>
                <div className="text-lg font-semibold text-foreground">
                  +4.8s
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-yellow-500 ring-2 ring-white/10" />
                <span className="text-sm font-medium">Medium · 14 laps old</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Timer size={16} />
                Track 48°C
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <AlertTriangle size={16} className="text-risky" />
                Rain rising
              </div>
            </div>

            <div className="bg-secondary/30 border border-border rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <Radio size={18} className="text-primary mt-0.5 shrink-0" />
                <p className="text-sm text-foreground leading-relaxed italic">
                  "Box, box? The mediums are starting to go. Rain coming."
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Button variant="default" className="w-full">
                Pit for Inters
              </Button>
              <Button variant="outline" className="w-full">
                Stay Out
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="px-6 py-16">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-3">
              Features
            </h2>
            <p className="text-muted-foreground max-w-lg mx-auto">
              Built with real race data, interpretable ML, and a simulation
              engine that understands tire physics.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="bg-card border border-border rounded-xl p-6 hover:border-primary/30 transition-colors"
              >
                <feature.icon
                  size={24}
                  className="text-primary mb-4"
                />
                <h3 className="text-base font-semibold text-foreground mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-6 py-16 bg-secondary/20">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-3">
              How It Works
            </h2>
            <p className="text-muted-foreground max-w-lg mx-auto">
              Three steps from race replay to strategy insight.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="text-center">
                <div className="text-4xl font-extrabold text-primary/20 mb-4">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="px-6 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-3">
            Tech Stack
          </h2>
          <p className="text-muted-foreground max-w-lg mx-auto mb-8">
            Modern tools across the entire data pipeline, from raw telemetry to
            React frontend.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            {TECH_STACK.map((tech) => (
              <Badge
                key={tech}
                variant="secondary"
                className="text-sm px-4 py-2"
              >
                {tech}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Ready to make the call?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Jump into a real race moment and see if you can out-strategize the
            pit wall.
          </p>
          <Button
            size="lg"
            className="text-base px-8 py-6"
            onClick={() => navigate("/scenarios")}
          >
            Browse Scenarios
            <ChevronRight size={18} className="ml-2" />
          </Button>
        </div>
      </section>
    </div>
  );
}
