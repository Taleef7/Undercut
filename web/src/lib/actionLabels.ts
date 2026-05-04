export const ACTION_LABELS: Record<string, string> = {
  // Pit decisions
  pit_now: "Pit Now",
  pit_now_inter: "Pit for Inters",
  pit_now_hard: "Pit for Hards",
  pit_now_soft: "Pit for Softs",
  pit_now_medium: "Pit for Mediums",
  pit_wet: "Pit for Wets",
  pit_inters: "Pit for Inters",
  // Stay out decisions
  stay_out: "Stay Out",
  stay_inter: "Stay on Inters",
  stay_wet: "Stay on Wets",
  stay_hard: "Stay on Hards",
  stay_soft: "Stay on Softs",
  stay_medium: "Stay on Mediums",
  // Extend decisions
  extend_stint: "Extend Stint",
  // Wet weather decisions
  switch_to_wet: "Switch to Wets",
  wait_and_see: "Wait and See",
  // Pace decisions
  push: "Push",
  manage: "Manage",
  ease_off: "Ease Off",
  // Defense decisions
  defend_position: "Defend Position",
  cover_undercut: "Cover Undercut",
  // Safety car decisions
  safety_car_pit: "Pit Under SC",
  late_race_attack: "Late Race Attack",
  // Generic fallback: replace underscores with spaces and title-case
};

export function getActionLabel(action: string): string {
  if (ACTION_LABELS[action]) {
    return ACTION_LABELS[action];
  }
  // Fallback: convert snake_case to Title Case
  return action
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
