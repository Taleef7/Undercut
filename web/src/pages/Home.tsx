import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
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
  Activity,
  Terminal,
} from "lucide-react";

const FEATURES = [
  {
    icon: Brain,
    title: "ML-Powered Recommendations",
    description:
      "Rule-based baseline models analyze stint age, gap deltas, weather flags, and track position to suggest optimal pit strategy.",
    code: "MODEL.predict(stint=14, gap=1.2, rain_prob=0.3)",
  },
  {
    icon: Gauge,
    title: "Simulation Engine",
    description:
      "Per-circuit tire degradation curves, pit-loss calculators, and overtaking difficulty models project race outcomes lap by lap.",
    code: "SIM.lap_projection(laps_remaining=39)",
  },
  {
    icon: Shuffle,
    title: "Chaos Engine",
    description:
      "Replay decisions with 'What if...?' modifiers: Safety Car, rain, tire cliff, slow stops, rival pits, red flags.",
    code: "CHAOS.apply(sc='active', rain='starting')",
  },
  {
    icon: Trophy,
    title: "Decision Scoring",
    description:
      "Get scored 0–100 against historical outcomes. Grades from 'Masterful' to 'Off the wall' with detailed tradeoff analysis.",
    code: "SCORE.evaluate(user_call, historical, sim)",
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
    <div className="min-h-screen bg-background text-foreground relative">
      {/* Grid background */}
      <div className="absolute inset-0 grid-bg pointer-events-none" />

      {/* Scanline overlay */}
      <div className="absolute inset-0 scanlines pointer-events-none" />

      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 py-20 sm:py-32">
        <div className="max-w-5xl mx-auto">
          {/* Terminal header bar */}
          <div className="mb-8 inline-flex items-center gap-2 px-3 py-1.5 bg-card border border-border">
            <div className="w-2 h-2 rounded-full bg-strong animate-pulse" />
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
              Undercut v1.0 // Unofficial F1 Fan Project
            </span>
          </div>

          <h1 className="text-foreground mb-6">
            Think you can out-strategize{" "}
            <span className="text-papaya">the pit wall?</span>
          </h1>

          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed font-sans">
            Replay historical race scenarios, make the call from the pit wall,
            and see how your strategy stacks up against real teams, ML models,
            and simulation projections.
          </p>

          <div className="flex flex-col sm:flex-row items-start gap-4">
            <Button
              size="lg"
              className="text-base px-8 py-6 bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide"
              onClick={() => navigate("/scenarios")}
            >
              Pick a Scenario
              <ChevronRight size={18} className="ml-2" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="text-base px-8 py-6 border-border hover:border-papaya/50 font-heading uppercase tracking-wide"
              onClick={() => navigate("/methodology")}
            >
              How It Works
            </Button>
          </div>
        </div>

        {/* Decorative telemetry lines */}
        <div className="absolute top-20 right-0 w-64 h-px bg-gradient-to-l from-papaya/20 to-transparent pointer-events-none" />
        <div className="absolute top-24 right-0 w-48 h-px bg-gradient-to-l from-telemetry/10 to-transparent pointer-events-none" />
        <div className="absolute bottom-20 left-0 w-96 h-px bg-gradient-to-r from-papaya/10 to-transparent pointer-events-none" />
      </section>

      {/* Animated Race State Card Preview */}
      <section className="relative px-6 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="bg-card border border-border glow-border p-6 sm:p-8 relative">
            {/* Terminal chrome */}
            <div className="flex items-center gap-2 mb-6 pb-4 border-b border-border">
              <Terminal size={14} className="text-muted-foreground" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                race_state_preview.exe
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                <div className="w-2 h-2 bg-strong animate-pulse" />
                <span className="text-xs font-mono text-strong">LIVE</span>
              </div>
            </div>

            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase tracking-wider">
                  2024 Brazilian GP · Race
                </div>
                <h2 className="text-2xl font-heading">
                  Lap 32 of 71
                </h2>
              </div>
              <div className="px-3 py-1 bg-strong/10 border border-strong/30">
                <span className="text-xs font-mono text-strong uppercase tracking-wider">
                  Green
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-secondary/50 border border-border p-4">
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">
                  Driver
                </div>
                <div className="text-3xl font-heading text-foreground">VER</div>
              </div>
              <div className="bg-secondary/50 border border-border p-4 text-right">
                <div className="text-xs font-mono text-muted-foreground mb-1 uppercase">
                  Position
                </div>
                <div className="text-5xl font-heading text-papaya leading-none">
                  P2
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-secondary/50 border border-border p-4">
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-1 uppercase">
                  <TrendingUp size={14} className="text-strong" />
                  Gap Ahead
                </div>
                <div className="text-xl font-mono text-foreground">
                  +1.2s
                </div>
              </div>
              <div className="bg-secondary/50 border border-border p-4">
                <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-1 uppercase">
                  <TrendingUp
                    size={14}
                    className="text-poor rotate-180"
                  />
                  Gap Behind
                </div>
                <div className="text-xl font-mono text-foreground">
                  +4.8s
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 mb-6 flex-wrap">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 ring-2 ring-white/5" />
                <span className="text-sm font-mono">Medium · 14 laps old</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground font-mono">
                <Timer size={14} />
                Track 48°C
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground font-mono">
                <AlertTriangle size={14} className="text-risky" />
                Rain rising
              </div>
            </div>

            <div className="bg-secondary/30 border border-border p-4 mb-6">
              <div className="flex items-start gap-3">
                <Radio size={16} className="text-papaya mt-0.5 shrink-0" />
                <p className="text-sm text-foreground leading-relaxed italic font-sans">
                  "Box, box? The mediums are starting to go. Rain coming."
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Button
                className="w-full bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide"
                onClick={() => navigate("/scenario/brazil_2024_lap32")}
              >
                Pit for Inters
              </Button>
              <Button
                variant="outline"
                className="w-full border-border hover:border-papaya/50 font-heading uppercase tracking-wide"
                onClick={() => navigate("/scenario/brazil_2024_lap32")}
              >
                Stay Out
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative px-6 py-16">
        <div className="max-w-5xl mx-auto">
          <div className="mb-12">
            <div className="flex items-center gap-2 mb-3">
              <Activity size={16} className="text-papaya" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                System Modules
              </span>
            </div>
            <h2 className="text-foreground mb-3">
              Features
            </h2>
            <p className="text-muted-foreground max-w-lg font-sans">
              Built with real race data, interpretable ML, and a simulation
              engine that understands tire physics.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="bg-card border border-border p-6 hover:border-papaya/30 transition-all glow-border group"
              >
                <feature.icon
                  size={20}
                  className="text-papaya mb-4"
                />
                <h3 className="text-base font-heading mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4 font-sans">
                  {feature.description}
                </p>
                <code className="text-xs text-telemetry opacity-60 group-hover:opacity-100 transition-opacity">
                  {feature.code}
                </code>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="relative px-6 py-16 bg-secondary/20">
        <div className="max-w-4xl mx-auto">
          <div className="mb-12">
            <div className="flex items-center gap-2 mb-3">
              <Terminal size={16} className="text-telemetry" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Execution Flow
              </span>
            </div>
            <h2 className="text-foreground mb-3">
              How It Works
            </h2>
            <p className="text-muted-foreground max-w-lg font-sans">
              Three steps from race replay to strategy insight.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="relative">
                <div className="text-5xl font-heading text-papaya/10 mb-4">
                  {item.step}
                </div>
                <h3 className="text-lg font-heading mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="relative px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <Terminal size={16} className="text-muted-foreground" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                Dependencies
              </span>
            </div>
            <h2 className="text-foreground mb-3">
              Tech Stack
            </h2>
            <p className="text-muted-foreground max-w-lg font-sans">
              Modern tools across the entire data pipeline, from raw telemetry to
              React frontend.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {TECH_STACK.map((tech) => (
              <div
                key={tech}
                className="text-xs font-mono px-3 py-1.5 bg-card border border-border text-muted-foreground hover:border-papaya/30 hover:text-foreground transition-colors"
              >
                {tech}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative px-6 py-20">
        <div className="max-w-2xl mx-auto">
          <div className="border border-border p-8 sm:p-12 text-center glow-border flex flex-col items-center">
            <h2 className="text-foreground mb-4">
              Ready to make the call?
            </h2>
            <p className="text-muted-foreground mb-8 font-sans leading-relaxed">
              Jump into a real race moment and see if you can out-strategize the pit wall.
            </p>
            <Button
              size="lg"
              className="text-base px-8 py-6 bg-papaya text-background hover:bg-papaya/90 font-heading uppercase tracking-wide"
              onClick={() => navigate("/scenarios")}
            >
              Browse Scenarios
              <ChevronRight size={18} className="ml-2" />
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
