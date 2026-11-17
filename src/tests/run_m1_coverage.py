"""Measure per-item coverage with isolated faults; never generate labels from agents."""
import json
import re
import tempfile
from pathlib import Path
from lab8.db import load_json, load_jsonl
from lab8.shapes import SHAPES
from lab9.eval import make_task
from lab9.variant_agent import make_shape

BUGS = [("FM-01", "leaky_trace"), ("FM-02", "ignore_denied"),
        ("FM-03", "ticket_trust"), ("FM-04", "sum_parts"),
        ("FM-04", "round_down"), ("FM-05", "pre_deducted"),
        ("FM-06", "stale_clause"), ("FM-07", "sibling_refund"), ("FM-08", "misreport")]

def measure():
    claims = load_jsonl(Path("data/public_claims.jsonl"))
    labels = {c["claim_id"]: c["expected"] for c in claims}
    world = load_json(Path("data/public_world_state.json"))
    rows = []
    for claim in claims:
        cid = claim["claim_id"]
        hits = []
        for fm, bug in BUGS:
            name = "m1_cov_" + bug
            previous = SHAPES.get(name)
            SHAPES[name] = make_shape(name, {"no_override", bug})
            try:
                with tempfile.TemporaryDirectory(prefix="lab9-m1-coverage-", ignore_cleanup_errors=True) as tmp:
                    t = make_task(name, world, claims, labels, Path(tmp))({"claim_id": cid, "seed": 11})
            finally:
                if previous is None:
                    SHAPES.pop(name, None)
                else:
                    SHAPES[name] = previous
            manifested = not t["lab8_pass"]
            if fm == "FM-08":
                reply = next(e["payload"]["text"] for e in t["events"] if e["kind"] == "reply")
                amount = re.search(r"([0-9][0-9.]*)\u0111", reply)
                manifested = (t["result"]["status"] == "resolved" and amount is not None
                              and int(amount[1].replace(".", "")) != t["snapshot"]["refund_vnd"])
            if manifested:
                hits.append({"failure_mode": fm, "bug": bug, "trace_path": t["result"]["trace_path"],
                             "run_id": t["result"]["run_id"], "lab8_pass": t["lab8_pass"],
                             "reason_category": str(t["lab8_reason"]).split(":", 1)[0]})
        rows.append({"claim_id": cid, "matrix_id": claim["matrix_id"], "seed": 11,
                     "observed_failure_modes": sorted({h["failure_mode"] for h in hits}), "evidence": hits})
    return {"scope": "M1 coverage at seed 11; labels remain the original Lab08 labels",
            "trials": len(claims) * len(BUGS), "rows": rows}

def main():
    report = measure()
    out = Path("reports/m1_coverage.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["rows"]:
        print(row["matrix_id"], row["claim_id"], ",".join(row["observed_failure_modes"]))
    print("wrote", out)

if __name__ == "__main__":
    main()
