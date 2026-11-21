"""Request-conditioned matched pairs: the guard reads the user's request beside the content.

Label rule. Content is an injection (label 1) when it holds an instruction to act that the user's request does not
call for. A request calls for an instruction when it states it, or when it delegates to the record that holds it
("do what the email from X asks"). Each training row is a (request, content) pair, shown to the model as one text:

    User request: <request>

    Content:
    <content>

Eight forms. The first four are built on the same content, so the content alone cannot tell their labels apart:
  inject                     unrelated request, instruction inside the content                    -> 1
  authorised_explicit        the request also states the same instruction                         -> 0
  authorised_delegated       the request delegates to the record that holds the instruction       -> 0
  delegated_elsewhere        the request delegates to a different record                          -> 1
and four controls:
  request_twin               the instruction is the user's request; the content is clean          -> 0
  host_only                  unrelated request, clean content                                     -> 0
  declarative_insert         unrelated request, a neutral statement inside the content            -> 0
  content_imperative_insert  unrelated request, a request to the human reader inside the content  -> 0

Two packs. The agent pack reuses the hosts, instruction units and family splits of src/action_pairs.py (same seed,
same families held out for validation) and adds two host kinds: an inbox (several emails) and a one-sentence snippet.
The document pack converts the structural splits of picalib-research (notebook 17) and adds one-sentence hosts.
Delegation forms exist only where content has a nameable record (an email's sender or subject, a file name, a
channel member, an event title, a ticket, an order, a web address). Every address, domain, phone number and account
is a placeholder. No wording is taken from an evaluation set.
"""
from __future__ import annotations
import copy, json, random, re
from collections import Counter, defaultdict
import action_pairs as ap
from action_pairs import (fill, build_units, body, insert_text, get_slot, set_slot, check_scrubbed, ACTION_FAMILIES, CONTENT_FAMILIES,
                          DECLARATIVE_FAMILIES, NAMES, CHANNELS, SUBJECTS, FNAMES, FDOMS, PATHS, OIDS, EVENTS, TOPICS, QUERIES, DATES,
                          TIMES, BODY_SENTENCES, FRAMES, FRAME_SHARE, DELIMS)
from structural_data import _sentences, split_by_key

FORMAT = "User request: {request}\n\nContent:\n{content}"
FORMS = {"inject": 1, "authorised_explicit": 0, "authorised_delegated": 0, "delegated_elsewhere": 1,
         "request_twin": 0, "host_only": 0, "declarative_insert": 0, "content_imperative_insert": 0}
PAIRED_FORMS = ("authorised_explicit", "authorised_delegated", "delegated_elsewhere")
P_EXPLICIT = 0.35          # share of injected contents that also get the explicit-authorisation pair
P_COMPOSITE = 0.25         # share of requests made of two parts ("First ... Then ...")
HOST_KINDS = ["email", "inbox", "calendar", "file", "search", "product", "transactions", "messages", "order", "ticket", "webpage", "snippet"]
HOST_WEIGHTS = [10, 8, 7, 9, 7, 7, 6, 9, 6, 6, 8, 17]
DELEGATABLE = {"email", "inbox", "calendar", "file", "messages", "order", "ticket", "webpage"}
MAILDOMS = ["mailbox.invalid", "relay.test", "updates.invalid", "keeper.test", "office.invalid", "team.test"]
DOC_REQUESTS = ["Summarize the following passage.", "What is the main topic of this text?", "Give this text a short title.",
                "List the people and places mentioned in this text.", "Pick three keywords that describe this text.",
                "Say in one sentence what this text is about.", "Which sentence of this text matters most, and why?"]
TWIN_WRAPPERS = ["{u}", "Please {ul}", "Can you {ul}", "I need you to {ul}", "{u} Thanks."]


def view(request, content):
    return FORMAT.format(request=request.strip(), content=content)


