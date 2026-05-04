import time
from pathlib import Path
from .base_client import BaseClient


class JolpicaClient(BaseClient):
    BASE_URL = "https://api.jolpi.ca/ergast/f1"
    SOURCE_SYSTEM = "jolpica"

    def fetch_raw_bootstrap(self, season: int) -> dict:
        return {
            "drivers": self._get(
                f"{season}/drivers.json",
                filename=self.raw_dir / str(season) / "season" / "drivers.json"
            ),
            "constructors": self._get(
                f"{season}/constructors.json",
                filename=self.raw_dir / str(season) / "season" / "constructors.json"
            ),
        }

    def fetch_raw(self, season: int, round: int) -> dict:
        return {
            "results": self._get(f"{season}/{round}/results.json"),
            "qualifying": self._get(f"{season}/{round}/qualifying.json"),
            "pit_stops": self._get(f"{season}/{round}/pitstops.json"),
            "lap_times": self._get_all_paginated(f"{season}/{round}/laps.json"),
        }

    def fetch_raw_all_time(self) -> dict:
        return {
            "circuits": self._get(
                "circuits.json",
                params={"limit": 100},
                filename=self.raw_dir / "all_time" / "circuits.json"
            ),
        }

    def _get_all_paginated(self, subpath: str, params: dict | None = None) -> list:
        all_data = []
        offset = 0
        limit = params.get("limit", 30) if params else 30
        while True:
            page_params = (params or {}) | {"offset": offset, "limit": limit}
            data = self._get(subpath, params=page_params)
            if not data:
                break
            items = self._extract_items(data, subpath)
            if not items:
                break
            all_data.extend(items)
            offset += limit
            time.sleep(1.0)
        return all_data

    def _extract_items(self, data: dict, subpath: str) -> list:
        mrdata = data.get("MRData", {})
        if "laps" in subpath:
            races = mrdata.get("RaceTable", {}).get("Races", [])
            if races:
                return races[0].get("Laps", [])
        if "drivers" in subpath:
            return mrdata.get("DriverTable", {}).get("Drivers", [])
        if "constructors" in subpath:
            return mrdata.get("ConstructorTable", {}).get("Constructors", [])
        if "circuits" in subpath:
            return mrdata.get("CircuitTable", {}).get("Circuits", [])
        if "results" in subpath:
            return mrdata.get("RaceTable", {}).get("Races", [])
        if "qualifying" in subpath:
            races = mrdata.get("RaceTable", {}).get("Races", [])
            if races:
                return races[0].get("QualifyingResults", [])
        if "pitstops" in subpath:
            races = mrdata.get("RaceTable", {}).get("Races", [])
            if races:
                return races[0].get("PitStops", [])
        return []
