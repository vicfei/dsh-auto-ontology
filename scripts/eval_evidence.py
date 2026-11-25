#!/usr/bin/env python3
"""eval_evidence — the honest precision metric (O4 issue #15; type-grounding view since O5.0 #35)

One number anyone can rerun: sample assertions from an ontology (deterministically,
seed + artifact), and for each ask a strict judge — given ONLY the evidence quote,
the TBox type definition and the source document's name — whether the quote grounds
the assertion. precision = supported / sampled.

Three layers print together, so the LLM number is never read alone:

  judge        the strict type-grounding verdict (scripts/grounding.py — the SAME
               judge the build's grounding pass uses)
  mechanical   no LLM: name-in-quote / endpoint-in-quote / verbatim rates over the
               whole artifact. Deterministic; anyone can recompute them.
  calibration  when the artifact carries type_grounding flags: support rate per flag

A build that ran the grounding judge is being graded here by that same judge — a
consistency check, not an independent validation. --judge-model re-judges with a
different model; that is the independent audit.

This measures the plugin's core claim ("every assertion carries supporting
evidence"), not a leaderboard: the artifact under test is the file you point at,
the sampling is seeded, the model and settings print with the result, and the
number ships as measured.

Usage:
  python3 scripts/eval_evidence.py --from ontologies/x.json [--n 20] [--seed 42] [--jobs 4]
  python3 scripts/eval_evidence.py --from ontologies/x.json --n 0              # whole population
  python3 scripts/eval_evidence.py --from x.json --judge-model deepseek-reasoner --out rows.jsonl
  python3 scripts/eval_evidence.py --from x.json --corpus '~/*/README.md'  # verbatim check
  python3 scripts/eval_evidence.py --adversarial                              # labelled traps
  auto-ontology eval ...                                                     # via the npm bin
"""
import argparse, concurrent.futures as cf, glob, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grounding as G

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.environ.get("ONTOLOGY_HOME") or os.path.join(KIT, "ontologies")
CASES = os.path.join(KIT, "scripts", "adversarial_cases.json")


def type_descs(o):
    types = {t["name"]: t.get("desc", "") for t in o.get("tbox", {}).get("entity_types", [])}
    preds = {r.get("name"): r.get("desc", "") for r in o.get("tbox", {}).get("relation_types", [])}
    return types, preds


def _first_ev(x):
    """v2 evidences list, or the v1 single-evidence field."""
    if x.get("evidences"):
        return x["evidences"][0]
    if x.get("evidence"):
        return {"quote": x["evidence"], "doc": x.get("doc", "?")}
    return {}


def sample_assertions(o, n, seed):
    """Deterministic sample across entities and relations — pure, CI-tested. The unit is an
    assertion with its FIRST evidence quote. n = 0 returns the whole population."""
    types, preds = type_descs(o)
    pool = []
    for e in o.get("abox", {}).get("entities", []):
        ev = _first_ev(e)
        pool.append({"kind": "entity", "assertion": f"{e['name']} is of type '{e['type']}'",
                     "quote": ev.get("quote", ""), "doc": ev.get("doc", "?"),
                     "name": e["name"], "type": e["type"], "type_desc": types.get(e["type"], ""),
                     "evidences": [dict(x) for x in (e.get("evidences") or ([ev] if ev else []))],
                     "flag": e.get("type_grounding")})
    for r in o.get("abox", {}).get("relations", []):
        ev = _first_ev(r)
        pool.append({"kind": "relation",
                     "assertion": f"{r['subject']} --{r['predicate']}--> {r['object']}",
                     "quote": ev.get("quote", ""), "doc": ev.get("doc", "?"),
                     "subject": r["subject"], "predicate": r["predicate"], "object": r["object"],
                     "type": r["predicate"], "type_desc": preds.get(r["predicate"], ""),
                     "evidences": [dict(x) for x in (r.get("evidences") or ([ev] if ev else []))],
                     "flag": r.get("grounding")})
    pool = [p for p in pool if p["quote"]]
    if not n:
        return pool, len(pool)
    rng = random.Random(seed)
    return (rng.sample(pool, n) if len(pool) >= n else pool), len(pool)


