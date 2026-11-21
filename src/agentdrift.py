"""AgentDrift (arXiv 2609.06972, CC BY 4.0) as a held-out agent test for guards that read a tool output, with or
without the user's request.

AgentDrift holds synthetic tool-call trajectories in five domains (email, banking, web, coding, medical). Each step
has the tool's observation and one label: benign, injection_point, hijacked or failed_injection. A guard here reads
one observation (and, for the request-conditioned models, the trajectory's user task beside it). Rows:
  positive       the observation that carries the injected instruction (injection_point or failed_injection)  -> 1
  negative       every step of a benign or hard-negative trajectory (no injection anywhere in it)               -> 0
reported, not marked:
  before_poison  benign steps of attacked or failed-attack trajectories before the poisoned observation
  after_poison   benign steps after it (the run recovered or the attack failed)
  hijacked       the observations returned by the actions the attack caused
The task-disjoint split is used (no task template shared between its parts); only its test part is read, and only
after the notebook's plan is committed. Clusters for bootstraps: the task string (one template per cluster).

Masked view (the dataset authors' advice against memorised targets): every email address becomes
staff@company.example when its domain belongs to the trajectory's world (the user and their contacts) and
contact@external.example otherwise; every dollar amount becomes $100.
"""
from __future__ import annotations
import json, re

POSITIVE = ("injection_point", "failed_injection")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def world_domains(world):
    emails = [str((world or {}).get("email", ""))] + [str(c.get("email", "")) for c in (world or {}).get("contacts", []) or []]
    return sorted({e.split("@")[-1].strip().lower() for e in emails if "@" in e})


def mask(text, domains):
    dom = set(domains)
    text = EMAIL_RE.sub(lambda m: "staff@company.example" if m.group(0).split("@")[-1].lower() in dom else "contact@external.example", text)
    return MONEY_RE.sub("$100", text)


def _obs(o):
    return o if isinstance(o, str) else json.dumps(o, ensure_ascii=False)


def step_rows(records):
    rows = []
    for t in records:
        steps = t["steps"]; labels = [s["label"] for s in steps]
        first = next((k for k, l in enumerate(labels) if l in POSITIVE), None)
        clean_run = t["category"] in ("benign", "hard_negative")
        assert not (clean_run and first is not None), f"{t['id']}: a {t['category']} trajectory with a poisoned step"
        doms = world_domains(t.get("world"))
        for k, s in enumerate(steps):
            lab = s["label"]
            if lab in POSITIVE:
                role, y = "positive", 1
            elif clean_run:
                role, y = "negative", 0
            elif lab == "hijacked":
                role, y = "hijacked", 0
            else:
                role, y = ("before_poison" if first is None or k < first else "after_poison"), 0
            rows.append(dict(id=t["id"], step=k, agent=t["agent"], category=t["category"], source_category=t.get("source_category", t["category"]),
                             compliance=t.get("compliance") or "", step_label=lab, role=role, label=y, task=t["task"], obs=_obs(s["obs"]),
                             domains=doms, cluster=t["task"]))
    return rows


def views(rows, view_fn):
    """The four views: content alone, request and content, and both masked. view_fn(request, content) is the guard's format."""
    out = {}
    for masked in (False, True):
        for with_req in (False, True):
            name = "agentdrift" + ("_req" if with_req else "") + ("_masked" if masked else "")
            vs = []
            for r in rows:
                task, obs = (mask(r["task"], r["domains"]), mask(r["obs"], r["domains"])) if masked else (r["task"], r["obs"])
                d = {k: v for k, v in r.items() if k != "domains"}
                d.update(request=task, content=obs, text=view_fn(task, obs) if with_req else obs)
                vs.append(d)
            out[name] = vs
    return out


def summary(rows):
    from collections import Counter
    c = Counter(r["role"] for r in rows)
    return dict(trajectories=len({r["id"] for r in rows}), steps=len(rows), tasks=len({r["task"] for r in rows}), **{f"role_{k}": v for k, v in sorted(c.items())},
                hard_negative_steps=sum(r["category"] == "hard_negative" for r in rows))
