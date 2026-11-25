#!/usr/bin/env python3
"""verify_kb_round — does a knowledge-base build's evidence really resolve into the base?

For every evidence an artifact carries (entities, relations, conflicts, the type
guard's catches, ungrounded clashes, certifications): the chunk its `chunk_id`
names exists, sits in the knowledge base the build says it read, belongs to the
document the evidence names (title == doc), and CONTAINS the quote.

Two independent readings of the chunk text:

  api   GET /api/v1/chunks/by-id/{id} — what an application sees
  sql   the `chunks` table through `docker exec psql` — what is stored (--sql)

A quote counts as contained when grounding.is_verbatim finds it in the chunk
(markdown marks and whitespace ignored) — the build's own gate. The strict count
(raw substring) is reported beside it and is expected to be lower: a quote may
span lines or drop a backtick.

Verdicts: a GROUNDED evidence must be contained — the verbatim gate guarantees
it. An ungrounded one is contained too, unless the build rejected it precisely
for not being verbatim (its reason says so): that quote is in no chunk, by
construction. Anything else is a failure and the exit status is 1.

Usage:
  python3 eval/kb-round/verify_kb_round.py ARTIFACT.json [--sql] [--json OUT.json]
  env WEKNORA_URL / WEKNORA_API_KEY [/ WEKNORA_TENANT_ID]; --sql needs the docker daemon
"""
import argparse, collections, json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import grounding

SQL = ("SELECT coalesce(json_agg(row_to_json(t)), '[]'::json) FROM (SELECT c.id, c.knowledge_base_id, "
       "c.knowledge_id, c.chunk_index, c.chunk_type, c.is_enabled, c.deleted_at IS NOT NULL AS deleted, "
       "k.title, c.content FROM chunks c LEFT JOIN knowledges k ON k.id = c.knowledge_id "
       "WHERE c.id = ANY(ARRAY[%s]::varchar[])) t")
NOT_VERBATIM = "quote is not verbatim in the source document"   # what the build's gate writes


def evidences(o):
    """(where, evidence) for every quote the artifact carries. A flagged record keeps its
    quote flattened (`evidence` is the string); the type guard's is typed like the rest."""
    for e in o["abox"]["entities"]:
        for ev in e["evidences"]:
            yield f"entity:{e['name']}", ev
    for r in o["abox"]["relations"]:
        for ev in r["evidences"]:
            yield f"relation:{r['subject']} {r['predicate']} {r['object']}", ev
    for c in o.get("conflicts") or []:
        for t, ev in (c.get("types") or {}).items():
            yield f"conflict:{c['entity']}:{t}", ev
    for f in o.get("flagged_unknown_types") or []:
        yield f"unknown_type:{f['name']}", {"quote": f.get("evidence"), "doc": f.get("doc"), "chunk_id": f.get("chunk_id")}
    for f in o.get("flagged_ungrounded") or []:
        yield f"ungrounded_clash:{f['entity']}", f.get("evidence") or {}
    for c in (o.get("certifications") or {}).values():
        yield f"certification:{c['name']}", c.get("evidence") or {}
        if c.get("retyped_to"):
            yield f"retyped_to:{c['name']}", c["retyped_to"]


def api_chunks(ids, titles):
    hdr = {"X-API-Key": os.environ["WEKNORA_API_KEY"]}
    if os.environ.get("WEKNORA_TENANT_ID"):
        hdr["X-Tenant-ID"] = os.environ["WEKNORA_TENANT_ID"]
    out = {}
    for i in ids:
        req = urllib.request.Request(f"{os.environ['WEKNORA_URL'].rstrip('/')}/api/v1/chunks/by-id/{i}", headers=hdr)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                c = json.load(r)["data"]
        except Exception as exc:                      # a missing chunk is a finding, not a crash
            out[i] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        out[i] = {"knowledge_base_id": c.get("knowledge_base_id"), "title": titles.get(c.get("knowledge_id")),
                  "chunk_index": c.get("chunk_index"), "chunk_type": c.get("chunk_type"), "is_enabled": c.get("is_enabled"),
                  "deleted": bool(c.get("deleted_at")), "content": c.get("content") or ""}
    return out


