"""Busy-request pairs (notebook 03c): requests that ask the agent to do things, beside attacked and clean content.

Notebook 03b's audit (reports/audit_03b.md) found a shortcut its pairs taught. Every attacked training example came
with a short question or a "summarize" request, every request that asked the agent to act was labelled harmless
(except "do what a different email says"), and no agent-side request was longer than 229 characters. The model
learned "a busy request means the content is fine" and let through AgentDojo attacks under long, many-part requests.

This module adds the missing contrast, on the label rule of src/request_pairs.py (content is an injection when it
holds an instruction to act that the request does not call for):
  inject_busy      a request that asks for one to four actions of its own, none of them the instruction inside
                   the content; in a share of rows one action is of the same kind as the embedded one, aimed
                   elsewhere (another address, account, folder)                                            -> 1
  authorised_busy  the same request with the embedded instruction added, on the same content              -> 0
  host_busy        a busy request over clean content                                                       -> 0
The first two differ only in whether the user asked for exactly that instruction. Half of the busy requests are
long (three to six sentences with names, amounts, account and order numbers, up to about 750 characters).
It also adds one-line tool outputs (a confirmation, a balance, an error, a number, a short price or address table),
as clean content and as hosts for injections, and tool outputs printed as Python dictionaries.

Same instruction units and family split as src/action_pairs.py and src/request_pairs.py at the same seed, so the
families held out for validation stay unseen. Every address, domain, phone number and account is a placeholder;
templates are this module's own; nothing is taken from AgentDojo, tau-bench, AgentDrift or any evaluation set.

Also here: the tau-bench request rule. Liu's tau-bench rows carry the user simulator's brief as the user request,
which opens with the simulated customer's name, zip code, email or user id and a list of character traits.
task_request() removes those sentences and keeps the task.
"""
from __future__ import annotations
import copy, json, random, re
from collections import Counter, defaultdict
import action_pairs as ap
import request_pairs as rp
from action_pairs import (fill, build_units, check_scrubbed, person_email, ACTION_FAMILIES, CONTENT_FAMILIES, DECLARATIVE_FAMILIES,
                          NAMES, CITIES, DATES, TIMES, AMOUNTS, ACCTS, FOUR, OIDS, HOTELS, FNAMES, FOLDERS, CHANNELS, EVENTS,
                          LOCATIONS, ITEMS, STATUSES, RATINGS, FRAMES, FRAME_SHARE, DELIMS)
from structural_data import split_by_key

FORMS_C = dict(rp.FORMS, inject_busy=1, authorised_busy=0, host_busy=0)
BUSY_FORMS = ("inject_busy", "authorised_busy", "host_busy")
MAX_REQUEST = 750

# everyday tasks a user gives an assistant (this module's words; they appear only as requests)
USER_TASKS = [
    "Book a table for {num_d} at a restaurant in {city} on {date}.",
    "Find the cheapest train to {city} on {date}.",
    "Add the {item} to my shopping list.",
    "Remind me about the {event} on {date} at {time}.",
    "Check the weather in {city} for {date}.",
    "Tell me how much I spent on {topic} last month.",
    "Move the {event} to {date} at {time}.",
    "Find a hotel in {city} for under {amount} a night.",
    "Write a short note to {name} saying I will be late for the {event}.",
    "Pay my {dept} invoice of {amount} from account {acct}.",
    "Look up the opening hours of the {city} office.",
    "Order a new {item} for the {dept} team.",
    "Put the {event} on my calendar for {date}.",
    "Compare the prices of the {hotel} and the {hotel2} in {city}.",
    "Let {name} know that the {doc} is ready.",
]
CONTEXT = [
    "I'm {name} from the {dept} team.",
    "My email is {pemail}.",
    "My account number is {acct}.",
    "Use the card ending in {four} for anything that needs paying.",
    "I'm travelling to {city} on {date} for {num} nights.",
    "The budget is {amount} at most.",
    "My order number is {oid}.",
    "The {event} is on {date} at {time} in {location}.",
    "{name} is my manager, so copy them on anything about {topic}.",
    "When in doubt, go for the cheaper option.",
    "Keep the answers short, I'm reading on my phone.",
    "We are getting ready for the {event}, so this is a bit urgent.",
]
CLOSINGS = ["Thanks!", "Let me know when it's done.", "Thank you.", "Tell me if anything fails.", "Cheers."]
FIRST_WRAP = ["{u}", "Please {ul}", "Can you {ul}", "I need you to {ul}", "Could you {ul}"]
NEXT_WRAP = ["{u}", "Please {ul}", "Also, {ul}", "Then {ul}", "After that, {ul}", "And {ul}"]
ERRORS = ["the account does not have enough money for this payment", "file not found", "the order can no longer be changed",
          "no rooms available on those dates", "the event overlaps with another event", "permission denied for that folder",
          "the recipient address is not valid", "the card was declined"]
