#!/usr/bin/env python3
"""trajectory — an artifact as the event stream that produced it (O5.1, ao-trajectory/0.1)

An artifact is a state: it says what is asserted now. An evolution kernel needs
what HAPPENED — which claims were made, which quote came with each, what the
judge said, what a human or an agent decided — as records it can count and
replay. export_events turns any v0.1/v0.2 artifact into that stream:

  build             the run that wrote the artifact (provenance, stats, TBox)
  fold              one per merge_log entry: a --merge or a coreference pass
  assertion         ONE PER EVIDENCE QUOTE — the append-only unit: claim + quote + verdict
  certification     a verdict that travels with the artifact (actor, note, evidence)
  conflict          both evidences, as kept
  unknown_type      the type guard's catch: asserted with a type outside the TBox
  ungrounded_clash  a different type asserted with a quote that does not ground it

Deterministic: the same artifact exports to the same events in the same order,
and an event's id says what the event says — never its position or its file
name — so replaying a stream into an append-only store adds nothing. The
artifact does not record when a single quote was folded (at = null there) nor
which judge model judged it (`by` = "judge"; the build event names its own
judge). Nothing here calls a model. docs/FORMAT.md carries the contract.
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grounding

SCHEMA = "ao-trajectory/0.1"
KINDS = ("build", "fold", "assertion", "certification", "conflict", "unknown_type", "ungrounded_clash")

# what makes an event itself: the same fact gets the same id whatever its order or file name
IDENTITY = {"build": ("domain", "at", "provenance", "tbox"),
            "fold": ("merge", "alias_merges"),
            "assertion": ("claim", "evidence", "verdict", "by"),
            "certification": ("claim", "verdict", "at", "by", "note", "evidence"),
            "conflict": ("subject",),
            "unknown_type": ("claim", "evidence"),
            "ungrounded_clash": ("subject", "evidence")}


def _id(e):
    def norm(v):
        return json.dumps(v, sort_keys=True, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    parts = [e["kind"]] + [norm(e.get(k)) for k in IDENTITY[e["kind"]]]
    return "aot_" + hashlib.sha1(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]


def _quote(ev, *extra):
    """The evidence of one event: quote, doc, and whatever else the format lets a quote carry."""
    ev = ev or {}
    return {k: ev[k] for k in ("quote", "doc", *extra) if k in ev}


def _assertion(kind, agent, claim, subject, ev):
    g = ev.get("grounded")
    verdict = {True: "grounded", False: "ungrounded"}.get(g)
    return {"kind": "assertion", "at": None, "agent": agent,
            "summary": f"[{kind} · {verdict or 'unjudged'}] {claim} — \"{(ev.get('quote') or '')[:80]}\" ({ev.get('doc', '?')})",
            "claim": claim, "subject": subject, "evidence": _quote(ev, "chunk_id"),
            "verdict": verdict, "by": ("judge:" + ev["judge"] if ev.get("judge") else "judge") if verdict else None,
            "reason": ev.get("reason"), "endorsed": g if verdict else None}


def export_events(o, source=None):
    """Ontology v0.1/v0.2 JSON -> the event list (envelopes complete; `seq` is the list position)."""
    domain, prov, st = o.get("domain", "?"), o.get("provenance") or {}, o.get("stats") or {}
    agent = "dsh-auto-ontology/" + (prov.get("model") or "unknown-model")
    judged = prov.get("grounding_pass") is True and bool(prov.get("judge_model"))
    head = {"schema": SCHEMA, "domain": domain,
            "artifact": {"built_at": o.get("built_at"), "source": source or "?",
                         "model": prov.get("model"), "judge": prov.get("judge_model") if judged else None}}
    evs = [{"kind": "build", "at": o.get("built_at"), "agent": agent,
            "summary": f"[build] {domain}: {st.get('entities', 0)} entities · {st.get('relations', 0)} relations · "
                       f"{prov.get('calls', '?')} call(s) · " + (f"judge {prov['judge_model']}" if judged else "no grounding pass"),
            "provenance": prov, "stats": st,
            "tbox": {"entity_types": [t.get("name") for t in o.get("tbox", {}).get("entity_types", [])],
                     "relation_types": [r.get("name") for r in o.get("tbox", {}).get("relation_types", [])]}}]
    for m in o.get("merge_log") or []:
        merges = [{"canonical": c.get("canonical"), "alias": c.get("alias")} for c in m.get("coref_merges") or []]
        if m.get("merged_into"):
            what = (f"[fold] merged {m.get('added_docs', '?')} doc(s) into {m['merged_into']}: "
                    f"{m.get('entities_before', '?')} → {m.get('entities_after', '?')} entities · "
                    f"{len(merges)} alias merge(s)")
        else:
            what = f"[fold] coreference pass: {len(merges)} alias merge(s)"
        evs.append({"kind": "fold", "at": m.get("ran_at"), "agent": agent, "summary": what,
                    "merge": {k: v for k, v in m.items() if k != "coref_merges"}, "alias_merges": merges})
    for e in o.get("abox", {}).get("entities", []):
        subject = {"name": e.get("name"), "type": e.get("type")}
        claim = grounding.entity_claim(e.get("name") or "?", e.get("type") or "?")
        evs += [_assertion("entity", agent, claim, subject, ev) for ev in e.get("evidences") or []]
    for r in o.get("abox", {}).get("relations", []):
        subject = {"subject": r.get("subject"), "predicate": r.get("predicate"), "object": r.get("object")}
        claim = grounding.relation_claim(r.get("subject") or "", r.get("predicate") or "", r.get("object") or "")
        evs += [_assertion("relation", agent, claim, subject, ev) for ev in r.get("evidences") or []]
    for c in (o.get("certifications") or {}).values():
        actor, note = c.get("actor") or "unspecified", c.get("note") or ""
        claim = grounding.entity_claim(c.get("name") or "?", c.get("type") or "?")
        evs.append({"kind": "certification", "at": c.get("at"), "agent": actor,
                    "summary": f"[certification · {c.get('verdict')}] {claim} by {actor}" + (f" — {note}" if note else ""),
                    "claim": claim, "subject": {"name": c.get("name"), "type": c.get("type")},
                    "evidence": _quote(c.get("evidence"), "grounded", "reason"), "verdict": c.get("verdict"),
                    "by": actor, "note": note, "endorsed": c.get("verdict") == "accept"})
    for c in o.get("conflicts") or []:
        types = c.get("types") or {}
        evs.append({"kind": "conflict", "at": None, "agent": agent,
                    "summary": f"[conflict] {c.get('entity')} is typed {' and '.join(types)} — both evidences kept",
                    "subject": {"name": c.get("entity"), "types": {t: _quote(v, "grounded") for t, v in types.items()}}})
    for f in o.get("flagged_unknown_types") or []:
        name, etype = f.get("name") or "?", f.get("type") or "?"
        evs.append({"kind": "unknown_type", "at": None, "agent": agent,
                    "summary": f"[unknown type] {name} typed {etype} — not in the TBox, kept out of the ABox ({f.get('doc', '?')})",
                    "claim": grounding.entity_claim(name, etype), "subject": {"name": name, "type": etype},
                    "evidence": _quote({"quote": f.get("evidence", ""), "doc": f.get("doc", "?")})})
    for f in o.get("flagged_ungrounded") or []:
        evs.append({"kind": "ungrounded_clash", "at": None, "agent": agent,
                    "summary": f"[ungrounded clash] {f.get('entity')} is typed {f.get('existing_type')}, challenged as "
                               f"{f.get('asserted_type')} with a quote that does not ground it — kept, not a conflict",
                    "subject": {"name": f.get("entity"), "existing_type": f.get("existing_type"),
                                "asserted_type": f.get("asserted_type")},
                    "evidence": _quote(f.get("evidence"))})
    out = []
    for i, e in enumerate(evs):
        full = {"schema": SCHEMA, "seq": i, **head, **e, "endorsed": e.get("endorsed")}
        full["id"] = _id(full)
        out.append({"schema": SCHEMA, "id": full["id"], "seq": i,
                    **{k: v for k, v in full.items() if k not in ("schema", "id", "seq")}})
    return out


def render(events):
    """-> newline-JSON lines (no trailing newline)."""
    return [json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in events]


def tally(events):
    """One line: how many events of each kind, and how many quotes the judge grounded."""
    n = " · ".join(f"{sum(1 for e in events if e['kind'] == k)} {k}" for k in KINDS if any(e["kind"] == k for e in events))
    a = [e for e in events if e["kind"] == "assertion"]
    return f"{len(events)} event(s): {n}" + (f" — quotes: {sum(1 for e in a if e['endorsed'] is True)}/{len(a)} grounded" if a else "")
