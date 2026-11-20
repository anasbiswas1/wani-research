# Plan for notebook 03: continued training of the strongest public guard on the matched-pair construction

Question. Does continuing the training of Wolf Defender, the strongest released guard of notebook 01, on the
matched-pair construction close its blind spot (the second indirect source, caught 0.447 at 1 percent false
positives; the BIPIA pairs, 0.835) without opening a new one on the agent tool outputs where it leads
(AD-Matched and AD-Shift 0.882, tau-bench 1.000) and without raising its false positives on clean outputs?

Base model. patronus-studio/wolf-defender-prompt-injection at revision af0b16a1d40ca246595e48246ccf9f906a52a50e (the weights notebook 01 scored; reports/revisions_01.json),
Apache-2.0. Trained and scored in the transformers>=5.6 environment; the released weights' scores are notebook 01's
caches, so every paired comparison is on identical rows.

Training data. Two packs, both matched-pair constructions.
(1) data/structural/train.jsonl of picalib-research (notebook 17): embedded instructions in SQuAD and AG News
    passages with their standalone twins, host-only, declarative and content-imperative controls.
(2) The agent-side pack of src/action_pairs.py (seed 0; 3000 embedded for training, 600 for
    validation): 24 families of tool actions (send, forward, transfer, book, delete, share, post, open, call, cancel,
    export) embedded in synthetic tool outputs (emails, calendar entries, files, search results, product listings,
    transactions, channel messages, orders, tickets, web pages; JSON, key-value or prose) and standalone as the user's
    own request; host-only, declarative and reader-directed-request controls; placeholders only. Families and hosts
    of the validation half are disjoint from the training half. Nothing from AgentDojo, tau-bench, InjecAgent or
    BIPIA is used.

Arms. twin = all five forms; notwin = positives with host-only and declarative controls only (the paper's
ablation_no_twins rule); sizematched = all forms with the negatives subsampled to the no-twin count.
Seeds: {'twin': [0, 1, 2], 'notwin': [0, 1, 2], 'sizematched': [0]}.

Recipe. Word embeddings frozen, every other weight trained; class-weighted cross-entropy; AdamW, learning rate 1e-05,
2 epochs, 8 x 2 sequences per step, 1024 tokens; mixed precision; selection among 4 evaluations per
epoch by mean AUROC over the structural and agent validation packs minus the false-positive rate at 0.5 on the
validation hosts. No evaluation set is read during training or selection.

Evaluation. The ten set files of notebook 01, hash-checked against reports/bar_03.json; 2,048-token scoring;
AUROC, caught at 1 percent false positives with the threshold on the evaluated set's benign scores (Liu's rule) and
at the guaranteed threshold; false positives and task-level block rate at 0.5 on clean outputs; cluster bootstraps
by task where a task key exists (1,000 resamples); paired differences on identical rows.

Marks (read on the twin arm at seed 0; Liu's rule).
  M1  second source: caught at or above 0.9 and the paired difference against the released weights with its
      lower end above 0.
  M2  AD-Matched, AD-Shift, tau-bench: lower end of the paired difference at or above -0.05.
  M3  BIPIA pairs, BIPIA documents (hijack), BIPIA documents (harmful): lower end of the paired difference at or
      above -0.05.
  M4  false positives at 0.5: at most 0.01 on AD-Clean, the tau-bench clean outputs and the recipes; at most
      0.05 on NotInject.
  T1  twin minus notwin on the second source, paired, lower end above 0 at every seed (the twin's part).

Decision.
  HOLDS                              M1 to M4 pass at seed 0 (ACROSS SEEDS when seeds 1 and 2 pass them too).
  CLOSES THE BLIND SPOT AT A COST    M1 passes, one of M2 to M4 fails; the failing sets are named.
  DOES NOT CLOSE THE BLIND SPOT      M1 fails.
  T1 is reported beside the decision as TWINS MATTER ON THIS BACKBONE or TWINS DO NOT SEPARATE.
All numbers are reported whatever the branch.

Outputs. reports/sets_03.csv, examples_03.md, training_03.csv, continued_03.csv, clean_03.csv, paired_03.csv,
decision_03.txt; figures/continued_03.png (600 dpi).