def mechanical(s):
    """The no-LLM verdict on the sampled quote. A reject filter: True never means grounded."""
    if s["kind"] == "entity":
        return {"name_in_quote": G.name_in_quote(s["name"], s["quote"])}
    a, b = G.endpoints_in_quote(s["subject"], s["object"], s["quote"])
    return {"one_endpoint": a or b, "both_endpoints": a and b}


def _item(s, quote, doc):
    return {"kind": s["kind"], "type_name": s["type"], "type_desc": s.get("type_desc", ""),
            "claim": (G.entity_claim(s["name"], s["type"]) if s["kind"] == "entity"
                      else G.relation_claim(s["subject"], s["predicate"], s["object"])),
            "quote": quote, "doc": doc}


def judge_sample(s, model, evidence="first"):
    """-> {supported, reason, quote, tried}. evidence='first' judges the first quote only
    (the O4 unit); 'any' walks the carried quotes in order and stops at the first grounded
    one. A judge call that keeps failing is reported as supported=None — never silently
    counted as a miss."""
    evs = s["evidences"][:1] if evidence == "first" else s["evidences"]
    reason, tried = "", 0
    for ev in evs:
        q = ev.get("quote", "")
        if not q:
            continue
        tried += 1
        try:
            v = G.judge([_item(s, q, ev.get("doc", "?"))], model)[0]
        except SystemExit as exc:
            return {"supported": None, "reason": f"judge error: {exc}", "quote": q, "tried": tried}
        if v["grounded"]:
            return {"supported": True, "reason": v["reason"], "quote": q, "tried": tried}
        reason = v["reason"]
    return {"supported": False, "reason": reason, "quote": s["quote"], "tried": tried}


# ── no-LLM rates over the whole artifact ────────────────────────────────────

def mechanical_rates(o):
    ents = [e for e in o.get("abox", {}).get("entities", []) if _first_ev(e).get("quote")]
    rels = [r for r in o.get("abox", {}).get("relations", []) if _first_ev(r).get("quote")]
    return {"entities": {"n": len(ents),
                         "name_in_quote": sum(G.name_in_quote(e["name"], _first_ev(e)["quote"]) for e in ents)},
            "relations": {"n": len(rels),
                          "one_endpoint": sum(any(G.endpoints_in_quote(r["subject"], r["object"], _first_ev(r)["quote"]))
                                              for r in rels),
                          "both_endpoints": sum(all(G.endpoints_in_quote(r["subject"], r["object"], _first_ev(r)["quote"]))
                                               for r in rels)}}


def corpus_texts(pattern):
    """--corpus GLOB: the * stands for the evidence doc name ('~/*/README.md' — the
    doc name is the full directory name, prefix included); a directory maps doc
    name -> file in it. -> callable(doc) -> text | None."""
    cache = {}

    def text_for(doc):
        if doc not in cache:
            p = pattern.replace("*", doc) if "*" in pattern else os.path.join(pattern, doc)
            p = os.path.expanduser(p)
            cache[doc] = open(p, errors="ignore").read() if os.path.isfile(p) else None
        return cache[doc]
    return text_for


# ── adversarial set ─────────────────────────────────────────────────────────

def load_cases(path=CASES):
    return json.load(open(path, encoding="utf-8"))["cases"]


def case_item(c):
    if c["kind"] == "entity":
        return {"kind": "entity", "type_name": c["type"], "type_desc": c.get("type_desc", ""),
                "claim": G.entity_claim(c["name"], c["type"]), "quote": c["quote"], "doc": c.get("doc", "?")}
    return {"kind": "relation", "type_name": c["predicate"], "type_desc": c.get("type_desc", ""),
            "claim": G.relation_claim(c["subject"], c["predicate"], c["object"]),
            "quote": c["quote"], "doc": c.get("doc", "?")}


def case_mechanical(c):
    if c["kind"] == "entity":
        return {"name_in_quote": G.name_in_quote(c["name"], c["quote"])}
    a, b = G.endpoints_in_quote(c["subject"], c["object"], c["quote"])
    return {"one_endpoint": a or b, "both_endpoints": a and b}