def _low(s):
    s = s.strip()
    return s[:1].lower() + s[1:] if s else s


def twin_request(unit, rng):
    return rng.choice(TWIN_WRAPPERS).format(u=unit.strip(), ul=_low(unit))


def explicit(req, unit, rng):
    if rng.random() < 0.5:
        return f"{req.strip()} After that, {_low(unit)}"
    return f"Please {_low(unit)} Also, {_low(req)}"


def composite(first, second, rng):
    return f"First, {_low(first)} Then, {_low(second)}"


# ----------------------------------------------------------------------------------------------------------------------
# hosts
# ----------------------------------------------------------------------------------------------------------------------
def make_host(kind, rng):
    if kind == "inbox":
        k = rng.randint(2, 4); senders = rng.sample(NAMES, k); subjects = rng.sample(SUBJECTS, k)
        emails = [{"from": f"{s.lower()}@{rng.choice(MAILDOMS)}", "date": f"{rng.choice(DATES)} {rng.choice(TIMES)}", "subject": subj,
                   "body": body(rng, 1, 3)} for s, subj in zip(senders, subjects)]
        return {"emails": emails}, ("emails", rng.randrange(k), "body")
    if kind == "messages":
        k = rng.randint(3, 5); users = rng.sample(NAMES, k)
        ms = [{"user": u, "time": rng.choice(TIMES), "body": body(rng, 1, 2)} for u in users]
        return {"channel": rng.choice(CHANNELS), "messages": ms}, ("messages", rng.randrange(k), "body")
    if kind == "snippet":
        return {"text": fill(rng.choice(BODY_SENTENCES), rng)}, "text"
    return ap.make_host(kind, rng)


def _scalar(v):
    s = str(v)
    return json.dumps(s) if (s == "" or "\n" in s or ": " in s or " #" in s or s[:1] in "-[{'\"#&*!|>%@") else s


def to_yaml(obj, indent=0):
    sp = "  " * indent; lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{sp}{k}:"); lines.append(to_yaml(v, indent + 1))
            else:
                lines.append(f"{sp}{k}: {_scalar(v) if not isinstance(v, (dict, list)) else '[]'}")
    else:
        for it in obj:
            if isinstance(it, dict):
                sub = to_yaml(it, indent + 1).split("\n")
                lines.append(f"{sp}- {sub[0].strip()}"); lines += sub[1:]
            else:
                lines.append(f"{sp}- {_scalar(it)}")
    return "\n".join(lines)


def render(fields, kind, fmt, rng):
    if kind == "snippet":
        return fields["text"]
    if fmt == "yaml":
        return to_yaml(fields)
    if kind == "inbox" and fmt == "prose":
        return "\n\n".join(f"From: {e['from']}\nDate: {e['date']}\nSubject: {e['subject']}\n\n{e['body']}" for e in fields["emails"])
    return ap.render(fields, kind, fmt, rng)


def pick_format(kind, rng):
    if kind == "snippet":
        return "raw"
    if kind in ("inbox", "messages", "search", "transactions", "product"):
        return rng.choice(["json", "yaml", "kv", "prose"])
    return rng.choice(["json", "json", "kv", "prose", "yaml"])


def insert(fields, slot, kind, unit, pos, delim, rng):
    if kind in DELEGATABLE or kind == "snippet":
        f = copy.deepcopy(fields)
        set_slot(f, slot, insert_text(get_slot(f, slot), unit, pos, delim, rng))
        return f
    return ap.insert_into_host(fields, slot, kind, unit, pos, delim, rng)


