"""Where this repository's inputs live.

PICALIB_DATA is the data folder of picalib-research on Drive. It is read only: every cache the guard work
depends on (the structural splits and models, the second source, the AgentDojo set, the rewrites) was produced
there and is never rewritten here. New files go under WANI_DATA.
"""
from __future__ import annotations
import os
from pathlib import Path

DRIVE = Path(os.environ.get("WANI_DRIVE", "/content/drive/MyDrive"))
PICALIB_REPO = DRIVE / "PICALIB_Research" / "picalib-research"
PICALIB_DATA = PICALIB_REPO / "data"
WANI_REPO = DRIVE / "WANI_Research" / "wani-research"
WANI_DATA = WANI_REPO / "data"

STRUCTURAL = PICALIB_DATA / "structural"                       # train/val/test.jsonl, model_*/best, scores/
MODEL_DIRS = {                                                 # notebooks 18, 19 and 24 of picalib-research
    "full": STRUCTURAL / "model_full" / "best",
    "full_seed1": STRUCTURAL / "model_full_seed1" / "best",
    "full_seed2": STRUCTURAL / "model_full_seed2" / "best",
    "ablation_no_twins": STRUCTURAL / "model_ablation_no_twins" / "best",
    "full_sizematched": STRUCTURAL / "model_full_sizematched" / "best",
    "full_aug": STRUCTURAL / "model_full_aug" / "best",
    "conventional_ft": STRUCTURAL / "model_conventional_ft" / "best",
}
SECOND_SOURCE = PICALIB_DATA / "opi" / "opi_eval.json"          # notebook 19
AGENTDOJO_SET = PICALIB_DATA / "agentdojo" / "set.json"         # notebook 25
PHASE5 = PICALIB_DATA / "phase5v2"                             # notebook 22: subset.json, rewrites.json, exec_out.json, judge_7b.json
REWRITES_12 = [PICALIB_DATA / "phase5v3" / "rewrites_full.json",   # notebook 30: twelve rewrites of all 210 injections
               PICALIB_DATA / "phase5v3" / "rewrites_extra.json"]
HOWTO = PICALIB_DATA / "closers" / "howto.json"                 # notebook 24: the 500 recipes


def picalib(*parts) -> Path:
    return PICALIB_DATA.joinpath(*parts)


def local(*parts) -> Path:
    p = WANI_DATA.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