def run_adversarial(model, jobs, path=CASES):
    """One judge call per case. `mechanical` carries the no-LLM checks as information:
    a case may well be grounded without spelling the name (an extractor-coined label
    under the document's own wording), so the checks never decide a case."""
    cases = load_cases(path)
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        verdicts = list(ex.map(lambda c: G.judge([case_item(c)], model)[0], cases))
    rows = []
    for c, v in zip(cases, verdicts):
        rows.append({"id": c["id"], "kind": c["kind"], "claim": case_item(c)["claim"], "quote": c["quote"],
                     "expected": "grounded" if c["grounded"] else "ungrounded",
                     "got": "grounded" if v["grounded"] else "ungrounded",
                     "ok": v["grounded"] == c["grounded"], "reason": v["reason"],
                     "mechanical": case_mechanical(c)})
    return rows


def render_adversarial(rows, model):
    traps = [r for r in rows if r["expected"] == "ungrounded"]
    trues = [r for r in rows if r["expected"] == "grounded"]
    ok = sum(r["ok"] for r in rows)
    L = [f"# adversarial set · {os.path.relpath(CASES, KIT)} · {len(rows)} cases "
         f"({len(traps)} must-reject, {len(trues)} must-accept)",
         f"judge {model} · temp 0", "",
         f"accuracy = {ok}/{len(rows)} = {ok / len(rows):.0%}   "
         f"traps rejected {sum(r['ok'] for r in traps)}/{len(traps)} · "
         f"true grounding accepted {sum(r['ok'] for r in trues)}/{len(trues)}", ""]
    misses = [r for r in rows if not r["ok"]]
    L.append("MISSES" if misses else "no misses")
    for r in misses:
        L += [f"✗ [{r['id']}] expected {r['expected']}, judged {r['got']}",
              f'   {r["kind"]}: {r["claim"]}  quote: "{r["quote"]}"', f'   reason: {r["reason"]}']
    L += ["", "The judge prompt is the one the build's grounding pass uses (scripts/grounding.py). "
          "The gold labels were written by hand before any judge ran (one case keeps the shape of a real "
          "failure with its names replaced); misses ship as-is."]
    return "\n".join(L)


# ── report ──────────────────────────────────────────────────────────────────

def _pct(k, n):
    return f"{k}/{n} = {k / n:.0%}" if n else "0/0"


def _weak(by_rate, limit=6):
    weak = sorted(((k, v) for k, v in by_rate.items() if v[1] >= 3), key=lambda kv: kv[1][0] / kv[1][1])
    weak = [kv for kv in weak if kv[1][0] / kv[1][1] < 0.5][:limit]
    return " · ".join(f"{t} {a}/{b}" for t, (a, b) in weak) or "none"


def built_judge(o):
    """The judge a build ran with, as the artifact records it (None = never judged)."""
    prov = o.get("provenance") or {}
    return prov.get("judge_model") or (prov.get("model") if prov.get("grounding_pass") else None)