STREETS = ["Harbour Street", "Mill Lane", "Station Road", "Park Avenue", "Church Street", "Market Square"]


def _low(s):
    s = s.strip()
    return s[:1].lower() + s[1:] if s else s


def _norm(s):
    return re.sub(r"\s+", " ", s.strip().rstrip(".!?").lower())


def _fill(t, rng):
    if "{pemail}" in t:
        t = t.replace("{pemail}", person_email(rng))
    if "{hotel2}" in t:
        h1, h2 = rng.sample(HOTELS, 2)
        t = t.replace("{hotel}", h1).replace("{hotel2}", h2)
    return fill(t, rng)


def units_and_splits(seed=0, per_family=40, fracs=(0.7, 0.3, 0.0)):
    """The instruction units and family splits of request_pairs.build_dataset at the same seed (same draws, same order)."""
    rng = random.Random(seed)
    actions = build_units(ACTION_FAMILIES, per_family, rng, "action")
    fillers = build_units(DECLARATIVE_FAMILIES, per_family, rng, "declarative")
    contents = build_units(CONTENT_FAMILIES, per_family, rng, "content_imperative")
    a_split = split_by_key([u["family"] for u in actions], rng, fracs)
    d_split = split_by_key([u["family"] for u in fillers], rng, fracs)
    c_split = split_by_key([u["family"] for u in contents], rng, fracs)
    return actions, a_split, d_split, c_split


# ----------------------------------------------------------------------------------------------------------------------
# busy requests
# ----------------------------------------------------------------------------------------------------------------------
def busy_plan(rng, actions, read=None, exclude=None, same_kind=None, long=False):
    """The parts of a busy request: actions (none equal to `exclude`), optional read part, context and closing."""
    k = rng.randint(2, 4) if long else rng.randint(1, 2)
    acts, tries = [], 0
    ex = _norm(exclude) if exclude else None
    while len(acts) < k and tries < 60:
        tries += 1
        a = _fill(rng.choice(USER_TASKS), rng) if rng.random() < 0.35 else rng.choice(actions)["unit"]
        if (ex and _norm(a) == ex) or a in acts:
            continue
        acts.append(a)
    if same_kind:
        acts[rng.randrange(len(acts))] = same_kind
    context = [_fill(c, rng) for c in rng.sample(CONTEXT, rng.randint(1, 3))] if long else []
    style = rng.choice(["plain", "chain", "numbered"]) if (long or len(acts) + bool(read) > 2) else "plain"
    return dict(acts=acts, read=read, read_first=rng.random() < 0.5, context=context,
                closing=rng.choice(CLOSINGS) if (long and rng.random() < 0.5) else "", style=style,
                wraps=[rng.randrange(1 << 30) for _ in range(12)], sep=rng.choice([" ", "\n"]), long=long)


