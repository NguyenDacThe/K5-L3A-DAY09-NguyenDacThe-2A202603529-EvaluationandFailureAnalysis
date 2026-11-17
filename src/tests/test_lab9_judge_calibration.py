"""M2 edge cases and calibration decisions, independent of later milestones."""
import csv
from pathlib import Path

import pytest

pytestmark = pytest.mark.student


@pytest.fixture
def stats():
    from lab9 import stats
    return stats


@pytest.mark.parametrize("human,judge", [
    ([], []), (["PASS"], []), (["UNKNOWN"], ["PASS"]), (["PASS"], ["fail"]),
])
def test_reject_invalid_labels(stats, human, judge):
    for function in (stats.confusion, stats.precision_recall, stats.cohen_kappa):
        with pytest.raises(ValueError):
            function(human, judge)


@pytest.mark.parametrize("human,judge,expected", [
    (["PASS", "FAIL"], ["PASS", "FAIL"], 1.0),
    (["PASS", "FAIL"], ["FAIL", "PASS"], -1.0),
    (["PASS", "FAIL"], ["PASS", "PASS"], 0.0),
])
def test_kappa_agreement_extremes(stats, human, judge, expected):
    assert stats.cohen_kappa(human, judge) == expected


@pytest.mark.parametrize("human,judge", [
    (["PASS"], ["PASS"]), (["FAIL"], ["PASS"]), (["PASS"], ["FAIL"]),
])
def test_precision_recall_zero_denominators(stats, human, judge):
    assert stats.precision_recall(human, judge) == (0.0, 0.0)


@pytest.mark.parametrize("rates", [
    (-0.1, 0.8, 0.9), (0.2, 1.1, 0.9), (0.2, 0.8, float("nan")),
    (float("inf"), 0.8, 0.9), (0.2, 0.5, 0.5),
])
def test_rogan_gladen_rejects_invalid_or_unidentifiable_rates(stats, rates):
    with pytest.raises(ValueError):
        stats.rogan_gladen(*rates)


def test_rogan_gladen_upper_clip_and_identity(stats):
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
    assert stats.rogan_gladen(0.37, 1.0, 1.0) == pytest.approx(0.37)


@pytest.mark.parametrize("name,passed,cm,kappa,precision,recall,observed", [
    ("tone", True, {"tp": 24, "fp": 4, "fn": 6, "tn": 66}, 0.757, 0.857, 0.8, 0.28),
    ("helpful", False, {"tp": 9, "fp": 0, "fn": 21, "tn": 70}, 0.375, 1.0, 0.3, 0.09),
])
def test_public_calibration(name, passed, cm, kappa, precision, recall, observed):
    from lab9.judge import calibrate

    result = calibrate(Path(f"data/eval/judge_{name}_public.csv"))
    assert result["n"] == 100
    assert result["passed"] is passed
    assert result["confusion"] == cm
    assert (result["kappa"], result["precision"], result["recall"]) == (kappa, precision, recall)
    assert result["observed_fail_rate"] == observed
    assert result["corrected_fail_rate"] == 0.3
    assert len(result["disagreements"]) == cm["fp"] + cm["fn"]


def test_constant_judge_fails_calibration_without_crash(tmp_path):
    from lab9.judge import calibrate

    path = tmp_path / "constant.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["item_id", "reply", "human", "judge"])
        writer.writerow(["constant", "reply", "PASS", "PASS"])
    result = calibrate(path)
    assert result["passed"] is False
    assert result["corrected_fail_rate"] is None
    assert "correction_error" in result


def test_calibration_uses_unrounded_floors(tmp_path, monkeypatch):
    from lab9 import judge

    path = tmp_path / "boundary.csv"
    path.write_text("item_id,reply,human,judge\na,reply,FAIL,FAIL\nb,reply,PASS,PASS\n", encoding="utf-8")
    monkeypatch.setattr(judge.stats, "precision_recall", lambda *_: (0.7996, 0.8))
    monkeypatch.setattr(judge.stats, "cohen_kappa", lambda *_: 0.7)
    result = judge.calibrate(path)
    assert result["precision"] == 0.8
    assert result["passed"] is False
