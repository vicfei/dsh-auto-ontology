#!/usr/bin/env python3
"""compare_builds — the same documents read as files and as chunks of a knowledge base.

Usage: python3 eval/kb-round/compare_builds.py FILE_BUILD.json KB_BUILD.json

Prints what each build made of the same documents and where the difference sits:
the entities both builds have by name and how each grounded them; of the names the
chunk build left ungrounded, how the file build typed them; the types of the
entities only one build has. The two builds do NOT share a TBox — each drew its
own from its own sample — so this is a description, not a controlled comparison.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
import build_ontology as M


def quotes(o):
    return [e for x in o["abox"]["entities"] for e in x["evidences"]] + [e for r in o["abox"]["relations"] for e in r["evidences"]]


def headline(tag, o, label):
    q = quotes(o)
    ent, rel = o["abox"]["entities"], o["abox"]["relations"]
    p = o["provenance"]
    print(f"{tag} — {label}")
    src = p.get("kb", {}).get("chunks") or p.get("docs_this_run")
    merge = " — a merge, the documents of earlier runs are in the artifact but not in this count" if p.get("merged_from") else ""
    print(f"  source      {src} chunk(s)/document(s) read this run{merge} · "
          f"{len(o['tbox']['entity_types'])} entity types · {len(o['tbox']['relation_types'])} relation types")
    print(f"  assertions  {len(ent)} entities · {len(rel)} relations")
    print(f"  grounded    entities {sum(1 for x in ent if x.get('type_grounding') is True)}/{len(ent)} · "
          f"relations {sum(1 for r in rel if r.get('grounding') is True)}/{len(rel)}")
    print(f"  evidence    {len(q)} quotes · {sum(1 for e in q if e.get('grounded') is True)} grounded "
          f"({100 * sum(1 for e in q if e.get('grounded') is True) // max(1, len(q))}%) · "
          f"{len({e.get('chunk_id') for e in q if e.get('chunk_id')})} distinct chunk(s) cited")
    print(f"  cost this run {p.get('calls')} calls · {p.get('tokens_in')} in / {p.get('tokens_out')} out tokens · {p.get('elapsed_s')} s · "
          f"judge {p.get('judge_model')}")


def main():
    fb, kb = (json.load(open(p)) for p in sys.argv[1:3])
    headline("FILE BUILD", fb, sys.argv[1])
    headline("KB BUILD", kb, sys.argv[2])
    fbe = {M._key(x["name"]): x for x in fb["abox"]["entities"]}
    kbe = {M._key(x["name"]): x for x in kb["abox"]["entities"]}
    both, fonly, konly = set(fbe) & set(kbe), set(fbe) - set(kbe), set(kbe) - set(fbe)
    print("\nBY NAME")
    print(f"  in both builds {len(both)} · only in the file build {len(fonly)} · only in the chunk build {len(konly)}")
    cell = collections.Counter((bool(kbe[k].get("type_grounding")), bool(fbe[k].get("type_grounding"))) for k in both)
    print(f"  of the {len(both)} shared names: grounded in both {cell[(True, True)]} · file only {cell[(False, True)]} · "
          f"chunk only {cell[(True, False)]} · neither {cell[(False, False)]}")
    lost = [k for k in both if fbe[k].get("type_grounding") is True and kbe[k].get("type_grounding") is False]
    typ = collections.Counter(fbe[k]["type"] for k in lost)
    print(f"  the {len(lost)} names grounded by the file build but not by the chunk build were typed there: {dict(typ)}")
    ktypes = {t["name"] for t in kb["tbox"]["entity_types"]}
    print(f"  of those types, absent from the chunk build's TBox: {sorted(t for t in typ if t not in ktypes)}")
    print(f"  of the {len(fonly)} file-only entities, {sum(1 for k in fonly if fbe[k].get('type_grounding') is True)} are grounded; by type: "
          f"{dict(collections.Counter(fbe[k]['type'] for k in fonly if fbe[k].get('type_grounding') is True).most_common())}")
    print(f"  chunk-only entities ({len(konly)}): " + ", ".join(f"{kbe[k]['name']} ({kbe[k]['type']})" for k in sorted(konly, key=lambda k: kbe[k]['name'].lower())))
    un = [x for x in kb["abox"]["entities"] if x.get("type_grounding") is False]
    plug = [x for x in un if "plugin" in (x["evidences"][0].get("reason") or "").lower()]
    print(f"\n  {len(un)} chunk-build entities are ungrounded; for {len(plug)} of them the judge's first reason speaks of "
          f"\"plugin\" — typed dsh_plugin because the TBox had no closer type, and the quote says something else")
    print("\nNOT CONTROLLED: different TBox (each build sampled its own), different extraction calls (a whole document's "
          "opening against one chunk), the same judge model. A same-TBox comparison has not been run.")


if __name__ == "__main__":
    main()
