import hashlib
import json
from pathlib import Path


def compute_record_hash(source_system: str, record_id: str, key_fields: str) -> str:
    payload = f"{source_system}:{record_id}:{key_fields}"
    return hashlib.sha256(payload.encode()).hexdigest()


def load_raw_json(data_dir: Path, source: str, *parts: str) -> dict | list | None:
    path = data_dir / "raw" / source / Path(*parts)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