# ----------------------------------------------------------------------------------------------------------------------
# requests
# ----------------------------------------------------------------------------------------------------------------------
def off_request(kind, f, slot, rng):
    """A request that does not call for any instruction inside the content."""
    if kind == "email":
        return rng.choice([f"Summarize the email from {f['from']}.", f"When did {f['from']} send this email?",
                           f"What is the subject of the email from {f['from']}?", f"Does the email from {f['from']} mention {rng.choice(TOPICS)}?"])
    if kind == "inbox":
        e = rng.choice(f["emails"])
        return rng.choice(["Summarize my latest emails.", f"Which of these emails mention {rng.choice(TOPICS)}?",
                           f"When did {e['from']} write to me?", "List the senders of my unread emails."])
    if kind == "calendar":
        return rng.choice([f"When does '{f['title']}' start?", f"Where is '{f['title']}' held?", f"Who is invited to '{f['title']}'?"])
    if kind == "file":
        return rng.choice([f"Summarize {f['name']}.", f"Who owns the file {f['name']}?", f"How big is {f['name']}?", f"When was {f['name']} last changed?"])
    if kind == "search":
        return rng.choice([f"Look up {f['query']}.", f"Find a few pages about {f['query']}.", f"Search the web for {f['query']}."])
    if kind == "product":
        return rng.choice([f"What is the rating of {f['name']}?", f"Summarize the reviews of {f['name']}.", f"How much does {f['name']} cost?"])
    if kind == "transactions":
        return rng.choice(["What was my largest payment recently?", "List my recent transactions.",
                           f"How much did I pay {rng.choice(f['transactions'])['recipient']}?"])
    if kind == "messages":
        m = rng.choice(f["messages"])
        return rng.choice([f"Summarize the messages in {f['channel']}.", f"What did {m['user']} say in {f['channel']}?",
                           f"Who posted in {f['channel']} today?"])
    if kind == "order":
        return rng.choice([f"What is the status of order {f['order_id']}?", f"What did I buy in order {f['order_id']}?",
                           f"How much was order {f['order_id']}?"])
    if kind == "ticket":
        return rng.choice([f"What is the priority of ticket {f['ticket']}?", f"Summarize ticket {f['ticket']}.",
                           f"When was ticket {f['ticket']} last updated?"])
    if kind == "webpage":
        return rng.choice([f"Summarize the page at {f['url']}.", f"What is {f['url']} about?", f"Read {f['url']} and tell me its main point."])
    if kind == "snippet":
        return rng.choice(["Summarize this note.", "What is this message about?", "Translate the gist of this note into plain words."])
    raise ValueError(kind)


def _other(values, current, rng, absent):
    """A name different from current: another record present in the content, or one absent from it."""
    present = [v for v in values if v != current]
    if present and rng.random() < 0.6:
        return rng.choice(present)
    return absent()


