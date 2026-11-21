"""Request-conditioned pairs: labels follow the forms, paired forms share content, delegation pairs differ only in
the request, the family split is notebook 03's, placeholders are scrubbed, and the document pack converts cleanly."""
import os, sys, random
from collections import defaultdict
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import request_pairs as rp
import action_pairs as ap
import structural_data as sd

SMALL = dict(n_items={"train": 240, "val": 80}, n_hosts={"train": 150, "val": 50})


def test_agent_pack_forms_and_split():
    ds, meta = rp.build_dataset(seed=0, **SMALL)
    for rows in ds.values():
        assert rp.check_pack(rows)
    assert {r["form"] for r in ds["train"]} == set(rp.FORMS)
    _, meta03 = ap.build_dataset(seed=0, n_embedded={"train": 60, "val": 20}, n_hosts={"train": 40, "val": 10})
    assert meta["action_family_split"] == meta03["action_family_split"], "the held-out families must be notebook 03's"
    tr = {r["family"] for r in ds["train"] if r["form"] == "inject"}; va = {r["family"] for r in ds["val"] if r["form"] == "inject"}
    assert not (tr & va)


def test_pairs_share_content_and_flip_label():
    ds, _ = rp.build_dataset(seed=1, **SMALL)
    by = defaultdict(dict)
    for r in ds["train"]:
        by[r["content_id"]][r["form"]] = r
    n_del = n_exp = 0
    for f in by.values():
        if "authorised_delegated" in f and "delegated_elsewhere" in f:
            a, b = f["authorised_delegated"], f["delegated_elsewhere"]
            assert a["content"] == b["content"] and a["request"] != b["request"] and (a["label"], b["label"]) == (0, 1)
            n_del += 1
        if "authorised_explicit" in f and "inject" in f:
            assert f["authorised_explicit"]["content"] == f["inject"]["content"]
            assert (f["authorised_explicit"]["label"], f["inject"]["label"]) == (0, 1)
            n_exp += 1
    assert n_del > 30 and n_exp > 30


def test_no_pairs_pack():
    ds, _ = rp.build_dataset(seed=0, pairs=False, **SMALL)
    for rows in ds.values():
        assert rp.check_pack(rows, pairs=False)
        assert not any(r["form"] in rp.PAIRED_FORMS for r in rows)


def test_view_and_determinism():
    a, _ = rp.build_dataset(seed=3, **SMALL); b, _ = rp.build_dataset(seed=3, **SMALL)
    assert [r["text"] for r in a["train"]] == [r["text"] for r in b["train"]]
    r = a["train"][0]
    assert r["text"] == rp.view(r["request"], r["content"]) and r["text"].startswith("User request: ") and "\n\nContent:\n" in r["text"]


def test_yaml_and_snippets():
    ds, _ = rp.build_dataset(seed=4, **SMALL)
    assert any(r["fmt"] == "yaml" for r in ds["train"] if r["form"] == "inject")
    sn = [r for r in ds["train"] if r["host_src"] == "snippet" and r["form"] == "inject"]
    assert sn and all(len(r["content"]) < 400 for r in sn)


def test_structural_conversion():
    rng = random.Random(0)
    words = "the report covers shipping prices in the city and the quarterly figures for the new office team".split()
    para = lambda: " ".join(" ".join(rng.choice(words) for _ in range(10)).capitalize() + "." for _ in range(3))
    hosts = [dict(text=para(), src="squad") for _ in range(200)]
    ds, _ = sd.build_dataset(hosts, seed=0, per_family=4, n_embedded={"train": 200, "val": 50, "test": 50})
    rows = rp.convert_structural(ds["train"], random.Random(1), pairs=True, n_short=100, split="train")
    assert rp.check_pack(rows)
    forms = {r["form"] for r in rows}
    assert {"inject", "authorised_explicit", "request_twin", "host_only"} <= forms and "authorised_delegated" not in forms
    assert any(r["host_src"] == "short" for r in rows)
    tw = [r for r in rows if r["form"] == "request_twin"]
    assert tw and all(r["label"] == 0 for r in tw)
    nopairs = rp.convert_structural(ds["train"], random.Random(1), pairs=False, n_short=100, split="train")
    assert rp.check_pack(nopairs, pairs=False)
