#!/usr/bin/env python3
"""Auto ontology construction engine (the NVIDIA auto-ontology concept, native to DSH)

Upstream auto-ontology (13.3k★, Apache-2.0) builds governed semantic layers from
enterprise metadata. This plugin implements the document-corpus slot: a two-pass
LLM pipeline in a zero-infra stdlib CLI, with the family's difference — **evidence
tracing**: every entity/relation carries a verbatim evidence span ("no evidence, no
assertion"), and a type guard flags unknown types instead of silently dropping them.

O2 engine (v2): one fold-based store handles fresh builds, incremental merges,
coreference, and conflicts (issues #5 #6 #7 #8):
  build:   TBox schema from a corpus sample (--sample) -> per-document ABox
  fold:    entities/relations accumulate append-only; the same name under a
           different TYPE becomes a conflict entry holding BOTH evidences —
           flagged for review, never silently resolved
  coref:   one LLM pass clusters mentions of the same real-world thing; merges
           record aliases and union evidence (provenance kept)
  merge:   --merge folds a new build into an existing ontology; prior evidence
           is never edited or dropped (append-only across runs)
  cost:    per-call usage accounting + --max-calls hard cap; every artifact
           carries provenance (model/temp/elapsed/calls/tokens)

Usage:
  python3 scripts/build_ontology.py --docs <dir_or_glob> --domain "..." --save [--lang zh]
  python3 scripts/build_ontology.py --docs <new> --domain "..." --merge ontologies/old.json --save
  python3 scripts/build_ontology.py --query "WrenAI" [--from ontologies/x.json]
  python3 scripts/build_ontology.py --trajectory [--from ontologies/x.json] [more.json ...] [--out traj.ndjson]
"""
import argparse, concurrent.futures as cf, datetime as dt, glob, json, math, os, re, sys, threading, time
from xml.sax.saxutils import escape

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grounding

# Output language: English by default (international-first), --lang zh / ONTOLOGY_LANG for Chinese
LANG = os.environ.get("ONTOLOGY_LANG") or "en"
def tt(en, zh):
    return en if LANG == "en" else zh

# npm CLI form lands artifacts in the caller's cwd via ONTOLOGY_HOME (repo default unchanged)
OUTDIR = os.environ.get("ONTOLOGY_HOME") or os.path.join(KIT, "ontologies")

COST = {"calls": 0, "in": 0, "out": 0}
MAX_CALLS = None
_LOCK = threading.Lock()   # the judge calls run concurrently; the ledger and the guard do not race


def _key(s):
    """Name-matching key: case/punctuation/whitespace-insensitive, script-agnostic
    (ASCII-only stripping used to drop CJK-named entities and collapse CJK relations)."""
    return re.sub(r"[\W_]+", "", str(s).lower())


MODEL = os.environ.get("ONTOLOGY_MODEL") or "deepseek-chat"
JUDGE_MODEL = MODEL  # set by --judge-model / ONTOLOGY_JUDGE_MODEL in main()


def _reserved_usage(u):
    """Token accounting for a call whose `calls` slot llm() reserved before it started."""
    with _LOCK:
        COST["in"] += int(u.get("prompt_tokens") or 0)
        COST["out"] += int(u.get("completion_tokens") or 0)


def llm(sysmsg, user, json_out=True, model=None):
    """Every LLM request of a run goes through here: cost guard first — the call is reserved
    under the lock, so concurrent judge calls cannot overshoot the cap — then one retried
    call; each answered attempt lands its tokens in the ledger."""
    with _LOCK:
        if MAX_CALLS is not None and COST["calls"] >= MAX_CALLS:
            raise SystemExit(f"cost guard: {MAX_CALLS} LLM calls reached (--max-calls)")
        COST["calls"] += 1
    out, _ = grounding.complete(model or MODEL, [{"role": "system", "content": sysmsg},
                                                 {"role": "user", "content": user}],
                                json_out=json_out, account=_reserved_usage)
    return out


# ── the fold store (pure; unit-tested in CI) ────────────────────────────────

def new_store(domain):
    return {"domain": domain, "entities": {}, "relations": {}, "conflicts": [],
            "flagged": [], "tbox_types": set(), "tbox_relations": {}, "merge_log": [],
            "certifications": {}, "suppressed": 0, "flagged_ungrounded": []}


def load_store(o):
    """v1 or v2 ontology JSON -> store (legacy single-evidence fields synthesized into lists)."""
    st = new_store(o.get("domain", "?"))
    for t in o.get("tbox", {}).get("entity_types", []):
        st["tbox_types"].add(t["name"])
    for r in o.get("tbox", {}).get("relation_types", []):
        st["tbox_relations"][(r.get("name"), r.get("domains"), r.get("ranges"))] = r
    for e in o.get("abox", {}).get("entities", []):
        evs = e.get("evidences") or [{"quote": e.get("evidence", ""), "doc": e.get("doc", "?")}]
        docs = set(e.get("docs", [])) | ({e["doc"]} if e.get("doc") and e["doc"] != "?" else set())
        st["entities"][_key(e["name"])] = {"name": e["name"], "type": e["type"],
                                           "aliases": list(e.get("aliases", [])),
                                           "docs": sorted(docs), "evidences": []}
        for ev in evs:
            _fold_ev(st["entities"][_key(e["name"])]["evidences"], ev)
        # a writer that flagged the assertion but not its evidences keeps its verdict on reload
        if e.get("type_grounding") is False and not any("grounded" in x for x in st["entities"][_key(e["name"])]["evidences"]):
            for x in st["entities"][_key(e["name"])]["evidences"]:
                x["grounded"] = False
    for r in o.get("abox", {}).get("relations", []):
        evs = r.get("evidences") or [{"quote": r.get("evidence", ""), "doc": r.get("doc", "?")}]
        docs = set(r.get("docs", [])) | ({r["doc"]} if r.get("doc") and r["doc"] != "?" else set())
        k = (_key(r["subject"]), r["predicate"], _key(r["object"]))
        st["relations"][k] = {"subject": r["subject"], "predicate": r["predicate"], "object": r["object"],
                              "docs": sorted(docs), "evidences": []}
        for ev in evs:
            _fold_ev(st["relations"][k]["evidences"], ev)
        if r.get("grounding") is False and not any("grounded" in x for x in st["relations"][k]["evidences"]):
            for x in st["relations"][k]["evidences"]:
                x["grounded"] = False
    st["conflicts"] = list(o.get("conflicts", []))
    st["flagged"] = list(o.get("flagged_unknown_types", []))
    st["flagged_ungrounded"] = list(o.get("flagged_ungrounded", []))
    st["merge_log"] = list(o.get("merge_log", []))
    # re-key by the certified name so a key-scheme change never orphans a verdict
    st["certifications"] = {_key(c.get("name", k)): c for k, c in o.get("certifications", {}).items()}
    st["suppressed"] = 0
    return st