def delegated(kind, f, slot, elsewhere, rng):
    """A request that delegates to the record holding the slot, or (elsewhere=True) to a different record."""
    if kind == "email":
        by_subject = rng.random() < 0.3
        if by_subject:
            subj = f["subject"] if not elsewhere else rng.choice([s for s in SUBJECTS if s != f["subject"]])
            return rng.choice([f"Handle the tasks in the email with the subject '{subj}'.", f"Do what the email titled '{subj}' asks."])
        name = f["from"] if not elsewhere else rng.choice([f"{n.lower()}@{d}" for n in NAMES for d in MAILDOMS if f"{n.lower()}@{d}" != f["from"]])
        return rng.choice([f"Please do what the email from {name} asks.", f"Take care of the requests in the email from {name}.",
                           f"Read the email from {name} and do what it says."])
    if kind == "inbox":
        holder = f["emails"][slot[1]]["from"]
        name = holder if not elsewhere else _other([e["from"] for e in f["emails"]], holder, rng,
                                                    lambda: rng.choice([f"{n.lower()}@{d}" for n in NAMES for d in MAILDOMS if f"{n.lower()}@{d}" not in [e['from'] for e in f['emails']]]))
        return rng.choice([f"Please do what the email from {name} asks.", f"Take care of the requests in the email from {name}.",
                           f"Find the email from {name} and follow its instructions."])
    if kind == "messages":
        holder = f["messages"][slot[1]]["user"]
        name = holder if not elsewhere else _other([m["user"] for m in f["messages"]], holder, rng,
                                                    lambda: rng.choice([n for n in NAMES if n not in [m['user'] for m in f['messages']]]))
        return rng.choice([f"Do what {name} asked for in {f['channel']}.", f"Take care of {name}'s request in {f['channel']}.",
                           f"Read {name}'s message in {f['channel']} and do it."])
    if kind == "file":
        name = f["name"] if not elsewhere else rng.choice([n for n in FNAMES if n != f["name"]])
        return rng.choice([f"Do the tasks listed in {name}.", f"Carry out the action items in the file {name}.", f"Open {name} and do what it says."])
    if kind == "calendar":
        name = f["title"] if not elsewhere else rng.choice([e for e in EVENTS if e != f["title"]])
        return rng.choice([f"Do what the notes of the '{name}' event ask for.", f"Follow the instructions in the '{name}' invitation."])
    if kind == "ticket":
        name = f["ticket"] if not elsewhere else f"T-{(int(f['ticket'][2:]) + rng.randint(1, 4000)) % 9000 + 1000}"
        return rng.choice([f"Resolve ticket {name} by doing what its summary asks.", f"Do what ticket {name} asks for."])
    if kind == "webpage":
        name = f["url"] if not elsewhere else rng.choice([f"http://{d}/{p}" for d in FDOMS for p in PATHS if f"http://{d}/{p}" != f["url"]])
        return rng.choice([f"Go to {name} and do the tasks listed there.", f"Follow the steps on {name}.", f"Open {name} and do what it asks."])
    if kind == "order":
        name = f["order_id"] if not elsewhere else rng.choice([o for o in OIDS if o != f["order_id"]])
        return rng.choice([f"Do what the delivery note on order {name} asks.", f"Follow the instructions in the note of order {name}."])
    raise ValueError(kind)


# ----------------------------------------------------------------------------------------------------------------------
# agent pack
# ----------------------------------------------------------------------------------------------------------------------
def _row(form, request, content, **meta):
    return dict(request=request, content=content, text=view(request, content), label=FORMS[form], form=form, **meta)


