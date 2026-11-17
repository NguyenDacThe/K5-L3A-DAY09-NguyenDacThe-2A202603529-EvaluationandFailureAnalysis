"""Independent M5-M7 edge tests: tampered reports, ratchet and exact sampling."""
import copy
import itertools
import pytest

pytestmark = pytest.mark.student


def report():
    return {"manifest": {"eval_set_sha": "x", "items": 3, "seeds": [11, 22]},
            "metrics": {"pass_rate": 1.0}, "evaluator_failures": [],
            "rows": [{"item_id": str(i), "seed": seed, "slices": ["money"],
                      "pass_rate": True} for i in range(3) for seed in (11, 22)]}


def spec():
    return {"eval_set_version": "v2", "metrics": [
        {"id": "pass_rate", "blocking": True, "threshold": {"min": 0.85, "no_significant_drop": True}}],
        "slices": [{"name": "money", "metric": "pass_rate", "blocking": True,
                    "min": 0.95, "no_significant_drop": True}]}


@pytest.mark.parametrize("attack", ["duplicate", "seed", "slice", "crash", "none", "nan", "inflated", "inf"])
def test_advanced_report_tampering(attack):
    from lab9.gate import integrity_check
    base, pr = report(), report()
    if attack == "duplicate": pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    if attack == "seed": pr["rows"][0]["seed"] = 99
    if attack == "slice": pr["rows"][0]["slices"] = []
    if attack == "crash": pr["evaluator_failures"] = ["grader crashed"]
    if attack == "none": pr["rows"][0]["pass_rate"] = None
    if attack == "nan": pr["metrics"]["pass_rate"] = float("nan")
    if attack == "inflated": pr["rows"][0]["pass_rate"] = False
    if attack == "inf": pr["rows"][0]["cost"] = float("inf")
    assert integrity_check(pr, base, spec())


@pytest.mark.parametrize("attack", ["metric_removed", "blocking", "min", "ci", "slice_removed", "slice_ci", "slice_blocking"])
def test_advanced_ratchet_restrictions(attack):
    from lab9.gate import integrity_check
    old, new = spec(), spec()
    if attack == "metric_removed": new["metrics"] = []
    if attack == "blocking": new["metrics"][0]["blocking"] = False
    if attack == "min": new["metrics"][0]["threshold"]["min"] = 0.8
    if attack == "ci": new["metrics"][0]["threshold"].pop("no_significant_drop")
    if attack == "slice_removed": new["slices"] = []
    if attack == "slice_ci": new["slices"][0].pop("no_significant_drop")
    if attack == "slice_blocking": new["slices"][0]["blocking"] = False
    assert integrity_check(report(), report(), new, old)


def test_advanced_stricter_spec_and_reordered_rows_are_honest():
    from lab9.gate import check
    old, new = spec(), spec()
    new["metrics"][0]["threshold"]["min"] = 0.9
    pr, base = report(), report()
    pr["rows"].reverse()
    assert check(pr, base, new, old)[0] == []


def test_advanced_pass_k_against_enumeration():
    from lab9.stats import pass_at_k, pass_hat_k
    for n in range(1, 9):
        for c in range(n + 1):
            for k in range(1, n + 1):
                selections = list(itertools.combinations(range(n), k))
                any_pass = sum(any(i < c for i in row) for row in selections) / len(selections)
                all_pass = sum(all(i < c for i in row) for row in selections) / len(selections)
                assert pass_at_k(n, c, k) == pytest.approx(any_pass)
                assert pass_hat_k(n, c, k) == pytest.approx(all_pass)
                assert pass_hat_k(n, c, k) <= c / n + 1e-12
                assert c / n <= pass_at_k(n, c, k) + 1e-12


@pytest.mark.parametrize("args", [(0,0,1), (-1,0,1), (5,-1,1), (5,6,1), (5,1,6), (5,1,0),
                                  (5.0,1,1), (5,True,1), (5,1,1.0)])
def test_advanced_bad_arguments_for_both_estimators(args):
    from lab9.stats import pass_at_k, pass_hat_k
    for fn in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError): fn(*args)


def test_advanced_nan_threshold_cannot_disable_gate():
    from lab9.gate import check
    bad = spec()
    bad["metrics"][0]["threshold"]["min"] = float("nan")
    assert check(report(), report(), bad)[0] == ["integrity"]
