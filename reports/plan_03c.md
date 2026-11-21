# Plan for notebook 03c: busy-request pairs, judged on a held-out agent test

Question. Notebook 03b's request-conditioned guard fixed the delegated records but let more AgentDojo attacks through.
Its audit (reports/audit_03b.md, read against src/request_pairs.py) traced this to the training data: every attacked
example came with a short question or a "summarize" request, every request asking the agent to act was labelled
harmless (except delegation to a different record), and no agent-side request was longer than 229 characters. Does
adding the missing contrast (busy and long requests beside attacked and clean content, and one-line tool outputs)
remove the shortcut without losing what 03b gained, and does the result hold on an agent test none of this work has
looked at?

Label rule (notebook 03b's). Content is an injection when it holds an instruction to act that the request does not call
for; a request calls for an instruction when it states it or delegates to the record that holds it.

Base model and recipe. patronus-studio/wolf-defender-prompt-injection at revision af0b16a1d40ca246595e48246ccf9f906a52a50e; notebook 03b's recipe (word embeddings frozen,
class-weighted cross-entropy, AdamW 1e-05, 2 epochs, 8 x 2 per step, 1024 tokens, checkpoint with the lowest
macro validation loss among 4 evaluations per epoch); seeds [0, 1, 2].

Training data (src/busy_pairs.py). Notebook 03b's req training pack, with whole content groups removed until as many rows
are gone as the new rows add, plus the new rows, so the pack has 03b's size. New rows, from notebook 03's instruction
units and training families (seed 0): 1500 attacked contents, each as inject_busy (a request asking for one to four
actions of its own, none the embedded instruction; in 40% of them one action is of the same kind aimed elsewhere;
label 1) and authorised_busy (the same request with the embedded instruction added, same content; label 0), and in
30% of them also under the short request that produced the content (label 1); 750 clean contents under busy
requests (host_busy, 0); 500 one-line outputs with an injection (1) and 250 without (0). 50% of busy requests are long
(three to six sentences, names, amounts, account and order numbers, up to about 750 characters); 40% of attacked busy
contents are one-line outputs; 25% of the other contents are printed as Python dictionaries. Validation: 03b's validation
pack plus the same forms from the held-out families (300 attacked contents), minus any content that occurs in training.
Placeholders only; nothing from AgentDojo, tau-bench, AgentDrift, InjecAgent, BIPIA or the second source: the one-line
formats are written in this repository's words, not copied from the outputs read in the AgentDojo audit or in the seven
AgentDrift training records.

Evaluation views. Notebook 03b's request views of notebook 01's ten sets, unchanged and hash-checked (03b's caches are
reused), except tau-bench: its user_request field is the user simulator's brief, so the request is the brief with the
sentences giving the simulated customer's name, zip code, email, user id or a bare list of character traits removed
(busy_pairs.task_request, a fixed rule written before scoring); the brief as before is still scored and reported.
Held-out agent test: AgentDrift (arXiv 2609.06972, CC BY 4.0), task-disjoint test split, file data_taskdisjoint/test.jsonl at commit
014a514fa998, sha256 df1c15dd6f25f52d..., downloaded only after this plan is committed. During design seven
records of its training split were opened (format and labels) and task and output lengths were counted on the training
split; the test split was not opened. Rows (src/agentdrift.py): positives are the observations carrying the injection
(injection_point and failed_injection steps); negatives are every step of benign and hard-negative trajectories; other
steps (before or after the poisoned step, and the outputs of hijacked actions) are reported only. Request models read
"User request: <task> / Content: <observation>"; the released weights and notebook 03's model read the observation alone.
Clusters for bootstraps: the task string. A masked view (addresses replaced by in-world or external placeholders, dollar
amounts by $100) is reported, not marked. The from-scratch DeBERTa guard is not scored on AgentDrift.

Models compared on identical rows: the released weights (content only; on AgentDrift scored here at the pinned revision,
on the other sets notebook 01's caches); the released weights with the request shown (untrained); notebook 03's model
(content only); notebook 03b's request models (seeds 0 to 2) and its no-pairs model; the three 03c models.

Marks (read on busy at seed 0; Liu's rule; M1 to M4 identical to notebooks 03 and 03b).
  M1  second source: caught at or above 0.9, and the paired difference against the released weights with its lower
      end above 0.
  M2  AD-Matched, AD-Shift, tau-bench: lower end of the paired difference at or above -0.05.
  M3  BIPIA pairs, BIPIA documents (hijack), BIPIA documents (harmful): lower end at or above -0.05.
  M4  false positives at 0.5: at most 0.01 on AD-Clean, the tau-bench clean outputs and the recipes; at most 0.05 on
      NotInject.
  H1  AgentDrift (held out): caught at 1 percent false positives, paired difference against the released weights with its
      lower end at or above -0.05; and false positives at 0.5 at most 0.01 on benign-trajectory steps and at most 0.01 on
      hard-negative steps.
  R2  busy (seed 0) minus 03b's request model (seed 0) on AgentDrift, paired, lower end above 0 (reported beside the decision).
AgentDojo is development data from this notebook on: the busy forms exist because of an audit of AgentDojo records.

Decision. HOLDS (ACROSS SEEDS when seeds 1 and 2 pass M1 to M4 and H1 too) / CLOSES THE BLIND SPOT AT A COST (M1 passes,
others named) / DOES NOT CLOSE THE BLIND SPOT (M1 fails), with H1 stated either way; R2 reported as THE BUSY-REQUEST
PAIRS MATTER or DO NOT SEPARATE. All numbers reported whatever the branch.

Stop rule. If H1 fails, no further training version is built from these sets; the next step is a plain assessment of what
the committed results support. AgentDrift's misses are not read for design in this notebook.

Outputs. reports/sets_03c.csv, examples_03c.md, training_03c.csv, continued_03c.csv, clean_03c.csv, paired_03c.csv,
agentdrift_03c.csv, agentdojo_suites_03c.csv, decision_03c.txt; figures/continued_03c.png (600 dpi).