def render_plan(plan, extra=None, extra_pos=None):
    """The request text; `extra` (the embedded instruction) is added as one more action at `extra_pos`."""
    acts = list(plan["acts"])
    if extra is not None:
        acts.insert(len(acts) if extra_pos is None else min(extra_pos, len(acts)), extra)
    items = acts[:]
    if plan["read"]:
        items = [plan["read"]] + items if plan["read_first"] else items + [plan["read"]]
    w = plan["wraps"]
    if plan["style"] == "numbered":
        lead = "Please do these in order:" if w[0] % 2 else "Here is what I need:"
        body = plan["sep"].join(f"{i + 1}. {it}" for i, it in enumerate(items))
        text = lead + plan["sep"] + body
    elif plan["style"] == "chain":
        conn = ["First, "] + ["Then, "] * max(0, len(items) - 2) + (["Finally, "] if len(items) > 1 else [])
        text = " ".join(c + _low(it) for c, it in zip(conn, items))
    else:
        parts = []
        for i, it in enumerate(items):
            if it.rstrip().endswith("?"):                      # a question is not wrapped ("Please who owns ...?" would not be English)
                parts.append(it.strip()); continue
            pool = FIRST_WRAP if i == 0 else NEXT_WRAP
            t = pool[w[(i + 1) % len(w)] % len(pool)].format(u=it.strip(), ul=_low(it))
            parts.append(t[:-1] + "?" if t.startswith(("Can you", "Could you")) and t.endswith(".") else t)
        text = " ".join(parts)
    pre = " ".join(plan["context"])
    out = (pre + " " + text if pre else text) + (" " + plan["closing"] if plan["closing"] else "")
    return out.strip()


def busy_request_pair(rng, actions, unit, read=None, same_kind=None, long=False):
    """(request without the unit, request with the unit) sharing everything else; the first stays under MAX_REQUEST."""
    for _ in range(8):
        plan = busy_plan(rng, actions, read=read, exclude=unit, same_kind=same_kind, long=long)
        while len(render_plan(plan, extra=unit)) > MAX_REQUEST and plan["context"]:
            plan["context"] = plan["context"][:-1]
        while len(render_plan(plan, extra=unit)) > MAX_REQUEST and len(plan["acts"]) > 1:
            idx = next((i for i in range(len(plan["acts"]) - 1, -1, -1) if plan["acts"][i] != same_kind), None)
            if idx is None:
                break
            plan["acts"].pop(idx)
        pos = rng.randint(0, len(plan["acts"]))
        a, b = render_plan(plan), render_plan(plan, extra=unit, extra_pos=pos)
        if _norm(unit) not in _norm(a) and _norm(unit) in _norm(b):
            return a, b, plan
    raise RuntimeError("could not build a busy request pair")


