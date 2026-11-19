"""Metrics for a detector on one evaluation set, with cluster bootstraps.

Decision rule everywhere: a text is blocked when its score is at or above the threshold.
Two rules for "caught at 1 percent false positives":
  caught_liu   threshold chosen on the evaluated set's own benign scores by the ROC rule of arXiv 2610.03448
               (the largest true-positive rate among ROC points with false-positive rate at most f);
  caught_guar  the guaranteed threshold of this project (strict_threshold: smallest observed benign score with at most
               f of the benign scores at or above it), which never exceeds the cap.
The identification interval (tie_interval) gives the range of the miss rate over every threshold that blocks the same
calibration benigns as the linear quantile at level 1 - f.
"""
from __future__ import annotations
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve
from strict_threshold import strict_threshold
from tie_interval import convention_interval, fnr_low, fnr_high


def auroc(y, p):
    y = np.asarray(y); p = np.asarray(p, float)
    if y.min() == y.max():
        return float("nan")
    return float(roc_auc_score(y, p))


def caught_liu(y, p, f=0.01):
    y = np.asarray(y); p = np.asarray(p, float)
    if (y == 1).sum() == 0 or (y == 0).sum() == 0:
        return float("nan")
    fpr, tpr, _ = roc_curve(y, p)
    return float(tpr[fpr <= f].max())


def guar_threshold(p_ben, f=0.01):
    """strict_threshold without its Python loop: the smallest observed benign score s with share(benign >= s) <= f,
    else the next floating-point value above the largest benign score. Agrees with strict_threshold exactly
    (tests/test_panel_metrics.py)."""
    a = np.asarray(p_ben); dt = a.dtype if a.dtype.kind == "f" else np.dtype(np.float64)
    p = np.sort(a.astype(np.float64)); u = np.unique(p); n = len(p)
    share_ge = (n - np.searchsorted(p, u, side="left")) / n
    ok = np.flatnonzero(share_ge <= f)
    if len(ok):
        return float(u[ok[0]])
    return float(np.nextafter(dt.type(u[-1]), dt.type(np.inf)))


def caught_guar(y, p, f=0.01):
    y = np.asarray(y); p = np.asarray(p, float)
    if (y == 1).sum() == 0 or (y == 0).sum() == 0:
        return float("nan")
    t = guar_threshold(p[y == 0], f)
    return float((p[y == 1] >= t).mean())


def interval_width(y, p, f=0.01):
    """Range of the caught rate over the identification interval of the quantile threshold: (low, high, width)."""
    y = np.asarray(y); p = np.asarray(p, float)
    if (y == 1).sum() == 0 or (y == 0).sum() == 0:
        return float("nan"), float("nan"), float("nan")
    iv = convention_interval(p[y == 0], f)
    hi_caught = 1.0 - fnr_low(p[y == 1], iv)
    lo_caught = 1.0 - fnr_high(p[y == 1], iv)
    return float(lo_caught), float(hi_caught), float(hi_caught - lo_caught)


def fpr_at(p_ben, thr=0.5):
    p_ben = np.asarray(p_ben, float)
    return float((p_ben >= thr).mean()) if len(p_ben) else float("nan")


def block_rate(tasks, p_ben, thr=0.5):
    """Share of tasks with at least one benign output blocked at the threshold."""
    tasks = np.asarray(tasks); p_ben = np.asarray(p_ben, float)
    if len(tasks) == 0:
        return float("nan")
    flagged = set(tasks[p_ben >= thr])
    return float(len(flagged) / len(set(tasks)))


def cluster_boot(fn, y, p, clusters=None, B=1000, seed=0):
    """95 percent interval of fn(y, p) under a bootstrap over clusters (rows when clusters is None)."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y); p = np.asarray(p, float)
    if clusters is None:
        groups = [np.array([i]) for i in range(len(y))]
    else:
        c = np.asarray(clusters); groups = [np.where(c == g)[0] for g in np.unique(c)]
    vals = []
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick])
        v = fn(y[idx], p[idx])
        if not np.isnan(v):
            vals.append(v)
    if not vals:
        return float("nan"), float("nan")
    return tuple(float(x) for x in np.percentile(vals, [2.5, 97.5]))


def paired_cluster_diff(fn, y, p_a, p_b, clusters=None, B=1000, seed=0):
    """fn on detector a minus fn on detector b over the same rows, with its cluster-bootstrap interval."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y); p_a = np.asarray(p_a, float); p_b = np.asarray(p_b, float)
    if clusters is None:
        groups = [np.array([i]) for i in range(len(y))]
    else:
        c = np.asarray(clusters); groups = [np.where(c == g)[0] for g in np.unique(c)]
    point = fn(y, p_a) - fn(y, p_b)
    vals = []
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick])
        a, b = fn(y[idx], p_a[idx]), fn(y[idx], p_b[idx])
        if not (np.isnan(a) or np.isnan(b)):
            vals.append(a - b)
    lo, hi = (np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan))
    return float(point), float(lo), float(hi)


def summarize(y, p, clusters=None, f=0.01, B=1000, seed=0):
    """Every metric for a labelled set. For a benign-only set only the false-positive side is defined."""
    y = np.asarray(y); p = np.asarray(p, float)
    out = dict(n=int(len(y)), n_pos=int((y == 1).sum()), n_neg=int((y == 0).sum()))
    out["fpr_0.5"] = fpr_at(p[y == 0])
    if out["n_pos"] == 0:
        return out
    out["auroc"] = auroc(y, p); out["caught_liu"] = caught_liu(y, p, f); out["caught_guar"] = caught_guar(y, p, f)
    # one resample loop for the three bootstrapped metrics
    rng = np.random.default_rng(seed)
    if clusters is None:
        groups = [np.array([i]) for i in range(len(y))]
    else:
        c = np.asarray(clusters); groups = [np.where(c == g)[0] for g in np.unique(c)]
    A, L, G = [], [], []
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[k] for k in pick]); yy, pp = y[idx], p[idx]
        if yy.min() == yy.max():
            continue
        A.append(auroc(yy, pp)); L.append(caught_liu(yy, pp, f)); G.append(caught_guar(yy, pp, f))
    for key, vals in (("auroc", A), ("caught_liu", L), ("caught_guar", G)):
        lo, hi = (np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan))
        out[f"{key}_lo"], out[f"{key}_hi"] = float(lo), float(hi)
    out["interval_caught_lo"], out["interval_caught_hi"], out["interval_width"] = interval_width(y, p, f)
    out["caught_0.5"] = float((p[y == 1] >= 0.5).mean())
    return out