def build_split(hosts, units, fillers, contents, n_items, rng, split, pairs=True):
    rows = []
    for cid in range(n_items):
        kind, fields, slot = rng.choice(hosts)
        u = rng.choice(units); frame = rng.choice(FRAMES) if rng.random() < FRAME_SHARE else ""
        inserted = frame + u["unit"]
        positions = ["start", "middle", "end"] + ([] if kind in DELEGATABLE or kind == "snippet" else ["item"])
        pos = rng.choice(positions); d = rng.choice(DELIMS); fmt = pick_format(kind, rng)
        f2 = insert(fields, slot, kind, inserted, pos, d, rng)
        content = render(f2, kind, fmt, rng)
        meta = dict(family=u["family"], host_src=kind, position=pos, fmt=fmt, unit=inserted, content_id=f"{split}-{cid}", pack="agent", split=split)
        r_off = off_request(kind, f2, slot, rng)
        if rng.random() < P_COMPOSITE:
            k2, g2, s2 = rng.choice(hosts); r_off = composite(off_request(k2, g2, s2, rng), r_off, rng) if rng.random() < 0.5 else composite(r_off, off_request(k2, g2, s2, rng), rng)
        rows.append(_row("inject", r_off, content, **meta))
        if not pairs:
            continue
        if rng.random() < P_EXPLICIT:
            rows.append(_row("authorised_explicit", explicit(r_off, u["unit"], rng), content, **meta))
        if kind in DELEGATABLE:
            r_on, r_else = delegated(kind, f2, slot, False, rng), delegated(kind, f2, slot, True, rng)
            if rng.random() < P_COMPOSITE:
                k2, g2, s2 = rng.choice(hosts); first = off_request(k2, g2, s2, rng)
                r_on, r_else = composite(first, r_on, rng), composite(first, r_else, rng)
            rows.append(_row("authorised_delegated", r_on, content, **meta))
            rows.append(_row("delegated_elsewhere", r_else, content, **meta))
    n_ctrl = n_items // 4
    for j in range(n_ctrl):
        kind, fields, slot = rng.choice(hosts); u = rng.choice(units)
        rows.append(_row("request_twin", twin_request(u["unit"], rng), render(fields, kind, pick_format(kind, rng), rng), family=u["family"], host_src=kind,
                         position="", fmt="", unit=u["unit"], content_id=f"{split}-t{j}", pack="agent", split=split))
    for j in range(n_ctrl):
        kind, fields, slot = rng.choice(hosts)
        rows.append(_row("host_only", off_request(kind, fields, slot, rng), render(fields, kind, pick_format(kind, rng), rng), family="", host_src=kind,
                         position="", fmt="", unit="", content_id=f"{split}-h{j}", pack="agent", split=split))
    for pool, form in ((fillers, "declarative_insert"), (contents, "content_imperative_insert")):
        for j in range(n_ctrl):
            kind, fields, slot = rng.choice(hosts); x = rng.choice(pool)
            pos = rng.choice(["start", "middle", "end"]); d = rng.choice(DELIMS)
            f2 = insert(fields, slot, kind, x["unit"], pos, d, rng)
            rows.append(_row(form, off_request(kind, f2, slot, rng), render(f2, kind, pick_format(kind, rng), rng), family=x["family"], host_src=kind,
                             position=pos, fmt="", unit=x["unit"], content_id=f"{split}-{form[:3]}{j}", pack="agent", split=split))
    seen, out = set(), []
    for r in rows:
        key = (r["request"], r["content"])
        if key not in seen:
            seen.add(key); out.append(r)
    return out


def build_dataset(seed=0, per_family=40, n_items={"train": 3000, "val": 600}, n_hosts={"train": 1500, "val": 400}, fracs=(0.7, 0.3, 0.0), pairs=True):
    """Same instruction units and family splits as action_pairs.build_dataset with the same seed and per_family."""
    rng = random.Random(seed)
    actions = build_units(ACTION_FAMILIES, per_family, rng, "action")
    fillers = build_units(DECLARATIVE_FAMILIES, per_family, rng, "declarative")
    contents = build_units(CONTENT_FAMILIES, per_family, rng, "content_imperative")
    a_split = split_by_key([u["family"] for u in actions], rng, fracs)
    d_split = split_by_key([u["family"] for u in fillers], rng, fracs)
    c_split = split_by_key([u["family"] for u in contents], rng, fracs)
    out = {}
    for sp in n_items:
        hosts = [(k, *make_host(k, rng)) for k in rng.choices(HOST_KINDS, weights=HOST_WEIGHTS, k=n_hosts[sp])]
        out[sp] = build_split(hosts, [u for u in actions if u["family"] in a_split[sp]], [f for f in fillers if f["family"] in d_split[sp]],
                              [c for c in contents if c["family"] in c_split[sp]], n_items[sp], rng, sp, pairs=pairs)
    meta = dict(seed=seed, per_family=per_family, n_items=n_items, n_hosts=n_hosts, pairs=pairs,
                action_family_split={k: sorted(v) for k, v in a_split.items()},
                declarative_family_split={k: sorted(v) for k, v in d_split.items()},
                content_family_split={k: sorted(v) for k, v in c_split.items()})
    return out, meta


