"""Score texts with released prompt-injection guards and with this project's own DeBERTa models, each run the way its
model card documents, with one JSON cache per (detector, set).

The released-guard runners (run_cls, run_segmented, run_sheltron, run_prismor) are adapted from scripts/score_many.py
of lzwhehe/benign-instruction-bench (commit 5d0ae7c, MIT License, Copyright (c) 2026 lzwhehe): the injection class is
read from id2label instead of being fixed, and results are cached. Everything else is this project's.

Command line (used for Wolf Defender, which needs a newer transformers than the rest of the panel):
    python src/guard_runners.py DETECTOR SET.jsonl OUT.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np

POSITIVE_HINTS = ("inject", "malicious", "jailbreak", "unsafe", "attack", "label_1", "harmful")
BS = 16

# name: (repo, kind, max_len, trust_remote_code, revision)
RELEASED = {
    # the seven guards of the paper
    "protectai-v1":      ("protectai/deberta-v3-base-prompt-injection",       "cls", 512, False, None),
    "protectai-v2":      ("protectai/deberta-v3-base-prompt-injection-v2",    "cls", 512, False, None),
    "promptguard2-86m":  ("meta-llama/Llama-Prompt-Guard-2-86M",              "seg", 512, False, None),
    "promptguard2-22m":  ("meta-llama/Llama-Prompt-Guard-2-22M",              "seg", 512, False, None),
    "deepset":           ("deepset/deberta-v3-base-injection",                "cls", 512, False, None),
    "fmops":             ("fmops/distilbert-prompt-injection",                "cls", 512, False, None),
    "piguard":           ("leolee99/PIGuard",                                 "cls", 512, True,  None),
    # guards released in 2026
    "horizon-base":        ("Horizon-Labs/prompt-injection-guard-base",       "cls", 2048, False, "af3c52e6a9d8bccc8e8c3ed4ba9d7fa084a47e33"),
    "horizon-base-latest": ("Horizon-Labs/prompt-injection-guard-base",       "cls", 2048, False, None),
    "wolf-defender":       ("patronus-studio/wolf-defender-prompt-injection", "cls", 2048, False, None),
    "prismor-1.5b":        ("prismor/prompt-guard-1.5b",                      "prismor", 512, False, None),
    "sheltron":            ("sheltron-ai/prompt-guard-68m",                   "sheltron", 1024, False, None),
    # further open guards, scored where they load
    "testsavant-large":    ("testsavantai/prompt-injection-defender-large-v0", "cls", 512, False, None),
    "injecguard":          ("leolee99/InjecGuard",                            "cls", 512, True,  None),
    "jasperls":            ("JasperLS/deberta-v3-base-injection",             "cls", 512, False, None),
    "qualifire-sentinel":  ("qualifire/prompt-injection-sentinel",            "cls", 2048, False, None),
    "protectai-small-v2":  ("protectai/deberta-v3-small-prompt-injection-v2", "cls", 512, False, None),
}
NEEDS_NEW_TRANSFORMERS = {"wolf-defender"}
# this project's models: name -> key in paths.MODEL_DIRS; scored with rule "trunc" (512 tokens) or "win" (max over 512-token windows)
OURS = {"wani-full-s0": "full", "wani-full-s1": "full_seed1", "wani-full-s2": "full_seed2", "wani-notwin": "ablation_no_twins",
        "wani-sizematched": "full_sizematched", "wani-aug": "full_aug", "wani-conventional": "conventional_ft"}
DISPLAY = {
    "protectai-v1": "ProtectAI v1", "protectai-v2": "ProtectAI v2", "promptguard2-86m": "Prompt-Guard-2 86M",
    "promptguard2-22m": "Prompt-Guard-2 22M", "deepset": "deepset DeBERTa", "fmops": "fmops DistilBERT", "piguard": "PIGuard",
    "horizon-base": "Horizon-Labs (Oct 2026 weights)", "horizon-base-latest": "Horizon-Labs (current weights)",
    "wolf-defender": "Wolf Defender", "prismor-1.5b": "Prismor-1.5B", "sheltron": "Sheltron 68M", "testsavant-large": "TestSavant L",
    "injecguard": "InjecGuard", "jasperls": "JasperLS", "qualifire-sentinel": "Qualifire Sentinel", "protectai-small-v2": "ProtectAI v2 small",
    "wani-full-s0": "Matched-pair guard (seed 0)", "wani-full-s1": "Matched-pair guard (seed 1)", "wani-full-s2": "Matched-pair guard (seed 2)",
    "wani-notwin": "No-twin ablation", "wani-sizematched": "Size-matched control", "wani-aug": "Paraphrase-augmented",
    "wani-conventional": "Conventional fine-tune",
}


def display_name(key):
    base, _, rule = key.partition(":")
    name = DISPLAY.get(base, base)
    return name + ({"trunc": ", truncated", "win": ", windowed"}.get(rule, ""))


def device():
    import torch
    return os.environ.get("DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")


def positive_index(model):
    id2label = getattr(model.config, "id2label", {}) or {}
    for i, lab in id2label.items():
        if any(h in str(lab).lower() for h in POSITIVE_HINTS):
            return int(i)
    return model.config.num_labels - 1


def run_cls(repo, max_len, remote, texts, revision=None, local_dir=None):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = device(); src = local_dir or repo
    tok = AutoTokenizer.from_pretrained(src, revision=revision)
    model = AutoModelForSequenceClassification.from_pretrained(src, trust_remote_code=remote, revision=revision).to(dev).eval()
    if model.config.pad_token_id is None and tok.pad_token_id is not None:
        model.config.pad_token_id = tok.pad_token_id
    idx = 1 if local_dir else positive_index(model)
    modern = "ModernBert" in str(getattr(model.config, "architectures", [""])[0])
    probs, trunc = [], 0
    for i in range(0, len(texts), BS):
        batch = [t if t.strip() else "." for t in texts[i:i + BS]]
        trunc += sum(len(tok(t, add_special_tokens=True)["input_ids"]) > max_len for t in batch)
        enc = tok(batch, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(dev)
        if modern:
            enc.pop("token_type_ids", None)
        with torch.no_grad():
            probs.extend(torch.softmax(model(**enc).logits.float(), -1)[:, idx].cpu().tolist())
    return probs, trunc / max(len(texts), 1), {"positive_index": idx, "id2label": {str(k): str(v) for k, v in (model.config.id2label or {}).items()}}


def run_segmented(repo, max_len, texts, pg1=False, local_dir=None, idx=None):
    """Prompt Guard cards: 512-token window; longer inputs split into segments, maximum score kept.
    Also the windowed rule for this project's DeBERTa models (local_dir, idx=1)."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = device(); src = local_dir or repo
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForSequenceClassification.from_pretrained(src).to(dev).eval()
    if idx is None:
        idx = positive_index(model)
    room = max_len - 2
    probs, trunc = [], 0
    for t in texts:
        body = tok.encode(t if t.strip() else ".", add_special_tokens=False)
        chunks = [body[j:j + room] for j in range(0, len(body), room)] or [body]
        trunc += len(chunks) > 1
        best = 0.0
        for j in range(0, len(chunks), BS):
            seqs = [[tok.cls_token_id] + c + [tok.sep_token_id] for c in chunks[j:j + BS]]
            L = max(len(x) for x in seqs)
            ids = torch.tensor([x + [tok.pad_token_id] * (L - len(x)) for x in seqs], device=dev)
            mask = torch.tensor([[1] * len(x) + [0] * (L - len(x)) for x in seqs], device=dev)
            with torch.no_grad():
                p = torch.softmax(model(input_ids=ids, attention_mask=mask).logits.float(), -1)
            s = (p[:, 1] + p[:, 2]) if pg1 else p[:, idx]
            best = max(best, s.max().item())
        probs.append(best)
    return probs, trunc / max(len(texts), 1), {"positive_index": idx, "rule": "max over windows"}