def certify(o, name, verdict, note="", actor=None):
    """Human verdict on an entity (issue #13, the upstream Learn pillar,
    evidence-first version): record travels WITH the ontology (portable artifact).
    rejected — the (name, type) pair is suppressed in every later fold; the
    original evidence stays in the certification record for audit. A different
    type re-asserting the same name is a NEW assertion and re-enters (the
    rejection was about that typing, not the string).
    accepted  — the entity is marked trusted; conflicts against it still get
    recorded (they are never silently resolved), the mark is the human word.
    `actor` names who issued the verdict — an agent applying one must say so."""
    st = load_store(o)
    k = _key(name)
    e = st["entities"].get(k)
    if e is None:
        raise SystemExit(tt(f"no such entity: {name}", f"无此实体：{name}"))
    rec = {"name": e["name"], "type": e["type"], "verdict": verdict, "at":
           dt.datetime.now().isoformat(timespec="seconds"), "note": note,
           "evidence": _strongest(e["evidences"])[0] if e["evidences"] else {}}
    if actor:
        rec["actor"] = actor
    o.setdefault("certifications", {})[k] = rec
    if verdict == "reject":
        del st["entities"][k]
        st["relations"] = {rk: r for rk, r in st["relations"].items()
                           if _key(r["subject"]) != k and _key(r["object"]) != k}
        o["abox"] = _abox(st)
        o["stats"]["entities"] = len(st["entities"])
        o["stats"]["relations"] = len(st["relations"])
    return o


def _fold_ev(evs, ev):
    if isinstance(ev, str):
        ev = {"quote": ev, "doc": "?"}
    q, d = ev.get("quote", ""), ev.get("doc", "?")
    if q and not any(e["quote"] == q for e in evs):
        item = {"quote": q, "doc": d}
        for k in ("grounded", "reason"):
            if k in ev:
                item[k] = ev[k]
        evs.append(item)


def _flag(evs):
    """The grounding flag of an assertion, derived from its evidences: True — some
    carried quote grounds the claim; False — judged, and none does; None — never judged."""
    if any(e.get("grounded") is True for e in evs):
        return True
    if evs and all(e.get("grounded") is False for e in evs):
        return False
    return None


def _strongest(evs):
    """Presentation order — stable, so fold order holds inside each class: a grounded
    quote first, an unjudged one next, an ungrounded one last. Nothing is edited or
    dropped; evidences[0] is simply the best quote the assertion carries."""
    return sorted(evs, key=lambda e: {True: 0, None: 1, False: 2}[e.get("grounded")])


def _flag_ungrounded(st, cur, etype, quote, doc):
    """A different-type challenger whose own quote does not ground it is no evidence
    of a conflict — it is a guess. Kept and flagged, never promoted on its own."""
    if not any(f["entity"] == cur["name"] and f["asserted_type"] == etype and f["evidence"]["quote"] == quote
               for f in st["flagged_ungrounded"]):
        st["flagged_ungrounded"].append({"entity": cur["name"], "existing_type": cur["type"],
                                         "asserted_type": etype, "evidence": {"quote": quote, "doc": doc}})


def _ev(quote, doc, grounded=None, reason=None):
    """A fold's evidence: the build's verdict rides on it when one was given."""
    ev = {"quote": quote, "doc": doc}
    if grounded is not None:
        ev["grounded"] = grounded
        if grounded is False and reason:
            ev["reason"] = reason
    return ev


def fold_entity(st, name, etype, quote, doc, grounded=None, reason=None):
    """Append-only entity fold; the same name under a different type => conflict
    holding BOTH evidences — recorded, never silently resolved. A rejected
    certification suppresses the (name, type) pair — counted, never re-asserted.
    `grounded` is the build's verdict on this quote (None = never judged)."""
    k = _key(name)
    if not k:
        return
    cert = st.get("certifications", {}).get(k)
    if cert and cert.get("verdict") == "reject" and cert.get("type") == etype:
        st["suppressed"] = st.get("suppressed", 0) + 1
        return
    cur = st["entities"].get(k)
    ev = _ev(quote, doc, grounded, reason)
    if cur is None:
        st["entities"][k] = {"name": name, "type": etype, "aliases": [],
                             "docs": [doc] if doc != "?" else [], "evidences": [ev]}
        return
    if cur["type"] != etype:
        if grounded is False:
            _flag_ungrounded(st, cur, etype, quote, doc)
            return
        st["conflicts"].append({"entity": cur["name"], "types": {
            cur["type"]: dict(_strongest(cur["evidences"])[0]) if cur["evidences"] else {"quote": "", "doc": "?"},
            etype: dict(ev)}})
        return
    _fold_ev(cur["evidences"], ev)
    if doc != "?":
        cur["docs"] = sorted(set(cur["docs"]) | {doc})


def fold_relation(st, subject, predicate, obj, quote, doc, alias_map=None, grounded=None, reason=None):
    if alias_map:  # canonicalize endpoints through the coref result before folding
        subject = alias_map.get(_key(subject), subject)
        obj = alias_map.get(_key(obj), obj)
    if not (subject and predicate and obj):
        return
    k = (_key(subject), predicate, _key(obj))
    cur = st["relations"].get(k)
    ev = _ev(quote, doc, grounded, reason)
    if cur is None:
        st["relations"][k] = {"subject": subject, "predicate": predicate, "object": obj,
                              "docs": [doc] if doc != "?" else [], "evidences": [ev]}
        return
    _fold_ev(cur["evidences"], ev)
    if doc != "?":
        cur["docs"] = sorted(set(cur["docs"]) | {doc})


def apply_aliases(st, alias_pairs):
    """Coref result [(canonical, alias)]: merge alias entities into canonical (aliases
    recorded, evidence unioned); existing relations re-pointed. Returns merge records."""
    merged, alias_map = [], {}
    for canonical, alias in alias_pairs:
        kc, ka = _key(canonical), _key(alias)
        if kc == ka or ka not in st["entities"] or kc not in st["entities"]:
            continue
        c, a = st["entities"][kc], st["entities"][ka]
        if c["type"] != a["type"]:
            continue  # a cross-type mention is a conflict, not a coref
        c["aliases"] = sorted(set(c["aliases"]) | {a["name"]} | set(a["aliases"]))
        for ev in a["evidences"]:
            _fold_ev(c["evidences"], ev)
        c["docs"] = sorted(set(c["docs"]) | set(a["docs"]))
        del st["entities"][ka]
        alias_map[ka] = c["name"]
        merged.append({"canonical": c["name"], "alias": a["name"], "docs": a["docs"]})
    for k in list(st["relations"]):  # re-point existing relations at canonical names
        r = st["relations"][k]
        r["subject"] = alias_map.get(_key(r["subject"]), r["subject"])
        r["object"] = alias_map.get(_key(r["object"]), r["object"])
        nk = (_key(r["subject"]), r["predicate"], _key(r["object"]))
        if nk != k:
            tgt = st["relations"].pop(k)
            if nk in st["relations"]:
                cur = st["relations"][nk]
                for ev in tgt["evidences"]:
                    _fold_ev(cur["evidences"], ev)
                cur["docs"] = sorted(set(cur["docs"]) | set(tgt["docs"]))
            else:
                st["relations"][nk] = tgt
    return merged, alias_map


