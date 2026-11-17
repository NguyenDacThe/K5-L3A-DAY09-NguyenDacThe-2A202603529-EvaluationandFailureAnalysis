"""Report validation and same-version specification ratchet used by the gate."""
import math

from lab9.graders import GRADERS


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def ratchet(spec, base_spec):
    if not base_spec or spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    problems = []
    for section in ("metrics", "slices"):
        key = (lambda m: m["id"]) if section == "metrics" else (lambda m: (m["name"], m["metric"]))
        current = {key(m): m for m in spec.get(section, [])}
        for old in base_spec.get(section, []):
            ident = key(old)
            new = current.get(ident)
            if new is None:
                problems.append(f"ratchet: removed {section} {ident}")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: disabled blocking {ident}")
            a = old.get("threshold", {}) if section == "metrics" else old
            b = new.get("threshold", {}) if section == "metrics" else new
            for name in ("min", "max", "max_increase"):
                if name in a and (name not in b or not finite(b[name]) or
                                  (b[name] < a[name] if name == "min" else b[name] > a[name])):
                    problems.append(f"ratchet: loosened {ident}/{name}")
            if a.get("no_significant_drop") and not b.get("no_significant_drop"):
                problems.append(f"ratchet: removed no_significant_drop {ident}")
    for name in ("seeds", "eval_set", "labels", "adversarial_pack"):
        if name in base_spec and spec.get(name) != base_spec[name]:
            problems.append(f"ratchet: changed {name} without a new eval-set version")
    return problems


def validate_report(report, spec, name):
    errors = []
    rows, manifest, metrics = report.get("rows"), report.get("manifest", {}), report.get("metrics", {})
    if not isinstance(rows, list) or not rows:
        return [f"{name}: missing/empty rows"], set(), {}
    if not isinstance(manifest, dict) or not isinstance(metrics, dict):
        return [f"{name}: invalid manifest/metrics"], set(), {}
    seeds, count = manifest.get("seeds"), manifest.get("items")
    if (not isinstance(seeds, list) or not seeds or any(type(s) is not int for s in seeds)
            or len(seeds) != len(set(seeds)) or type(count) is not int or count < 1):
        return [f"{name}: invalid item/seed manifest"], set(), {}
    if spec.get("seeds") is not None and set(seeds) != set(spec["seeds"]):
        errors.append(f"{name}: manifest seeds differ from spec")
    if len(rows) != count * len(seeds):
        errors.append(f"{name}: row count differs from items x seeds")
    if report.get("evaluator_failures"):
        errors.append(f"{name}: evaluator_failures is non-empty")
    for mid, value in metrics.items():
        if not finite(value):
            errors.append(f"{name}: metric {mid} is missing or non-finite")
    for m in spec.get("metrics", []):
        if m["id"] not in metrics:
            errors.append(f"{name}: missing metric {m['id']}")
    graded = [m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS]
    pairs, slices, by_item = [], {}, {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("item_id"), (str, int)) or type(row.get("seed")) is not int:
            errors.append(f"{name}: invalid identity at row {i}")
            continue
        pair = (row["item_id"], row["seed"])
        pairs.append(pair)
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags) or len(tags) != len(set(tags)):
            errors.append(f"{name}: invalid slice tags at {pair}")
            tags = []
        slices[pair] = frozenset(tags)
        if pair[0] in by_item and by_item[pair[0]] != slices[pair]:
            errors.append(f"{name}: inconsistent slice tags within item {pair[0]}")
        by_item[pair[0]] = slices[pair]
        for mid in graded:
            value = row.get(mid)
            if not finite(value) or not 0 <= value <= 1:
                errors.append(f"{name}: missing/non-finite graded row {pair}/{mid}")
        for key, value in row.items():
            if isinstance(value, float) and not math.isfinite(value):
                errors.append(f"{name}: non-finite row field {pair}/{key}")
    if len(pairs) != len(set(pairs)):
        errors.append(f"{name}: duplicate (item_id, seed) rows")
    expected = {(item, seed) for item in by_item for seed in seeds}
    if set(pairs) != expected or len(by_item) != count:
        errors.append(f"{name}: incomplete item/seed coverage")
    # Independently verify aggregate grader values; editing only the displayed mean must fail.
    for mid in graded:
        values = [r.get(mid) for r in rows]
        if all(finite(v) for v in values):
            actual = sum(values) if mid in ("secret_leak", "approval_bypass") else round(sum(values) / len(values), 4)
            if finite(metrics.get(mid)) and not math.isclose(metrics[mid], actual, abs_tol=1e-9):
                errors.append(f"{name}: aggregate {mid} disagrees with rows")
    # Derive pass@k/pass^k and cost when a full harness report is available.
    if not errors and all("cost" in r and "pass_rate" in r for r in rows):
        from lab9.eval import aggregate
        derived = aggregate(rows, graded, k_values=spec.get("pass_k", []))
        for mid in metrics.keys() & derived.keys():
            a, b = metrics[mid], derived[mid]
            if not finite(b) or not math.isclose(a, b, abs_tol=1e-9):
                errors.append(f"{name}: derived {mid} disagrees with rows")
    return errors, set(pairs), slices


def validate(pr, base, spec, base_spec=None):
    problems = ratchet(spec, base_spec)
    for section in ("metrics", "slices"):
        entries = spec.get(section, [])
        keys = [m.get("id") if section == "metrics" else (m.get("name"), m.get("metric")) for m in entries]
        if len(keys) != len(set(keys)):
            problems.append(f"spec: duplicate {section}")
        for entry in entries:
            threshold = entry.get("threshold", {}) if section == "metrics" else entry
            for key in ("min", "max", "max_increase"):
                if key in threshold and not finite(threshold[key]):
                    problems.append(f"spec: non-finite {section}/{key}")
    a, pairs_a, tags_a = validate_report(pr, spec, "PR")
    b, pairs_b, tags_b = validate_report(base, spec, "baseline")
    problems += a + b
    if pairs_a != pairs_b:
        problems.append("PR item/seed pairs differ from baseline")
    if any(tags_a[p] != tags_b[p] for p in pairs_a & pairs_b):
        problems.append("PR slice membership differs from baseline")
    return problems
