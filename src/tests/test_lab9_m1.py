"""M1 dataset integrity and provenance checks, independent of M2/M3 TODOs."""
import json
from pathlib import Path
import pytest
from lab9 import evalset

pytestmark = pytest.mark.student
SOURCE = Path(__file__).resolve().parents[1] / "data/public_claims.jsonl"


def test_lab9_m1_labels_are_preserved_and_items_have_no_inline_answers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert evalset.build(SOURCE) == (14, 14)
    items = evalset.load_jsonl(evalset.ITEMS)
    labels = json.loads(evalset.LABELS.read_text(encoding="utf-8"))
    original = evalset.load_jsonl(SOURCE)
    assert labels == {c["claim_id"]: c["expected"] for c in original}
    assert len({i["claim_id"] for i in items}) == 14
    for item in items:
        assert not {"expected", "label", "ticket", "parent_secret"}.intersection(item)
        assert item["failure_modes"]
        assert all(evalset.FM_CODE.fullmatch(fm) for fm in item["failure_modes"])
        provenance = item["provenance"]
        assert provenance["from_trace"] in provenance["trace_refs"]
        assert provenance["source_sha"] == evalset.sha12(SOURCE)
        assert provenance["checked_by"].startswith("automated:")
        assert provenance["label_by"] == "lab8_matrix"
    assert not evalset.check()


def test_lab9_m1_rebuild_is_deterministic_and_does_not_change_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = SOURCE.read_bytes()
    evalset.build(SOURCE)
    first = (evalset.ITEMS.read_bytes(), evalset.LABELS.read_bytes())
    evalset.build(SOURCE)
    assert first == (evalset.ITEMS.read_bytes(), evalset.LABELS.read_bytes())
    assert SOURCE.read_bytes() == before


def test_lab9_m1_unknown_source_case_requires_review(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "unreviewed.jsonl"
    source.write_text(json.dumps({"claim_id": "C-NEW", "matrix_id": "T99", "expected": {}}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No reviewed M1 coverage"):
        evalset.build(source)