def query_ontology(o, term):
    """Every assertion touching `term` (name, alias, or endpoint) with its evidence spans."""
    k = _key(term)
    hits = {"entities": [], "relations": []}
    for e in o.get("abox", {}).get("entities", []):
        if k in (_key(e["name"]), *[_key(a) for a in e.get("aliases", [])]):
            hits["entities"].append(e)
    for r in o.get("abox", {}).get("relations", []):
        if k in (_key(r["subject"]), _key(r["object"])):
            hits["relations"].append(r)
    return hits


def _mark(x, key):
    """Digest marker of an assertion's grounding flag: ✓ grounded · ⚠ ungrounded · none = never judged."""
    return {True: " ✓", False: " ⚠"}.get(x.get(key), "")


def to_markdown(o):
    """Ontology v2 -> shareable markdown digest (issue #12): stats + provenance,
    conflicts table, entities by type, relations with evidence quotes."""
    from collections import defaultdict
    st = o.get("stats", {})
    prov = o.get("provenance", {})
    L = [f"# Ontology · {o.get('domain', '?')}", "",
         f"- **{st.get('entities', 0)} entities · {st.get('relations', 0)} relations · "
         f"{st.get('conflicts', 0)} conflicts · {st.get('flagged', 0)} unknown types flagged**",
         f"- provenance: {prov.get('model', '?')} · {prov.get('calls', '?')} calls · "
         f"{prov.get('tokens_in', 0):,} in / {prov.get('tokens_out', 0):,} out tokens · "
         f"{prov.get('elapsed_s', '?')}s · built {o.get('built_at', '?')}"]
    if sum(st.get(k, 0) for k in ("entities_grounded", "entities_ungrounded",
                                  "relations_grounded", "relations_ungrounded")):
        L.append(f"- type grounding (judged at build time): entities {st.get('entities_grounded', 0)} grounded · "
                 f"{st.get('entities_ungrounded', 0)} ungrounded; relations {st.get('relations_grounded', 0)} grounded · "
                 f"{st.get('relations_ungrounded', 0)} ungrounded — ✓ the best carried quote grounds the claim; "
                 "⚠ no carried quote grounds it (kept and flagged, never dropped)")
    L.append("")
    if o.get("conflicts"):
        L += ["## Conflicts (both evidences kept, awaiting review)", "",
              "| Entity | Types | Evidence A | Evidence B |", "|---|---|---|---|"]
        for c in o["conflicts"][:20]:
            t1, t2 = list(c["types"].items())[:2]
            L.append(f"| {c['entity']} | {t1[0]} / {t2[0]} | "
                     f"\"{t1[1].get('quote', '')[:50]}\" ({t1[1].get('doc', '?')}) | "
                     f"\"{t2[1].get('quote', '')[:50]}\" ({t2[1].get('doc', '?')}) |")
        L.append("")
    if o.get("flagged_ungrounded"):
        L += ["## Ungrounded type clashes (kept, not conflicts)", "",
              "| Entity | Typed as | Challenged as | Challenger's quote |", "|---|---|---|---|"]
        for c in o["flagged_ungrounded"][:20]:
            L.append(f"| {c['entity']} | {c['existing_type']} | {c['asserted_type']} | "
                     f"\"{c['evidence'].get('quote', '')[:50]}\" ({c['evidence'].get('doc', '?')}) |")
        L += ["", "> A different type asserted with a quote that does not ground it is a guess, not a "
              "conflict; it becomes one only when a grounded quote says so.", ""]
    by_type = defaultdict(list)
    for e in o.get("abox", {}).get("entities", []):
        by_type[e["type"]].append(e)
    L.append("## Entities")
    for t, es in sorted(by_type.items()):
        L.append(f"\n### {t} ({len(es)})")
        for e in es[:40]:
            al = f" · aka {', '.join(e['aliases'])}" if e.get("aliases") else ""
            ev = e["evidences"][0]["quote"] if e.get("evidences") else ""
            L.append(f"- **{e['name']}**{al}{_mark(e, 'type_grounding')} — \"{ev[:70]}\" ({', '.join(e.get('docs', [])[:3])})")
    L += ["", "## Relations", "", "| Subject | Predicate | Object | Evidence |", "|---|---|---|---|"]
    for r in o.get("abox", {}).get("relations", [])[:200]:
        ev = r["evidences"][0]["quote"] if r.get("evidences") else ""
        L.append(f"| {r['subject']} | {r['predicate']} | {r['object']}{_mark(r, 'grounding')} | \"{ev[:50]}\" |")
    L += ["", "> Every assertion carries its evidence span in the JSON; this page is the digest. "
          "Not investment/enterprise advice."]
    return "\n".join(L)


def diff_ontologies(a, b):
    """Run-layer diff (issue #14): what changed between two ontology artifacts,
    at evidence granularity. Removed entities are reported with their cause when
    knowable (certification rejection recorded in b)."""
    ea = {e["name"]: e for e in a.get("abox", {}).get("entities", [])}
    eb = {e["name"]: e for e in b.get("abox", {}).get("entities", [])}
    ra = {(r["subject"], r["predicate"], r["object"]): r for r in a.get("abox", {}).get("relations", [])}
    rb = {(r["subject"], r["predicate"], r["object"]): r for r in b.get("abox", {}).get("relations", [])}
    certs_b = {c.get("name"): c for c in b.get("certifications", {}).values()}
    d = {"entities_added": sorted(set(eb) - set(ea)),
         "entities_removed": sorted(set(ea) - set(eb)),
         "removal_causes": {n: ("certified-reject: " + certs_b[n]["note"]) if n in certs_b and certs_b[n]["verdict"] == "reject"
                            else "not re-asserted" for n in sorted(set(ea) - set(eb))},
         "evidence_grown": {n: len(eb[n].get("evidences", [])) - len(ea[n].get("evidences", []))
                            for n in set(ea) & set(eb)
                            if len(eb[n].get("evidences", [])) != len(ea[n].get("evidences", []))},
         "aliases_added": {n: [x for x in eb[n].get("aliases", []) if x not in ea[n].get("aliases", [])]
                           for n in set(ea) & set(eb) if set(eb[n].get("aliases", [])) - set(ea[n].get("aliases", []))},
         "relations_added": sorted(set(rb) - set(ra)),
         "relations_removed": sorted(set(ra) - set(rb)),
         "conflicts_added": [c for c in b.get("conflicts", []) if c not in a.get("conflicts", [])],
         "certifications_added": [c for c in b.get("certifications", {}).values()
                                  if c["name"] not in {x.get("name") for x in a.get("certifications", {}).values()}],
         "stats": {"a": a.get("stats", {}), "b": b.get("stats", {})}}
    return d


