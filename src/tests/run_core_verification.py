"""Run the local equivalent of the Core eval-gate job and retain its evidence."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    steps = []
    commands = [
        (["-m", "lab9.smoke"], 0),
        (["-m", "pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9 and not advanced", "-p", "no:cacheprovider"], 0),
        (["-m", "lab9.evalset", "--check"], 0),
        (["-m", "lab9.eval", "--shape", "swarm", "--out", "reports/eval_pr.json"], 0),
        (["-m", "lab9.gate", "--pr", "reports/eval_pr.json", "--baseline", "reports/baseline_v1.json"], 0),
        (["-m", "lab9.ci_check", "--pr", "reports/eval_pr.json", "--baseline", "reports/baseline_v1.json"], 0),
        (["-m", "lab9.eval", "--shape", "fixed"], 0),
        (["-m", "lab9.gate", "--pr", "reports/eval_fixed.json", "--baseline", "reports/baseline_v1.json"], 0),
        (["-m", "lab9.eval", "--shape", "seeded_regression"], 0),
        (["-m", "lab9.gate", "--pr", "reports/eval_seeded_regression.json", "--baseline", "reports/baseline_v1.json"], 1),
    ]
    for args, expected in commands:
        completed = subprocess.run([sys.executable, "-B", *args], cwd=root, capture_output=True,
                                   text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        ok = completed.returncode == expected
        if expected == 1:
            verdict = next((line for line in completed.stdout.splitlines() if line.startswith("exit 1")), "")
            ok &= "pass_rate" in verdict
        steps.append({"args": args, "exit_code": completed.returncode, "expected_exit_code": expected,
                      "passed": ok, "stdout": completed.stdout, "stderr": completed.stderr})
        print("PASS" if ok else "FAIL", " ".join(args), flush=True)
        if not ok:
            print(completed.stdout, completed.stderr, flush=True)
            break
    artifact_paths = ["reports/baseline_v1.json", "reports/eval_pr.json", "reports/eval_fixed.json",
                      "reports/eval_seeded_regression.json", "reports/m3_detection.json",
                      "config/metric_spec.yaml", "lab9/stats.py", "lab9/graders.py"]
    report = {"run_id": datetime.now(timezone.utc).strftime("core-%Y%m%dT%H%M%SZ"),
              "recipe": "python -B -m tests.run_core_verification", "scope": "local Core job; not remote GitHub Actions",
              "passed": len(steps) == len(commands) and all(s["passed"] for s in steps),
              "steps": steps, "artifact_sha256": {
                  p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in artifact_paths}}
    output = root / "reports/core_verification.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
