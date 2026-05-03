from pathlib import Path
from .base_client import BaseClient


class OpenF1Client(BaseClient):
    BASE_URL = "https://api.openf1.org/v1"
    SOURCE_SYSTEM = "openf1"

    def get_meetings(self, year: int) -> list:
        return self._get("meetings", params={"year": year}) or []

    def get_sessions(self, meeting_key: int) -> list:
        return self._get("sessions", params={"meeting_key": meeting_key}) or []

    def fetch_session(self, session_key: int, meeting_key: int) -> dict:
        endpoints = {
            "laps": f"sessions/{session_key}/laps",
            "stints": f"sessions/{session_key}/stints",
            "pit": f"sessions/{session_key}/pit",
            "intervals": f"sessions/{session_key}/intervals",
            "positions": f"sessions/{session_key}/position",
            "weather": f"sessions/{session_key}/weather",
            "race_control": f"sessions/{session_key}/race_control",
            "session_result": f"sessions/{session_key}/session_result",
            "starting_grid": f"sessions/{session_key}/starting_grid",
        }
        results = {}
        for name, subpath in endpoints.items():
            raw_dir = self.raw_dir / str(meeting_key) / str(session_key)
            raw_dir.mkdir(parents=True, exist_ok=True)
            results[name] = self._get(subpath)
        return results
