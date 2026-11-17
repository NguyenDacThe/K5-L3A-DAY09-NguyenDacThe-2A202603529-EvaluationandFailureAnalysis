"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """Return tp/fp/fn/tn, treating FAIL as positive; reject invalid pairs."""
    if len(human) != len(judge) or not human:
        raise ValueError("Expected nonempty, equally sized label sequences")
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for h, j in zip(human, judge):
        if h not in {"PASS", POS} or j not in {"PASS", POS}:
            raise ValueError("Labels must be PASS or FAIL")
        key = ("tp" if j == POS else "fn") if h == POS else ("fp" if j == POS else "tn")
        cm[key] += 1
    return cm


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    """Return failure precision and recall; a zero denominator yields 0.0."""
    cm = confusion(human, judge)
    predicted = cm["tp"] + cm["fp"]
    actual = cm["tp"] + cm["fn"]
    return (cm["tp"] / predicted if predicted else 0.0,
            cm["tp"] / actual if actual else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """Chance-corrected agreement; raise ValueError when expected agreement is 1."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    human_fail = cm["tp"] + cm["fn"]
    judge_fail = cm["tp"] + cm["fp"]
    # Use integer counts to detect p_e == 1 without floating-point rounding.
    expected = human_fail * judge_fail + (n - human_fail) * (n - judge_fail)
    denominator = n * n - expected
    if denominator == 0:
        raise ValueError("Cohen kappa is undefined when expected agreement is 1")
    return ((cm["tp"] + cm["tn"]) * n - expected) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct the observed failure rate and clip to [0, 1].

    Rates must be finite probabilities. Sensitivity + specificity == 1
    makes the correction unidentifiable and raises ValueError.
    """
    if any(not math.isfinite(rate) or not 0.0 <= rate <= 1.0
           for rate in (observed_rate, sensitivity, specificity)):
        raise ValueError("Rates must be finite numbers in [0, 1]")
    denominator = sensitivity + specificity - 1.0
    if denominator == 0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity == 1")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 2:
        raise ValueError("Expected at least two paired, one-dimensional observations")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Bootstrap observations must be finite")
    if not isinstance(n_resamples, int) or isinstance(n_resamples, bool) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if np.array_equal(x, y):
        return 0.0, 0.0, 0.0

    def difference(first, second, axis=-1):
        return np.mean(first, axis=axis) - np.mean(second, axis=axis)

    result = bootstrap((x, y), difference, paired=True, method="percentile",
                       n_resamples=n_resamples, confidence_level=confidence,
                       rng=np.random.default_rng(rng))
    return (float(np.mean(x) - np.mean(y)),
            float(result.confidence_interval.low), float(result.confidence_interval.high))


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_k(n, c, k)
    return 1.0 if n - c < k else 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_k(n, c, k)
    return 0.0 if c < k else math.comb(c, k) / math.comb(n, k)


def _validate_pass_k(n: int, c: int, k: int) -> None:
    if any(type(x) is not int for x in (n, c, k)) or not (n >= 1 and 0 <= c <= n and 1 <= k <= n):
        raise ValueError("Expected integers n >= 1, 0 <= c <= n, 1 <= k <= n")
