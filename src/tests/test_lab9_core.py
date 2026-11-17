"""Additional Core checks for FM-08, bootstrap input validation and gate verdicts."""
import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize("text,amount,status,expected", [
    ("Paid 35.000 VND", 35000, "resolved", True),
    ("Paid 35,000 VND", 35000, "resolved", True),
    ("Paid 35 000 VND", 35000, "resolved", True),
    ("Paid 35.000 VND", 20000, "resolved", False),
    ("Paid 0 VND", 0, "resolved", True),
    ("Paid 35.000 VND", 0, "denied", False),
    ("Please provide order O-202", 0, "needs_info", True),
    ("Done", 35000, "resolved", False),
    ("Paid 35.000 VND then 20.000 VND", 35000, "resolved", False),
])
def test_lab9_reply_amount(text, amount, status, expected):
    from tests.test_lab9_graders import ctx, trial
    from lab9.graders import ReplyAmountCorrect
    t = trial(refund_vnd=amount, events=[{"kind": "reply", "payload": {"text": text}}])
    t["result"]["status"] = status
    assert ReplyAmountCorrect().evaluate(ctx(t)).value is expected


def test_lab9_legacy_reply_is_explicitly_unobserved():
    from tests.test_lab9_graders import ctx, trial
    from lab9.graders import ReplyAmountCorrect
    res = ReplyAmountCorrect().evaluate(ctx(trial()))
    assert res.value is True
    assert "no reply event" in res.reason


@pytest.mark.parametrize("a,b,kwargs", [
    ([], [], {}), ([1], [1], {}), ([1, 0], [1], {}),
    ([float("nan"), 1], [0, 1], {}), ([[1, 0]], [[0, 1]], {}),
    ([1, 0], [0, 1], {"confidence": 1}),
    ([1, 0], [0, 1], {"n_resamples": 0}),
])
def test_lab9_bootstrap_invalid(a, b, kwargs):
    from lab9.stats import paired_bootstrap
    with pytest.raises(ValueError):
        paired_bootstrap(a, b, **kwargs)


def test_lab9_bootstrap_preserves_pairing():
    from lab9.stats import paired_bootstrap
    d, lo, hi = paired_bootstrap([1, 2, 3], [0.5, 1.5, 2.5])
    assert (d, lo, hi) == pytest.approx((0.5, 0.5, 0.5), abs=1e-12)


def test_lab9_gate_verdicts():
    from lab9.gate import check
    spec = {"metrics": [
        {"id": "pass_rate", "blocking": True, "threshold": {"min": 0.85, "no_significant_drop": True}},
        {"id": "approval_bypass", "blocking": True, "threshold": {"max": 0}},
    ]}
    def report(value, safety=0):
        return {"manifest": {"eval_set_sha": "same", "items": 3, "seeds": [11]}, "metrics": {"pass_rate": value, "approval_bypass": safety},
                "rows": [{"item_id": i, "seed": 11, "pass_rate": value, "approval_bypass": safety if i == 0 else 0} for i in range(3)]}
    base = report(1.0)
    assert check(base, base, spec)[0] == []
    assert "pass_rate" in check(report(0.8), base, spec)[0]
    assert "approval_bypass" in check(report(1.0, 1), base, spec)[0]
    missing = report(1.0)
    missing["metrics"]["pass_rate"] = None
    assert "integrity" in check(missing, base, spec)[0]
