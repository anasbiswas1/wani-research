# Words Are Not Instructions

A text guard against indirect prompt injection, trained on matched pairs: every instruction appears once hidden inside a document (an injection) and once on its own as the user's request (benign), so the guard learns to score where an instruction sits, not what it says.

Part of the PICALIB project by Md Anas Biswas (School of Computing, University of Portsmouth). Shares its data caches and the released evaluation code with [picalib-research](https://github.com/anasbiswas1/picalib-research) (commit d7f77fe); see `src/PROVENANCE.md`.

Work in progress. Notebooks are numbered in the order they were run; every result table is written to `reports/` by the notebook that produced it.
