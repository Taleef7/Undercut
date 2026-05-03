import json
from datetime import datetime
from pathlib import Path


def write_report(warnings: list[str], errors: list[str],
                 season: int, round_num: int, session_type: str,
                 output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"validation_report_{season}_{round_num}_{timestamp}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / filename

    report = {
        "season": season,
        "round": round_num,
        "session_type": session_type,
        "timestamp": datetime.now().isoformat(),
        "warnings": warnings,
        "errors": errors,
        "warning_count": len(warnings),
        "error_count": len(errors),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path