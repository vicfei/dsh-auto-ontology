#!/usr/bin/env python3
"""eval_evidence — the honest precision metric (issue #15, O4)

One number anyone can rerun: sample N assertions from an ontology
(deterministically, seed+ontology), and for each ask a model — given ONLY the
evidence quote and the source doc name — whether the quote supports the
assertion. precision = supported / sampled. This measures the plugin's core
claim ("every assertion carries supporting evidence"), not a leaderboard: no
enterprise stack, no hidden test set — the artifact under test is the file you
point at, the sampling is seeded, the model and settings print with the result.

Usage:
  python3 scripts/eval_evidence.py --from ontologies/x.json [--n 20] [--seed 42]
  auto-ontology eval --from ontologies/x.json          # via the npm bin
"""
import argparse, glob, json, os, random, re, subprocess, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.environ.get("ONTOLOGY_HOME") or os.path.join(KIT, "ontologies")


def sample_assertions(o, n, seed):
    """Deterministic sample across entities and relations — pure, CI-tested."""
    def first_ev(x):  # v2 evidences list, or the v1 single-evidence field
        if x.get("evidences"):
            return x["evidences"][0]
        if x.get("evidence"):
            return {"quote": x["evidence"], "doc": x.get("doc", "?")}
        return {}
    pool = []
    for e in o.get("abox", {}).get("entities", []):
        ev = first_ev(e)
        pool.append({"kind": "entity", "assertion": f"{e['name']} is of type '{e['type']}'",
                     "quote": ev.get("quote", ""), "doc": ev.get("doc", "?")})
    for r in o.get("abox", {}).get("relations", []):
        ev = first_ev(r)
        pool.append({"kind": "relation",
                     "assertion": f"{r['subject']} --{r['predicate']}--> {r['object']}",
                     "quote": ev.get("quote", ""), "doc": ev.get("doc", "?")})
    pool = [p for p in pool if p["quote"]]
    rng = random.Random(seed)
    return (rng.sample(pool, n) if len(pool) >= n else pool), len(pool)


def judge(sample):
    """One call: does the quote alone support the assertion? yes/no + reason."""
    key = subprocess.run(["bash", "-c", 'grep -m1 "^export DEEPSEEK_API_KEY=" ~/.bashrc | cut -d= -f2'],
                         capture_output=True, text=True).stdout.strip().strip('"')
    body = {"model": "deepseek-chat", "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content":
                 'You audit ontology assertions. Given ONLY an evidence quote and the assertion it '
                 'allegedly supports, output JSON {"supported": true|false, "reason": "<=20 words"}. '
                 'Be strict: paraphrase is fine, but if the quote does not actually contain the fact '
                 'asserted, it is not supported. Do not use outside knowledge.'},
                {"role": "user", "content":
                 f"Assertion: {sample['assertion']}\nEvidence quote (from doc {sample['doc']}): "
                 f"\"{sample['quote']}\""}]}
    r = subprocess.run(["curl", "-s", "-m", "120", "https://api.deepseek.com/chat/completions",
                        "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json",
                        "-d", json.dumps(body)], capture_output=True, text=True)
    out = json.loads(r.stdout)["choices"][0]["message"]["content"]
    return json.loads(re.sub(r"^```(json)?|```$", "", out.strip(), flags=re.M).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default=None)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    path = args.frm or max(glob.glob(os.path.join(OUTDIR, "*.json")), key=os.path.getmtime)
    o = json.load(open(path))
    samples, pool = sample_assertions(o, args.n, args.seed)
    if not samples:
        sys.exit("no evidenced assertions to sample")
    ok, rows = 0, []
    for s in samples:
        v = judge(s)
        ok += bool(v.get("supported"))
        rows.append((s, v))
    precision = ok / len(samples)
    print(f"# evidence-support precision · {path}")
    print(f"sampled {len(samples)}/{pool} evidenced assertions · seed {args.seed} · deepseek-chat · temp 0\n")
    for s, v in rows:
        mark = "✓" if v.get("supported") else "✗"
        print(f"{mark} [{s['kind']}] {s['assertion']}")
        print(f'   quote: "{s["quote"]}" ({s["doc"]}) — {v.get("reason", "")}')
    print(f"\nprecision = {ok}/{len(samples)} = {precision:.0%}")
    print("rerun: same artifact + same seed → same sample (judge temperature is 0). "
          "This measures quote-support of the file you point at — not a leaderboard.")


if __name__ == "__main__":
    main()
