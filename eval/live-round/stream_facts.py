#!/usr/bin/env python3
"""stream_facts — what the two exported rounds of the live round contain, and how they differ.

Usage: python3 eval/live-round/stream_facts.py
Prints the kinds in each stream, the events round 2 adds and retires, and the
event ids that changed between the v0.2-engine export of round 2 (18:52) and its
v0.3 re-export (19:38) — a named judge changes an assertion's id, and a re-issued
certification gets a new timestamp and so a new id.
"""
import collections, json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, "stream", name)) as f:
        return [json.loads(line) for line in f if line.strip()]


def kinds(events):
    return " · ".join(f"{n} {k}" for k, n in sorted(collections.Counter(e["kind"] for e in events).items(),
                                                   key=lambda kv: ["build", "fold", "assertion", "certification"].index(kv[0])))


def show(e):
    claim = e.get("claim")
    who = claim.get("name") if isinstance(claim, dict) else claim
    return f"{e['kind']} · {who} · by {e.get('by')} · at {e.get('at')}"


def main():
    r1, r2, r2_old = load("round1.ndjson"), load("round2.ndjson"), load("round2-v02-engine.ndjson")
    for tag, ev in (("round1 (the input)", r1), ("round2, v0.3 engine (19:38)", r2), ("round2, v0.2 engine (18:52)", r2_old)):
        print(f"{tag}: {len(ev)} event(s) — {kinds(ev)}")
        if tag.startswith("round1"):
            for e in ev:
                if e["kind"] in ("build", "certification"):
                    print(f"   {e['kind']}: {e['summary'][:150]}")
    by = {e["id"]: e for e in r1 + r2 + r2_old}
    i1, i2, i2o = ({e["id"] for e in ev} for ev in (r1, r2, r2_old))
    print(f"\nround 2 against round 1 (v0.3 ids): +{len(i2 - i1)} event(s), -{len(i1 - i2)} event(s)")
    for i in sorted(i2 - i1):
        print(f"   added   {show(by[i])}")
    for i in sorted(i1 - i2):
        print(f"   retired {show(by[i])}")
    print(f"\nv0.3 export against v0.2-engine export of the same round 2: {len(i2 - i2o)} id(s) differ on each side")
    old_claims = {json.dumps(by[i].get("claim"), sort_keys=True): i for i in i2o - i2}
    for i in sorted(i2 - i2o):
        print(f"   v0.3 {show(by[i])}")
    for i in sorted(i2o - i2):
        print(f"   v0.2 {show(by[i])}")
    def g(ev):
        return sum(1 for e in ev if e["kind"] == "assertion" and e.get("verdict") == "grounded")
    print(f"\nassertions exported as grounded: round 1 {g(r1)}/370 · round 2 {g(r2)}/370 (the same 370 claims; the re-typed one was ungrounded before)")
    print("who an assertion's verdict is attributed to, round 2: " +
          " · ".join(f"{by_} {n}" for by_, n in collections.Counter(e.get("by") for e in r2 if e["kind"] == "assertion").items()))
    for e in r2:
        if e["kind"] == "assertion" and isinstance(e.get("subject"), dict) and e["subject"].get("name") == "OAR":
            print(f"\nthe re-typed Term as round 2 exports it:\n  claim    {e['claim']}\n  verdict  {e['verdict']}\n  by       {e['by']}"
                  f"\n  reason   {e['reason']}\n  evidence {json.dumps(e['evidence'], ensure_ascii=False)[:160]}…")
    for e in r1:
        if e["kind"] == "assertion" and isinstance(e.get("subject"), dict) and e["subject"].get("name") == "OAR":
            print(f"\nthe same Term as round 1 exports it:\n  claim    {e['claim']}\n  verdict  {e['verdict']}\n  by       {e['by']}"
                  f"\n  evidence {json.dumps(e['evidence'], ensure_ascii=False)[:160]}…")


if __name__ == "__main__":
    main()
