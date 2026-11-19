# Plan for notebook 01: the guard panel on public sets

Question. Where does every detector stand, including the guards released in 2026 and this project's own models, on
evaluation sets a reviewer can regenerate, and what number must notebook 03's model reach on agent tool outputs?

Sets.
- AD-Clean: AgentDojo v1.2 ground-truth tool calls replayed without a model and without injections; all benign.
- AD-Matched: the same replay with AgentDojo's important_instructions, ignore_previous and direct attacks in the
  injection slots; a tool output is positive when it differs from the clean replay of the same call.
- AD-Shift: as AD-Matched with the tool_knowledge, injecagent, system_message, important_instructions_no_names and
  important_instructions_wrong_model_name attacks.
- BIPIA pairs: every clean email, table and code context of BIPIA (train and test) once as benign and four times with
  one of BIPIA's own attack strings inserted at the start, middle or end; metrics use the test-half attacks only.
- TB-eval: tau-bench retail and airline tool calls replayed without a model (benign) plus the retail replays whose
  product names carry an InjecAgent attacker instruction (injected by differential replay).
- This project's own sets, as in the paper: BIPIA documents (210 hijack and harmful injections at the end of 778 hosts),
  the second indirect source (Open-Prompt-Injection construction), the AgentDojo slot set of notebook 25, NotInject and
  the 500 recipes.
All builders are the published ones (lzwhehe/benign-instruction-bench, MIT) with paths changed; counts are printed
beside the published counts.

Detectors. The paper's seven released guards; Horizon-Labs prompt-injection-guard-base at revision af3c52e6 (the
weights Liu scored) and at the current revision; Wolf Defender; Prismor-1.5B; Sheltron; further open guards where they
load; this project's models (full seeds 0, 1, 2; no-twin ablation; size-matched; paraphrase-augmented; conventional
fine-tune), each scored truncated at 512 tokens and as the maximum over 512-token windows.

Metrics. AUROC; share of injections caught at 1 percent false positives with the threshold set on the evaluated set's
benign scores (Liu's rule) and at the guaranteed threshold (this project's rule, strict_threshold); the width of the
identification interval of the 1 percent threshold; false-positive rate and task-level block rate at the default 0.5 on
AD-Clean and the tau-bench clean outputs. 95 percent intervals by cluster bootstrap over tasks where a task key exists
(1,000 resamples), otherwise over rows.

Outputs. reports/sets_01.csv (every set, its rows by label and its hash), reports/public_panel_01.csv (detector by set),
reports/clean_outputs_01.csv (false positives and block rates on clean tool outputs), reports/bar_03.json (Horizon-Labs
at revision af3c52e6: caught at 1 percent on AD-Matched and AD-Shift by both rules, block rate on AD-Clean),
reports/decision_01.txt, figures/public_panel_01.png at 600 dpi.

Rule for notebook 03. Its first mark is to meet or exceed the two caught-at-1-percent numbers in bar_03.json on the
same set files (hash-checked) under Liu's rule, with the cluster-bootstrap interval of the difference clear of zero.
No pass or fail is attached to this notebook.