def render_diff(d):
    L = ["# Ontology diff"]
    L.append(f"\n{d['stats']['a'].get('entities', '?')} → {d['stats']['b'].get('entities', '?')} entities · "
             f"{d['stats']['a'].get('relations', '?')} → {d['stats']['b'].get('relations', '?')} relations\n")
    if d["entities_added"]:
        L.append("**Entities added**: " + ", ".join(d["entities_added"]))
    if d["entities_removed"]:
        L.append("**Entities removed**:")
        L += [f"- {n} — {cause}" for n, cause in d["removal_causes"].items()]
    if d["evidence_grown"]:
        L.append("**Evidence grown**: " + ", ".join(f"{n} ({v:+d})" for n, v in d["evidence_grown"].items()))
    if d["aliases_added"]:
        L.append("**Aliases added**: " + ", ".join(f"{n} += {a}" for n, a in d["aliases_added"].items() if a))
    if d["relations_added"]:
        L.append(f"**Relations added** ({len(d['relations_added'])}):")
        L += [f"- ({s}) -[{p}]-> ({o})" for s, p, o in d["relations_added"][:30]]
    if d["relations_removed"]:
        L.append(f"**Relations removed**: {len(d['relations_removed'])}")
    if d["conflicts_added"]:
        L.append("**New conflicts**:")
        L += [f"- {c['entity']}: {' vs '.join(c['types'])}" for c in d["conflicts_added"]]
    if d["certifications_added"]:
        L.append("**Certifications**:")
        L += [f"- {c['name']} → {c['verdict']}" + (f" ({c['note']})" if c.get("note") else "")
              for c in d["certifications_added"]]
    if not any([d["entities_added"], d["entities_removed"], d["relations_added"], d["relations_removed"],
                d["evidence_grown"], d["conflicts_added"], d["certifications_added"], d["aliases_added"]]):
        L.append("(no material changes)")
    return "\n".join(L)


def to_jsonld(o):
    """Ontology v2 JSON -> JSON-LD 1.1 (issue #9): entities as typed nodes with
    evidence, relations as reified statement nodes with subject/object refs.
    @vocab is a stable placeholder namespace — evidence stays first-class."""
    import hashlib
    def eid(name):
        return "urn:dshao:entity:" + re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    def rid(r):
        h = hashlib.sha1(f"{r['subject']}|{r['predicate']}|{r['object']}".encode()).hexdigest()[:10]
        return f"urn:dshao:rel:{h}"
    ctx = {"@vocab": "https://dsh-auto-ontology.dev/vocab/",
           "name": "https://schema.org/name",
           "aliases": {"@id": "https://dsh-auto-ontology.dev/vocab/alias", "@container": "@set"},
           "evidence": {"@id": "https://dsh-auto-ontology.dev/vocab/evidence", "@container": "@list"}}
    graph = []
    for e in o.get("abox", {}).get("entities", []):
        node = {"@id": eid(e["name"]), "@type": e["type"], "name": e["name"],
                "aliases": e.get("aliases", []), "evidence": e.get("evidences", [])}
        if "type_grounding" in e:
            node["type_grounding"] = e["type_grounding"]
        graph.append(node)
    for r in o.get("abox", {}).get("relations", []):
        node = {"@id": rid(r), "@type": r["predicate"],
                "subject": {"@id": eid(r["subject"]), "name": r["subject"]},
                "object": {"@id": eid(r["object"]), "name": r["object"]},
                "evidence": r.get("evidences", [])}
        if "grounding" in r:
            node["grounding"] = r["grounding"]
        graph.append(node)
    return {"@context": ctx, "@graph": graph,
            "dshao:domain": o.get("domain"), "dshao:built_at": o.get("built_at")}


def _abox(st):
    """The store's ABox in artifact shape — the ONE place entities and relations are
    serialized, so a certification rebuild keeps every derived flag."""
    ents, rels = [], []
    for e in sorted(st["entities"].values(), key=lambda x: x["name"].lower()):
        f = _flag(e["evidences"])
        ents.append(dict(e, evidences=_strongest(e["evidences"]), **({"type_grounding": f} if f is not None else {})))
    for r in sorted(st["relations"].values(), key=lambda r: (r["subject"].lower(), r["predicate"])):
        f = _flag(r["evidences"])
        rels.append(dict(r, evidences=_strongest(r["evidences"]), **({"grounding": f} if f is not None else {})))
    return {"entities": ents, "relations": rels}


def store_to_ontology(st, new_type_descs, provenance):
    abox = _abox(st)

    def n(kind, key, f):
        return sum(1 for x in abox[kind] if x.get(key) is f)
    return {
        "domain": st["domain"], "built_at": dt.datetime.now().isoformat(timespec="seconds"),
        "provenance": provenance,
        "tbox": {"entity_types": [{"name": t, "desc": new_type_descs.get(t, "")}
                                   for t in sorted(st["tbox_types"])],
                 "relation_types": list(st["tbox_relations"].values())},
        "abox": abox,
        "conflicts": st["conflicts"],
        "flagged_unknown_types": st["flagged"],
        "flagged_ungrounded": st["flagged_ungrounded"],
        "merge_log": st["merge_log"],
        "certifications": st.get("certifications", {}),
        "stats": {"entities": len(abox["entities"]), "relations": len(abox["relations"]),
                  "conflicts": len(st["conflicts"]), "flagged": len(st["flagged"]),
                  "suppressed_by_certification": st.get("suppressed", 0),
                  "entities_grounded": n("entities", "type_grounding", True),
                  "entities_ungrounded": n("entities", "type_grounding", False),
                  "relations_grounded": n("relations", "grounding", True),
                  "relations_ungrounded": n("relations", "grounding", False),
                  "ungrounded_type_clashes": len(st["flagged_ungrounded"])},
    }


# ── pipeline ────────────────────────────────────────────────────────────────

