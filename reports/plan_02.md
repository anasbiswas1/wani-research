# Plan for notebook 02: the attacker's budget against every guard, counted target-aware

Question. As a paraphrasing attacker's budget grows from one attempt to thirteen, what share of the 210 BIPIA
injections gets past each guard and still works on the target, with the guard's threshold fixed before the attack?

Attempts. The 210 injections of the paper's full subset as written (attempt 1) and their twelve whole-document
rewrites by Qwen2.5-7B-Instruct (attempts 2 to 13), from the caches of picalib-research (phase5v3/subset_full.json,
rewrites_full.json, rewrites_extra.json). The rewrites were made once, without any guard in the loop.

Target-aware counting. An attempt counts only if the undefended Qwen2.5-3B-Instruct target carried the injection
out: cached outputs and judge verdicts of picalib-research (distill2/, phase5v3/, adaptive_strict/), strict rules of
its notebook 44 (emoji and base64 only when new to the output; scams only with markers and the judge; the other
categories by the validated 7B judge or the programmatic rule). The target and judge run here only for attempts with
no cached verdict, writing to this repository's own cache.

Guards. Every detector with a notebook-01 cache on the paper's BIPIA documents (ours_bipia); the notebook-03
checkpoints in data/continued/models.json where present. Threshold per guard: the guaranteed threshold at 0.01 false
positives on the 778 host documents, taken from the notebook-01 cache (identical rows); the default 0.5 beside it.

Measure. A guard misses an injection within k attempts when one of its first k attempts works on the target and
scores below the threshold. Reported for k = 1 to 13 (headline at (1, 4, 7, 13)): the miss share of all 210
injections; the no-guard ceiling (works within k attempts); the share of feasible attacks let through
(miss divided by ceiling); 95 percent bootstrap intervals over injections (1,000 resamples); the difference against
wolf-defender at 13 attempts, paired on the same injections; the miss share by BIPIA category at 13 attempts.

Decision. Measurement only; no pass or fail. The attacker is fixed; a guard-aware attacker is notebook 05.

Outputs. reports/variants_02.csv, budget_thresholds_02.csv, budget_curve_02.csv, budget_paired_02.csv,
budget_by_category_02.csv, decision_02.txt; figures/budget_curve_02.png (600 dpi).
