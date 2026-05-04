import json
import random
import time
import httpx
from abc import ABC
from pathlib import Path


class BaseClient(ABC):
    BASE_URL: str
    SOURCE_SYSTEM: str

    def __init__(self, data_dir: Path | None = None):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "User-Agent": "Undercut/0.1 (portfolio project; contact@example.com)"
            },
            timeout=30.0,
        )
        if data_dir:
            self.raw_dir = data_dir / "raw" / self.SOURCE_SYSTEM
        else:
            self.raw_dir = Path("data") / "raw" / self.SOURCE_SYSTEM

    def _cache_path(self, subpath: str, params: dict | None = None) -> Path:
        base = self.raw_dir / subpath.strip("/")
        if params:
            param_suffix = "_".join(f"{k}_{v}" for k, v in sorted(params.items()))
            if "." in base.name:
                parts = base.name.split(".")
                name = f"{parts[0]}_{param_suffix}.{parts[1]}"
                return base.parent / name
            return base.parent / f"{base.name}_{param_suffix}.json"
        if base.suffix == "":
            return base.with_suffix(".json")
        return base

    def _get(self, subpath: str, params: dict | None = None,
             filename: Path | str | None = None) -> dict | None:
        cache_path = Path(filename) if filename else self._cache_path(subpath, params)

        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                resp = self.client.get(subpath, params=params)
                if resp.status_code < 400:
                    data = resp.json() if resp.text else {}
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    return data
                elif resp.status_code < 500:
                    return None
                else:
                    if attempt < max_retries:
                        wait = 2 ** attempt * (0.5 + random.random())
                        time.sleep(wait)
                        continue
                    return None
            except httpx.RequestError:
                if attempt < max_retries:
                    wait = 2 ** attempt * (0.5 + random.random())
                    time.sleep(wait)
                    continue
                return None
        return None