def sql_chunks(ids):
    if not all(re.fullmatch(r"[0-9a-fA-F-]{36}", i) for i in ids):
        sys.exit("sql: every chunk id must be a uuid")
    r = subprocess.run(["docker", "exec", "-i", "WeKnora-postgres-dev", "psql", "-U", "postgres", "-d", "WeKnora", "-At"],
                       input=SQL % ",".join(f"'{i}'" for i in ids), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"sql failed: {r.stderr.strip()[:300]}")
    return {c["id"]: c for c in json.loads(r.stdout)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--sql", action="store_true", help="also read the chunks from Postgres (docker exec)")
    ap.add_argument("--json", dest="out", help="write the full finding list here")
    a = ap.parse_args()
    o = json.load(open(a.artifact))
    kb = (o.get("provenance") or {}).get("kb") or {}
    if not kb:
        sys.exit("the artifact's provenance has no kb block: not a knowledge-base build")
    evs = [(w, ev) for w, ev in evidences(o)]
    ids = sorted({ev.get("chunk_id") for _, ev in evs if ev.get("chunk_id")})
    hdr = {"X-API-Key": os.environ["WEKNORA_API_KEY"]}
    if os.environ.get("WEKNORA_TENANT_ID"):
        hdr["X-Tenant-ID"] = os.environ["WEKNORA_TENANT_ID"]
    titles, page = {}, 1
    while True:                                       # one page of 100 at a time: the list endpoint defaults to 20
        req = urllib.request.Request(f"{os.environ['WEKNORA_URL'].rstrip('/')}/api/v1/knowledge-bases/{kb['id']}/knowledge"
                                     f"?page={page}&page_size=100", headers=hdr)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        rows = d.get("data") or []
        titles |= {k["id"]: k.get("title") for k in rows}
        if len(rows) < 100 or page * 100 >= int(d.get("total") or 0):
            break
        page += 1
    readers = [("api", api_chunks(ids, titles))]
    if a.sql:
        readers.append(("sql", sql_chunks(ids)))
    findings, bad = [], 0
    for w, ev in evs:
        cid, quote = ev.get("chunk_id"), ev.get("quote") or ""
        f = {"where": w, "doc": ev.get("doc"), "chunk_id": cid, "grounded": ev.get("grounded"), "quote": quote}
        if not cid:
            f["problem"] = "no chunk_id"
        for name, chunks in readers:
            c = chunks.get(cid)
            if not c:
                f[name] = "chunk not found"
            elif "error" in c:
                f[name] = c["error"]
            else:
                norm = grounding.is_verbatim(quote, c["content"])
                strict = bool(quote) and quote in c["content"]
                f[name] = {"in_kb": c.get("knowledge_base_id") == kb["id"], "title_is_doc": c.get("title") == ev.get("doc"),
                           "text_chunk": c.get("chunk_type") in (None, "text"), "enabled": c.get("is_enabled") is not False,
                           "deleted": c.get("deleted"), "contained": norm, "strictly": strict}
        failed = [name for name in ("api", "sql") if name in f and
                  (not isinstance(f[name], dict) or not all(f[name][k] for k in ("in_kb", "title_is_doc", "text_chunk", "enabled"))
                   or f[name]["deleted"])]
        contained = isinstance(f.get("api"), dict) and f["api"]["contained"]
        gate_rejected = ev.get("grounded") is False and ev.get("reason") == NOT_VERBATIM
        if ev.get("grounded") is True and not contained:
            failed.append("a grounded quote is not in its chunk")
        if not gate_rejected and not contained and "api" in f and isinstance(f["api"], dict):
            failed.append("quote not in its chunk")
        if failed:
            f["FAILED"] = failed
            bad += 1
        findings.append(f)
    n = len(findings)
    gate = sum(1 for _, ev in evs if ev.get("grounded") is False and ev.get("reason") == NOT_VERBATIM)
    print(f"artifact: {a.artifact}")
    print(f"knowledge base: {kb['id']} — the build read {kb['chunks']} chunk(s) of {kb['documents']} document(s); "
          f"{len(ids)} distinct chunk id(s) are cited by {n} evidence record(s)")
    print(f"evidence with a chunk_id: {sum(1 for f in findings if f['chunk_id'])}/{n} · "
          f"grounded {sum(1 for _, ev in evs if ev.get('grounded') is True)} · "
          f"ungrounded {sum(1 for _, ev in evs if ev.get('grounded') is False)} · never judged "
          f"{sum(1 for _, ev in evs if ev.get('grounded') is None)}")
    for name, _ in readers:
        got = [f[name] for f in findings if isinstance(f.get(name), dict)]
        print(f"{name}: chunk found {len(got)}/{n} · in this knowledge base {sum(1 for c in got if c['in_kb'])} · "
              f"title is the evidence's doc {sum(1 for c in got if c['title_is_doc'])} · text and enabled "
              f"{sum(1 for c in got if c['text_chunk'] and c['enabled'] and not c['deleted'])}")
        print(f"{' ' * len(name)}  quote contained (verbatim form) {sum(1 for c in got if c['contained'])}/{len(got)} · "
              f"raw substring {sum(1 for c in got if c['strictly'])}/{len(got)}")
    print(f"the build's verbatim gate rejected {gate} quote(s) as not in their chunk — expected to be absent there")
    print(f"FAILED evidence records: {bad}")
    if a.out:
        json.dump({"artifact": a.artifact, "kb": kb, "evidence_records": n, "distinct_chunk_ids": len(ids),
                   "failed": bad, "findings": findings}, open(a.out, "w"), ensure_ascii=False, indent=1)
        print(f"findings written to {a.out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
