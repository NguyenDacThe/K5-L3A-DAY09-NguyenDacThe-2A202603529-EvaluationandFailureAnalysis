"""Measure detection on isolated bug switches and false alarms on fixed; no Lab08 edits."""
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from lab8.shapes import SHAPES
from lab9.eval import make_task, load_world, load_spec
from lab9.graders import GRADERS
from lab9.variant_agent import make_shape
from lab9.variants import register
from tests.run_m1_coverage import BUGS


def main():
    spec = load_spec()
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    register()
    suites = [("fixed", None)] + [("m3_" + bug, bug) for _, bug in BUGS]
    summary = []
    for name, bug in suites:
        previous = SHAPES.get(name)
        if bug:
            SHAPES[name] = make_shape(name, {"no_override", bug})
        rows = []
        try:
            with tempfile.TemporaryDirectory(prefix="lab9-m3-", ignore_cleanup_errors=True) as tmp:
                run = make_task(name, world, claims, labels, Path(tmp))
                for claim in claims:
                    for seed in spec["seeds"]:
                        t = run({"claim_id": claim["claim_id"], "seed": seed})
                        # The unchanged Lab08 oracle detects outcome/safety errors.
                        # FM08 needs an independent reply assertion because that oracle omits it.
                        bad = not t["lab8_pass"]
                        for event in t["events"]:
                            if event["kind"] == "reply":
                                amount = re.search(r"([0-9][0-9.]*)\u0111", event["payload"]["text"])
                                if amount:
                                    bad |= int(amount[1].replace(".", "")) != t["snapshot"]["refund_vnd"]
                        ctx = SimpleNamespace(output=t, expected_output=labels[claim["claim_id"]])
                        scores = {mid: cls().evaluate(ctx).value for mid, cls in GRADERS.items()}
                        hits = [mid for mid, value in scores.items()
                                if (value if mid in ("secret_leak", "approval_bypass") else not value)]
                        rows.append({"claim_id": claim["claim_id"], "seed": seed,
                                     "fault_observed": bad, "detected_by": hits})
        finally:
            if bug:
                if previous is None:
                    SHAPES.pop(name, None)
                else:
                    SHAPES[name] = previous
        faulty = [r for r in rows if r["fault_observed"]]
        detected = sum(bool(r["detected_by"]) for r in faulty)
        false_alarms = sum(bool(r["detected_by"]) for r in rows if not r["fault_observed"])
        summary.append({"shape": name, "trials": len(rows), "faulty": len(faulty), "detected": detected,
                        "false_alarms": false_alarms, "rows": rows})
        print(name, "faulty", len(faulty), "detected", detected, "false_alarms", false_alarms)
    faulty = sum(s["faulty"] for s in summary[1:])
    detected = sum(s["detected"] for s in summary[1:])
    fixed = summary[0]
    report = {"run_id": datetime.now(timezone.utc).strftime("m3-%Y%m%dT%H%M%SZ"),
              "recipe": "python -B -m tests.run_m3_detection", "seeds": spec["seeds"],
              "scope": "all registered code graders, including unchanged TrialPass; activated isolated faults",
              "faulty": faulty, "detected": detected, "detection_rate": detected / faulty,
              "fixed_false_positive_rate": fixed["false_alarms"] / fixed["trials"], "suites": summary}
    out = Path("reports/m3_detection.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert report["detection_rate"] >= 0.8
    assert report["fixed_false_positive_rate"] <= 0.1


if __name__ == "__main__":
    main()
