#!/usr/bin/env python3
"""weknora_bridge — ingest an evidence-linked ontology into a WeKnora KB (issue #10, O3)

Family synergy: WeKnora is the family's knowledge store; this bridge turns each
ontology entity into a small manual-knowledge document (name, type, aliases,
evidence quotes with source docs, and its relations) so that KB retrieval — and
anything built on it — is grounded in the same evidence spans the ontology
carries. Grounded in WeKnora = grounded in quotes, not vibes.

Scope discipline (deliberate): the bridge never creates a knowledge base — the
scoped API key used here allows ingest only, and a KB is a person's choice.
Pass an existing --kb id (created with a management key, or by the owner).
Auth follows the family convention: env WEKNORA_URL / WEKNORA_API_KEY /
WEKNORA_TENANT_ID (headers X-API-Key / X-Tenant-ID — the weknora-ops form).

Usage:
  python3 scripts/weknora_bridge.py --from ontologies/x.json --kb <kb-id> [--limit 50] [--dry-run]
"""
import argparse, glob, json, os, sys, urllib.request

OUTDIR = os.environ.get("ONTOLOGY_HOME") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ontologies")


def entity_docs(o, limit=None):
    """Pure: ontology v2 -> [(title, markdown)] per entity, evidence-first.
    Relations touching the entity ride along (with their evidence quotes)."""
    by_name = {}
    for e in o.get("abox", {}).get("entities", []):
        by_name[e["name"]] = e
    rel_by_end = {}
    for r in o.get("abox", {}).get("relations", []):
        rel_by_end.setdefault(r["subject"], []).append(r)
        rel_by_end.setdefault(r["object"], []).append(r)
    docs = []
    for e in o.get("abox", {}).get("entities", []):
        evs = "\n".join(f'- "{v["quote"]}" ({v["doc"]})' + ("  — ungrounded" if v.get("grounded") is False else "")
                        for v in e.get("evidences", [])[:5]) or "- (no evidence)"
        aliases = f"\nAliases: {', '.join(e.get('aliases', []))}." if e.get("aliases") else ""
        flag = e.get("type_grounding")
        # the verdict travels into the KB: a retriever must not read a mention-only lead as a fact
        claim = ("" if flag is None else
                 "\nType claim: grounded — a carried quote states what this entity is.\n" if flag else
                 "\nType claim: NOT grounded — the quotes only mention the entity; its type is an "
                 "unverified lead.\n")
        rels = rel_by_end.get(e["name"], [])
        rel_lines = "\n".join(
            f"- ({r['subject']}) -[{r['predicate']}]-> ({r['object']}) — \"{r['evidences'][0]['quote']}\""
            if r.get("evidences") else f"- ({r['subject']}) -[{r['predicate']}]-> ({r['object']})"
            for r in rels[:8])
        body = (f"# {e['name']} ({e['type']}){aliases}\n\n"
                f"Domain: {o.get('domain', '?')} · type: {e['type']} · "
                f"sources: {', '.join(e.get('docs', [])[:5]) or '?'}\n{claim}\n"
                f"Evidence:\n{evs}\n"
                + (f"\nRelations:\n{rel_lines}\n" if rel_lines else ""))
        docs.append((f"Ontology: {e['name']} ({e['type']})", body))
        if limit and len(docs) >= limit:
            break
    return docs


def ingest(title, text, kb, base, key, tenant):
    body = json.dumps({"title": title, "text": text, "content": text}).encode()
    headers = {"X-API-Key": key, "Content-Type": "application/json"}
    if tenant:
        headers["X-Tenant-ID"] = tenant
    req = urllib.request.Request(f"{base.rstrip('/')}/api/v1/knowledge-bases/{kb}/knowledge/manual",
                                 data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default=None, help="ontology JSON (default: newest artifact)")
    ap.add_argument("--kb", required=True, help="existing WeKnora knowledge-base id (the bridge never creates one)")
    ap.add_argument("--limit", type=int, default=50, help="max entity docs this pass (default 50)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    newest = sorted(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
    path = args.frm or (newest[-1] if newest else sys.exit(f"no ontology artifact in {OUTDIR} — pass --from"))
    o = json.load(open(path))
    docs = entity_docs(o, limit=args.limit)
    print(f"{path} → kb {args.kb}: {len(docs)} entity doc(s)" + (" (dry run)" if args.dry_run else ""))
    if args.dry_run:
        for title, body in docs[:2]:
            print(f"\n--- {title}\n{body[:300]}")
        return
    base = os.environ.get("WEKNORA_URL")
    key = os.environ.get("WEKNORA_API_KEY")
    if not (base and key):
        sys.exit("WEKNORA_URL / WEKNORA_API_KEY not set (family config: ~/.config/weknora-ops/config)")
    tenant = os.environ.get("WEKNORA_TENANT_ID")
    ok = 0
    for title, body in docs:
        try:
            ingest(title, body, args.kb, base, key, tenant)
            ok += 1
        except Exception as exc:
            print(f"✗ {title}: {exc}", file=sys.stderr)
    print(f"ingested {ok}/{len(docs)}")


if __name__ == "__main__":
    main()