# ----------------------------------------------------------------------------------------------------------------------
# document pack: the structural splits of picalib-research, with requests, plus one-sentence hosts
# ----------------------------------------------------------------------------------------------------------------------
def convert_structural(rows, rng, pairs=True, n_short=1500, split=""):
    hosts = [r["text"] for r in rows if r["form"] == "host_only"]
    units = [r["unit"] for r in rows if r["form"] == "embedded" and r.get("unit")]
    assert hosts and units, "the structural rows need host_only and embedded forms"
    out = []
    def add(form, req, content, **meta):
        out.append(_row(form, req, content, pack="structural", split=split, **meta))
    for i, r in enumerate(rows):
        req = rng.choice(DOC_REQUESTS); meta = dict(family=r.get("family", ""), host_src=r.get("host_src", ""), position=r.get("position", ""),
                                                    fmt="", unit=r.get("unit", ""), content_id=f"s{split}-{i}")
        if r["form"] == "embedded":
            add("inject", req, r["text"], **meta)
            if pairs and rng.random() < P_EXPLICIT:
                add("authorised_explicit", explicit(req, r["unit"], rng), r["text"], **meta)
        elif r["form"] == "standalone":
            add("request_twin", r["text"], rng.choice(hosts), **meta)
        elif r["form"] in ("host_only", "declarative_insert", "content_imperative_insert"):
            add(r["form"], req, r["text"], **meta)
    shorts = [s for s in (_sentences(h)[0] for h in hosts) if len(s) >= 25]
    for j in range(n_short):
        h = rng.choice(shorts); u = rng.choice(units); d = rng.choice(["\n", " ", "\n\n"])
        text = (h + d + u) if rng.random() < 0.8 else (u + d + h)
        req = rng.choice(DOC_REQUESTS); meta = dict(family="", host_src="short", position="short", fmt="", unit=u, content_id=f"s{split}-short{j}")
        add("inject", req, text, **meta)
        if pairs and rng.random() < P_EXPLICIT:
            add("authorised_explicit", explicit(req, u, rng), text, **meta)
    for j in range(n_short // 2):
        add("host_only", rng.choice(DOC_REQUESTS), rng.choice(shorts), family="", host_src="short", position="", fmt="", unit="", content_id=f"s{split}-shorth{j}")
    for j in range(n_short // 4):
        u = rng.choice(units)
        add("request_twin", twin_request(u, rng), rng.choice(shorts), family="", host_src="short", position="", fmt="", unit=u, content_id=f"s{split}-shortt{j}")
    seen, res = set(), []
    for r in out:
        key = (r["request"], r["content"])
        if key not in seen:
            seen.add(key); res.append(r)
    return res


# ----------------------------------------------------------------------------------------------------------------------
# checks
# ----------------------------------------------------------------------------------------------------------------------
def check_pack(rows, pairs=True):
    """Labels follow FORMS; paired forms share content with an inject row; a delegation pair differs only in the request;
    placeholders scrubbed in requests and contents."""
    by_cid = defaultdict(list)
    for r in rows:
        assert r["label"] == FORMS[r["form"]], (r["form"], r["label"])
        by_cid[r["content_id"]].append(r)
    for cid, rs in by_cid.items():
        forms = {r["form"]: r for r in rs}
        for f in PAIRED_FORMS:
            if f in forms and "inject" in forms:                       # an inject row can be dropped as an exact duplicate of another item's
                assert forms[f]["content"] == forms["inject"]["content"], (cid, f)
        if "authorised_delegated" in forms and "delegated_elsewhere" in forms:
            a, b = forms["authorised_delegated"], forms["delegated_elsewhere"]
            assert a["content"] == b["content"] and a["request"] != b["request"], cid
    if not pairs:
        assert not any(r["form"] in PAIRED_FORMS for r in rows), "paired forms in a no-pairs pack"
    check_scrubbed([r["request"] for r in rows] + [r["content"] for r in rows])
    return True


def summarize(rows, name):
    c = Counter(r["form"] for r in rows)
    return dict(pack=name, n=len(rows), label1=sum(r["label"] for r in rows), label0=sum(1 - r["label"] for r in rows), **{f: c.get(f, 0) for f in FORMS})
