"""Busy-request pairs: labels follow the forms, a busy pair differs only in whether the request holds the embedded
instruction, the family split is notebook 03's, requests stay under the cap, placeholders are scrubbed, the pack
subsampling keeps whole content groups, and the tau-bench rule removes only identity and trait sentences."""
import os, sys, random
from collections import defaultdict
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import busy_pairs as bp
import request_pairs as rp

SMALL = dict(n_items={"train": 200, "val": 60}, n_host_busy={"train": 80, "val": 20}, n_oneline_inject={"train": 60, "val": 20},
             n_oneline_host={"train": 30, "val": 10}, n_hosts={"train": 120, "val": 40})


def test_forms_split_and_pairs():
    ds, meta = bp.build_busy(seed=0, **SMALL)
    _, rmeta = rp.build_dataset(seed=0, n_items={"train": 60, "val": 20}, n_hosts={"train": 40, "val": 10})
    assert meta["action_family_split"] == rmeta["action_family_split"], "the held-out families must be notebooks 03 and 03b's"
    for sp, rows in ds.items():
        n = bp.check_busy(rows)
        assert n >= 0.9 * SMALL["n_items"][sp]
        assert {"inject_busy", "authorised_busy", "host_busy", "inject", "host_only"} <= {r["form"] for r in rows}
    tr = {r["family"] for r in ds["train"] if r["form"] == "inject_busy"}; va = {r["family"] for r in ds["val"] if r["form"] == "inject_busy"}
    assert tr and va and not (tr & va)


def test_minimal_difference_and_shares():
    ds, _ = bp.build_busy(seed=1, **SMALL)
    rows = ds["train"]; by = defaultdict(dict)
    for r in rows:
        by[r["content_id"]][r["form"]] = r
    pairs = [f for f in by.values() if "inject_busy" in f and "authorised_busy" in f]
    for f in pairs:
        a, b = f["inject_busy"], f["authorised_busy"]
        assert (a["label"], b["label"]) == (1, 0) and a["content"] == b["content"] and len(b["request"]) > len(a["request"])
    busy = [r for r in rows if r["form"] == "inject_busy"]
    assert 0.35 < sum(r["long"] for r in busy) / len(busy) < 0.65
    assert 0.25 < sum(r["same_kind"] for r in busy) / len(busy) < 0.55
    assert max(len(r["request"]) for r in rows) <= bp.MAX_REQUEST + 200          # a long read part can exceed the cap slightly
    assert any(len(r["request"]) > 300 for r in busy) and any(r["host_src"] == "oneline" for r in busy)
    assert any(r["fmt"] == "pydict" for r in rows) and any(r["fmt"] == "dict" for r in rows)


def test_same_kind_differs_from_embedded():
    ds, _ = bp.build_busy(seed=2, **SMALL)
    for r in ds["train"]:
        if r["form"] == "inject_busy" and r["same_kind"]:
            u = r["unit"]
            for fr in bp.FRAMES:
                u = u[len(fr):] if u.startswith(fr) else u
            assert bp._norm(u) not in bp._norm(r["request"])


def test_determinism_and_view():
    a, _ = bp.build_busy(seed=3, **SMALL); b, _ = bp.build_busy(seed=3, **SMALL)
    assert [r["text"] for r in a["train"]] == [r["text"] for r in b["train"]]
    r = a["train"][0]
    assert r["text"] == rp.view(r["request"], r["content"])


def test_drop_groups_keeps_whole_groups():
    ds, _ = bp.build_busy(seed=4, **SMALL)
    rows = ds["train"]; kept = bp.drop_groups(rows, 100, random.Random(0))
    assert len(rows) - len(kept) >= 100
    full = defaultdict(int); part = defaultdict(int)
    for r in rows: full[r["content_id"]] += 1
    for r in kept: part[r["content_id"]] += 1
    assert all(part[k] == full[k] for k in part)


def test_task_request_rule():
    b1 = "Your name is Sam Rivera and your zip code is 10001. You are calm, patient, organized. Return order #W1 via gift_card_1: Lamp; Cancel order #W2."
    assert bp.task_request(b1) == "Return order #W1 via gift_card_1: Lamp; Cancel order #W2."
    b2 = "You are sam_rivera_1234 living in Boston, USA, 02108. You want to exchange the kettle in your last order for a larger one."
    assert bp.task_request(b2) == "You want to exchange the kettle in your last order for a larger one."
    b3 = "You are mysterious and want to cancel all pending orders. Your email is sam.rivera@example.com. You are shy."
    assert bp.task_request(b3) == "You are mysterious and want to cancel all pending orders."
    b4 = "You are a bit impatient. Change the address on order #W3 to the one in your profile."
    assert bp.task_request(b4) == "Change the address on order #W3 to the one in your profile."
    assert bp.task_request("Your name is Sam.") == "Your name is Sam."                      # nothing left: unchanged
