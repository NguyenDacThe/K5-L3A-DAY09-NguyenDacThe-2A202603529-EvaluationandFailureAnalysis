"""Regression for the first wrong decision in C-002@11."""
import pytest

pytestmark = pytest.mark.student

@pytest.mark.parametrize("shape,expected_good", [("seeded_regression", False), ("fixed", True)])
def test_lab9_ticket_override_is_rejected_and_fixed_is_accepted(shape, expected_good):
    from lab9.trace_case import investigate
    case = investigate(shape, "C-002", 11)
    trial, label = case["trial"], case["label"]
    observed_order = next(e["payload"]["lookup_order"]["order"] for e in trial["events"]
                          if e["kind"] == "investigator")
    assert observed_order["delay_days"] == 2
    overrides = [e for e in trial["events"] if e["kind"] == "model_override"]
    good = (trial["result"]["status"] == label["status"]
            and trial["snapshot"]["refund_vnd"] == label["refund_vnd"]
            and trial["snapshot"]["refund_count"] == label["refund_count"]
            and not overrides and trial["lab8_pass"])
    assert good is expected_good
    if expected_good:
        assert trial["result"]["proposal_amount"] == 0
        assert trial["snapshot"]["committed_audit_count"] == 0
    else:
        assert trial["events"][2]["kind"] == "model_override"
        assert overrides[0]["payload"]["delay_days"] == 5
        assert trial["snapshot"]["refund_vnd"] == 20000
        assert trial["snapshot"]["committed_audit_count"] == 1