P_TBOX = {
    "en": ("You are an ontology engineer. Extract the ontology schema (TBox) from the corpus sample. Output JSON: "
           '{"entity_types":[{"name":"...","desc":"..."}],"relation_types":[{"name":"...","domains":"TypeA","ranges":"TypeB","desc":"..."}]}. '
           "Type names in English snake_case; write every desc in English. Extract only what the corpus genuinely supports — prefer fewer, truer types."),
    "zh": ("你是本体工程师。从语料样本抽取本体模式（TBox）。输出 JSON："
           '{"entity_types":[{"name":"...","desc":"..."}],"relation_types":[{"name":"...","domains":"类型A","ranges":"类型B","desc":"..."}]}'
           "。类型名用英文 snake_case，desc 用中文。只抽取语料真实支撑的，宁缺毋滥。"),
}
P_COREF = {
    "en": ("You resolve entity mentions in an ontology. Given entity names (with types), output JSON "
           '{"pairs":[{"canonical":"...","alias":"..."}]} where alias is clearly the SAME real-world '
           "thing as canonical under a different mention (abbreviation, casing, prefix). Merge ONLY "
           "when certain; when arguable, do not merge. Never pair entities of different types."),
    "zh": ("你在本体中做实体提及消解。给定实体名（含类型），输出 JSON "
           '{"pairs":[{"canonical":"...","alias":"..."}]}——alias 与 canonical 须确定是同一现实事物'
           "（缩写/大小写/前缀差异）。只有确定才合并，可争议的不合；不同类型绝不配对。"),
}
P_ABOX = {
    "en": ("You are an ontology instance extractor. From the document, extract entity and relation instances (ABox) based on the given TBox. "
           "Discipline: types must come from the TBox; when unsure, do not extract. "
           "EVIDENCE is a verbatim quote copied EXACTLY from the document (up to 200 chars, no paraphrase): "
           "for an entity, the sentence that states what the entity IS - it must contain the entity's name as written; "
           "for a relation, the sentence that names an endpoint and states the relation. "
           "When a line takes its meaning from the list label, heading or table header above it, "
           "start the quote at that label. "
           "If the document only mentions a name without saying what it is, quote the sentence that mentions it. "
           "Output JSON: "
           '{"entities":[{"name":"...","type":"...","evidence":"..."}],'
           '"relations":[{"subject":"...","predicate":"...","object":"...","evidence":"..."}]}'),
    "zh": ("你是本体实例抽取器。基于给定 TBox 从文档抽取实体与关系实例（ABox）。"
           "**纪律**：类型必须取自 TBox；不确定的不抽。"
           "evidence 必须是**逐字**复制的原文引文（不超过 200 字，不得改写）："
           "实体——说明该实体**是什么**的那句话，且必须包含实体名原文；"
           "关系——点出关系一端并陈述该关系的那句话。"
           "当某一行的含义来自其上方的列表标签、标题或表头时，引文从该标签开始。"
           "若文档只是提及名字而未说明其为何物，则引用提及它的那句话。"
           "输出 JSON："
           '{"entities":[{"name":"...","type":"...","evidence":"..."}],'
           '"relations":[{"subject":"...","predicate":"...","object":"...","evidence":"..."}]}'),
}
P_REGROUND = {
    "en": ("You repair evidence quotes for ontology assertions. For each numbered claim, find in the document the "
           "contiguous span that STATES the claim and copy it exactly (up to 200 chars). The span may start at the "
           "list label, heading or table header that gives a line its meaning (for example \"Family: [X] - [Y]\" "
           "before a link). An entity quote must contain the entity's name as written and say what the entity is; "
           "a relation quote must name an endpoint and state the relation. If the document does not state the "
           "claim, set quote to null - never paraphrase, never stitch together sentences that are not adjacent. "
           'Output JSON: {"repairs":[{"i":1,"quote":"... or null"}]} - exactly one entry per item, same numbering.'),
    "zh": ("你为 ontology 断言修复证据引文。对每条编号断言，在文档中找到**陈述**该断言的连续原文片段并逐字复制"
           "（不超过 200 字）。片段可以从赋予该行含义的列表标签、标题或表头开始（例如链接之前的“Family: [X] · [Y]”）。"
           "实体引文必须包含实体名原文并说明该实体是什么；关系引文必须点出一个端点并陈述该关系。"
           "若文档并未陈述该断言，quote 置为 null——不得改写、不得拼接不相邻的句子。"
           '输出 JSON：{"repairs":[{"i":1,"quote":"... 或 null"}]}——每项恰好一条，编号一致。'),
}

JUDGE_JOBS = int(os.environ.get("ONTOLOGY_JUDGE_JOBS") or 8)   # concurrent single-item judge calls


def _reject_reason(x, text):
    """Why an extracted quote can never ground its claim — None when it may be judged.

    The one check the judge cannot make: it sees the quote, not the document, so only a
    verbatim span of the document is evidence. A quote that does not spell the entity's
    name or a relation's endpoint is still JUDGED. (Until 2026-11-25 that was a
    pre-reject; on the published before-artifact it would have turned away 30 ungrounded
    assertions and 9 grounded ones — "payload" for market_data_payload, a plugin typed
    from its own title line. A quote about ANOTHER instance of the type stays rejected by
    the judge: the adversarial set pins it.)"""
    q = x.get("evidence", "")
    if not q or not grounding.is_verbatim(q, text):
        return tt("quote is not verbatim in the source document", "引文并非文档原文")
    return None


def _item(kind, x, doc, descs):
    tname = x["type"] if kind == "entity" else x["predicate"]
    desc = descs.get(tname, "")
    claim = (grounding.entity_claim(x["name"], x["type"]) if kind == "entity"
             else grounding.relation_claim(x.get("subject") or "", x["predicate"], x.get("object") or ""))
    return {"kind": kind, "type_name": tname, "type_desc": desc, "claim": claim, "quote": x["evidence"], "doc": doc}


def _judge(cands, doc, descs):
    """-> verdicts in the same order: the shared judge, ONE call per item — the protocol the
    eval and the adversarial set use (a hand audit found batched verdicts less accurate).
    The items are judged concurrently; the order of the verdicts is the order of the input."""
    items = [_item(k, x, doc, descs) for k, x in cands]
    if not items:
        return []
    with cf.ThreadPoolExecutor(max_workers=min(JUDGE_JOBS, len(items))) as ex:
        return list(ex.map(lambda it: grounding.judge([it], JUDGE_MODEL, call=_judge_call)[0], items))


def _judge_call(sysmsg, user):
    """A judge call: through the cost guard AND through --judge-model. grounding.judge()
    hands `call` no model, so a bare llm() here judged with the build model while the
    provenance named the judge model."""
    return llm(sysmsg, user, model=JUDGE_MODEL)


def _reground(d, failed, descs):
    """-> a replacement quote (or None) per failed assertion, from ONE call."""
    L = [tt(f"Document ({d['path']}):", f"文档（{d['path']}）："), d["text"], "", tt("Claims:", "断言：")]
    for i, (kind, x) in enumerate(failed, 1):
        L.append(f"{i}. {_item(kind, x, d['path'], descs)['claim']}\n   "
                 + tt("rejected quote", "被否决的引文") + f": {json.dumps(x['evidence'], ensure_ascii=False)}")
    out = llm(P_REGROUND[LANG], "\n".join(L))
    got = {}
    for r in out.get("repairs", []):
        try:
            got[int(r.get("i", 0))] = r.get("quote")
        except (AttributeError, TypeError, ValueError):
            continue
    return [got.get(i) for i in range(1, len(failed) + 1)]