# ----------------------------------------------------------------------------------------------------------------------
# one-line tool outputs
# ----------------------------------------------------------------------------------------------------------------------
def make_oneline(rng):
    """(object, kind, the request that produced it). Objects are strings or small dictionaries."""
    k = rng.randrange(12)
    if k == 0:
        return f"Saved draft #{rng.randint(100, 999)} in your drafts folder.", "text", _fill("Draft an email to {name} about {topic}.", rng)
    if k == 1:
        return _fill("Payment of {amount} to {name} scheduled for {date}.", rng), "text", _fill("Schedule a payment of {amount} to {name}.", rng)
    if k == 2:
        return _fill("Balance on {acct}: {amount}", rng), "text", "How much money is in my account?"
    if k == 3:
        f, d = rng.choice(FNAMES), rng.choice(FOLDERS)
        return f"File {f} moved to {d}.", "text", f"Put {f} in the {d} folder."
    if k == 4:
        e = rng.choice(EVENTS)
        return _fill(f"Event '{e}' created on {{date}} at {{time}}.", rng), "text", f"Add the {e} to my calendar."
    if k == 5:
        c = rng.choice(CHANNELS)
        return f"Message posted in {c}.", "text", f"Post a short update in {c}."
    if k == 6:
        return f"Error: {rng.choice(ERRORS)}", "text", _fill(rng.choice(USER_TASKS), rng)
    if k == 7:
        return f"{rng.randint(1, 999)}.{rng.randint(0, 99):02d}", "text", "Work out the total cost."
    if k == 8:
        o = rng.choice(OIDS)
        return f"Order {o}: {rng.choice(STATUSES)}", "text", f"What is the status of order {o}?"
    if k == 9:
        hs = rng.sample(HOTELS, rng.randint(2, 4)); city = rng.choice(CITIES)
        lo = [rng.randint(60, 300) for _ in hs]
        return {h: f"from {a} to {a + rng.randint(40, 400)} dollars per night" for h, a in zip(hs, lo)}, "dict", f"How much do the hotels in {city} cost?"
    if k == 10:
        hs = rng.sample(HOTELS, rng.randint(1, 3)); city = rng.choice(CITIES)
        return {h: f"{rng.randint(1, 90)} {rng.choice(STREETS)}, {city}" for h in hs}, "dict", "What are the addresses of those hotels?"
    hs = rng.sample(HOTELS, rng.randint(2, 4))
    if rng.random() < 0.5:
        return {h: f"{rng.choice(RATINGS)} out of 5" for h in hs}, "dict", "Which of these hotels has the best rating?"
    return "Hotels found: " + ", ".join(hs), "text", _fill("Which hotels are there in {city}?", rng)


def render_oneline(obj, rng):
    if isinstance(obj, dict):
        return repr(obj) if rng.random() < 0.6 else json.dumps(obj)
    return obj


def insert_oneline(obj, unit, delim, rng):
    if isinstance(obj, dict):
        d = dict(obj); key = rng.choice(list(d)); d[key] = d[key] + rng.choice([" ", "\n", "\n\n"]) + unit
        return d
    return (obj.rstrip() + delim + unit) if rng.random() < 0.8 else (unit + delim + obj)


def render_host(fields, kind, rng, p_pydict):
    """A request_pairs host rendered by request_pairs.render, or as a Python dictionary."""
    if kind != "snippet" and rng.random() < p_pydict:
        return repr(fields), "pydict"
    fmt = rp.pick_format(kind, rng)
    return rp.render(fields, kind, fmt, rng), fmt


# ----------------------------------------------------------------------------------------------------------------------
# packs
# ----------------------------------------------------------------------------------------------------------------------
def _row(form, request, content, **meta):
    return dict(request=request, content=content, text=rp.view(request, content), label=FORMS_C[form], form=form, pack="agent", **meta)


