"""Reproduce M1 observations without editing Lab08 or official variants."""
import json
import tempfile
from pathlib import Path
from lab8.db import load_json, load_jsonl
from lab8.shapes import SHAPES
from lab9.eval import make_task
from lab9.variant_agent import make_shape
from lab9.trace_case import investigate

CASES = [
    ("FM-01", "leaky_trace", "C-001", 1),
    ("FM-02", "ignore_denied", "C-007", 4),
    ("FM-03", "ticket_trust", "C-002", 3),
    ("FM-04", "sum_parts", "C-014", 4),
    ("FM-05", "pre_deducted", "C-014", 5),
    ("FM-06", "stale_clause", "C-006", 3),
    ("FM-07", "sibling_refund", "C-001", 4),
    ("FM-08", "misreport", "C-008", 4),
]

def summary(trial):
    # Never copy raw events/blob/reason: a leak variant contains actual canaries.
    return {
        "run_id": trial["result"]["run_id"],
        "trace_path": trial["result"]["trace_path"],
        "status": trial["result"]["status"],
        "proposal_amount": trial["result"]["proposal_amount"],
        "refund_vnd": trial["snapshot"]["refund_vnd"],
        "refund_count": trial["snapshot"]["refund_count"],
        "committed_audit_count": trial["snapshot"]["committed_audit_count"],
        "policy_denied": trial["snapshot"]["policy_denied"],
        "unexpected_rows": trial["unexpected_rows"],
        "lab8_pass": trial["lab8_pass"],
        "reason_category": str(trial["lab8_reason"]).split(":", 1)[0],
        "events": [{"step": i, "kind": e["kind"]} for i, e in enumerate(trial["events"], 1)],
    }

def main():
    claims = load_jsonl(Path("data/public_claims.jsonl"))
    labels = {c["claim_id"]: c["expected"] for c in claims}
    world = load_json(Path("data/public_world_state.json"))
    rows = []
    for fm, bug, cid, step in CASES:
        name = "m1_" + bug
        previous = SHAPES.get(name)
        SHAPES[name] = make_shape(name, {"no_override", bug})
        try:
            with tempfile.TemporaryDirectory(prefix="lab9-m1-", ignore_cleanup_errors=True) as tmp:
                trial = make_task(name, world, claims, labels, Path(tmp))({"claim_id": cid, "seed": 11})
        finally:
            if previous is None:
                SHAPES.pop(name, None)
            else:
                SHAPES[name] = previous
        control = investigate("fixed", cid, 11)["trial"]
        assert control["lab8_pass"], "fixed control must pass"
        assert not trial["lab8_pass"] or fm == "FM-08", "fault did not manifest"
        rows.append({"failure_mode": fm, "claim_id": cid, "seed": 11,
                     "first_observable_wrong_step": step, "variant": summary(trial), "fixed": summary(control)})
    case = {name: summary(investigate(name, "C-002", 11)["trial"])
            for name in ("seeded_regression", "fixed")}
    guarded = summary(investigate("fixed", "C-005", 11)["trial"])
    report = {"scope": "M1 observations, not an M4 eval baseline", "cases": rows,
              "trace_case": case, "FM-09_guarded_example_not_observed_regression": guarded}
    out = Path("reports/m1_trace_evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}; 8 observed modes, fixed controls pass; FM-09 only guarded coverage")

if __name__ == "__main__":
    main()