def ground_doc(d, out, known, descs, reground=True):
    """The grounding pass for ONE document, in place on the extracted assertions: every
    (claim, quote) leaves with `grounded` True / False, or untouched when it never had a
    quote to judge. Order: the verbatim gate (no LLM — a span not in the document is not
    evidence), one judge call per verbatim quote, then — only if something failed — one
    re-ground call and a re-judge of every repaired quote. Nothing is dropped: an
    ungrounded assertion is folded like any other and flagged.
    -> {entities: [grounded, ungrounded], relations: [...], regrounded}"""
    cands = [("entity", e) for e in out.get("entities", []) if e.get("name") and e.get("type") in known]
    cands += [("relation", r) for r in out.get("relations", [])]
    todo = []
    for kind, x in cands:
        why = _reject_reason(x, d["text"])
        if why is None:
            todo.append((kind, x))
        else:
            x["grounded"], x["judge_reason"] = False, why
    for (kind, x), v in zip(todo, _judge(todo, d["path"], descs)):
        x["grounded"], x["judge_reason"] = v["grounded"], v["reason"]
    failed = [(k, x) for k, x in cands if x.get("evidence") and x.get("grounded") is False]
    repaired = []
    if reground and failed:
        for (kind, x), q in zip(failed, _reground(d, failed, descs)):
            if q and _reject_reason(dict(x, evidence=q), d["text"]) is None:
                x["evidence"], x["regrounded"] = q, True
                repaired.append((kind, x))
        for (kind, x), v in zip(repaired, _judge(repaired, d["path"], descs)):
            x["grounded"], x["judge_reason"] = v["grounded"], v["reason"]
    return {"entities": [sum(1 for k, x in cands if k == "entity" and x.get("grounded") is True),
                         sum(1 for k, x in cands if k == "entity" and x.get("grounded") is False)],
            "relations": [sum(1 for k, x in cands if k == "relation" and x.get("grounded") is True),
                          sum(1 for k, x in cands if k == "relation" and x.get("grounded") is False)],
            "regrounded": len(repaired)}


def build(docs, domain, base=None, sample=4, ground=True, reground=True):
    st = base if base is not None else new_store(domain)
    tbox = llm(P_TBOX[LANG],
               tt(f"Domain: {domain}\nCorpus sample:\n" + "\n\n".join(d["text"][:1500] for d in docs[:sample]),
                  f"领域：{domain}\n语料样本：\n" + "\n\n".join(d["text"][:1500] for d in docs[:sample])))
    known = {e["name"] for e in tbox.get("entity_types", [])}
    new_type_descs = {e["name"]: e.get("desc", "") for e in tbox.get("entity_types", [])
                      if e["name"] not in st["tbox_types"]}
    st["tbox_types"] |= known
    for r in tbox.get("relation_types", []):
        st["tbox_relations"][(r.get("name"), r.get("domains"), r.get("ranges"))] = r
    descs = {t["name"]: t.get("desc", "") for t in tbox.get("entity_types", [])}
    descs.update({r.get("name"): r.get("desc", "") for r in tbox.get("relation_types", [])})

    per_doc, tally, quoteless = [], {"entities": [0, 0], "relations": [0, 0], "regrounded": 0}, 0
    for d in docs:
        out = llm(P_ABOX[LANG],
                  tt(f"TBox:\n{json.dumps(tbox, ensure_ascii=False)}\n\nDocument ({d['path']}):\n{d['text']}",
                     f"TBox：{json.dumps(tbox, ensure_ascii=False)}\n\n文档（{d['path']}）：\n{d['text']}"))
        if ground:
            g = ground_doc(d, out, known, descs, reground=reground)
            for k in ("entities", "relations"):
                tally[k] = [a + b for a, b in zip(tally[k], g[k])]
            tally["regrounded"] += g["regrounded"]
        per_doc.append((d, out))
        for e in out.get("entities", []):
            if not e.get("name"):
                continue
            if not e.get("evidence"):
                quoteless += 1
            elif e.get("type") in known:
                fold_entity(st, e["name"], e["type"], e["evidence"], d["path"], grounded=e.get("grounded"),
                            reason=e.get("judge_reason"))
            else:
                st["flagged"].append({**e, "doc": d["path"]})  # type guard — never silently dropped

    merged_aliases, alias_map = [], {}
    names = [f"{e['name']} ({e['type']})" for e in st["entities"].values()]
    if len(names) >= 2:
        pairs = llm(P_COREF[LANG], tt(f"Domain: {domain}\nEntities:\n" + "\n".join(names),
                                      f"领域：{domain}\n实体：\n" + "\n".join(names)))
        merged_aliases, alias_map = apply_aliases(st, [(p.get("canonical"), p.get("alias"))
                                                       for p in pairs.get("pairs", [])
                                                       if p.get("canonical") and p.get("alias")])
    for d, out in per_doc:  # relations fold AFTER coref so endpoints are canonical
        for r in out.get("relations", []):
            if not r.get("evidence"):
                quoteless += 1
                continue
            fold_relation(st, r.get("subject"), r.get("predicate"), r.get("object"), r["evidence"], d["path"],
                          alias_map=alias_map, grounded=r.get("grounded"), reason=r.get("judge_reason"))
    if quoteless:
        print(tt(f"{quoteless} extracted assertion(s) arrived without a quote — not folded (no evidence, no assertion)",
                 f"{quoteless} 条抽取结果未带引文——不予并入（无证据，无断言）"), file=sys.stderr)
    return st, new_type_descs, merged_aliases, tally


def _text_w(s, fs):
    """Approximate rendered width in px: a monospace cell is ~0.6 em, a CJK cell ~1 em."""
    return fs * sum(1.0 if ord(c) > 0x2E80 else 0.6 for c in s)