def source_type(r):
    s = r.get("suite", "")
    if s.startswith("bipia-"):
        return {"bipia-email": "email", "bipia-code": "code", "bipia-table": "table"}.get(s, "other")
    if s in ("workspace", "travel", "banking", "slack") or s.startswith("tau-") or s == "ours-agentdojo":
        return "tool_result"
    if s == "ours-bipia":
        return "email"
    return "other"


def run_sheltron(repo, max_len, rows):
    """Documented input of the Sheltron card: one untrusted tool_result segment with a source-type token."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    dev = device()
    tok = AutoTokenizer.from_pretrained(repo, use_fast=True)
    model = AutoModelForSequenceClassification.from_pretrained(repo).to(dev).eval()
    s = model.config.sheltron_prompt_guard["structural_tokens"]
    reserved = {s["segment_start"], s["segment_end"], s["task_content_scan"], *s["roles"].values(), *s["trust_levels"].values(), *s["source_types"].values()}
    stride = model.config.sheltron_prompt_guard.get("stride", 768)

    def ids(text):
        return [tok.unk_token_id if t in reserved else t for t in tok.encode(text, add_special_tokens=False)]

    def seg(role, trust, src, body):
        return [s["segment_start"], s["roles"][role], s["trust_levels"][trust], s["source_types"][src], *body, s["segment_end"]]

    probs, trunc = [], 0
    for r in rows:
        body = ids(r["text"] if r["text"].strip() else ".")
        prefix = [tok.cls_token_id, s["task_content_scan"]]
        src = source_type(r)
        src = src if src in s["source_types"] else "other"
        room = max_len - len(prefix) - 7
        windows = [body[j:j + room] for j in range(0, max(len(body) - room, 0) + 1, stride)] or [body]
        trunc += len(windows) > 1
        best = 0.0
        for w in windows:
            seq = prefix + seg("tool_result", "untrusted", src, w) + [tok.sep_token_id]
            with torch.no_grad():
                z = model(input_ids=torch.tensor([seq], device=dev), attention_mask=torch.ones((1, len(seq)), dtype=torch.long, device=dev)).logits[0, 0]
            best = max(best, torch.sigmoid(z.float()).item())
        probs.append(best)
    return probs, trunc / max(len(rows), 1), {"rule": "sheltron documented input"}


def run_prismor(repo, max_len, texts):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = device()
    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.bfloat16 if dev == "cuda" else torch.float32).to(dev).eval()
    sys_msg = ("You are a security classifier. Respond with exactly INJECTION if the "
               "prompt is a prompt injection attack, or SAFE if it is benign.")
    head = f"<|im_start|>system\n{sys_msg}<|im_end|>\n<|im_start|>user\nClassify this prompt:\n\n"
    tail = "<|im_end|>\n<|im_start|>assistant\n"
    inj = tok.encode("INJECTION", add_special_tokens=False)[0]
    safe = tok.encode("SAFE", add_special_tokens=False)[0]
    room = max_len - len(tok.encode(head + tail, add_special_tokens=False))
    probs, trunc = [], 0
    for t in texts:
        body = tok.encode(t if t.strip() else ".", add_special_tokens=False)
        trunc += len(body) > room
        text = tok.decode(body[:room])
        x = tok(head + text + tail, return_tensors="pt", add_special_tokens=False).to(dev)
        with torch.no_grad():
            lp = torch.log_softmax(model(**x).logits[0, -1].float(), -1)
        a, b = lp[inj].exp().item(), lp[safe].exp().item()
        probs.append(a / (a + b + 1e-12))
    return probs, trunc / max(len(texts), 1), {"rule": "P(INJECTION) / (P(INJECTION) + P(SAFE))"}


def model_dir_for(name):
    import paths
    return str(paths.MODEL_DIRS[OURS[name]])


def score_rows(detector: str, rows: list):
    """Returns (probs, truncated_fraction, meta) for one detector key on one list of rows (dicts with 'text')."""
    texts = [r["text"] for r in rows]
    base, _, rule = detector.partition(":")
    if base in OURS:
        d = model_dir_for(base)
        if rule == "win":
            return run_segmented(None, 512, texts, local_dir=d, idx=1)
        return run_cls(None, 512, False, texts, local_dir=d)
    repo, kind, max_len, remote, revision = RELEASED[base]
    if kind == "cls":
        return run_cls(repo, max_len, remote, texts, revision=revision)
    if kind == "seg":
        return run_segmented(repo, max_len, texts)
    if kind == "sheltron":
        return run_sheltron(repo, max_len, rows)
    if kind == "prismor":
        return run_prismor(repo, max_len, texts)
    raise ValueError(kind)


def cache_path(cache_dir, detector, set_name):
    return os.path.join(cache_dir, f"{detector.replace(':', '-')}__{set_name}.json")


def score_cached(detector: str, set_name: str, rows: list, cache_dir: str, set_hash: str = "", python_for_new_transformers: str | None = None):
    """Scores one (detector, set) unless its cache exists; Wolf Defender runs in the second environment."""
    out = cache_path(cache_dir, detector, set_name)
    if os.path.exists(out):
        return json.load(open(out))
    base = detector.partition(":")[0]
    if base in NEEDS_NEW_TRANSFORMERS:
        import subprocess, tempfile
        tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for r in rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        py = python_for_new_transformers or sys.executable
        r = subprocess.run([py, os.path.abspath(__file__), detector, tmp.name, out], capture_output=True, text=True,
                           env=dict(os.environ, SET_HASH=set_hash, SET_NAME=set_name))
        os.unlink(tmp.name)
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(r.stderr[-1500:])
        return json.load(open(out))
    probs, trunc, meta = score_rows(detector, rows)
    rec = dict(detector=detector, set=set_name, set_hash=set_hash, n=len(rows), probs=[float(p) for p in probs],
               labels=[int(r["label"]) for r in rows] if rows and "label" in rows[0] else None, truncated=float(trunc), meta=meta)
    json.dump(rec, open(out, "w"))
    try:
        import torch; torch.cuda.empty_cache()
    except Exception:
        pass
    return rec


if __name__ == "__main__":
    det, set_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = [json.loads(l) for l in open(set_path, encoding="utf-8")]
    probs, trunc, meta = score_rows(det, rows)
    rec = dict(detector=det, set=os.environ.get("SET_NAME", os.path.basename(set_path)), set_hash=os.environ.get("SET_HASH", ""), n=len(rows),
               probs=[float(p) for p in probs], labels=[int(r["label"]) for r in rows] if rows and "label" in rows[0] else None,
               truncated=float(trunc), meta=meta)
    json.dump(rec, open(out, "w"))
    print(det, len(rows), "scored")