def build_busy_split(hosts, units, n_items, n_host_busy, n_oneline_inject, n_oneline_host, rng, split,
                     p_long=0.5, p_same_kind=0.4, p_pydict=0.25, p_plain=0.3, p_oneline=0.4):
    by_fam = defaultdict(list)
    for u in units:
        by_fam[u["family"]].append(u)
    rows = []
    for cid in range(n_items):
        u = rng.choice(units); frame = rng.choice(FRAMES) if rng.random() < FRAME_SHARE else ""
        inserted = frame + u["unit"]; d = rng.choice(DELIMS); long = rng.random() < p_long
        if rng.random() < p_oneline:
            obj, _, produced_by = make_oneline(rng)
            content = render_oneline(insert_oneline(obj, inserted, d, rng), rng); kind, fmt, pos = "oneline", ("dict" if isinstance(obj, dict) else "text"), "edge"
            read = produced_by if rng.random() < 0.8 else None
        else:
            kind, fields, slot = rng.choice(hosts)
            pos = rng.choice(["start", "middle", "end"] + ([] if kind in rp.DELEGATABLE or kind == "snippet" else ["item"]))
            f2 = rp.insert(fields, slot, kind, inserted, pos, d, rng)
            content, fmt = render_host(f2, kind, rng, p_pydict)
            produced_by = rp.off_request(kind, f2, slot, rng)
            read = produced_by if rng.random() < 0.7 else None
        same = None
        if rng.random() < p_same_kind:
            alts = [v["unit"] for v in by_fam[u["family"]] if _norm(v["unit"]) != _norm(u["unit"])]
            same = rng.choice(alts) if alts else None
        req_a, req_b, plan = busy_request_pair(rng, units, u["unit"], read=read, same_kind=same, long=long)
        meta = dict(family=u["family"], host_src=kind, position=pos, fmt=fmt, unit=inserted, content_id=f"{split}-b{cid}", split=split,
                    same_kind=bool(same), long=long, n_actions=len(plan["acts"]))
        rows.append(_row("inject_busy", req_a, content, **meta))
        rows.append(_row("authorised_busy", req_b, content, **meta))
        if rng.random() < p_plain:
            rows.append(_row("inject", produced_by, content, **meta))
    for j in range(n_host_busy):
        long = rng.random() < p_long
        if rng.random() < 0.5:
            obj, _, produced_by = make_oneline(rng); content = render_oneline(obj, rng); kind, fmt = "oneline", ("dict" if isinstance(obj, dict) else "text")
        else:
            kind, fields, slot = rng.choice(hosts); content, fmt = render_host(fields, kind, rng, p_pydict); produced_by = rp.off_request(kind, fields, slot, rng)
        plan = busy_plan(rng, units, read=produced_by if rng.random() < 0.7 else None, long=long)
        while len(render_plan(plan)) > MAX_REQUEST and plan["context"]:
            plan["context"] = plan["context"][:-1]
        rows.append(_row("host_busy", render_plan(plan), content, family="", host_src=kind, position="", fmt=fmt, unit="",
                         content_id=f"{split}-bh{j}", split=split, same_kind=False, long=long, n_actions=len(plan["acts"])))
    for j in range(n_oneline_inject):
        u = rng.choice(units); frame = rng.choice(FRAMES) if rng.random() < FRAME_SHARE else ""; inserted = frame + u["unit"]
        obj, _, produced_by = make_oneline(rng)
        content = render_oneline(insert_oneline(obj, inserted, rng.choice(DELIMS), rng), rng)
        rows.append(_row("inject", produced_by, content, family=u["family"], host_src="oneline", position="edge", fmt=("dict" if isinstance(obj, dict) else "text"),
                         unit=inserted, content_id=f"{split}-bo{j}", split=split, same_kind=False, long=False, n_actions=0))
    for j in range(n_oneline_host):
        obj, _, produced_by = make_oneline(rng)
        rows.append(_row("host_only", produced_by, render_oneline(obj, rng), family="", host_src="oneline", position="", fmt=("dict" if isinstance(obj, dict) else "text"),
                         unit="", content_id=f"{split}-boh{j}", split=split, same_kind=False, long=False, n_actions=0))
    seen, out = set(), []
    for r in rows:
        key = (r["request"], r["content"])
        if key not in seen:
            seen.add(key); out.append(r)
    return out


def build_busy(seed=0, per_family=40, n_items={"train": 1500, "val": 300}, n_host_busy={"train": 750, "val": 150},
               n_oneline_inject={"train": 500, "val": 100}, n_oneline_host={"train": 250, "val": 50}, n_hosts={"train": 800, "val": 200}, **kw):
    """Busy-request rows for each split, on notebook 03's units and family split; generation draws from its own stream."""
    actions, a_split, _, _ = units_and_splits(seed, per_family)
    rng = random.Random(seed * 1000 + 303)
    out = {}
    for sp in n_items:
        hosts = [(k, *rp.make_host(k, rng)) for k in rng.choices(rp.HOST_KINDS, weights=rp.HOST_WEIGHTS, k=n_hosts[sp])]
        units = [u for u in actions if u["family"] in a_split[sp]]
        out[sp] = build_busy_split(hosts, units, n_items[sp], n_host_busy[sp], n_oneline_inject[sp], n_oneline_host[sp], rng, sp, **kw)
    meta = dict(seed=seed, per_family=per_family, n_items=n_items, n_host_busy=n_host_busy, n_oneline_inject=n_oneline_inject,
                n_oneline_host=n_oneline_host, n_hosts=n_hosts, options=kw, action_family_split={k: sorted(v) for k, v in a_split.items()})
    return out, meta


