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
            "laps": ("laps", {"session_key": session_key}),
            "stints": ("stints", {"session_key": session_key}),
            "pit": ("pit", {"session_key": session_key}),
            "intervals": ("intervals", {"session_key": session_key}),
            "positions": ("position", {"session_key": session_key}),
            "weather": ("weather", {"session_key": session_key}),
            "race_control": ("race_control", {"session_key": session_key}),
            "session_result": ("session_result", {"session_key": session_key}),
            "starting_grid": ("starting_grid", {"session_key": session_key}),
        }
        results = {}
        for name, (subpath, params) in endpoints.items():
            raw_dir = self.raw_dir / str(meeting_key) / str(session_key)
            raw_dir.mkdir(parents=True, exist_ok=True)
            results[name] = self._get(subpath, params=params, filename=raw_dir / f"{name}.json")
        return results
