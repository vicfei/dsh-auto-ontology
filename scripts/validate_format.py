#!/usr/bin/env python3
"""validate_format — evidence-linked ontology v0.2 conformance (issue #16).

Pure stdlib checks of the normative clauses in docs/FORMAT.md. Exit 1 with the
violation list when any check fails; quiet success otherwise. v0.2 is
backward-compatible: every addition is optional, so a v0.1 artifact validates.
"""
import json, sys

VERSION = "v0.2"


def _derived(evs):
    """The grounding flag an assertion's evidences imply (FORMAT clause 5)."""
    if any(isinstance(e, dict) and e.get("grounded") is True for e in evs):
        return True
    if evs and all(isinstance(e, dict) and e.get("grounded") is False for e in evs):
        return False
    return None


def _v02(x, key, label):
    """Optional v0.2 fields on one assertion: the flag, its evidences' verdicts,
    and the consistency between the two. A flag on an assertion whose evidences
    imply none (nothing judged, or judged and unjudged mixed without a grounded
    quote) is a contradiction too."""
    v, flag = [], x.get(key)
    if key in x and not isinstance(flag, bool):
        v.append(f"{label}: {key} must be a boolean (clause 5)")
    evs = x.get("evidences") or []
    for ev in evs:
        if not isinstance(ev, dict):
            continue
        if "grounded" in ev and not isinstance(ev["grounded"], bool):
            v.append(f"{label}: evidence grounded must be a boolean (clause 4)")
        if "reason" in ev and not isinstance(ev["reason"], str):
            v.append(f"{label}: evidence reason must be a string (clause 4)")
    if key in x and evs and flag != _derived(evs):
        v.append(f"{label}: {key}={str(flag).lower()} contradicts its evidences "
                 f"(they imply {str(_derived(evs)).lower()}) (clause 5)")
    return v


def validate(o):
    v = []
    for k in ("domain", "built_at", "tbox", "abox", "stats", "provenance"):
        if k not in o:
            v.append(f"missing top-level key: {k}")
    if "provenance" in o and not isinstance(o["provenance"], dict):
        v.append("provenance must be an object (clause 1)")
    tbox_types = {t.get("name") for t in o.get("tbox", {}).get("entity_types", [])}
    abox = o.get("abox", {})
    ents = abox.get("entities", [])
    rels = abox.get("relations", [])
    if not ents and not rels:
        v.append("abox has no entities and no relations")
    for e in ents:
        n = e.get("name")
        if not n:
            v.append("entity without a name")
            continue
        if e.get("type") not in tbox_types:
            v.append(f"entity {n!r}: type {e.get('type')!r} not in tbox")
        evs = e.get("evidences") or []
        if not evs or not any(isinstance(x, dict) and x.get("quote") for x in evs):
            v.append(f"entity {n!r}: no evidence quote (contract clause 2)")
        for x in evs:
            if not x.get("quote") or not x.get("doc"):
                v.append(f"entity {n!r}: malformed evidence {x!r}")
        v += _v02(e, "type_grounding", f"entity {n!r}")
    for r in rels:
        if not (r.get("subject") and r.get("predicate") and r.get("object")):
            v.append(f"relation missing endpoint/predicate: {r!r}")
            continue
        label = f"relation {r['subject']}-{r['predicate']}->{r['object']}"
        evs = r.get("evidences") or []
        if not evs or not any(isinstance(x, dict) and x.get("quote") for x in evs):
            v.append(f"{label}: no evidence quote (clause 3)")
        v += _v02(r, "grounding", label)
    for c in o.get("conflicts", []):
        if len(c.get("types", {})) < 2:
            v.append(f"conflict on {c.get('entity')!r} carries fewer than two typed sides (clause 7)")
    for c in o.get("flagged_ungrounded", []):
        if not (isinstance(c, dict) and c.get("entity") and c.get("asserted_type")
                and isinstance(c.get("evidence"), dict) and c["evidence"].get("quote")):
            v.append(f"malformed ungrounded type clash: {c!r} (clause 6)")
    for k, c in o.get("certifications", {}).items():
        if c.get("verdict") not in ("accept", "reject"):
            v.append(f"certification {k!r}: verdict must be accept|reject (clause 8)")
        if "actor" in c and not isinstance(c["actor"], str):
            v.append(f"certification {k!r}: actor must be a string (clause 8)")
        if "retyped_to" in c and not (c.get("verdict") == "reject" and isinstance(c["retyped_to"], dict)
                                      and all(isinstance(c["retyped_to"].get(f), str) for f in ("type", "quote", "doc"))):
            v.append(f"certification {k!r}: retyped_to is {{type, quote, doc}} on a reject (clause 8)")
        if "also_rejects" in c and not (c.get("verdict") == "reject" and isinstance(c["also_rejects"], list)
                                        and all(isinstance(t, str) for t in c["also_rejects"])):
            v.append(f"certification {k!r}: also_rejects is a list of type names on a reject (clause 8)")
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
            print(f"✓ {p} conforms to evidence-linked ontology {VERSION}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
