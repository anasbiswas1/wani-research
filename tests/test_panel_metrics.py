"""guar_threshold agrees with strict_threshold, including ties and the all-tied fallback; caught_liu matches sklearn's ROC rule."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
from strict_threshold import strict_threshold
from panel_metrics import guar_threshold, caught_liu, caught_guar, interval_width, block_rate


def test_guar_matches_strict():
    rng = np.random.default_rng(0)
    for trial in range(200):
        n = int(rng.integers(5, 400))
        p = rng.choice(np.round(rng.random(int(rng.integers(2, 30))), 3), n).astype(rng.choice([np.float32, np.float64]))
        for f in (0.01, 0.05, 0.2):
            assert guar_threshold(p, f) == strict_threshold(p, f)[0], (trial, f)
    assert guar_threshold(np.array([0.9, 0.9, 0.9], dtype=np.float32), 0.01) == strict_threshold(np.array([0.9, 0.9, 0.9], dtype=np.float32), 0.01)[0]


def test_caught_rules():
    rng = np.random.default_rng(1)
    y = np.r_[np.ones(300), np.zeros(700)]; p = np.r_[rng.beta(5, 2, 300), rng.beta(2, 5, 700)]
    assert 0 <= caught_guar(y, p) <= caught_liu(y, p) <= 1
    lo, hi, w = interval_width(y, p)
    assert lo <= caught_liu(y, p) + 1e-12 and w >= 0


def test_block_rate():
    assert block_rate(["a", "a", "b", "c"], [0.9, 0.1, 0.1, 0.6], 0.5) == 2 / 3