def _write_svg(path, o, domain):
    ents, rels = o["abox"]["entities"], o["abox"]["relations"]
    by_type = {}
    for e in ents:
        by_type.setdefault(e["type"], []).append(e)
    colors = ["#2456c4", "#c23531", "#2f8a4c", "#8a5fc2", "#b07a2a", "#2a8a8a"]
    nodes, cx, cy = [], 400, 340
    clusters = list(by_type.items())[:6]
    for ci, (t, es) in enumerate(clusters):
        r0, ang0 = 60 + ci * 45, ci * 2 * math.pi / max(len(clusters), 1)
        gx, gy = cx + r0 * 1.9 * math.cos(ang0), cy + r0 * 1.5 * math.sin(ang0)
        for i, e in enumerate(es[:10]):
            a = 2 * math.pi * i / max(len(es[:10]), 1)
            nodes.append((e["name"][:14], gx + 52 * math.cos(a), gy + 40 * math.sin(a), colors[ci % 6]))
    # the title takes two lines and the graph is shifted so that no label leaves the canvas:
    # with six type clusters the outer rings used to put labels above y=0 and left of x=0
    title = domain
    while title and _text_w(title, 13) > 840:
        title = title[:-1]
    if title != domain:
        title += "…"
    st = o.get("stats") or {}
    line2 = f"{len(ents)} entities / {len(rels)} relations"
    if "entities_grounded" in st:
        ok = st["entities_grounded"] + st["relations_grounded"]
        line2 += f" · {ok} judged grounded · {len(ents) + len(rels) - ok} not grounded, kept and flagged"
    TOP, PAD, W, H = 48, 8, 860, 700
    tx = ty = 0.0
    if nodes:
        x0 = min(n[1] for n in nodes) - 4
        x1 = max(n[1] + 6 + _text_w(n[0], 9) for n in nodes)
        y0 = min(n[2] for n in nodes) - 7
        y1 = max(n[2] for n in nodes) + 4
        W, H = max(W, math.ceil(x1 - x0) + 2 * PAD), max(H, math.ceil(y1 - y0) + TOP + PAD)
        tx, ty = (W - (x1 - x0)) / 2 - x0, TOP - y0
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="monospace">',
           f'<text x="10" y="16" font-size="13">{escape(title)}</text>',
           f'<text x="10" y="33" font-size="13">{escape(line2)}</text>',
           f'<g transform="translate({tx:.0f} {ty:.0f})">']
    nm = {n[0]: (n[1], n[2]) for n in nodes}
    for r in rels:
        if r["subject"][:14] in nm and r["object"][:14] in nm:
            x1, y1 = nm[r["subject"][:14]]
            x2, y2 = nm[r["object"][:14]]
            svg.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#99a" stroke-width="0.7"/>')
    for name, x, y, c in nodes:
        svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{c}"/>'
                   f'<text x="{x + 6:.0f}" y="{y + 3:.0f}" font-size="9" fill="#345">{escape(name)}</text>')
    svg.append("</g></svg>")
    open(path, "w").write("".join(svg))


def _ev_mark(ev):
    """Query-output marker of one evidence: its verdict, and why when it failed."""
    if ev.get("grounded") is True:
        return "  ✓"
    if ev.get("grounded") is False:
        return "  ⚠" + (f" — {ev['reason']}" if ev.get("reason") else "")
    return ""


