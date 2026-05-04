from typing import Any


VALID_DECISION_TYPES = {
    "pit_now_vs_stay_out",
    "cover_undercut",
    "extend_to_end",
    "switch_to_wet",
    "safety_car_pit",
    "late_race_attack",
    "defend_position",
}

REQUIRED_TOP_LEVEL_FIELDS = [
    "id", "session_id", "driver_id", "lap_number", "decision_type",
    "scenario_title", "scenario_description", "available_actions",
    "actual_decision", "actual_outcome_summary", "explanation_short",
    "explanation_long", "race_state",
]

REQUIRED_RACE_STATE_FIELDS = [
    "current_position", "compound", "stint_age_laps", "laps_remaining",
    "track_temperature_c", "air_temperature_c", "rainfall", "track_status",
    "safety_car_active", "virtual_safety_car_active",
]


class DecisionPointValidator:
    def validate(self, dp: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        for field in REQUIRED_TOP_LEVEL_FIELDS:
            if field not in dp:
                errors.append(f"Missing required field: {field}")

        if "decision_type" in dp and dp["decision_type"] not in VALID_DECISION_TYPES:
            errors.append(f"Invalid decision_type: {dp['decision_type']}")

        if "available_actions" in dp:
            if not isinstance(dp["available_actions"], list) or len(dp["available_actions"]) == 0:
                errors.append("available_actions must be a non-empty list")
            if len(dp["available_actions"]) > 4:
                errors.append("available_actions must not exceed 4 choices")

        if "race_state" in dp:
            rs = dp["race_state"]
            for field in REQUIRED_RACE_STATE_FIELDS:
                if field not in rs:
                    errors.append(f"Missing race_state field: {field}")

        if "actual_decision" in dp and dp["actual_decision"] not in dp.get("available_actions", []):
            errors.append("actual_decision must be one of available_actions")

        return errors
