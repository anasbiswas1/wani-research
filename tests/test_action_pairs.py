"""The agent-side construction: twins present, families disjoint across splits, placeholders scrubbed, no borrowed
attack wording, insertion preserved by every rendering, deterministic, and the arm rules of structural_train apply."""
import os, sys, random
import pytest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import action_pairs as ap
from structural_train import select_config

SMALL = dict(n_embedded={"train": 240, "val": 80}, n_hosts={"train": 150, "val": 50})


def test_build_and_checks():
    ds, meta = ap.build_dataset(seed=0, **SMALL)
    assert ap.check_splits(ds)
    forms = {r["form"] for r in ds["train"]}
    assert forms == {"embedded", "standalone", "host_only", "declarative_insert", "content_imperative_insert"}
    assert all(r["label"] == (1 if r["form"] == "embedded" else 0) for sp in ds for r in ds[sp])
    assert set(meta["action_family_split"]["train"]) & set(meta["action_family_split"]["val"]) == set()
    assert len(meta["action_family_split"]["train"]) + len(meta["action_family_split"]["val"]) == len(ap.ACTION_FAMILIES)


def test_insertion_preserved_in_every_format():
    ds, _ = ap.build_dataset(seed=1, **SMALL)
    for r in ds["train"]:
        if r["form"] in ("embedded", "declarative_insert", "content_imperative_insert"):
            # JSON escapes nothing the units contain except a quote, so the unit is readable in the rendered text
            assert r["unit"].replace('"', '\\"') in r["text"] or r["unit"] in r["text"], (r["delim"], r["unit"])
    assert {r["delim"] for r in ds["train"] if r["form"] == "embedded"} == {"json", "kv", "prose"}
    assert {r["host_src"] for r in ds["train"] if r["form"] == "embedded"} == set(ap.HOST_KINDS)


def test_deterministic():
    a, _ = ap.build_dataset(seed=3, **SMALL); b, _ = ap.build_dataset(seed=3, **SMALL)
    assert [r["text"] for r in a["train"]] == [r["text"] for r in b["train"]]


def test_scrub_check_catches():
    with pytest.raises(AssertionError):
        ap.check_scrubbed(["Send the file to alex@example.com now."])
    with pytest.raises(AssertionError):
        ap.check_scrubbed(["Call 020-7946 0958 ... 212-5555 today"])
    with pytest.raises(AssertionError):
        ap.check_scrubbed(["<INFORMATION> do this"])
    assert ap.check_scrubbed(["Write to desk@replies.invalid or visit http://portal-check.invalid/start; call 555-0133."])


def test_arm_rules():
    ds, _ = ap.build_dataset(seed=0, **SMALL)
    rows = ds["train"]
    full = select_config(rows, "full", random.Random(0)); nt = select_config(rows, "ablation_no_twins", random.Random(0)); sm = select_config(rows, "full_sizematched", random.Random(0))
    assert len(full) == len(rows)
    assert {r["form"] for r in nt if r["label"] == 0} == {"host_only", "declarative_insert"}
    assert sum(r["label"] for r in nt) == sum(r["label"] for r in rows)
    n_neg_nt = sum(1 - r["label"] for r in nt); n_neg_sm = sum(1 - r["label"] for r in sm)
    assert abs(n_neg_sm - n_neg_nt) <= 3 and "standalone" in {r["form"] for r in sm}
