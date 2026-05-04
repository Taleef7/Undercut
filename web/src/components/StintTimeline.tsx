interface StintTimelineProps {
  totalLaps: number;
  currentLap: number;
  compound: string;
  stintAge: number;
}

const COMPOUND_COLORS: Record<string, string> = {
  soft: "#ef4444",
  medium: "#eab308",
  hard: "#9ca3af",
  intermediate: "#22c55e",
  wet: "#3b82f6",
};

export default function StintTimeline({
  totalLaps,
  currentLap,
  compound,
  stintAge,
}: StintTimelineProps) {
  const color = COMPOUND_COLORS[compound.toLowerCase()] ?? "#6b7280";
  const stintStart = Math.max(1, currentLap - stintAge + 1);
  const widthPct = ((currentLap - stintStart + 1) / totalLaps) * 100;
  const leftPct = ((stintStart - 1) / totalLaps) * 100;
  const currentPct = ((currentLap - 1) / totalLaps) * 100;

  return (
    <div className="w-full">
      {/* Labels */}
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
        <span>Lap 1</span>
        <span>Lap {totalLaps}</span>
      </div>

      {/* Bar */}
      <div className="relative w-full h-4 bg-secondary rounded-full overflow-hidden">
        {/* Stint segment */}
        <div
          className="absolute top-0 h-full rounded-full opacity-90"
          style={{
            left: `${leftPct}%`,
            width: `${widthPct}%`,
            backgroundColor: color,
          }}
        />

        {/* Current lap marker */}
        <div
          className="absolute top-0 h-full w-0.5 bg-white shadow-sm"
          style={{ left: `${currentPct}%` }}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="capitalize">{compound}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white" />
          <span>Current lap</span>
        </div>
      </div>
    </div>
  );
}
