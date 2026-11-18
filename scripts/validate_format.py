#!/usr/bin/env python3
"""validate_format — evidence-linked ontology v0.1 conformance (issue #16).

Pure stdlib checks of the normative clauses in docs/FORMAT.md. Exit 1 with the
violation list when any check fails; quiet success otherwise.
"""
import json, re, sys


def validate(o):
    v = []
    for k in ("domain", "built_at", "tbox", "abox", "stats"):
        if k not in o:
            v.append(f"missing top-level key: {k}")
    tbox_types = {t.get("name") for t in o.get("tbox", {}).get("entity_types", [])}
    abox = o.get("abox", {})
    ents = abox.get("entities", [])
    rels = abox.get("relations", [])
    if not ents and not rels:
        v.append("abox has no entities and no relations")
    names = set()
    for e in ents:
        n = e.get("name")
        if not n:
            v.append("entity without a name")
            continue
        names.add(n)
        if e.get("type") not in tbox_types:
            v.append(f"entity {n!r}: type {e.get('type')!r} not in tbox")
        evs = e.get("evidences") or []
        if not evs or not any(x.get("quote") for x in evs):
            v.append(f"entity {n!r}: no evidence quote (contract clause 2)")
        for x in evs:
            if not x.get("quote") or not x.get("doc"):
                v.append(f"entity {n!r}: malformed evidence {x!r}")
    for r in rels:
        if not (r.get("subject") and r.get("predicate") and r.get("object")):
            v.append(f"relation missing endpoint/predicate: {r!r}")
            continue
        evs = r.get("evidences") or []
        if not evs or not any(x.get("quote") for x in evs):
            v.append(f"relation {r['subject']}-{r['predicate']}->{r['object']}: no evidence quote (clause 3)")
    for c in o.get("conflicts", []):
        if len(c.get("types", {})) < 2:
            v.append(f"conflict on {c.get('entity')!r} carries fewer than two typed sides (clause 4)")
    for k, c in o.get("certifications", {}).items():
        if c.get("verdict") not in ("accept", "reject"):
            v.append(f"certification {k!r}: verdict must be accept|reject (clause 5)")
    return v


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: validate_format.py <ontology.json> [...]")
    bad = 0
    for p in sys.argv[1:]:
        try:
            v = validate(json.load(open(p)))
        except Exception as exc:
            print(f"✗ {p}: unreadable ({exc})")
            bad += 1
            continue
        if v:
            bad += 1
            print(f"✗ {p}:")
            for x in v[:10]:
                print(f"  - {x}")
        else:
            print(f"✓ {p} conforms to evidence-linked ontology v0.1")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
