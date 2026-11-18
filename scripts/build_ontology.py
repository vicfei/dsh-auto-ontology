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
"""
import argparse, datetime as dt, glob, json, math, os, re, subprocess, sys, time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Output language: English by default (international-first), --lang zh / ONTOLOGY_LANG for Chinese
LANG = os.environ.get("ONTOLOGY_LANG") or "en"
def tt(en, zh):
    return en if LANG == "en" else zh

# npm CLI form lands artifacts in the caller's cwd via ONTOLOGY_HOME (repo default unchanged)
OUTDIR = os.environ.get("ONTOLOGY_HOME") or os.path.join(KIT, "ontologies")

COST = {"calls": 0, "in": 0, "out": 0}
MAX_CALLS = None


def _key(s):
    """Name-matching key: case/punctuation-insensitive."""
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def llm(sysmsg, user, json_out=True):
    if MAX_CALLS is not None and COST["calls"] >= MAX_CALLS:
        raise SystemExit(f"cost guard: {MAX_CALLS} LLM calls reached (--max-calls)")
    key = subprocess.run(["bash", "-c", 'grep -m1 "^export DEEPSEEK_API_KEY=" ~/.bashrc | cut -d= -f2'],
                         capture_output=True, text=True).stdout.strip().strip('"')
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}]}
    if json_out:
        body["response_format"] = {"type": "json_object"}
    r = subprocess.run(["curl", "-s", "-m", "180", "https://api.deepseek.com/chat/completions",
                        "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json",
                        "-d", json.dumps(body)], capture_output=True, text=True)
    parsed = json.loads(r.stdout)
    txt = parsed["choices"][0]["message"]["content"]
    COST["calls"] += 1
    u = parsed.get("usage") or {}
    COST["in"] += int(u.get("prompt_tokens") or 0)
    COST["out"] += int(u.get("completion_tokens") or 0)
    return json.loads(re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip()) if json_out else txt


# ── the fold store (pure; unit-tested in CI) ────────────────────────────────

def new_store(domain):
    return {"domain": domain, "entities": {}, "relations": {}, "conflicts": [],
            "flagged": [], "tbox_types": set(), "tbox_relations": {}, "merge_log": [],
            "certifications": {}, "suppressed": 0}


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
    for r in o.get("abox", {}).get("relations", []):
        evs = r.get("evidences") or [{"quote": r.get("evidence", ""), "doc": r.get("doc", "?")}]
        docs = set(r.get("docs", [])) | ({r["doc"]} if r.get("doc") and r["doc"] != "?" else set())
        k = (_key(r["subject"]), r["predicate"], _key(r["object"]))
        st["relations"][k] = {"subject": r["subject"], "predicate": r["predicate"], "object": r["object"],
                              "docs": sorted(docs), "evidences": []}
        for ev in evs:
            _fold_ev(st["relations"][k]["evidences"], ev)
    st["conflicts"] = list(o.get("conflicts", []))
    st["flagged"] = list(o.get("flagged_unknown_types", []))
    st["merge_log"] = list(o.get("merge_log", []))
    st["certifications"] = dict(o.get("certifications", {}))
    st["suppressed"] = 0
    return st

def certify(o, name, verdict, note=""):
    """Human verdict on an entity (issue #13, the upstream Learn pillar,
    evidence-first version): record travels WITH the ontology (portable artifact).
    rejected — the (name, type) pair is suppressed in every later fold; the
    original evidence stays in the certification record for audit. A different
    type re-asserting the same name is a NEW assertion and re-enters (the
    rejection was about that typing, not the string).
    accepted  — the entity is marked trusted; conflicts against it still get
    recorded (they are never silently resolved), the mark is the human word."""
    st = load_store(o)
    k = _key(name)
    e = st["entities"].get(k)
    if e is None:
        raise SystemExit(tt(f"no such entity: {name}", f"无此实体：{name}"))
    o.setdefault("certifications", {})[k] = {
        "name": e["name"], "type": e["type"], "verdict": verdict, "at":
        dt.datetime.now().isoformat(timespec="seconds"), "note": note,
        "evidence": e["evidences"][0] if e["evidences"] else {}}
    if verdict == "reject":
        del st["entities"][k]
        st["relations"] = {rk: r for rk, r in st["relations"].items()
                           if _key(r["subject"]) != k and _key(r["object"]) != k}
        o["abox"] = {"entities": sorted(st["entities"].values(), key=lambda x: x["name"].lower()),
                     "relations": sorted(st["relations"].values(),
                                         key=lambda r: (r["subject"].lower(), r["predicate"]))}
        o["stats"]["entities"] = len(st["entities"])
        o["stats"]["relations"] = len(st["relations"])
    return o


def _fold_ev(evs, ev):
    if isinstance(ev, str):
        ev = {"quote": ev, "doc": "?"}
    q, d = ev.get("quote", ""), ev.get("doc", "?")
    if q and not any(e["quote"] == q for e in evs):
        evs.append({"quote": q, "doc": d})


def fold_entity(st, name, etype, quote, doc):
    """Append-only entity fold; the same name under a different type => conflict
    holding BOTH evidences — recorded, never silently resolved. A rejected
    certification suppresses the (name, type) pair — counted, never re-asserted."""
    k = _key(name)
    if not k:
        return
    cert = st.get("certifications", {}).get(k)
    if cert and cert.get("verdict") == "reject" and cert.get("type") == etype:
        st["suppressed"] = st.get("suppressed", 0) + 1
        return
    cur = st["entities"].get(k)
    if cur is None:
        st["entities"][k] = {"name": name, "type": etype, "aliases": [],
                             "docs": [doc] if doc != "?" else [],
                             "evidences": [{"quote": quote, "doc": doc}]}
        return
    if cur["type"] != etype:
        st["conflicts"].append({"entity": cur["name"], "types": {
            cur["type"]: cur["evidences"][0] if cur["evidences"] else {"quote": "", "doc": "?"},
            etype: {"quote": quote, "doc": doc}}})
        return
    _fold_ev(cur["evidences"], {"quote": quote, "doc": doc})
    if doc != "?":
        cur["docs"] = sorted(set(cur["docs"]) | {doc})


def fold_relation(st, subject, predicate, obj, quote, doc, alias_map=None):
    if alias_map:  # canonicalize endpoints through the coref result before folding
        subject = alias_map.get(_key(subject), subject)
        obj = alias_map.get(_key(obj), obj)
    if not (subject and predicate and obj):
        return
    k = (_key(subject), predicate, _key(obj))
    cur = st["relations"].get(k)
    if cur is None:
        st["relations"][k] = {"subject": subject, "predicate": predicate, "object": obj,
                              "docs": [doc] if doc != "?" else [],
                              "evidences": [{"quote": quote, "doc": doc}]}
        return
    _fold_ev(cur["evidences"], {"quote": quote, "doc": doc})
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
         f"{prov.get('elapsed_s', '?')}s · built {o.get('built_at', '?')}", ""]
    if o.get("conflicts"):
        L += ["## Conflicts (both evidences kept, awaiting review)", "",
              "| Entity | Types | Evidence A | Evidence B |", "|---|---|---|---|"]
        for c in o["conflicts"][:20]:
            t1, t2 = list(c["types"].items())[:2]
            L.append(f"| {c['entity']} | {t1[0]} / {t2[0]} | "
                     f"\"{t1[1].get('quote', '')[:50]}\" ({t1[1].get('doc', '?')}) | "
                     f"\"{t2[1].get('quote', '')[:50]}\" ({t2[1].get('doc', '?')}) |")
        L.append("")
    by_type = defaultdict(list)
    for e in o.get("abox", {}).get("entities", []):
        by_type[e["type"]].append(e)
    L.append("## Entities")
    for t, es in sorted(by_type.items()):
        L.append(f"\n### {t} ({len(es)})")
        for e in es[:40]:
            al = f" · aka {', '.join(e['aliases'])}" if e.get("aliases") else ""
            ev = e["evidences"][0]["quote"] if e.get("evidences") else ""
            L.append(f"- **{e['name']}**{al} — \"{ev[:70]}\" ({', '.join(e.get('docs', [])[:3])})")
    L += ["", "## Relations", "", "| Subject | Predicate | Object | Evidence |", "|---|---|---|---|"]
    for r in o.get("abox", {}).get("relations", [])[:200]:
        ev = r["evidences"][0]["quote"] if r.get("evidences") else ""
        L.append(f"| {r['subject']} | {r['predicate']} | {r['object']} | \"{ev[:50]}\" |")
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
        graph.append({"@id": eid(e["name"]), "@type": e["type"], "name": e["name"],
                      "aliases": e.get("aliases", []), "evidence": e.get("evidences", [])})
    for r in o.get("abox", {}).get("relations", []):
        graph.append({"@id": rid(r), "@type": r["predicate"],
                      "subject": {"@id": eid(r["subject"]), "name": r["subject"]},
                      "object": {"@id": eid(r["object"]), "name": r["object"]},
                      "evidence": r.get("evidences", [])})
    return {"@context": ctx, "@graph": graph,
            "dshao:domain": o.get("domain"), "dshao:built_at": o.get("built_at")}


def store_to_ontology(st, new_type_descs, provenance):
    ents = sorted(st["entities"].values(), key=lambda e: e["name"].lower())
    rels = sorted(st["relations"].values(), key=lambda r: (r["subject"].lower(), r["predicate"]))
    return {
        "domain": st["domain"], "built_at": dt.datetime.now().isoformat(timespec="seconds"),
        "provenance": provenance,
        "tbox": {"entity_types": [{"name": t, "desc": new_type_descs.get(t, "")}
                                   for t in sorted(st["tbox_types"])],
                 "relation_types": list(st["tbox_relations"].values())},
        "abox": {"entities": ents, "relations": rels},
        "conflicts": st["conflicts"],
        "flagged_unknown_types": st["flagged"],
        "merge_log": st["merge_log"],
        "certifications": st.get("certifications", {}),
        "stats": {"entities": len(ents), "relations": len(rels),
                  "conflicts": len(st["conflicts"]), "flagged": len(st["flagged"]),
                  "suppressed_by_certification": st.get("suppressed", 0)},
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
P_ABOX = {
    "en": ("You are an ontology instance extractor. From the document, extract entity and relation instances (ABox) based on the given TBox. "
           "Discipline: every instance must carry evidence=a verbatim quote from the document (<=40 chars); types must come from the TBox; "
           "when unsure, do not extract. Output JSON: "
           '{"entities":[{"name":"...","type":"...","evidence":"..."}],'
           '"relations":[{"subject":"...","predicate":"...","object":"...","evidence":"..."}]}'),
    "zh": ("你是本体实例抽取器。基于给定 TBox 从文档抽取实体与关系实例（ABox）。"
           "**纪律**：每条实例必须附 evidence=文档原文引文（不超过40字）；类型必须取自 TBox；"
           "不确定的不抽。输出 JSON："
           '{"entities":[{"name":"...","type":"...","evidence":"..."}],'
           '"relations":[{"subject":"...","predicate":"...","object":"...","evidence":"..."}]}'),
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


def build(docs, domain, base=None, sample=4):
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

    per_doc = []
    for d in docs:
        out = llm(P_ABOX[LANG],
                  tt(f"TBox:\n{json.dumps(tbox, ensure_ascii=False)}\n\nDocument ({d['path']}):\n{d['text']}",
                     f"TBox：{json.dumps(tbox, ensure_ascii=False)}\n\n文档（{d['path']}）：\n{d['text']}"))
        per_doc.append((d, out))
        for e in out.get("entities", []):
            if not e.get("name"):
                continue
            if e.get("type") in known:
                fold_entity(st, e["name"], e["type"], e.get("evidence", ""), d["path"])
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
            fold_relation(st, r.get("subject"), r.get("predicate"), r.get("object"),
                          r.get("evidence", ""), d["path"], alias_map=alias_map)
    return st, new_type_descs, merged_aliases


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
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="860" height="700" font-family="monospace">',
           f'<text x="10" y="16" font-size="13">{domain} · {len(ents)} entities / {len(rels)} relations</text>']
    nm = {n[0]: (n[1], n[2]) for n in nodes}
    for r in rels:
        if r["subject"][:14] in nm and r["object"][:14] in nm:
            x1, y1 = nm[r["subject"][:14]]
            x2, y2 = nm[r["object"][:14]]
            svg.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#99a" stroke-width="0.7"/>')
    for name, x, y, c in nodes:
        svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{c}"/>'
                   f'<text x="{x + 6:.0f}" y="{y + 3:.0f}" font-size="9" fill="#345">{name}</text>')
    svg.append("</svg>")
    open(path, "w").write("".join(svg))


def main():
    global LANG, MAX_CALLS
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=None, help="directory or glob, e.g. '~/dsh-*/README.md'")
    ap.add_argument("--domain", default=None, help="corpus domain description (schema pass)")
    ap.add_argument("--merge", default=None, help="existing ontology JSON to fold into (append-only)")
    ap.add_argument("--query", default=None, help="query mode: every assertion about X, with evidence")
    ap.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"),
                    help="diff two ontology artifacts at evidence granularity")
    ap.add_argument("--certify", default=None, metavar="NAME",
                    help="certification mode: --certify NAME --verdict accept|reject [--note ...] [--from x.json]")
    ap.add_argument("--verdict", choices=("accept", "reject"), default=None, help="verdict for --certify")
    ap.add_argument("--note", default="", help="optional note recorded with a certification")
    ap.add_argument("--jsonld", action="store_true", help="export the ontology as JSON-LD 1.1 (with --from, or the newest artifact)")
    ap.add_argument("--html", action="store_true", help="render the ontology as a single-file HTML digest (with --save, or --from standalone)")
    ap.add_argument("--from", dest="frm", default=None, help="ontology file for --query (default: newest in outdir)")
    ap.add_argument("--sample", type=int, default=4, help="docs sampled for the TBox schema pass")
    ap.add_argument("--max-calls", type=int, default=None, help="cost guard: abort beyond this many LLM calls")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--lang", choices=("en", "zh"), default=LANG, help="output language (default en)")
    args = ap.parse_args()
    LANG = args.lang
    MAX_CALLS = args.max_calls
    t0 = time.time()

    if args.diff:
        a, b = (json.load(open(p)) for p in args.diff)
        print(render_diff(diff_ontologies(a, b)))
        return

    if args.certify:
        if not args.verdict:
            sys.exit("--certify needs --verdict accept|reject")
        path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
        o = certify(json.load(open(path)), args.certify, args.verdict, note=args.note)
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
        hits = query_ontology(json.load(open(path)), args.query)
        print(f"# {args.query} — {path}")
        for e in hits["entities"]:
            print(f"\n[{e['type']}] {e['name']}" +
                  (f" (aliases: {', '.join(e['aliases'])})" if e.get("aliases") else ""))
            for ev in e.get("evidences", []):
                print(f'  | {ev["doc"]}: "{ev["quote"]}"')
        for r in hits["relations"]:
            print(f"\n({r['subject']}) -[{r['predicate']}]-> ({r['object']})")
            for ev in r.get("evidences", []):
                print(f'  | {ev["doc"]}: "{ev["quote"]}"')
        if not hits["entities"] and not hits["relations"]:
            print(tt("no assertions matched", "无匹配断言"))
        return

    if not args.docs or not args.domain:
        sys.exit(tt("--docs and --domain are required for a build", "构建需要 --docs 与 --domain"))
    paths = sorted(glob.glob(os.path.expanduser(args.docs))) if "*" in args.docs else \
        sorted(glob.glob(os.path.join(args.docs, "*")))
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

    st, new_type_descs, corefed = build(docs, args.domain, base=base, sample=max(1, args.sample))
    if corefed:
        st["merge_log"].append({"ran_at": dt.datetime.now().isoformat(timespec="seconds"),
                                "coref_merges": corefed})
    if prior_stats:
        st["merge_log"][-1] if st["merge_log"] else st["merge_log"].append({})
        st["merge_log"][-1].update({"merged_into": args.merge,
                                    "added_docs": len(docs),
                                    "entities_before": prior_stats["entities"],
                                    "entities_after": len(st["entities"])})
    prov = {"model": "deepseek-chat", "temperature": 0, "elapsed_s": round(time.time() - t0),
            "calls": COST["calls"], "tokens_in": COST["in"], "tokens_out": COST["out"],
            "docs_this_run": len(docs), "merged_from": bool(args.merge)}
    o = store_to_ontology(st, new_type_descs, prov)

    print(f"\n## Ontology build · {args.domain}\n")
    print(tt(f"- Entity types {len(o['tbox']['entity_types'])} · entities {o['stats']['entities']} · "
             f"relations {o['stats']['relations']} · conflicts {o['stats']['conflicts']} · "
             f"unknown types flagged {o['stats']['flagged']}",
             f"- 实体类型 {len(o['tbox']['entity_types'])} · 实体 {o['stats']['entities']} · "
             f"关系 {o['stats']['relations']} · 冲突 {o['stats']['conflicts']} · "
             f"未知类型拦截 {o['stats']['flagged']}"))
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
        open(base_path + ".md", "w").write(tt(
            f"# Ontology · {args.domain}\n\nEntities {o['stats']['entities']} · relations {o['stats']['relations']} · "
            f"conflicts {o['stats']['conflicts']} · unknown types flagged {o['stats']['flagged']}.\n"
            f"Evidence lives in the JSON; provenance: {prov['calls']} calls, {prov['elapsed_s']}s.\n",
            f"# 本体 · {args.domain}\n\n实体 {o['stats']['entities']} · 关系 {o['stats']['relations']} · "
            f"冲突 {o['stats']['conflicts']} · 未知类型拦截 {o['stats']['flagged']}。\n"
            f"证据随 JSON；溯源：{prov['calls']} 次调用，{prov['elapsed_s']}s。\n"))
        print(f"\n→ {base_path}.json / .svg / .md", file=sys.stderr)


if __name__ == "__main__":
    main()