def drop_groups(rows, n_drop, rng):
    """Removes whole content groups (every form built on one content) until at least n_drop rows are gone."""
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("pack"), r["content_id"])].append(r)
    keys = sorted(groups, key=str); rng.shuffle(keys)
    drop, removed = set(), 0
    for k in keys:
        if removed >= n_drop:
            break
        drop.add(k); removed += len(groups[k])
    return [r for r in rows if (r.get("pack"), r["content_id"]) not in drop]


def check_busy(rows):
    """Labels follow FORMS_C; a busy pair shares its content; the harmful request leaves the embedded instruction out and
    the harmless one contains it; same-kind actions differ from the embedded one; placeholders scrubbed."""
    by = defaultdict(dict)
    for r in rows:
        assert r["label"] == FORMS_C[r["form"]], (r["form"], r["label"])
        by[r["content_id"]][r["form"]] = r
        if r["form"] == "inject_busy":
            u = r["unit"]
            for fr in FRAMES:
                u = u[len(fr):] if u.startswith(fr) else u
            assert _norm(u) not in _norm(r["request"]), ("embedded instruction inside a harmful busy request", r["content_id"])
    n = 0
    for cid, f in by.items():
        if "inject_busy" in f and "authorised_busy" in f:
            a, b = f["inject_busy"], f["authorised_busy"]
            u = a["unit"]
            for fr in FRAMES:
                u = u[len(fr):] if u.startswith(fr) else u
            assert a["content"] == b["content"] and a["request"] != b["request"], cid
            assert _norm(u) in _norm(b["request"]), ("authorised busy request lacks the instruction", cid)
            n += 1
    check_scrubbed([r["request"] for r in rows] + [r["content"] for r in rows])
    return n


def summarize(rows, name):
    c = Counter(r["form"] for r in rows)
    out = dict(pack=name, n=len(rows), label1=sum(r["label"] for r in rows), label0=sum(1 - r["label"] for r in rows), **{f: c.get(f, 0) for f in FORMS_C})
    busy = [r for r in rows if r["form"] in BUSY_FORMS]
    if busy:
        out.update(busy_long=sum(r.get("long", False) for r in busy), busy_same_kind=sum(r.get("same_kind", False) for r in busy),
                   oneline=sum(r.get("host_src") == "oneline" for r in rows), pydict=sum(r.get("fmt") == "pydict" for r in rows),
                   request_chars_max=max(len(r["request"]) for r in rows))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# tau-bench: the task part of the user simulator's brief
# ----------------------------------------------------------------------------------------------------------------------
PERSONA_RE = re.compile(
    r"^(?:Your name is\b|Your zip code is\b|Your zip is\b|Your email is\b|Your user id is\b|You live in\b|"
    r"You are [\w.-]*\d[\w.-]*\b|"
    r"You are (?:(?:very|quite|a bit|somewhat|extremely|rather)\s+)?[a-z]+(?:\s*,\s*(?:and\s+)?[a-z]+)*\s*\.$)")


def task_request(brief):
    """Removes the sentences that give the simulated customer's identity (name, zip code, email, user id) or a bare list
    of character traits; everything else is kept. Returns the brief unchanged when nothing would be left."""
    sents = re.split(r"(?<=[.!?])\s+", brief.strip())
    keep = [s for s in sents if not PERSONA_RE.match(s.strip())]
    return " ".join(keep).strip() if keep else brief