def main():
    global LANG, MAX_CALLS, JUDGE_MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=None, help="directory, glob or single file, e.g. '~/dsh-*/README.md'")
    ap.add_argument("--domain", default=None, help="corpus domain description (schema pass)")
    ap.add_argument("--merge", default=None, help="existing ontology JSON to fold into (append-only)")
    ap.add_argument("--query", default=None, help="query mode: every assertion about X, with evidence")
    ap.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"),
                    help="diff two ontology artifacts at evidence granularity")
    ap.add_argument("--certify", default=None, metavar="NAME",
                    help="certification mode: --certify NAME --verdict accept|reject [--note ...] [--from x.json]")
    ap.add_argument("--verdict", choices=("accept", "reject"), default=None, help="verdict for --certify")
    ap.add_argument("--note", default="", help="optional note recorded with a certification")
    ap.add_argument("--actor", default=None,
                    help="who issues a --certify verdict, recorded with it (env ONTOLOGY_ACTOR; "
                         "an agent applying a verdict must name itself)")
    ap.add_argument("--jsonld", action="store_true", help="export the ontology as JSON-LD 1.1 (with --from, or the newest artifact)")
    ap.add_argument("--html", action="store_true", help="render the ontology as a single-file HTML digest (with --save, or --from standalone)")
    ap.add_argument("--from", dest="frm", default=None,
                    help="ontology file for --query / --jsonld / --html / --trajectory (default: newest in outdir)")
    ap.add_argument("--trajectory", action="store_true",
                    help="export mode: the artifact as an ao-trajectory/0.1 event stream, one JSON event per line")
    ap.add_argument("artifacts", nargs="*",
                    help="artifact files for --trajectory (default: --from, or the newest in outdir)")
    ap.add_argument("--out", default=None, help="with --trajectory: write the stream here instead of stdout")
    ap.add_argument("--sample", type=int, default=4, help="docs sampled for the TBox schema pass")
    ap.add_argument("--max-calls", type=int, default=None, help="cost guard: abort beyond this many LLM calls")
    ap.add_argument("--no-ground", action="store_true",
                    help="skip the type-grounding judge (no assertion gets a grounding flag)")
    ap.add_argument("--judge-model", default=None,
                    help="model for the grounding judge (default: the build model; env ONTOLOGY_JUDGE_MODEL)")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--lang", choices=("en", "zh"), default=LANG, help="output language (default en)")
    args = ap.parse_args()
    LANG = args.lang
    MAX_CALLS = args.max_calls
    JUDGE_MODEL = args.judge_model or os.environ.get("ONTOLOGY_JUDGE_MODEL") or MODEL
    t0 = time.time()

    if args.diff:
        a, b = (json.load(open(p)) for p in args.diff)
        print(render_diff(diff_ontologies(a, b)))
        return

    if args.artifacts and not args.trajectory:
        ap.error("artifact files are read only with --trajectory")
    if args.trajectory:
        import trajectory
        if args.artifacts and args.frm:
            ap.error("--trajectory takes artifact files or --from, not both")
        paths = args.artifacts or ([args.frm] if args.frm else
                                   sorted(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)[-1:])
        if not paths:
            sys.exit(tt(f"no ontology artifact under {OUTDIR}", f"{OUTDIR} 下没有本体文件"))
        for p in paths:
            if not os.path.isfile(p):
                sys.exit(tt(f"no such ontology artifact: {p}", f"没有这个本体文件：{p}"))
        events = [e for p in paths for e in trajectory.export_events(json.load(open(p)), os.path.basename(p))]
        for i, e in enumerate(events):   # one stream: positions run on across artifacts
            e["seq"] = i
        lines = trajectory.render(events)
        if args.out:
            open(args.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            print(f"trajectory: {trajectory.tally(events)} -> {args.out}")
        else:
            print("\n".join(lines))
            print(f"trajectory: {trajectory.tally(events)}", file=sys.stderr)
        return

    if args.certify:
        if not args.verdict:
            sys.exit("--certify needs --verdict accept|reject")
        path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
        actor = args.actor or os.environ.get("ONTOLOGY_ACTOR") or "unspecified"
        o = certify(json.load(open(path)), args.certify, args.verdict, note=args.note, actor=actor)
        out = os.path.join(OUTDIR, dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-certified.json")
        json.dump(o, open(out, "w"), ensure_ascii=False, indent=1)
        print(f"{args.certify} {args.verdict} -> {out}")
        return

    if args.html and not args.docs:
        import render_html
        path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
        out = os.path.splitext(path)[0] + ".html"
        open(out, "w", encoding="utf-8").write(render_html.render(to_markdown(json.load(open(path)))))
        print(f"html -> {out}")
        return

    if args.jsonld:
        path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
        out = os.path.splitext(path)[0] + ".jsonld"
        json.dump(to_jsonld(json.load(open(path))), open(out, "w"), ensure_ascii=False, indent=1)
        print(f"jsonld -> {out}")
        return

    if args.query:
        path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
        o = json.load(open(path))
        hits = query_ontology(o, args.query)
        print(f"# {args.query} — {path}")
        for e in hits["entities"]:
            print(f"\n[{e['type']}] {e['name']}" +
                  (f" (aliases: {', '.join(e['aliases'])})" if e.get("aliases") else "") + _mark(e, "type_grounding"))
            for ev in e.get("evidences", []):
                print(f'  | {ev["doc"]}: "{ev["quote"]}"' + _ev_mark(ev))
        for r in hits["relations"]:
            print(f"\n({r['subject']}) -[{r['predicate']}]-> ({r['object']})" + _mark(r, "grounding"))
            for ev in r.get("evidences", []):
                print(f'  | {ev["doc"]}: "{ev["quote"]}"' + _ev_mark(ev))
        if not hits["entities"] and not hits["relations"]:
            print(tt("no assertions matched", "无匹配断言"))
        elif any("type_grounding" in e for e in hits["entities"]) or any("grounding" in r for r in hits["relations"]):
            print("\n" + tt("✓ the quote grounds the claim · ⚠ no carried quote grounds it (kept and flagged)",
                            "✓ 引文支撑断言 · ⚠ 现有引文均不支撑（保留并标记）"))
        return

    if not args.docs or not args.domain:
        sys.exit(tt("--docs and --domain are required for a build", "构建需要 --docs 与 --domain"))
    target = os.path.expanduser(args.docs)
    paths = (sorted(glob.glob(target)) if "*" in args.docs else
             [target] if os.path.isfile(target) else sorted(glob.glob(os.path.join(target, "*"))))
    docs = []
    for p in paths:
        try:
            docs.append({"path": os.path.basename(os.path.dirname(p)) or p,
                         "text": open(p, errors="ignore").read()[:6000]})
        except OSError:
            pass
    if not docs:
        sys.exit(tt("no documents matched", "无文档"))
    print(tt(f"corpus: {len(docs)} doc(s) · domain: {args.domain}",
             f"语料：{len(docs)} 篇 · 领域：{args.domain}"), file=sys.stderr)

    base, prior_stats = None, None
    if args.merge:
        base = load_store(json.load(open(args.merge)))
        prior_stats = {k: len(base[k]) for k in ("entities", "relations", "conflicts")}
        print(tt(f"merging into {args.merge} (append-only)", f"增量并入 {args.merge}（append-only）"), file=sys.stderr)

    st, new_type_descs, corefed, tally = build(docs, args.domain, base=base, sample=max(1, args.sample),
                                               ground=not args.no_ground)
    if corefed:
        st["merge_log"].append({"ran_at": dt.datetime.now().isoformat(timespec="seconds"),
                                "coref_merges": corefed})
    if prior_stats:
        st["merge_log"][-1] if st["merge_log"] else st["merge_log"].append({})
        st["merge_log"][-1].update({"merged_into": args.merge,
                                    "added_docs": len(docs),
                                    "entities_before": prior_stats["entities"],
                                    "entities_after": len(st["entities"])})
    prov = {"model": MODEL, "temperature": 0, "elapsed_s": round(time.time() - t0),
            "calls": COST["calls"], "tokens_in": COST["in"], "tokens_out": COST["out"],
            "docs_this_run": len(docs), "merged_from": bool(args.merge),
            "judge_model": JUDGE_MODEL, "grounding_pass": not args.no_ground}
    o = store_to_ontology(st, new_type_descs, prov)

    print(f"\n## Ontology build · {args.domain}\n")
    print(tt(f"- Entity types {len(o['tbox']['entity_types'])} · entities {o['stats']['entities']} · "
             f"relations {o['stats']['relations']} · conflicts {o['stats']['conflicts']} · "
             f"unknown types flagged {o['stats']['flagged']}",
             f"- 实体类型 {len(o['tbox']['entity_types'])} · 实体 {o['stats']['entities']} · "
             f"关系 {o['stats']['relations']} · 冲突 {o['stats']['conflicts']} · "
             f"未知类型拦截 {o['stats']['flagged']}"))
    if not args.no_ground:
        s = o["stats"]
        print(tt(f"- type grounding (judge {JUDGE_MODEL}): entities {s['entities_grounded']} grounded · "
                 f"{s['entities_ungrounded']} ungrounded; relations {s['relations_grounded']} grounded · "
                 f"{s['relations_ungrounded']} ungrounded; {tally['regrounded']} quote(s) re-grounded · "
                 f"{s['ungrounded_type_clashes']} ungrounded type clash(es) kept out of conflicts",
                 f"- 类型接地（判官 {JUDGE_MODEL}）：实体 {s['entities_grounded']} 接地 · "
                 f"{s['entities_ungrounded']} 未接地；关系 {s['relations_grounded']} 接地 · "
                 f"{s['relations_ungrounded']} 未接地；{tally['regrounded']} 条引文重取 · "
                 f"{s['ungrounded_type_clashes']} 条未接地类型冲突未计入 conflicts"))
    print(tt(f"- provenance: {prov['calls']} calls · {prov['tokens_in']:,} in / {prov['tokens_out']:,} out tokens · {prov['elapsed_s']}s",
             f"- 溯源：{prov['calls']} 次调用 · {prov['tokens_in']:,} 入 / {prov['tokens_out']:,} 出 · {prov['elapsed_s']}s"))
    for c in o["conflicts"][:6]:
        print(f"  ⚔ conflict: {c['entity']} typed " + " vs ".join(c["types"]) +
              tt(" — both evidences kept, awaiting review", " —— 双方证据保全，待复核"))
    for r in o["abox"]["relations"][:10]:
        ev = r["evidences"][0]["quote"] if r["evidences"] else ""
        print(f"  - R: ({r['subject']}) -[{r['predicate']}]-> ({r['object']}) | ev: {ev[:40]}")

    if args.save:
        os.makedirs(OUTDIR, exist_ok=True)
        base_path = os.path.join(OUTDIR, dt.datetime.now().strftime("%Y%m%d-%H%M"))
        json.dump(o, open(base_path + ".json", "w"), ensure_ascii=False, indent=1)
        _write_svg(base_path + ".svg", o, args.domain)
        if args.html:
            try:
                import render_html
                open(base_path + ".html", "w", encoding="utf-8").write(render_html.render(to_markdown(o)))
            except Exception as exc:
                print(f"⚠ html render skipped ({type(exc).__name__})", file=sys.stderr)
        open(base_path + ".md", "w", encoding="utf-8").write(to_markdown(o))
        print(f"\n→ {base_path}.json / .svg / .md", file=sys.stderr)


if __name__ == "__main__":
    main()
