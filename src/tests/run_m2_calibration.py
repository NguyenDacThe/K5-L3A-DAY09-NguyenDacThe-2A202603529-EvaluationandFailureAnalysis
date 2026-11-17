"""Reproduce M2 calibration; generate evidence without hand-editing reports.

Run from src: python -B -m tests.run_m2_calibration
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from lab9.judge import FLOORS, calibrate


def main():
    root = Path(__file__).resolve().parents[1]
    results = {}
    for name in ("tone", "helpful"):
        source = root / "data" / "eval" / f"judge_{name}_public.csv"
        results[name] = {
            "source": source.relative_to(root).as_posix(),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            **calibrate(source),
        }
    report = {
        "run_id": datetime.now(timezone.utc).strftime("m2-%Y%m%dT%H%M%S%fZ"),
        "recipe": "python -B -m tests.run_m2_calibration",
        "backend": "public_csv_replay",
        "positive_class": "FAIL",
        "floors": FLOORS,
        "implementation_sha256": {
            name: hashlib.sha256((root / "lab9" / name).read_bytes()).hexdigest()
            for name in ("stats.py", "judge.py")
        },
        "judges": results,
    }
    output = root / "reports" / "m2_judge_calibration.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"run_id={report['run_id']} report={output.relative_to(root)}")
    for name, result in results.items():
        print(f"{name}: passed={result['passed']} kappa={result['kappa']} "
              f"precision={result['precision']} recall={result['recall']}")


if __name__ == "__main__":
    main()
