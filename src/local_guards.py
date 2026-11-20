"""Score this repository's continued-training checkpoints the way guard_runners scores a released guard, in the
environment their transformers version needs, with the same cache record so panel_metrics reads both alike.

    python src/local_guards.py NAME MODEL_DIR MAX_LEN SET.jsonl OUT.json
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from guard_runners import POSITIVE_HINTS, BS, cache_path, device


def positive_index(config):
    id2label = getattr(config, "id2label", {}) or {}
    for i, lab in id2label.items():
        if any(h in str(lab).lower() for h in POSITIVE_HINTS):
            return int(i)
    return int(config.num_labels) - 1


def score_local(model_dir, max_len, texts):
    """Probability of the injection class, truncated at max_len tokens (the released guard's documented input length)."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = device()
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(dev).eval()
    if model.config.pad_token_id is None and tok.pad_token_id is not None:
        model.config.pad_token_id = tok.pad_token_id
    idx = positive_index(model.config)
    probs, trunc = [], 0
    for i in range(0, len(texts), BS):
        batch = [t if t.strip() else "." for t in texts[i:i + BS]]
        trunc += sum(len(tok(t, add_special_tokens=True)["input_ids"]) > max_len for t in batch)
        enc = tok(batch, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(dev)
        enc.pop("token_type_ids", None)
        with torch.no_grad():
            probs.extend(torch.softmax(model(**enc).logits.float(), -1)[:, idx].cpu().tolist())
    meta_path = os.path.join(model_dir, "training_meta.json")
    training = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    meta = {"positive_index": idx, "id2label": {str(k): str(v) for k, v in dict(model.config.id2label or {}).items()}, "model_dir": model_dir,
            "max_len": max_len, "base": training.get("base"), "base_revision": training.get("revision"), "best_step": (training.get("best") or {}).get("step")}
    return probs, trunc / max(len(texts), 1), meta


def score_cached_local(name, model_dir, max_len, set_name, rows, cache_dir, set_hash, python):
    """Runs the scorer in the given interpreter unless the cache for (name, set) exists."""
    out = cache_path(cache_dir, name, set_name)
    if os.path.exists(out):
        return json.load(open(out))
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for r in rows:
        tmp.write(json.dumps(r) + "\n")
    tmp.close()
    r = subprocess.run([python, os.path.abspath(__file__), name, model_dir, str(max_len), tmp.name, out], capture_output=True, text=True,
                       env=dict(os.environ, SET_HASH=set_hash, SET_NAME=set_name))
    os.unlink(tmp.name)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(r.stderr[-2500:])
    return json.load(open(out))


if __name__ == "__main__":
    name, model_dir, max_len, set_path, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
    rows = [json.loads(l) for l in open(set_path, encoding="utf-8")]
    probs, trunc, meta = score_local(model_dir, max_len, [r["text"] for r in rows])
    rec = dict(detector=name, set=os.environ.get("SET_NAME", os.path.basename(set_path)), set_hash=os.environ.get("SET_HASH", ""), n=len(rows),
               probs=[float(p) for p in probs], labels=[int(r["label"]) for r in rows] if rows and "label" in rows[0] else None,
               truncated=float(trunc), meta=meta)
    json.dump(rec, open(out, "w"))
    print(name, len(rows), "scored")
