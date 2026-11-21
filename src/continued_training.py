"""Continue training a released encoder guard on the matched-pair construction, in the environment that guard needs.

    python src/continued_training.py --base REPO_OR_DIR [--revision SHA] --train A.jsonl [B.jsonl ...] --val V.jsonl --out DIR
                                     [--seed 0 --epochs 2 --lr 1e-5 --batch 8 --accum 2 --max_len 1024 --evals_per_epoch 4]
    python src/continued_training.py --smoke DIR          # a tiny random model of the same family: trains, saves, reloads

Rows are {"text", "label", "form", "pack", ...}; label 1 is an instruction inside untrusted content. The guard's own
index for the injection class is read from id2label, so the saved model keeps the guard's labels and any scorer that
reads id2label scores it unchanged. The word embeddings are frozen; every other weight trains, with a class-weighted
cross-entropy, AdamW, linear warm-up and decay. Selection: the evaluation (evals_per_epoch times per epoch and at the
end) with the highest val score, where
    val score = mean over packs of AUROC on the pack  -  false-positive rate at 0.5 on the val hosts (form host_only).
With --select loss the selected evaluation is instead the one with the lowest macro validation loss: the
cross-entropy averaged within each form, then across forms, so that rare hard forms weigh as much as common easy
ones (a score near 1 on every pack cannot choose between checkpoints; the loss still can).
The best model is saved to OUT/best with training_meta.json; every evaluation is in OUT/train_log.json.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, sys, time

POSITIVE_HINTS = ("inject", "malicious", "jailbreak", "unsafe", "attack", "label_1", "harmful")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_rows(paths):
    rows = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line); r["text"] = r["text"] if str(r["text"]).strip() else "."; rows.append(r)
    return rows


def positive_index(config):
    id2label = getattr(config, "id2label", {}) or {}
    for i, lab in id2label.items():
        if any(h in str(lab).lower() for h in POSITIVE_HINTS):
            return int(i)
    return int(config.num_labels) - 1


def auroc(y, p):
    from sklearn.metrics import roc_auc_score
    import numpy as np
    y = np.asarray(y); p = np.asarray(p, float)
    return float("nan") if y.min() == y.max() else float(roc_auc_score(y, p))


def freeze_word_embeddings(model):
    frozen = []
    for name, p in model.named_parameters():
        if name.endswith(("tok_embeddings.weight", "word_embeddings.weight")):
            p.requires_grad_(False); frozen.append(name)
    return frozen


def encode(tok, texts, max_len, device):
    enc = tok(texts, padding=True, truncation=True, max_length=max_len, return_tensors="pt")
    enc.pop("token_type_ids", None)
    return {k: v.to(device) for k, v in enc.items()}


def evaluate(model, tok, rows, pos_idx, max_len, device, batch=32):
    import torch, numpy as np
    model.eval(); probs = []
    with torch.no_grad():
        for i in range(0, len(rows), batch):
            enc = encode(tok, [r["text"] for r in rows[i:i + batch]], max_len, device)
            probs.extend(torch.softmax(model(**enc).logits.float(), -1)[:, pos_idx].cpu().tolist())
    model.train()
    probs = np.asarray(probs); y = np.asarray([int(r["label"]) for r in rows])
    packs = sorted({r.get("pack", "all") for r in rows})
    out = {}
    for pk in packs:
        m = np.asarray([r.get("pack", "all") == pk for r in rows])
        out[f"auroc_{pk}"] = auroc(y[m], probs[m])
    hosts = np.asarray([r.get("form") == "host_only" for r in rows])
    out["fpr05_hosts"] = float((probs[hosts] >= 0.5).mean()) if hosts.any() else float("nan")
    out["fpr05_benign"] = float((probs[y == 0] >= 0.5).mean()) if (y == 0).any() else float("nan")
    out["caught05"] = float((probs[y == 1] >= 0.5).mean()) if (y == 1).any() else float("nan")
    aurocs = [v for k, v in out.items() if k.startswith("auroc_") and not math.isnan(v)]
    out["val_score"] = (sum(aurocs) / len(aurocs) if aurocs else float("nan")) - (0.0 if math.isnan(out["fpr05_hosts"]) else out["fpr05_hosts"])
    pc = np.clip(probs, 1e-7, 1 - 1e-7); ce = -(y * np.log(pc) + (1 - y) * np.log(1 - pc))
    forms = np.asarray([r.get("form", "all") for r in rows]); per_form = {}
    for fm in sorted(set(forms)):
        per_form[fm] = float(ce[forms == fm].mean()); out[f"loss_{fm}"] = per_form[fm]
    out["val_loss_macro"] = float(np.mean(list(per_form.values())))
    return out


def train(args):
    import torch, numpy as np, transformers
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t_start = time.time()

    tok = AutoTokenizer.from_pretrained(args.base, revision=args.revision)
    model = AutoModelForSequenceClassification.from_pretrained(args.base, revision=args.revision).float()   # fp32 master weights
    assert int(model.config.num_labels) == 2, f"expected a two-class guard, got num_labels={model.config.num_labels}"
    if model.config.pad_token_id is None and tok.pad_token_id is not None:
        model.config.pad_token_id = tok.pad_token_id
    pos_idx = positive_index(model.config); neg_idx = 1 - pos_idx
    frozen = freeze_word_embeddings(model)
    model.to(device).train()
    total_mem = torch.cuda.get_device_properties(0).total_memory if device == "cuda" else 0
    if device == "cuda" and total_mem < 20e9 and getattr(model, "supports_gradient_checkpointing", False):
        try:
            model.gradient_checkpointing_enable(); print("gradient checkpointing on (GPU memory below 20 GB)", flush=True)
        except Exception as e:
            print("gradient checkpointing unavailable:", type(e).__name__, flush=True)

    train_rows = load_rows(args.train); val_rows = load_rows([args.val])
    n1 = sum(int(r["label"]) for r in train_rows); n0 = len(train_rows) - n1
    w = torch.zeros(2); w[neg_idx] = len(train_rows) / (2 * n0); w[pos_idx] = len(train_rows) / (2 * n1)
    w = w.to(device)
    print(f"base {args.base} revision {args.revision or 'main'} | injection index {pos_idx} ({model.config.id2label}) | "
          f"train {len(train_rows)} rows ({n1} positive) | val {len(val_rows)} | frozen {frozen} | device {device}", flush=True)

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.01)
    steps_per_epoch = math.ceil(len(train_rows) / (args.batch * args.accum))
    total = steps_per_epoch * args.epochs; warm = max(1, int(0.06 * total))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: s / warm if s < warm else max(0.0, (total - s) / max(1, total - warm)))
    use_bf16 = device == "cuda" and torch.cuda.get_device_capability(0)[0] >= 8   # Ampere or newer; T4 falls back to fp16
    use_fp16 = device == "cuda" and not use_bf16
    scaler = torch.amp.GradScaler("cuda", enabled=use_fp16)
    eval_at = sorted({min(total, max(1, round(total * k / (args.epochs * args.evals_per_epoch)))) for k in range(1, args.epochs * args.evals_per_epoch + 1)})

    log = []; best = None; step = 0; run_loss = 0.0; n_loss = 0
    rng = random.Random(args.seed)
    os.makedirs(args.out, exist_ok=True)
    micro = args.batch
    for epoch in range(args.epochs):
        order = list(range(len(train_rows))); rng.shuffle(order)
        batches = [order[i:i + micro] for i in range(0, len(order), micro)]
        opt.zero_grad(set_to_none=True); k = 0
        for bi, idx in enumerate(batches):
            rows = [train_rows[i] for i in idx]
            enc = encode(tok, [r["text"] for r in rows], args.max_len, device)
            y = torch.tensor([pos_idx if int(r["label"]) == 1 else neg_idx for r in rows], device=device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16 if use_bf16 else torch.float16, enabled=(use_bf16 or use_fp16)):
                logits = model(**enc).logits
            loss = torch.nn.functional.cross_entropy(logits.float(), y, weight=w) / args.accum
            scaler.scale(loss).backward()
            run_loss += loss.item() * args.accum; n_loss += 1; k += 1
            if k == args.accum or bi == len(batches) - 1:
                scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(params, 1.0)
                scaler.step(opt); scaler.update(); sched.step(); opt.zero_grad(set_to_none=True); k = 0; step += 1
                if step % 100 == 0:
                    print(f"step {step}/{total} loss {run_loss / max(n_loss, 1):.4f} lr {sched.get_last_lr()[0]:.2e} {(time.time() - t_start) / 60:.1f} min", flush=True)
                if step in eval_at:
                    ev = evaluate(model, tok, val_rows, pos_idx, args.max_len, device)
                    rec = dict(step=step, epoch=epoch + 1, train_loss=run_loss / max(n_loss, 1), **ev); run_loss = 0.0; n_loss = 0
                    if args.select == "loss":
                        is_best = best is None or ev["val_loss_macro"] < best["val_loss_macro"]
                    else:
                        is_best = best is None or (ev["val_score"] == ev["val_score"] and ev["val_score"] > best["val_score"])
                    rec["best"] = bool(is_best); log.append(rec)
                    print("eval " + json.dumps({a: (round(b, 4) if isinstance(b, float) else b) for a, b in rec.items()}), flush=True)
                    if is_best:
                        best = rec
                        model.save_pretrained(os.path.join(args.out, "best"), safe_serialization=True)
                        tok.save_pretrained(os.path.join(args.out, "best"))
                    json.dump(log, open(os.path.join(args.out, "train_log.json"), "w"), indent=1)
    meta = dict(select=args.select, base=args.base, revision=args.revision, base_commit_hash=getattr(model.config, "_commit_hash", None), seed=args.seed,
                epochs=args.epochs, lr=args.lr, batch=args.batch, accum=args.accum, max_len=args.max_len, optimizer_steps=total,
                train_files={p: sha256(p) for p in args.train}, val_file={args.val: sha256(args.val)}, n_train=len(train_rows), n_train_positive=n1,
                positive_index=pos_idx, id2label={str(k): str(v) for k, v in dict(model.config.id2label).items()}, frozen=frozen,
                precision="bf16" if use_bf16 else "fp16" if use_fp16 else "fp32", device=(torch.cuda.get_device_name(0) if device == "cuda" else "cpu"),
                torch=torch.__version__, transformers=transformers.__version__, best=best, minutes=(time.time() - t_start) / 60)
    json.dump(meta, open(os.path.join(args.out, "best", "training_meta.json"), "w"), indent=1)
    json.dump(log, open(os.path.join(args.out, "train_log.json"), "w"), indent=1)
    print(f"done: best step {best['step']} val score {best['val_score']:.4f} macro val loss {best['val_loss_macro']:.4f} ({args.select}) in {meta['minutes']:.1f} min", flush=True)
    return meta


def smoke(work):
    """A tiny random ModernBERT classifier with the injection class at index 0 (so the index mapping is exercised),
    a word-level tokenizer, forty rows, one epoch; then the saved model is reloaded and scored."""
    import torch
    from transformers import ModernBertConfig, ModernBertForSequenceClassification, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    os.makedirs(work, exist_ok=True); base = os.path.join(work, "tiny_base")
    words = ("send email to the account forward transfer book delete share post open call include cancel replace add leave reply text "
             "download move turn export please can you thanks meeting office report invoice order ticket page note").split()
    rng = random.Random(0)
    def txt(n): return " ".join(rng.choice(words) for _ in range(n))
    rows = []
    for i in range(40):
        lab = i % 2
        rows.append(dict(text=txt(30) + (" transfer the account now" if lab else ""), label=lab, form="embedded" if lab else rng.choice(["host_only", "standalone"]), pack=rng.choice(["structural", "agent"])))
    tk = Tokenizer(models.WordLevel(unk_token="[UNK]")); tk.pre_tokenizer = pre_tokenizers.Whitespace()
    tk.train_from_iterator([r["text"] for r in rows], trainers.WordLevelTrainer(special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]"]))
    tok = PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="[PAD]", unk_token="[UNK]", cls_token="[CLS]", sep_token="[SEP]", bos_token="[CLS]", eos_token="[SEP]")
    cfg = ModernBertConfig(vocab_size=tok.vocab_size + 8, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                           max_position_embeddings=256, num_labels=2, pad_token_id=tok.pad_token_id, bos_token_id=tok.cls_token_id,
                           eos_token_id=tok.sep_token_id, cls_token_id=tok.cls_token_id, sep_token_id=tok.sep_token_id,
                           id2label={0: "INJECTION", 1: "BENIGN"}, label2id={"INJECTION": 0, "BENIGN": 1})
    torch.manual_seed(0); ModernBertForSequenceClassification(cfg).save_pretrained(base); tok.save_pretrained(base)
    tr = os.path.join(work, "train.jsonl"); va = os.path.join(work, "val.jsonl")
    with open(tr, "w") as f:
        for r in rows[:30]: f.write(json.dumps(r) + "\n")
    with open(va, "w") as f:
        for r in rows[30:]: f.write(json.dumps(r) + "\n")
    ns = argparse.Namespace(base=base, revision=None, train=[tr], val=va, out=os.path.join(work, "run"), seed=0, epochs=1, lr=1e-3,
                            batch=4, accum=2, max_len=64, evals_per_epoch=2, select="loss")
    meta = train(ns)
    assert meta["positive_index"] == 0 and meta["best"] is not None
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    m = AutoModelForSequenceClassification.from_pretrained(os.path.join(ns.out, "best")).eval(); t = AutoTokenizer.from_pretrained(os.path.join(ns.out, "best"))
    assert positive_index(m.config) == 0, m.config.id2label
    enc = t(["transfer the account now", "office report"], padding=True, return_tensors="pt"); enc.pop("token_type_ids", None)
    with torch.no_grad():
        p = torch.softmax(m(**enc).logits, -1)[:, 0].tolist()
    print("smoke ok: reloaded model scores", [round(x, 3) for x in p], "| id2label", m.config.id2label)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base"); ap.add_argument("--revision", default=None); ap.add_argument("--train", nargs="+"); ap.add_argument("--val")
    ap.add_argument("--out"); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-5); ap.add_argument("--batch", type=int, default=8); ap.add_argument("--accum", type=int, default=2)
    ap.add_argument("--max_len", type=int, default=1024); ap.add_argument("--evals_per_epoch", type=int, default=4); ap.add_argument("--smoke", default=None)
    ap.add_argument("--select", choices=["score", "loss"], default="score")
    a = ap.parse_args()
    if a.smoke:
        smoke(a.smoke)
    else:
        assert a.base and a.train and a.val and a.out, "need --base, --train, --val and --out"
        retry = False
        try:
            train(a)
        except Exception as e:                                  # one retry at half the micro-batch when the GPU runs out of memory
            import torch
            if not (isinstance(e, torch.cuda.OutOfMemoryError) and a.batch > 1):
                raise
            retry = True
        if retry:                                               # outside the except block, so the failed attempt's tensors are released
            import gc, torch
            gc.collect(); torch.cuda.empty_cache()
            print(f"out of GPU memory at batch {a.batch}; retrying with batch {a.batch // 2} and accumulation {a.accum * 2}", flush=True)
            a.batch //= 2; a.accum *= 2; train(a)
