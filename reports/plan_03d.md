# Plan for notebook 03d: twins and false alarms on AgentDrift (scoring only)

Models: notebook 03's continued Wolf Defender, arms twin (seeds [0, 1, 2]), no-twin (seeds [0, 1, 2]) and size-matched (seed 0),
and the released weights at revision af0b16a1d40c. Each reads the tool output alone. No training.
Rows: AgentDrift task-disjoint test split (sha256 df1c15dd6f25f52d...), notebook 03c's rows and views
(src/agentdrift.py): positives are observations carrying an injection; negatives are every step of benign and hard-negative
trajectories. Clusters: the task string.

T2 (the claim): at every seed s, false alarms at 0.5 on hard-negative steps, twin-s minus no-twin-s, paired cluster
bootstrap: upper end of the interval below 0.
Reported: size-matched minus no-twin (seed 0) on the same measure; false alarms at 0.5 on benign-trajectory steps; attacks
caught at 1 false alarm in 100 (Liu's rule) and AUROC, twin minus no-twin per seed; the masked view.
Decision: TWINS LOWER FALSE ALARMS ON THE HELD-OUT AGENT TEST when T2 holds at all three seeds; AT SOME SEEDS when it holds
at one or two; NO EFFECT ON THE HELD-OUT AGENT TEST otherwise. The catch rate is stated beside the decision whatever it is.