def render(rows, path, pool, args, rates, verb, built=None):
    judged = [r for r in rows if r["supported"] is not None]
    failed = len(rows) - len(judged)
    ok = sum(r["supported"] for r in judged)
    n = len(judged)
    L = [f"# evidence-support precision · {path}",
         f"sampled {len(rows)}/{pool} evidenced assertions"
         + (" (whole population)" if not args.n else f" · seed {args.seed}")
         + f" · evidence: {'first quote' if args.evidence == 'first' else 'any carried quote'}",
         f"judge {args.judge_model} · temp 0 · jobs {args.jobs}", "",
         "## LLM judge (strict type-grounding)",
         f"precision = {_pct(ok, n)}" + (f"   [judge failures excluded: {failed}]" if failed else ""), ""]
    for kind in ("entity", "relation"):
        ks = [r for r in judged if r["kind"] == kind]
        if ks:
            L.append(f"   {kind:<9} {_pct(sum(r['supported'] for r in ks), len(ks))}")
    for kind, label in (("entity", "entity types"), ("relation", "predicates")):
        by = {}
        for r in judged:
            if r["kind"] == kind:
                a, b = by.get(r["type"], (0, 0))
                by[r["type"]] = (a + bool(r["supported"]), b + 1)
        if by:
            L.append(f"   weakest {label} (<50%, n>=3): {_weak(by)}")
    L += ["", "## Mechanical (no LLM, whole artifact)",
          f"   entities: name-in-quote {_pct(rates['entities']['name_in_quote'], rates['entities']['n'])}",
          f"   relations: >=1 endpoint in quote "
          f"{_pct(rates['relations']['one_endpoint'], rates['relations']['n'])} · both endpoints "
          f"{_pct(rates['relations']['both_endpoints'], rates['relations']['n'])}"]
    if verb:
        found, good = sum(v is not None for v in verb.values()), sum(v is True for v in verb.values())
        L.append(f"   verbatim: {_pct(good, found)} of {len(verb)} quotes "
                 f"({len(verb) - found} source files not resolved)")
    flags = {}
    for r in judged:
        if r["flag"] is not None:
            a, b = flags.get(r["flag"], (0, 0))
            flags[r["flag"]] = (a + bool(r["supported"]), b + 1)
    if flags:
        L += ["", "## Grounding-flag calibration (judged at build time)"]
        for f in sorted(flags, key=lambda x: x is not True):
            a, b = flags[f]
            L.append(f"   {('type_grounding=' + str(f).lower()):<22} {_pct(a, b)}")
        L.append(f"   build judge: {built or 'not recorded'}")
        same = args.judge_model == built
        L += ["   NOTE: " + ("same judge model as the build — a consistency check, not independent "
                             "validation. Re-judge with --judge-model <other model>."
                             if same else "different judge model from the build — an independent audit.")]
    L += ["", "## Rows"]
    for r in rows:
        mark = {True: "✓", False: "✗", None: "?"}[r["supported"]]
        fl = "" if r["flag"] is None else f"  (type_grounding={str(r['flag']).lower()})"
        L.append(f'{mark} [{r["kind"]}] {r["assertion"]}{fl}')
        vb = verb.get(r["assertion"])
        L.append(f'   quote: "{r["quote"][:160]}" ({r["doc"]}) — {r["reason"].strip()}'
                 + ("" if vb is None else "  · verbatim" if vb else "  · NOT verbatim"))
    L += ["", "rerun: same artifact + same seed → same sample (judge temperature is 0). "
          "This measures quote-support of the file you point at — not a leaderboard; "
          "the number ships as measured."]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default=None)
    ap.add_argument("--n", type=int, default=20, help="sample size; 0 = every evidenced assertion (default 20)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--jobs", type=int, default=4, help="parallel judge calls (default 4)")
    ap.add_argument("--evidence", choices=("first", "any"), default="first",
                    help="first: judge the first quote only (default); any: any quote the assertion carries")
    ap.add_argument("--judge-model", default="deepseek-chat",
                    help="a different model is the only independent audit of a build's own verdicts")
    ap.add_argument("--corpus", default=None,
                    help="GLOB with a * standing for the evidence doc name (verbatim check), or a directory")
    ap.add_argument("--out", default=None, help="write one JSON row per judged assertion (audit trail)")
    ap.add_argument("--adversarial", action="store_true",
                    help="run the labelled trap set instead of sampling an artifact")
    args = ap.parse_args()

    if args.adversarial:
        rows = run_adversarial(args.judge_model, args.jobs)
        print(render_adversarial(rows, args.judge_model))
        if args.out:
            _dump(args.out, rows)
            print(f"\nrows -> {args.out}")
        return

    newest = sorted(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
    path = args.frm or (newest[-1] if newest else sys.exit(f"no ontology artifact in {OUTDIR} — pass --from"))
    o = json.load(open(path))
    samples, pool = sample_assertions(o, args.n, args.seed)
    if not samples:
        sys.exit("no evidenced assertions to sample")
    text_for = corpus_texts(args.corpus) if args.corpus else None
    verb = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        rows = list(ex.map(lambda s: judge_sample(s, args.judge_model, args.evidence), samples))
    for s, r in zip(samples, rows):
        r.update({k: s[k] for k in ("kind", "assertion", "doc", "flag", "type")})
        r["mechanical"] = mechanical(s)
        if text_for:
            t = text_for(s["doc"])
            verb[s["assertion"]] = G.is_verbatim(r["quote"], t) if t is not None else None
    print(render(rows, path, pool, args, mechanical_rates(o), verb, built=built_judge(o)))
    if args.out:
        _dump(args.out, [dict(r, verbatim=verb.get(r["assertion"])) for r in rows])
        print(f"\nrows -> {args.out}")


def _dump(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
